#!/usr/bin/env python3
"""Generate and validate an editor-independent Content OS edit handoff pack.

This backend deliberately produces an auditable editing brief, not an editor
project.  One immutable pack is created for each project revision at:

    90_Draft_Project/edit_handoff/<project_revision>/

It may be used by a human editor or by a later editor adapter, but it never
writes proprietary editor drafts and it never substitutes a different editor
backend when an input cannot be used.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from edl_contract import EDLContractError  # noqa: E402
from edl_contract import parse_seconds as _canonical_parse_seconds  # noqa: E402
from edl_contract import parse_time_range as _canonical_parse_time_range  # noqa: E402
from media_common import file_sha256 as sha256_file  # noqa: E402
from media_common import is_raw360_path  # noqa: E402
from media_common import utc_now_z as utc_now  # noqa: E402


SPEC_VERSION = "content_os_v0.2"
BACKEND = "handoff_pack"
MANIFEST_TYPE = "edit_handoff_manifest"
RESULT_TYPE = "edit_handoff_result"
VALIDATION_TYPE = "edit_handoff_validation"
TIMING_TOLERANCE = 0.000_001
CSV_FIELDS = [
    "timeline_order",
    "slot",
    "timeline_start_sec",
    "timeline_end_sec",
    "duration_sec",
    "source_file",
    "source_start_sec",
    "source_end_sec",
    "purpose",
    "visual_need",
    "edit_note",
    "caption",
]


class HandoffError(Exception):
    """A user-actionable contract failure with a stable machine error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise HandoffError("input_missing", f"{label}文件不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HandoffError("invalid_json", f"{label}不是有效 JSON：{path}") from exc
    if not isinstance(data, dict):
        raise HandoffError("invalid_json_root", f"{label}的根节点必须是对象：{path}")
    return data


def is_raw360(path: Path) -> bool:
    """Delegates to the shared media_common.is_raw360_path (see L-02 dedup)."""
    return is_raw360_path(path)


def parse_seconds(value: Any, *, field: str) -> float:
    """Validate a seconds value using the shared edl_contract.parse_seconds.

    Delegates to the canonical implementation so timing validation (including
    millisecond-precision enforcement) stays identical across every backend;
    edl_contract's error codes ("invalid_timing" / "timing_precision") are
    reused as-is so downstream consumers of HandoffError.code (the Mac to
    cloud blocked-result payload) keep seeing the same stable codes.
    """
    try:
        return _canonical_parse_seconds(value, path=field)
    except EDLContractError as exc:
        raise HandoffError(exc.code, f"{field}: {exc.message}") from exc


def parse_project_revision(value: Any) -> int:
    """Project revision is an increasing positive integer across all v0.2 parts."""
    if isinstance(value, bool):
        raise HandoffError("revision_invalid", "项目版本必须是正整数")
    try:
        revision = int(str(value))
    except (TypeError, ValueError) as exc:
        raise HandoffError("revision_invalid", "项目版本必须是正整数") from exc
    if revision < 1 or str(value).strip() != str(revision):
        raise HandoffError("revision_invalid", "项目版本必须是正整数，不能使用 r003 等旧格式")
    return revision


def parse_time_range(value: Any) -> tuple[float, float]:
    try:
        return _canonical_parse_time_range(value, path="time_range")
    except EDLContractError as exc:
        raise HandoffError(exc.code, str(exc)) from exc


def srt_timestamp(seconds: float) -> str:
    total = int(round(seconds * 1000))
    milliseconds = total % 1000
    total_seconds = total // 1000
    seconds_part = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}"


def parse_srt_timestamp(value: str) -> float:
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not match:
        raise HandoffError("invalid_srt", f"SRT 时间格式错误：{value!r}")
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise HandoffError("invalid_srt", f"SRT 时间值错误：{value!r}")
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def resolve_path(value: str, bases: list[Path]) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    for base in bases:
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return (bases[0] / candidate).resolve()


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def material_policy(materials_path: Path | None) -> tuple[set[Path], Path | None]:
    """Read an optional material allowlist/root without guessing media files."""
    if materials_path is None:
        return set(), None
    path = materials_path.expanduser().resolve()
    if path.is_dir():
        return set(), path
    if not path.is_file():
        raise HandoffError("materials_missing", f"材料清单不存在：{path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HandoffError("materials_format", f"材料清单必须是目录或 JSON：{path}") from exc

    root: Path | None = None
    entries: list[Any]
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        root_value = data.get("local_project_path") or data.get("materials_root")
        if isinstance(root_value, str) and root_value.strip():
            root = resolve_path(root_value, [path.parent])
            if not root.is_dir():
                raise HandoffError("materials_root_missing", f"材料根目录不存在：{root}")
        entries = []
        for key in ("files", "paths", "media_files", "materials"):
            value = data.get(key)
            if isinstance(value, list):
                entries.extend(value)
    else:
        raise HandoffError("materials_format", "材料清单根节点必须是数组或对象")

    allowed: set[Path] = set()
    for entry in entries:
        value = entry.get("path") if isinstance(entry, dict) else entry
        if not isinstance(value, str) or not value.strip():
            raise HandoffError("materials_format", "材料清单中的每项必须是有效路径")
        resolved = resolve_path(value, [root or path.parent, path.parent])
        if not resolved.exists():
            raise HandoffError("materials_entry_missing", f"材料清单包含不存在的路径：{resolved}")
        allowed.add(resolved)
    if not allowed and root is None:
        raise HandoffError("materials_empty", "材料清单必须列出文件，或声明一个有效的材料根目录")
    return allowed, root


def choose_source(
    clip: dict[str, Any],
    *,
    edl_path: Path,
    local_project_path: Path | None,
    materials_allowed: set[Path],
    materials_root: Path | None,
) -> tuple[Path, list[str]]:
    explicit_source = clip.get("source_file")
    candidates: list[Any]
    if isinstance(explicit_source, str) and explicit_source.strip():
        candidates = [explicit_source]
    else:
        raw_candidates = clip.get("candidate_files")
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise HandoffError("source_missing", "每个 EDL 片段必须包含 source_file 或非空 candidate_files")
        candidates = raw_candidates

    bases = [edl_path.parent]
    if local_project_path is not None:
        bases.insert(0, local_project_path)
    if materials_root is not None:
        bases.insert(0, materials_root)

    raw_sources: list[str] = []
    existing_candidates: list[Path] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        source = resolve_path(candidate, bases)
        if is_raw360(source):
            raw_sources.append(str(source))
            continue
        if source.is_file():
            existing_candidates.append(source)

    if not existing_candidates:
        if raw_sources:
            raise HandoffError(
                "raw360_reframe_required",
                "检测到只能直接使用的 360 原始素材。请先导出已重构视角的可剪视频，再生成剪辑交接包："
                + "；".join(raw_sources),
            )
        raise HandoffError("source_missing", "未找到 EDL 片段可用的材料文件")

    source = existing_candidates[0]
    if materials_allowed and source not in materials_allowed:
        raise HandoffError("source_not_in_materials", f"EDL 使用的材料不在材料清单中：{source}")
    if materials_root is not None and not path_is_within(source, materials_root):
        raise HandoffError("source_outside_materials_root", f"EDL 使用的材料不在材料根目录中：{source}")
    return source, raw_sources


def normalise_timeline(
    edl: dict[str, Any],
    edl_path: Path,
    *,
    materials_allowed: set[Path],
    materials_root: Path | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    clips = edl.get("clips")
    if not isinstance(clips, list) or not clips:
        raise HandoffError("edl_clips_missing", "EDL 必须有非空 clips 列表")
    local_project_path: Path | None = None
    local_value = edl.get("local_project_path")
    if isinstance(local_value, str) and local_value.strip():
        local_project_path = resolve_path(local_value, [edl_path.parent])
        if not local_project_path.is_dir():
            raise HandoffError("local_project_missing", f"EDL 的本地项目目录不存在：{local_project_path}")

    timeline: list[dict[str, Any]] = []
    raw_sources: list[str] = []
    slots: set[int] = set()
    for index, raw_clip in enumerate(clips, start=1):
        if not isinstance(raw_clip, dict):
            raise HandoffError("edl_clip_format", f"EDL 第 {index} 个片段必须是对象")
        try:
            slot = int(raw_clip.get("slot", index))
        except (TypeError, ValueError) as exc:
            raise HandoffError("edl_slot_invalid", f"EDL 第 {index} 个片段的 slot 无效") from exc
        if slot <= 0 or slot in slots:
            raise HandoffError("edl_slot_invalid", f"EDL slot 必须为唯一正整数：{slot}")
        slots.add(slot)

        if "time_range" in raw_clip:
            start, end = parse_time_range(raw_clip["time_range"])
            duration = round(end - start, 3)
        else:
            start = parse_seconds(raw_clip.get("timeline_start_sec"), field=f"clips[{index}].timeline_start_sec")
            duration = parse_seconds(raw_clip.get("duration_sec"), field=f"clips[{index}].duration_sec")
            if duration <= 0:
                raise HandoffError("invalid_timing", f"clips[{index}].duration_sec 必须大于 0")
            end = round(start + duration, 3)

        caption = str(raw_clip.get("caption", raw_clip.get("subtitle", ""))).strip()
        if not caption:
            raise HandoffError("caption_missing", f"EDL 第 {index} 个片段缺少 caption；交接包要求每段均有可校验字幕")
        source, skipped_raw = choose_source(
            raw_clip,
            edl_path=edl_path,
            local_project_path=local_project_path,
            materials_allowed=materials_allowed,
            materials_root=materials_root,
        )
        raw_sources.extend(skipped_raw)
        source_start = parse_seconds(raw_clip.get("source_start_sec", 0), field=f"clips[{index}].source_start_sec")
        source_end = round(source_start + duration, 3)
        timeline.append(
            {
                "timeline_order": index,
                "slot": slot,
                "timeline_start_sec": start,
                "timeline_end_sec": end,
                "duration_sec": duration,
                "source_file": str(source),
                "source_start_sec": source_start,
                "source_end_sec": source_end,
                "purpose": str(raw_clip.get("purpose", "")).strip(),
                "visual_need": str(raw_clip.get("visual_need", "")).strip(),
                "edit_note": str(raw_clip.get("edit_note", "")).strip(),
                "caption": caption,
            }
        )

    input_slots = [int(clip["slot"]) for clip in timeline]
    timeline.sort(key=lambda item: (float(item["timeline_start_sec"]), int(item["slot"])))
    if input_slots != [int(clip["slot"]) for clip in timeline]:
        raise HandoffError("edl_order_mismatch", "EDL 的 clips 顺序必须与时间线顺序一致，不能由交接包静默重排")
    for expected_order, clip in enumerate(timeline, start=1):
        clip["timeline_order"] = expected_order
        if expected_order == 1:
            if abs(float(clip["timeline_start_sec"])) > TIMING_TOLERANCE:
                raise HandoffError("timeline_not_zero", "剪辑交接包的第一段必须从 0 秒开始")
            continue
        previous = timeline[expected_order - 2]
        if abs(float(clip["timeline_start_sec"]) - float(previous["timeline_end_sec"])) > TIMING_TOLERANCE:
            raise HandoffError(
                "timeline_gap_or_overlap",
                f"EDL 时间线必须连续且无重叠：第 {previous['slot']} 段结束于 {previous['timeline_end_sec']}，"
                f"第 {clip['slot']} 段开始于 {clip['timeline_start_sec']}",
            )
    return timeline, sorted(set(raw_sources))


def input_descriptor(role: str, path: Path) -> dict[str, str]:
    return {"role": role, "path": str(path), "sha256": sha256_file(path)}


def revision_basis_descriptor(
    path: Path,
    *,
    project_id: str,
    revision: int,
    editor_backend: str,
) -> dict[str, str]:
    """Read a confirmed revision request before binding it to an immutable pack."""

    basis_path = path.expanduser().resolve()
    basis = read_json_object(basis_path, label="已确认修改依据")
    if basis.get("spec_version") != SPEC_VERSION or basis.get("doc_type") != "confirmed_revision_basis":
        raise HandoffError("revision_basis_contract", "修改依据不是 Content OS v0.2 的已确认修改")
    if (
        basis.get("project_id") != project_id
        or basis.get("project_revision") != revision
        or basis.get("editor_backend") != editor_backend
    ):
        raise HandoffError("revision_basis_identity", "修改依据与当前项目、版本或剪辑方式不一致")
    change_request_id = basis.get("change_request_id")
    if not isinstance(change_request_id, str) or not change_request_id.strip():
        raise HandoffError("revision_basis_change_request", "修改依据缺少已确认的修改单编号")
    summary = basis.get("change_summary")
    if not isinstance(summary, dict) or any(
        not isinstance(summary.get(key), str) or not summary[key].strip()
        for key in ("requested_location", "requested_change", "reason")
    ):
        raise HandoffError("revision_basis_summary", "修改依据缺少结构化的修改说明")
    return {
        "role": "confirmed_revision_basis",
        "path": str(basis_path),
        "sha256": sha256_file(basis_path),
        "change_request_id": change_request_id.strip(),
    }


def write_clips_csv(path: Path, timeline: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for clip in timeline:
            writer.writerow({field: clip[field] for field in CSV_FIELDS})


def write_srt(path: Path, timeline: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for index, clip in enumerate(timeline, start=1):
        lines.extend(
            [
                str(index),
                f"{srt_timestamp(float(clip['timeline_start_sec']))} --> {srt_timestamp(float(clip['timeline_end_sec']))}",
                str(clip["caption"]),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_handoff_note(path: Path, *, project_id: str, revision: int, timeline: list[dict[str, Any]]) -> None:
    rows = "\n".join(
        f"| {clip['timeline_order']} | {clip['timeline_start_sec']:.3f}–{clip['timeline_end_sec']:.3f} | "
        f"{clip['purpose'] or '未说明'} | {clip['caption']} |"
        for clip in timeline
    )
    path.write_text(
        f"""# 剪辑交接说明

项目：`{project_id}`  
版本：`{revision}`

这是一份可编辑剪辑的交接包。它只记录已经确认的剪辑顺序、时长、材料位置与字幕；不会生成或修改任何剪辑软件项目。

## 编辑时必须保持

- 严格按 `clips.csv` 的顺序、起止时间和来源材料处理。
- 使用 `captions.srt` 作为同一版字幕时间轴。
- 如需改动脚本、顺序、时长或素材，请先提交修改，不要直接覆盖这个版本的文件。
- 任何 360 原始文件均未被直接使用；若素材清单提示需要重构，应先导出可剪视频。

## 时间线摘要

| 顺序 | 时间 | 目的 | 字幕 |
| --- | --- | --- | --- |
{rows}
""",
        encoding="utf-8",
    )


def write_preview_note(path: Path, *, timeline: list[dict[str, Any]]) -> None:
    duration = float(timeline[-1]["timeline_end_sec"])
    path.write_text(
        f"""# 预览说明

本交接包没有把原始材料重新渲染成预览视频。这样可以避免把“预览文件”误当成可继续编辑的唯一来源。

- 预览总时长：`{duration:.3f}` 秒
- 预览顺序：按 `clips.csv` 的 `timeline_order` 从 1 到 {len(timeline)}。
- 字幕预览：打开 `captions.srt`，时间必须与 `clips.csv` 一致。
- 画面预览：按 `clips.csv` 的 `source_file`、`source_start_sec` 和 `duration_sec` 在编辑器中查看对应片段。

若必须交付渲染预览，应由人工或专用渲染流程在此版本之外生成，并在其结果中记录来源版本。
""",
        encoding="utf-8",
    )


def ensure_new_revision_dir(output_root: Path, revision: int) -> Path:
    root = output_root.expanduser().resolve()
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise HandoffError("output_root_invalid", f"交接包根目录不是文件夹：{root}")
    destination = (root / str(revision)).resolve()
    if not path_is_within(destination, root):
        raise HandoffError("revision_invalid", "项目版本不能跳出交接包根目录")
    if destination.exists():
        raise HandoffError("revision_exists", f"该项目版本的交接包已经存在，版本不可覆盖：{destination}")
    return destination


def build_manifest(
    *,
    package_dir: Path,
    artifact_dir: Path,
    project_id: str,
    revision: int,
    edl_path: Path,
    storyboard_path: Path,
    materials_path: Path | None,
    revision_basis_path: Path | None,
    timeline: list[dict[str, Any]],
    skipped_raw_sources: list[str],
) -> dict[str, Any]:
    artifacts = {
        "clips_csv": "clips.csv",
        "captions_srt": "captions.srt",
        "handoff_note": "剪辑交接说明.md",
        "preview": {"kind": "explanation", "path": "预览说明.md", "rendered_video": False},
    }
    checksums = {
        key: sha256_file(artifact_dir / relative)
        for key, relative in {
            "clips_csv": artifacts["clips_csv"],
            "captions_srt": artifacts["captions_srt"],
            "handoff_note": artifacts["handoff_note"],
            "preview_note": artifacts["preview"]["path"],
        }.items()
    }
    inputs = [input_descriptor("edl", edl_path), input_descriptor("storyboard", storyboard_path)]
    if materials_path is not None:
        if materials_path.is_file():
            inputs.append(input_descriptor("materials", materials_path))
        else:
            inputs.append({"role": "materials_root", "path": str(materials_path), "sha256": "directory"})
    if revision_basis_path is not None:
        inputs.append(
            revision_basis_descriptor(
                revision_basis_path,
                project_id=project_id,
                revision=revision,
                editor_backend=BACKEND,
            )
        )
    return {
        "spec_version": SPEC_VERSION,
        "doc_type": MANIFEST_TYPE,
        "project_id": project_id,
        "project_revision": revision,
        "editor_backend": BACKEND,
        "generated_at": utc_now(),
        "package_dir": str(package_dir),
        "inputs": inputs,
        "timeline": timeline,
        "artifacts": artifacts,
        "artifact_checksums": checksums,
        "raw360_direct_use": "blocked",
        "materials_requiring_reframe": skipped_raw_sources,
    }


def result_from_manifest(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest["artifacts"]
    package_dir = manifest_path.parent
    return {
        "spec_version": SPEC_VERSION,
        "doc_type": RESULT_TYPE,
        "status": "done",
        "project_id": manifest["project_id"],
        "project_revision": manifest["project_revision"],
        "editor_backend": BACKEND,
        "pack_dir": str(package_dir),
        "manifest": str(manifest_path),
        "artifacts": {
            "clips_csv": str(package_dir / artifacts["clips_csv"]),
            "captions_srt": str(package_dir / artifacts["captions_srt"]),
            "handoff_note": str(package_dir / artifacts["handoff_note"]),
            "preview_note": str(package_dir / artifacts["preview"]["path"]),
        },
        "manifest_sha256": sha256_file(manifest_path),
        "raw360_direct_use": "blocked",
    }


def generate(
    *,
    project_id: str | None,
    project_revision: int,
    edl_path: Path,
    storyboard_path: Path,
    output_root: Path,
    materials_path: Path | None,
    revision_basis_path: Path | None,
) -> dict[str, Any]:
    edl_path = edl_path.expanduser().resolve()
    storyboard_path = storyboard_path.expanduser().resolve()
    edl = read_json_object(edl_path, label="EDL")
    if not storyboard_path.is_file() or not storyboard_path.read_text(encoding="utf-8").strip():
        raise HandoffError("storyboard_missing", f"Storyboard 文件不存在或为空：{storyboard_path}")
    declared_project_id = str(edl.get("project_id", "")).strip()
    effective_project_id = project_id or declared_project_id
    if not effective_project_id:
        raise HandoffError("project_id_missing", "必须通过 --project-id 或 EDL.project_id 提供项目编号")
    if declared_project_id and project_id and project_id != declared_project_id:
        raise HandoffError("project_id_mismatch", "--project-id 与 EDL.project_id 不一致")

    resolved_materials_path = materials_path.expanduser().resolve() if materials_path else None
    materials_allowed, materials_root = material_policy(resolved_materials_path)
    timeline, skipped_raw_sources = normalise_timeline(
        edl,
        edl_path,
        materials_allowed=materials_allowed,
        materials_root=materials_root,
    )
    destination = ensure_new_revision_dir(output_root, project_revision)
    staging_parent = destination.parent
    staging = Path(tempfile.mkdtemp(prefix=f".{project_revision}.staging-", dir=staging_parent))
    try:
        write_clips_csv(staging / "clips.csv", timeline)
        write_srt(staging / "captions.srt", timeline)
        write_handoff_note(staging / "剪辑交接说明.md", project_id=effective_project_id, revision=project_revision, timeline=timeline)
        write_preview_note(staging / "预览说明.md", timeline=timeline)
        manifest = build_manifest(
            package_dir=destination,
            artifact_dir=staging,
            project_id=effective_project_id,
            revision=project_revision,
            edl_path=edl_path,
            storyboard_path=storyboard_path,
            materials_path=resolved_materials_path,
            revision_basis_path=revision_basis_path,
            timeline=timeline,
            skipped_raw_sources=skipped_raw_sources,
        )
        # Checksums were calculated from the staging files. Their content is
        # identical after the atomic directory rename, while their final paths
        # in the manifest point at the immutable destination.
        write_json(staging / "manifest.json", manifest)
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    manifest_path = destination / "manifest.json"
    return result_from_manifest(manifest_path, read_json_object(manifest_path, label="manifest"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != CSV_FIELDS:
                raise HandoffError("clips_csv_columns", "clips.csv 的列顺序或名称不符合交接包契约")
            rows = list(reader)
    except csv.Error as exc:
        raise HandoffError("clips_csv_invalid", "clips.csv 无法解析") from exc
    if not rows:
        raise HandoffError("clips_csv_empty", "clips.csv 不能为空")
    return rows


def parse_srt(path: Path) -> list[tuple[int, float, float, str]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise HandoffError("captions_empty", "captions.srt 不能为空")
    blocks = re.split(r"\n\s*\n", text)
    result: list[tuple[int, float, float, str]] = []
    for position, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        if len(lines) < 3:
            raise HandoffError("invalid_srt", f"SRT 第 {position} 个字幕块不完整")
        try:
            index = int(lines[0].strip())
        except ValueError as exc:
            raise HandoffError("invalid_srt", f"SRT 第 {position} 个字幕序号无效") from exc
        match = re.fullmatch(r"(.+?)\s+-->\s+(.+?)", lines[1].strip())
        if not match:
            raise HandoffError("invalid_srt", f"SRT 第 {position} 个字幕时间轴无效")
        start = parse_srt_timestamp(match.group(1))
        end = parse_srt_timestamp(match.group(2))
        if end <= start:
            raise HandoffError("invalid_srt", f"SRT 第 {position} 个字幕结束时间必须晚于开始时间")
        caption = "\n".join(lines[2:]).strip()
        if not caption:
            raise HandoffError("invalid_srt", f"SRT 第 {position} 个字幕缺少正文")
        result.append((index, start, end, caption))
    return result


def require_artifact(package_dir: Path, relative: Any, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise HandoffError("manifest_artifact_missing", f"manifest 缺少 {label} 路径")
    path = (package_dir / relative).resolve()
    if not path_is_within(path, package_dir) or not path.is_file() or path.stat().st_size == 0:
        raise HandoffError("manifest_artifact_missing", f"交接包缺少 {label}：{relative}")
    return path


def validate_manifest_revision_basis(manifest: dict[str, Any], *, project_id: str, revision: int) -> dict[str, str] | None:
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list):
        raise HandoffError("manifest_contract", "manifest 缺少 inputs")
    candidates = [entry for entry in inputs if isinstance(entry, dict) and entry.get("role") == "confirmed_revision_basis"]
    if not candidates:
        return None
    if len(candidates) != 1:
        raise HandoffError("revision_basis_contract", "manifest 只能绑定一份已确认修改依据")
    descriptor = candidates[0]
    path_value = descriptor.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise HandoffError("revision_basis_contract", "manifest 的修改依据路径无效")
    actual = revision_basis_descriptor(
        Path(path_value),
        project_id=project_id,
        revision=revision,
        editor_backend=BACKEND,
    )
    if descriptor != actual:
        raise HandoffError("revision_basis_checksum", "已确认修改依据已变更，不能继续使用该交接包")
    return actual


def validate(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = read_json_object(manifest_path, label="manifest")
    package_dir = manifest_path.parent
    if manifest.get("spec_version") != SPEC_VERSION or manifest.get("doc_type") != MANIFEST_TYPE:
        raise HandoffError("manifest_contract", "manifest 不是 Content OS v0.2 的剪辑交接包")
    if manifest.get("editor_backend") != BACKEND:
        raise HandoffError("manifest_backend", "manifest 的剪辑方式不是 handoff_pack")
    project_id = manifest.get("project_id")
    revision = manifest.get("project_revision")
    if not isinstance(project_id, str) or not project_id.strip() or not isinstance(revision, int) or revision < 1:
        raise HandoffError("manifest_identity", "manifest 缺少有效项目编号或项目版本")
    if package_dir.name != str(revision):
        raise HandoffError("manifest_revision_path", "manifest 所在目录必须与项目版本一致")
    revision_basis = validate_manifest_revision_basis(manifest, project_id=project_id, revision=revision)

    artifacts = manifest.get("artifacts")
    checksums = manifest.get("artifact_checksums")
    timeline = manifest.get("timeline")
    if not isinstance(artifacts, dict) or not isinstance(checksums, dict) or not isinstance(timeline, list) or not timeline:
        raise HandoffError("manifest_contract", "manifest 缺少 artifacts、artifact_checksums 或 timeline")
    preview = artifacts.get("preview")
    if not isinstance(preview, dict) or preview.get("kind") not in {"explanation", "rendered_video"}:
        raise HandoffError("preview_contract", "manifest 必须声明预览方式")

    artifact_paths = {
        "clips_csv": require_artifact(package_dir, artifacts.get("clips_csv"), label="clips.csv"),
        "captions_srt": require_artifact(package_dir, artifacts.get("captions_srt"), label="captions.srt"),
        "handoff_note": require_artifact(package_dir, artifacts.get("handoff_note"), label="剪辑交接说明"),
        "preview_note": require_artifact(package_dir, preview.get("path"), label="预览说明"),
    }
    for key, path in artifact_paths.items():
        if checksums.get(key) != sha256_file(path):
            raise HandoffError("artifact_checksum_mismatch", f"交接包文件已被修改：{path.name}")

    rows = read_csv_rows(artifact_paths["clips_csv"])
    if len(rows) != len(timeline):
        raise HandoffError("timeline_count", "clips.csv 与 manifest 的片段数不一致")
    srt_entries = parse_srt(artifact_paths["captions_srt"])
    if len(srt_entries) != len(timeline):
        raise HandoffError("caption_count", "captions.srt 必须与每个剪辑片段一一对应")

    previous_end: float | None = None
    for index, (row, clip, srt_entry) in enumerate(zip(rows, timeline, srt_entries), start=1):
        if not isinstance(clip, dict):
            raise HandoffError("manifest_timeline", f"manifest 第 {index} 个片段不是对象")
        if int(row["timeline_order"]) != index or int(clip.get("timeline_order", 0)) != index:
            raise HandoffError("timeline_order", "交接包片段顺序必须从 1 连续递增")
        try:
            start = parse_seconds(row["timeline_start_sec"], field="clips.csv timeline_start_sec")
            end = parse_seconds(row["timeline_end_sec"], field="clips.csv timeline_end_sec")
            duration = parse_seconds(row["duration_sec"], field="clips.csv duration_sec")
        except KeyError as exc:
            raise HandoffError("clips_csv_columns", "clips.csv 缺少必需列") from exc
        if abs((end - start) - duration) > TIMING_TOLERANCE or duration <= 0:
            raise HandoffError("timeline_duration", f"clips.csv 第 {index} 行的时长不一致")
        if previous_end is None:
            if abs(start) > TIMING_TOLERANCE:
                raise HandoffError("timeline_not_zero", "clips.csv 第一段必须从 0 秒开始")
        elif abs(start - previous_end) > TIMING_TOLERANCE:
            raise HandoffError("timeline_gap_or_overlap", "clips.csv 时间线必须连续且无重叠")
        previous_end = end
        if is_raw360(Path(row["source_file"])):
            raise HandoffError("raw360_reframe_required", "交接包不得直接使用 360 原始材料")
        source = Path(row["source_file"])
        if not source.is_file():
            raise HandoffError("source_missing", f"交接包引用的材料不存在：{source}")
        for key in ("slot", "timeline_start_sec", "timeline_end_sec", "duration_sec", "source_file", "caption"):
            if str(clip.get(key, "")) != row[key]:
                raise HandoffError("manifest_csv_mismatch", f"manifest 与 clips.csv 在第 {index} 段的 {key} 不一致")
        srt_index, srt_start, srt_end, srt_caption = srt_entry
        if srt_index != index or abs(srt_start - start) > TIMING_TOLERANCE or abs(srt_end - end) > TIMING_TOLERANCE:
            raise HandoffError("srt_timing_mismatch", f"captions.srt 第 {index} 段时间与 clips.csv 不一致")
        if srt_caption != row["caption"]:
            raise HandoffError("srt_caption_mismatch", f"captions.srt 第 {index} 段文字与 clips.csv 不一致")

    if manifest.get("raw360_direct_use") != "blocked":
        raise HandoffError("raw360_policy", "manifest 必须明确禁止直接使用 360 原始材料")
    result = {
        "spec_version": SPEC_VERSION,
        "doc_type": VALIDATION_TYPE,
        "status": "passed",
        "project_id": project_id,
        "project_revision": revision,
        "editor_backend": BACKEND,
        "manifest": str(manifest_path),
        "clip_count": len(timeline),
        "caption_count": len(srt_entries),
        "preview_kind": preview["kind"],
        "raw360_direct_use": "blocked",
    }
    if revision_basis is not None:
        result["revision_basis"] = revision_basis
    return result


def emit(payload: dict[str, Any], output_path: Path | None) -> None:
    if output_path is not None:
        write_json(output_path.expanduser().resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    commands = argument_parser.add_subparsers(dest="command", required=True)
    generate_parser = commands.add_parser("generate", help="生成不可覆盖的项目版本交接包")
    generate_parser.add_argument("--project-id")
    generate_parser.add_argument("--project-revision", required=True, type=int)
    generate_parser.add_argument("--edl", required=True, type=Path)
    generate_parser.add_argument("--storyboard", required=True, type=Path)
    generate_parser.add_argument("--output-root", required=True, type=Path)
    generate_parser.add_argument("--materials", type=Path)
    generate_parser.add_argument("--revision-basis", type=Path)
    generate_parser.add_argument("--result-output", type=Path)
    validate_parser = commands.add_parser("validate", help="校验剪辑交接包内容、时长、字幕和材料")
    validate_parser.add_argument("--manifest", required=True, type=Path)
    validate_parser.add_argument("--result-output", type=Path)
    return argument_parser


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "generate":
            payload = generate(
                project_id=args.project_id,
                project_revision=parse_project_revision(args.project_revision),
                edl_path=args.edl,
                storyboard_path=args.storyboard,
                output_root=args.output_root,
                materials_path=args.materials,
                revision_basis_path=args.revision_basis,
            )
        else:
            payload = validate(args.manifest)
        emit(payload, args.result_output)
        return 0
    except HandoffError as exc:
        emit(
            {
                "spec_version": SPEC_VERSION,
                "status": "blocked",
                "editor_backend": BACKEND,
                "error_code": exc.code,
                "message": exc.message,
            },
            getattr(args, "result_output", None),
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
