#!/usr/bin/env python3
"""Build or explicitly execute a silent preview rough-cut from canonical EDL."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from edl_contract import load_and_normalise, parse_time_range
from media_common import safe_project_file


class PreviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreviewClip:
    slot: int
    source: str
    source_start_sec: float
    duration_sec: float
    timeline_start_sec: float
    timeline_end_sec: float


def _safe_source(project: Path, raw: str, *, require_exists: bool) -> Path:
    """L-07: shares media_common.safe_project_file's resolution/escape-guard core.

    Kept as a local wrapper (not a direct call) because this script's failure
    mode is a raised PreviewError, and require_exists (allowing a plan to
    reference an output path that does not exist yet) is unique to this
    caller -- see L-07's divergence notes.
    """
    resolved = safe_project_file(project, raw, must_be_file=False)
    if resolved is None:
        raise PreviewError(f"source escapes project root: {raw}")
    if require_exists and not resolved.is_file():
        raise PreviewError(f"source file does not exist: {raw}")
    return resolved


def build_plan(
    edl: dict[str, Any],
    *,
    project: Path,
    output: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    require_sources: bool = True,
) -> dict[str, Any]:
    clips: list[PreviewClip] = []
    inputs: list[str] = []
    filter_parts: list[str] = []
    for index, clip in enumerate(edl["clips"]):
        source_value = str(clip.get("source_file") or clip["candidate_files"][0])
        source = _safe_source(project, source_value, require_exists=require_sources)
        start, end = parse_time_range(clip["time_range"])
        duration = round(end - start, 3)
        source_start = float(clip["source_start_sec"])
        clips.append(PreviewClip(int(clip["slot"]), source_value, source_start, duration, start, end))
        inputs.extend(["-i", str(source)])
        filter_parts.append(
            f"[{index}:v]trim=start={source_start:.3f}:duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{index}]"
        )
    concat_inputs = "".join(f"[v{index}]" for index in range(len(clips)))
    filter_parts.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[outv]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-movflags",
        "+faststart",
        str(output),
    ]
    return {
        "schema_version": "preview_render_plan_v1",
        "mode": "silent_roughcut",
        "project_ref": project.name,
        "output_name": output.name,
        "clips": [asdict(clip) for clip in clips],
        "command": command,
        "privacy": {"raw_media_upload": False, "local_execution_only": True},
    }


def execute_plan(plan: dict[str, Any]) -> None:
    if shutil.which("ffmpeg") is None:
        raise PreviewError("ffmpeg is not available")
    command = plan.get("command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise PreviewError("render plan command is invalid")
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise PreviewError(completed.stderr.strip() or f"ffmpeg failed with {completed.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--edl", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plan-output", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--execute", action="store_true", help="明确执行 ffmpeg；默认只生成计划")
    parser.add_argument("--allow-missing-sources", action="store_true", help="仅用于 dry-run 测试")
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    edl = load_and_normalise(args.edl.expanduser().resolve())
    plan = build_plan(
        edl,
        project=project,
        output=output,
        width=args.width,
        height=args.height,
        fps=args.fps,
        require_sources=not args.allow_missing_sources,
    )
    plan_path = args.plan_output.expanduser().resolve() if args.plan_output else output.with_suffix(".preview-plan.json")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"preview_plan={plan_path}")
    print(f"ffmpeg={shlex.join(plan['command'])}")
    if args.execute:
        execute_plan(plan)
        print(f"preview={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
