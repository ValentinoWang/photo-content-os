#!/usr/bin/env python3
"""Plan how a mixed 待增加 folder should merge into a target project."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from media_common import (
    ANALYSIS_DIR,
    IMAGE_EXTS,
    MEDIA_EXTS,
    METADATA_EXTS,
    RENAME_PREVIEW_SAMPLING,
    VIDEO_EXTS,
    build_frame_contact_sheet,
    discover_live_groups,
    ensure_project_additions_dir,
    extract_still_frame_preview,
    extract_video_keyframes,
    is_hidden_or_analysis,
    live_status_for,
    media_dimensions_for_image,
    media_id,
    now_iso,
    project_path,
    relative_posix,
    safe_slug,
    source_type,
    video_info,
)


RAW_TOKENS = ("原始", "录屏", "模糊待选", "待修复", "待防抖", "待降噪", "待转码", "待重构", "半组", "待确认")
GENERIC_NAME_RE = re.compile(r"^(IMG|VID|DJI|GX|GP|PXL|MVIMG|DSC|ScreenRecording)[_\-\s]?[A-Za-z0-9].*", re.IGNORECASE)


def addition_keyframes_dir(additions_dir: Path, record: dict[str, object]) -> Path:
    output_dir = additions_dir / ANALYSIS_DIR / "addition_keyframes" / str(record["media_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("frame_*.jpg"):
        old.unlink()
    return output_dir


def visual_media_classification(path: Path, additions_dir: Path, record: dict[str, object]) -> dict[str, object]:
    if record.get("media_type") not in {"video", "image"}:
        return {"visual_key": None, "visual_reason": None, "frames": [], "contact_sheet": None, "flags": []}

    output_dir = addition_keyframes_dir(additions_dir, record)
    if record.get("media_type") == "video":
        duration = float(record.get("duration_sec") or 0)
        frames = extract_video_keyframes(path, output_dir, duration, RENAME_PREVIEW_SAMPLING)
    else:
        frames = extract_still_frame_preview(path, output_dir)
    sheet = build_frame_contact_sheet(frames, output_dir / "contact_sheet.jpg")
    return {
        "visual_key": None,
        "visual_reason": "已生成关键帧/预览图和联系表；场景语义需由 LLM 结合项目 prompt 判读",
        "frames": frames,
        "contact_sheet": sheet,
        "flags": ["evidence_generated"] if frames else [],
    }


def target_filename_exists(target_project: Path, target_dir: str, filename: str) -> bool:
    return (target_project / target_dir / filename).exists()


def uniquify_filename(target_project: Path, target_dir: str, filename: str, entry_id: str) -> str:
    if not target_filename_exists(target_project, target_dir, filename):
        return filename
    path = Path(filename)
    return f"{path.stem}_{entry_id}{path.suffix}"


def choose_live_stem(
    target_project: Path,
    target_dir: str,
    base_stem: str,
    live_group_id: str,
    live_name_stems: dict[tuple[str, str], str],
) -> str:
    key = (target_dir, live_group_id)
    if key in live_name_stems:
        return live_name_stems[key]
    directory = target_project / target_dir
    candidate_exts = (".HEIC", ".heic", ".HEIF", ".heif", ".JPG", ".jpg", ".JPEG", ".jpeg", ".MOV", ".mov", ".XMP", ".xmp")
    for number in range(1, 100):
        stem = f"{base_stem}_LIVE{number:02d}"
        if not any((directory / f"{stem}{ext}").exists() for ext in candidate_exts):
            live_name_stems[key] = stem
            return stem
    stem = f"{base_stem}_LIVE_{live_group_id}"
    live_name_stems[key] = stem
    return stem


def section_dirs(target_project: Path) -> dict[str, str | None]:
    sections: dict[str, str | None] = {
        "raw": "00_RawVault_不可直用/Raw_待处理",
        "llm_pending": "__LLM待定__",
    }
    return sections


def classify_target(
    text: str,
    ext: str,
    sections: dict[str, str | None],
    visual: dict[str, object],
) -> tuple[str, str, str, str | None]:
    if ext in METADATA_EXTS or any(token in text for token in RAW_TOKENS):
        return str(sections["raw"]), "raw_or_pending", "文件名或格式显示为原始、录屏、待修复、待重构、模糊待选等不可直用素材", None
    return str(sections["llm_pending"]), "needs_llm_review", "非 Raw 增量素材需要 LLM/人工结合项目全局结构判读；脚本不按关键词投放到内容目录", None


def suggested_filename(
    path: Path,
    target_lifecycle: str,
    target_dir: str,
    entry_id: str,
    live_group_id: str | None,
    classification_key: str | None,
    target_project: Path,
    live_name_stems: dict[tuple[str, str], str],
) -> tuple[str, str, bool]:
    name = path.name
    ext = path.suffix
    stem = path.stem
    if GENERIC_NAME_RE.match(name):
        if live_group_id:
            return (
                f"待命名_LIVE_{live_group_id}{ext}",
                "Live Photo 原始组使用同一个待命名 LIVE 基名，保证 HEIC/MOV/XMP 同名不同后缀",
                True,
            )
        if "screenrecording" in name.lower():
            return f"录屏_原始_{entry_id}{ext}", "原始录屏文件名已替换为可复核的录屏原始命名", True
        return f"待命名_{entry_id}{ext}", "原始相机文件名缺少画面信息，需要根据关键帧或人工判断改成人话命名", True
    if target_lifecycle == "needs_llm_review":
        return f"{safe_slug(stem)}_待命名{ext}", "缺少显式场景线索，需要 LLM/人工判读后再确认命名", True
    if target_lifecycle == "raw_or_pending" and not any(token in stem for token in RAW_TOKENS):
        return f"{safe_slug(stem)}_待确认{ext}", "进入 Raw_待处理但原名没有不可直用原因，追加待确认", True
    return name, "沿用已有描述性文件名", False


def media_record(
    path: Path,
    additions_dir: Path,
    live_groups: dict[tuple[str, str], dict[str, bool]],
) -> dict[str, object]:
    ext = path.suffix.lower()
    rel = relative_posix(path, additions_dir)
    stat = path.stat()
    live_status, live_role, live_group_id = live_status_for(path, additions_dir, live_groups)
    if ext in VIDEO_EXTS:
        media_type = "video"
    elif ext in IMAGE_EXTS:
        media_type = "image"
    elif ext in METADATA_EXTS:
        media_type = "metadata"
    else:
        raise AssertionError(f"unexpected media extension: {path}")

    record: dict[str, object] = {
        "media_id": media_id(rel),
        "source_relative_path": rel,
        "source_absolute_path": str(path),
        "filename": path.name,
        "extension": ext,
        "size_mb": round(stat.st_size / 1024 / 1024, 3),
        "media_type": media_type,
        "live_photo_status": live_status,
        "live_photo_role": live_role,
        "live_group_id": live_group_id,
        "duration_sec": None,
        "width": None,
        "height": None,
        "has_audio": None,
        "created_at": None,
        "location_raw": None,
        "gps_latitude": None,
        "gps_longitude": None,
        "gps_altitude": None,
        "gps_horizontal_accuracy": None,
    }
    if media_type == "video":
        record.update(video_info(path))
    elif media_type == "image":
        width, height = media_dimensions_for_image(path)
        record["width"] = width
        record["height"] = height
    record["source_type"] = source_type(path.name, rel, live_status)
    return record


def inherit_live_group_visual(visual: dict[str, object]) -> dict[str, object]:
    inherited = dict(visual)
    inherited["visual_reason"] = f"同组 Live Photo 已生成动态/静态证据：{visual.get('visual_reason')}"
    inherited["flags"] = sorted(set([*list(visual.get("flags", [])), "inherited_live_group_evidence"]))
    return inherited


def build_plan(additions_dir: Path, target_project: Path) -> dict[str, object]:
    sections = section_dirs(target_project)
    candidates = [
        path
        for path in additions_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTS and not is_hidden_or_analysis(path, additions_dir)
    ]
    live_groups = discover_live_groups(candidates, additions_dir)
    prepared: list[tuple[Path, dict[str, object], dict[str, object]]] = []
    live_visuals: dict[str, dict[str, object]] = {}
    for path in sorted(candidates, key=lambda p: relative_posix(p, additions_dir)):
        record = media_record(path, additions_dir, live_groups)
        visual = visual_media_classification(path, additions_dir, record)
        live_group_id = record.get("live_group_id")
        if isinstance(live_group_id, str) and visual.get("visual_key") and live_group_id not in live_visuals:
            live_visuals[live_group_id] = visual
        prepared.append((path, record, visual))

    items: list[dict[str, object]] = []
    live_name_stems: dict[tuple[str, str], str] = {}
    for path, record, visual in prepared:
        live_group_id = record.get("live_group_id")
        if (
            isinstance(live_group_id, str)
            and not visual.get("visual_key")
            and live_group_id in live_visuals
        ):
            visual = inherit_live_group_visual(live_visuals[live_group_id])
        text = f"{record['filename']} {record['source_relative_path']}"
        target_dir, lifecycle, classification_reason, classification_key = classify_target(
            text,
            str(record["extension"]),
            sections,
            visual,
        )
        name, naming_reason, needs_name_review = suggested_filename(
            path,
            lifecycle,
            target_dir,
            str(record["media_id"]),
            live_group_id if isinstance(live_group_id, str) else None,
            classification_key,
            target_project,
            live_name_stems,
        )
        name = uniquify_filename(target_project, target_dir, name, str(record["media_id"]))
        target_relative_path = f"{target_dir}/{name}"
        target_exists = (target_project / target_relative_path).exists()
        unresolved = lifecycle == "needs_llm_review"
        needs_review = bool(needs_name_review or target_exists or lifecycle == "raw_or_pending" and "待确认" in name)
        confidence = "low" if needs_review else "medium"
        record.update(
            {
                "status": "blocked" if unresolved else "pending",
                "target_lifecycle": lifecycle,
                "suggested_target_dir": target_dir,
                "suggested_filename": name,
                "target_relative_path": target_relative_path,
                "classification_key": classification_key,
                "classification_reason": classification_reason,
                "naming_reason": naming_reason,
                "addition_keyframes": [relative_posix(frame, additions_dir) for frame in visual.get("frames", [])],
                "addition_contact_sheet": relative_posix(visual["contact_sheet"], additions_dir)
                if isinstance(visual.get("contact_sheet"), Path)
                else None,
                "visual_flags": visual.get("flags", []),
                "unresolved": unresolved,
                "target_exists": target_exists,
                "needs_review": needs_review,
                "confidence": confidence,
            }
        )
        items.append(record)
    return {
        "plan_version": 1,
        "generated_at": now_iso(),
        "additions_dir": str(additions_dir),
        "target_project_dir": str(target_project),
        "notes": "08 只生成证据和机械合并计划，不移动文件，也不按关键帧颜色硬判语义；确认后再用 09_apply_additions_merge.py 执行。",
        "items": items,
    }


def llm_review_prompt(plan: dict[str, object]) -> str:
    lines = [
        "# 待增加素材 LLM 合并判读任务",
        "",
        "你是素材库整理助理。请根据项目语境、文件元数据、关键帧目录和联系表，给出宏观语义判断。",
        "",
        "## 项目信息",
        "",
        f"- 待增加目录：{plan['additions_dir']}",
        f"- 目标项目：{plan['target_project_dir']}",
        "",
        "## 判读原则",
        "",
        "1. 不要按颜色、单个关键词或脚本启发式硬猜；要结合项目主题、前后素材、关键帧和文件名整体判断。",
        "2. 能确认的条目，把 `additions_merge_plan.json` 中的 `status` 改为 `approved`，并填写准确的 `target_relative_path`。",
        "3. 不能确认的条目保持 `blocked` 或 `needs_review=true`，不要强行放入 Raw。",
        "4. Live Photo 或原始关联组必须保持同名不同后缀；不要把同组素材拆成不同语义。",
        "5. 命名只说画面内容和处理状态，不把“精选”“高光”写进 L3 项目归档文件名。",
        "",
        "## 待判读素材",
        "",
    ]
    for item in plan["items"]:
        lines.extend(
            [
                f"### {item['source_relative_path']}",
                "",
                f"- media_id：{item['media_id']}",
                f"- 类型：{item['media_type']} / {item['source_type']}",
                f"- 时长：{item.get('duration_sec')}",
                f"- 分辨率：{item.get('width')} x {item.get('height')}",
                f"- Live Photo：{item.get('live_photo_status')} / {item.get('live_photo_role')}",
                f"- 当前建议：{item.get('target_relative_path')}",
                f"- 当前状态：{item.get('status')}，需复核：{item.get('needs_review')}",
                f"- 依据：{item.get('classification_reason')}",
                f"- 联系表：{item.get('addition_contact_sheet') or '无'}",
                f"- 关键帧：{', '.join(item.get('addition_keyframes') or []) or '无'}",
                "",
            ]
        )
    return "\n".join(lines)


def write_plan(plan: dict[str, object], additions_dir: Path) -> tuple[Path, Path, Path]:
    output_dir = additions_dir / ANALYSIS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "additions_merge_plan.json"
    md_path = output_dir / "additions_merge_plan.md"
    prompt_path = output_dir / "additions_llm_review_prompt.md"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt_path.write_text(llm_review_prompt(plan), encoding="utf-8")

    lines = [
        "# 待增加素材合并计划",
        "",
        f"- 生成时间：{plan['generated_at']}",
        f"- 待增加目录：{plan['additions_dir']}",
        f"- 目标项目：{plan['target_project_dir']}",
        f"- 素材数量：{len(plan['items'])}",
        "",
        "## 使用方式",
        "",
        "1. 先检查下表中的目标目录、建议命名和是否需复核；泛名素材请优先看 `additions_llm_review_prompt.md` 和联系表。",
        "2. 需要调整时，编辑 `additions_merge_plan.json` 中对应条目的 `target_relative_path`、`suggested_filename`、`classification_reason` 或 `status`。",
        "3. 确认后把要执行的条目设为 `approved`，或在明确确认整表无误后使用 `09_apply_additions_merge.py --apply-all-pending`。",
        "",
    ]
    if plan["items"]:
        lines.extend(
            [
                "## 合并明细",
                "",
                "| 状态 | 源文件 | 建议目标 | 生命周期 | 需复核 | 依据 |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in plan["items"]:
            lines.append(
                "| {status} | {source} | {target} | {lifecycle} | {review} | {reason} |".format(
                    status=item["status"],
                    source=item["source_relative_path"],
                    target=item["target_relative_path"],
                    lifecycle=item["target_lifecycle"],
                    review="是" if item["needs_review"] else "否",
                    reason=item["classification_reason"],
                )
            )
    else:
        lines.extend(["## 合并明细", "", "没有发现可合并的媒体文件。"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, prompt_path


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描待增加目录，生成合并到目标项目的分类与命名计划")
    parser.add_argument("additions_dir", help="待增加素材目录")
    parser.add_argument("target_project_dir", help="目标正式项目目录")
    args = parser.parse_args()

    additions_dir = project_path(args.additions_dir)
    target_project = project_path(args.target_project_dir)
    ensure_project_additions_dir(additions_dir, target_project)
    plan = build_plan(additions_dir, target_project)
    json_path, md_path, prompt_path = write_plan(plan, additions_dir)
    print(f"待增加合并计划已生成：{md_path}")
    print(f"JSON 计划：{json_path}")
    print(f"LLM 判读 prompt：{prompt_path}")
    print(f"共发现素材：{len(plan['items'])} 个")


if __name__ == "__main__":
    main()
