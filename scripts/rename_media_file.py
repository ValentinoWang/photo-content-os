#!/usr/bin/env python3
"""Auto-rename one media file in place after lightweight content analysis."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from media_common import (
    ANALYSIS_DIR,
    MEDIA_EXTS,
    RENAME_PREVIEW_SAMPLING,
    VIDEO_EXTS,
    build_frame_contact_sheet,
    extract_still_frame_preview,
    extract_video_keyframes,
    ffprobe_json,
    media_id,
    now_iso,
    path_inside as inside,
    project_path,
    relative_posix,
)
from project_bootstrap_common import run_project_analysis as run_analysis


LIVE_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".mov", ".xmp"}
RAW_ASSOCIATED_EXTS = {".osv", ".lrf", ".insv"}
IMAGE_EXTS_FOR_PREVIEW = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
GENERIC_NAME_RE = re.compile(r"^(IMG|VID|DJI|GX|GP|PXL|MVIMG|DSC|ScreenRecording|2084|待命名)[_\-\s]?[A-Za-z0-9_]*", re.IGNORECASE)
RAW_STATUS_TOKENS = ("raw", "原始", "待确认", "待命名", "低清", "低质")
LIVE_SUFFIX_RE = re.compile(r"^(?P<base>.+)_LIVE\d{2,}$")


@dataclass(frozen=True)
class ContentDecision:
    stem: str | None
    key: str | None
    reason: str
    confidence: str
    frames: list[Path]
    contact_sheet: Path | None
    flags: list[str]


def resolve_source(project: Path, source_value: str) -> Path:
    source = Path(source_value).expanduser()
    if not source.is_absolute():
        source = project / source
    source = source.resolve()
    if not inside(source, project):
        raise RuntimeError(f"source escapes project_dir: {source}")
    if not source.exists():
        raise FileNotFoundError(f"source file not found: {source}")
    if not source.is_file():
        raise IsADirectoryError(f"source is not a file: {source}")
    if source.suffix.lower() not in MEDIA_EXTS:
        raise RuntimeError(f"source is not a supported media/metadata file: {source.name}")
    return source


def live_group_for(source: Path) -> list[Path]:
    if source.suffix.lower() not in LIVE_EXTS:
        return [source]
    siblings = [
        path
        for path in source.parent.iterdir()
        if path.is_file() and path.stem == source.stem and path.suffix.lower() in LIVE_EXTS
    ]
    has_still = any(path.suffix.lower() in {".heic", ".heif", ".jpg", ".jpeg"} for path in siblings)
    has_motion = any(path.suffix.lower() == ".mov" for path in siblings)
    if has_still and has_motion:
        return sorted(siblings, key=lambda p: (p.suffix.lower(), p.name))
    return [source]


def raw_associated_group_for(source: Path) -> list[Path]:
    if source.suffix.lower() not in RAW_ASSOCIATED_EXTS:
        return [source]
    siblings = [
        path
        for path in source.parent.iterdir()
        if path.is_file() and path.stem == source.stem and path.suffix.lower() in RAW_ASSOCIATED_EXTS
    ]
    return sorted(siblings, key=lambda p: (p.stem, p.suffix.lower(), p.name)) or [source]


def media_group_for(source: Path) -> list[Path]:
    live_group = live_group_for(source)
    if len(live_group) > 1:
        return live_group
    raw_group = raw_associated_group_for(source)
    if len(raw_group) > 1:
        return raw_group
    return [source]


def representative_media(group: list[Path]) -> Path:
    videos = [path for path in group if path.suffix.lower() in VIDEO_EXTS]
    if videos:
        return videos[0]
    images = [path for path in group if path.suffix.lower() in IMAGE_EXTS_FOR_PREVIEW]
    if images:
        return images[0]
    return group[0]


def video_duration(path: Path) -> float:
    info = ffprobe_json(path)
    duration = info.get("format", {}).get("duration")
    if not duration:
        return 0.0
    return float(duration)


def analysis_output_dir(project: Path, source: Path) -> Path:
    rel = relative_posix(source, project)
    output = project / ANALYSIS_DIR / "rename_keyframes" / media_id(rel)
    output.mkdir(parents=True, exist_ok=True)
    for old in output.glob("frame_*.jpg"):
        old.unlink()
    for old in output.glob("contact_sheet.jpg"):
        old.unlink()
    return output


def extract_content_frames(project: Path, source: Path) -> list[Path]:
    if source.suffix.lower() in VIDEO_EXTS:
        output_dir = analysis_output_dir(project, source)
        return extract_video_keyframes(source, output_dir, video_duration(source), RENAME_PREVIEW_SAMPLING)
    if source.suffix.lower() in IMAGE_EXTS_FOR_PREVIEW:
        output_dir = analysis_output_dir(project, source)
        return extract_still_frame_preview(source, output_dir)
    return []


def contact_sheet(project: Path, source: Path, frames: list[Path]) -> Path | None:
    path = project / ANALYSIS_DIR / "rename_keyframes" / media_id(relative_posix(source, project)) / "contact_sheet.jpg"
    return build_frame_contact_sheet(frames, path)


def is_generic_or_status_name(stem: str) -> bool:
    lower = stem.lower()
    return bool(GENERIC_NAME_RE.match(stem)) or any(token in lower or token in stem for token in RAW_STATUS_TOKENS)


def content_decision(project: Path, source: Path, group: list[Path]) -> ContentDecision:
    representative = representative_media(group)
    frames = extract_content_frames(project, representative)
    sheet = contact_sheet(project, representative, frames)

    current_stem = source.stem
    if not is_generic_or_status_name(current_stem):
        return ContentDecision(
            current_stem,
            "existing_descriptive_name",
            "已生成关键帧/联系表；当前文件名不是相机泛名或状态名，保留为描述性命名",
            "existing",
            frames,
            sheet,
            ["evidence_generated"],
        )

    return ContentDecision(
        None,
        None,
        "已生成关键帧/联系表；语义命名需要 LLM 结合项目 prompt 和画面证据判读，请使用 --override-stem 执行",
        "low",
        frames,
        sheet,
        ["needs_llm_judgement"],
    )


def same_existing_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return left.samefile(right)
    except OSError:
        return False


def build_operations(project: Path, group: list[Path], new_stem: str) -> list[tuple[Path, Path]]:
    operations = [(source, source.with_name(f"{new_stem}{source.suffix}")) for source in group]
    target_paths = [target for _, target in operations]
    if len({str(path) for path in target_paths}) != len(target_paths):
        raise RuntimeError("rename plan contains duplicate target paths")

    source_paths = {str(source) for source, _ in operations}
    for source, target in operations:
        if not inside(target, project):
            raise RuntimeError(f"target escapes project_dir: {target}")
        if target.exists() and str(target) not in source_paths and not same_existing_file(source, target):
            raise FileExistsError(f"target already exists: {target}")
    return [(source, target) for source, target in operations if source.name != target.name]


def group_kind(group: list[Path]) -> str:
    if len(group) <= 1:
        return "single"
    suffixes = {path.suffix.lower() for path in group}
    if suffixes & RAW_ASSOCIATED_EXTS:
        return "raw_associated"
    return "live_photo"


def group_scope_label(group: list[Path]) -> str:
    kind = group_kind(group)
    if kind == "raw_associated":
        return "原始关联组"
    if kind == "live_photo":
        return "Live Photo 整组"
    return "单文件"


def safe_stem_for_group(group: list[Path], base_stem: str) -> str:
    if len(group) <= 1:
        return base_stem

    kind = group_kind(group)
    stems = {path.stem for path in group}
    if kind == "live_photo" and len(stems) == 1:
        current_stem = next(iter(stems))
        match = LIVE_SUFFIX_RE.match(current_stem)
        if match and match.group("base") == base_stem:
            return current_stem

    directory = group[0].parent
    group_paths = {path.resolve() for path in group}
    candidate_exts = {path.suffix for path in group}
    if kind == "raw_associated":
        candidates = [base_stem, *(f"{base_stem}_原始组{number:02d}" for number in range(1, 100))]
    else:
        candidates = [f"{base_stem}_LIVE{number:02d}" for number in range(1, 100)]

    for candidate in candidates:
        blocked = False
        for ext in candidate_exts:
            target = (directory / f"{candidate}{ext}").resolve()
            if target.exists() and target not in group_paths:
                blocked = True
                break
        if not blocked:
            return candidate

    suffix = "_原始组" if kind == "raw_associated" else "_LIVE"
    return f"{base_stem}{suffix}_{media_id(base_stem)}"


def live_safe_stem(group: list[Path], base_stem: str) -> str:
    # Backward-compatible wrapper for older callers.
    return safe_stem_for_group(group, base_stem)


def unique_single_stem(source: Path, base_stem: str) -> str:
    if source.stem == base_stem:
        return base_stem
    first = source.with_name(f"{base_stem}{source.suffix}")
    if not first.exists():
        return base_stem
    for number in range(1, 100):
        candidate = f"{base_stem}_补充{number:02d}"
        target = source.with_name(f"{candidate}{source.suffix}")
        if not target.exists():
            return candidate
    return f"{base_stem}_{media_id(source.name)}"


def apply_operations(operations: list[tuple[Path, Path]]) -> None:
    for source, target in operations:
        if target.exists() and same_existing_file(source, target):
            temp = source.with_name(f".rename_tmp_{media_id(source.name)}_{source.name}")
            source.rename(temp)
            temp.rename(target)
        else:
            source.rename(target)


def append_rename_log(project: Path, operations: list[tuple[Path, Path]], decision: ContentDecision, group_mode: bool) -> None:
    log_path = project / "素材整理记录.md"
    lines: list[str] = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 素材整理记录", ""])
    lines.extend(
        [
            f"## 自动重命名记录 {now_iso()}",
            "",
            "| 原位置 | 新位置 | 范围 | 依据 |",
            "| --- | --- | --- | --- |",
        ]
    )
    scope = group_scope_label([source for source, _ in operations]) if group_mode else "单文件"
    for source, target in operations:
        lines.append(f"| {relative_posix(source, project)} | {relative_posix(target, project)} | {scope} | {decision.reason} |")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_rename_plan(project: Path, source: Path, group: list[Path], decision: ContentDecision, operations: list[tuple[Path, Path]]) -> Path:
    output_dir = project / ANALYSIS_DIR / "rename_plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / f"{media_id(relative_posix(source, project))}_rename_plan.json"
    payload = {
        "generated_at": now_iso(),
        "source": relative_posix(source, project),
        "group": [relative_posix(path, project) for path in group],
        "recommended_stem": decision.stem,
        "classification_key": decision.key,
        "reason": decision.reason,
        "confidence": decision.confidence,
        "flags": decision.flags,
        "frames": [relative_posix(frame, project) for frame in decision.frames],
        "contact_sheet": relative_posix(decision.contact_sheet, project) if decision.contact_sheet else None,
        "operations": [
            {"from": relative_posix(source_path, project), "to": relative_posix(target_path, project)}
            for source_path, target_path in operations
        ],
    }
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan_path


def print_plan(project: Path, decision: ContentDecision, operations: list[tuple[Path, Path]], group_mode: bool, plan_path: Path) -> None:
    print("自动重命名拆解结果：")
    print(f"范围：{group_scope_label([source for source, _ in operations]) if group_mode and operations else ('整组' if group_mode else '单文件')}")
    print(f"推荐基名：{decision.stem or '无法可靠生成'}")
    print(f"识别类型：{decision.key or 'unknown'}")
    print(f"置信度：{decision.confidence}")
    print(f"依据：{decision.reason}")
    if decision.contact_sheet:
        print(f"联系表：{decision.contact_sheet}")
    print(f"计划文件：{plan_path}")
    if operations:
        for source, target in operations:
            print(f"{relative_posix(source, project)} -> {relative_posix(target, project)}")
    else:
        print("无需重命名：当前文件名已经等于推荐名称。")


def main() -> None:
    parser = argparse.ArgumentParser(description="为单个素材生成命名证据，并按 LLM/人工给出的基名在项目内安全重命名")
    parser.add_argument("project_dir", help="正式项目目录")
    parser.add_argument("source_path", help="要自动重命名的文件路径，可用项目相对路径或绝对路径")
    parser.add_argument("--single", action="store_true", help="即使命中 Live Photo 同名组，也只改当前文件")
    parser.add_argument("--plan", action="store_true", help="只生成自动重命名计划，不移动文件")
    parser.add_argument("--allow-low-confidence", action="store_true", help="允许低置信度结果执行；默认低置信度会停止")
    parser.add_argument("--override-stem", help="使用 LLM/人工判读给出的推荐基名；脚本只负责整组保护、冲突避让和执行改名")
    parser.add_argument("--override-key", default="llm_override", help="配合 --override-stem 写入计划的分类 key")
    parser.add_argument("--override-reason", default="LLM/人工基于关键帧判读指定名称", help="配合 --override-stem 写入整理记录的依据")
    parser.add_argument("--skip-analysis", action="store_true", help="重命名后不自动重跑 run_analyze_project.sh")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    source = resolve_source(project, args.source_path)
    group = media_group_for(source) if not args.single else [source]
    decision = content_decision(project, source, group)
    if args.override_stem:
        decision = replace(
            decision,
            stem=args.override_stem,
            key=args.override_key,
            reason=args.override_reason,
            confidence="llm",
            flags=sorted(set([*decision.flags, "llm_override"])),
        )
    if decision.stem:
        safe_stem = safe_stem_for_group(group, decision.stem) if len(group) > 1 else unique_single_stem(source, decision.stem)
        decision = replace(decision, stem=safe_stem)
    operations = build_operations(project, group, decision.stem) if decision.stem else []
    plan_path = write_rename_plan(project, source, group, decision, operations)
    print_plan(project, decision, operations, len(group) > 1, plan_path)

    if decision.confidence == "low" and not args.allow_low_confidence:
        raise RuntimeError("low confidence auto-rename blocked; inspect the contact sheet or rename with a stronger content signal")
    if args.plan:
        print("已生成计划；未执行重命名。")
        return
    if not operations:
        print("没有需要执行的重命名。")
        return

    apply_operations(operations)
    append_rename_log(project, operations, decision, len(group) > 1)
    print(f"已自动重命名：{len(operations)} 个文件")
    if not args.skip_analysis:
        run_analysis(project)


if __name__ == "__main__":
    main()
