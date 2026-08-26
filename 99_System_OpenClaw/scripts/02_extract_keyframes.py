#!/usr/bin/env python3
"""Extract evidence keyframes under a deterministic analysis-tier budget."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from analysis_tiering import evenly_spaced_indexes
from media_common import eligible_item, load_manifest, project_path, relative_posix, safe_slug, save_manifest


class KeyframeError(RuntimeError):
    pass


def _load_plan(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise KeyframeError(f"analysis plan is invalid JSON: {path}") from exc
    plans = value.get("plans") if isinstance(value, dict) else None
    if not isinstance(plans, list):
        raise KeyframeError("analysis plan must contain a plans array")
    result: dict[str, dict[str, Any]] = {}
    for item in plans:
        if isinstance(item, dict) and item.get("media_id"):
            result[str(item["media_id"])] = item
    return result


def _timestamp_candidates(duration: float, count: int) -> list[float]:
    if count <= 0 or duration <= 0:
        return []
    # Avoid exact first/last frames, which are frequently black or incomplete.
    start = min(0.35, max(0.0, duration * 0.05))
    end = max(start, duration - min(0.35, duration * 0.05))
    if count == 1:
        return [round((start + end) / 2, 3)]
    return [round(start + index * (end - start) / (count - 1), 3) for index in range(count)]


def _run_ffmpeg(source: Path, output: Path, timestamp: float, *, max_edge: int) -> bool:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({max_edge},iw)':-2",
        "-q:v",
        "3",
        str(output),
    ]
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0 and output.is_file() and output.stat().st_size > 0


def extract_for_item(
    project: Path,
    item: dict[str, Any],
    *,
    output_root: Path,
    image_budget: int,
    max_edge: int,
) -> list[str]:
    if item.get("media_type") != "video" or image_budget <= 0:
        return []
    source = (project / str(item.get("relative_path") or "")).resolve()
    try:
        source.relative_to(project.resolve())
    except ValueError as exc:
        raise KeyframeError("media path escapes project root") from exc
    if not source.is_file():
        raise KeyframeError(f"media file does not exist: {source}")
    duration = float(item.get("duration_sec") or 0)
    if not math.isfinite(duration) or duration <= 0:
        return []
    media_id = str(item.get("media_id") or item.get("id") or safe_slug(source.stem))
    item_dir = output_root / f"{media_id}_{safe_slug(source.stem)}"
    item_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index, timestamp in enumerate(_timestamp_candidates(duration, image_budget), start=1):
        output = item_dir / f"frame_{index:03d}_{timestamp:.3f}s.jpg"
        if output.is_file() and output.stat().st_size > 0:
            outputs.append(relative_posix(output, project))
            continue
        if _run_ffmpeg(source, output, timestamp, max_edge=max_edge):
            outputs.append(relative_posix(output, project))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--include-derived", action="store_true")
    parser.add_argument("--analysis-plan", type=Path)
    parser.add_argument("--max-frames", type=int, default=8, help="无分析计划时的单视频预算")
    parser.add_argument("--max-edge", type=int, default=1280)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.max_frames <= 40:
        parser.error("--max-frames must be between 0 and 40")
    if not 320 <= args.max_edge <= 4096:
        parser.error("--max-edge must be between 320 and 4096")
    if shutil.which("ffmpeg") is None:
        raise KeyframeError("ffmpeg not found")

    project = project_path(args.project_dir)
    plan_path = args.analysis_plan.expanduser().resolve() if args.analysis_plan else project / "_ai_analysis" / "analysis_plan.json"
    plan_by_id = _load_plan(plan_path if plan_path.exists() else None)
    manifest = load_manifest(project)
    output_root = project / "_ai_analysis" / "keyframes"
    output_root.mkdir(parents=True, exist_ok=True)
    extracted = 0
    skipped = 0
    for item in manifest.get("items", []):
        if not isinstance(item, dict) or not eligible_item(item, include_derived=args.include_derived):
            continue
        media_id = str(item.get("media_id") or item.get("id") or "")
        plan = plan_by_id.get(media_id, {})
        tier = str(plan.get("tier") or "preview")
        image_budget = int(plan.get("image_budget", args.max_frames))
        item["analysis_tier"] = tier
        item["analysis_cache_key"] = plan.get("cache_key")
        item["image_evidence_budget"] = image_budget
        if item.get("media_type") != "video":
            item["keyframe_status"] = "not_required_for_image"
            continue
        if tier == "metadata" or image_budget <= 0:
            item["keyframe_status"] = "skipped_metadata_tier"
            item["keyframes"] = []
            skipped += 1
            continue
        if item.get("keyframes") and not args.overwrite:
            item["keyframe_status"] = "cached"
            skipped += 1
            continue
        frames = extract_for_item(
            project,
            item,
            output_root=output_root,
            image_budget=image_budget,
            max_edge=args.max_edge,
        )
        item["keyframes"] = frames
        item["keyframe_status"] = "ok" if frames else "pending_manual"
        extracted += len(frames)
    manifest["analysis_plan_path"] = relative_posix(plan_path, project) if plan_path.exists() else None
    save_manifest(project, manifest)
    print(f"关键帧提取完成：{output_root}；新增/确认 {extracted} 帧，跳过 {skipped} 个素材")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
