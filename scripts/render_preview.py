#!/usr/bin/env python3
"""Build or explicitly execute a mixed preview rough-cut from canonical EDL."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from edl_contract import load_and_normalise, parse_time_range, require_flat_timeline
from media import safe_project_file
from audio_plan import compile_audio_plan, probe_audio_source


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
    """L-07: shares media.safe_project_file's resolution/escape-guard core.

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


AUDIO_RATE = 48000


def _factor_expression(points: list[list[float]], timeline_start: float) -> str:
    """Translate one plan factor without flattening products or step boundaries."""
    time = f"(t+{timeline_start:.9f})"
    expression = f"{points[-1][1]:.12g}"
    for (a, x), (b, y) in reversed(list(zip(points, points[1:]))):
        if b == a:
            continue
        value = f"({x:.12g}+({y-x:.12g})*({time}-{a:.9f})/{b-a:.9f})"
        expression = f"if(lt({time},{b:.9f}),{value},{expression})"
    return f"if(lt({time},{points[0][0]:.9f}),{points[0][1]:.12g},{expression})"


def _audio_filters(plan: dict[str, Any], indices: dict[str, int]) -> list[str]:
    if plan["source_validation"] != "passed":
        return []
    length = round(plan["duration_sec"] * AUDIO_RATE)
    filters = [f"anullsrc=r={AUDIO_RATE}:cl=stereo,atrim=end_sample={length}[silence]"]
    labels = ["[silence]"]
    for index, segment in enumerate(plan["segments"]):
        start, end = segment["timeline_start_sec"], segment["timeline_end_sec"]
        chain = [f"[{indices[segment['source']]}:a:0]aresample={AUDIO_RATE}",
                 "aformat=sample_fmts=fltp:channel_layouts=stereo",
                 f"atrim=start_sample={round(segment['source_start_sec']*AUDIO_RATE)}:end_sample={round(segment['source_end_sec']*AUDIO_RATE)}",
                 "asetpts=N/SR/TB"]
        expressions = []
        for factor in segment["gain_envelope"]["factors"]:
            points = factor["points"]
            # The common trapezoid maps directly to sample-counted FFmpeg fades.
            # Looped excerpts can retain a whole-song factor: evaluate those
            # on film time instead of restarting the song's fade on every loop.
            if (factor["kind"] == "base_and_fade" and len(points) == 4
                    and points[0] == [start, 0] and points[-1] == [end, 0]
                    and points[1][1] == points[2][1]):
                chain += [f"volume={points[1][1]:.12g}",
                          f"afade=t=in:ss=0:ns={max(1, round((points[1][0]-start)*AUDIO_RATE))}",
                          f"afade=t=out:ss={round((points[2][0]-start)*AUDIO_RATE)}:ns={max(1, round((end-points[2][0])*AUDIO_RATE))}"]
            else:
                expressions.append(_factor_expression(points, start))
        if expressions:
            gain = "*".join(f"({expression})" for expression in expressions)
            # volume's frame evaluation cannot express a sample-accurate ramp.
            chain.append(f"aeval=exprs='val(0)*{gain}|val(1)*{gain}'")
        chain.append(f"adelay={round(start*AUDIO_RATE)}S:all=1[a{index}]")
        filters.append(",".join(chain))
        labels.append(f"[a{index}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0,atrim=end_sample={length},asetpts=N/SR/TB[outa]")
    return filters


def build_plan(
    edl: dict[str, Any],
    *,
    project: Path,
    output: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    require_sources: bool = True,
    video: Path | None = None,
) -> dict[str, Any]:
    # The preview concatenates clips end to end, so a layered EDL would render
    # overlays inline as extra shots instead of composited on top of the cut.
    require_flat_timeline(edl, backend="本地预览粗剪")
    project = project.expanduser().resolve()
    chosen = [str(c.get("source_file") or c["candidate_files"][0]) for c in edl["clips"]]
    chosen += [track["source"] for section in ("audio_beds", "music") for track in edl.get(section, [])]
    sources = {raw: _safe_source(project, raw, require_exists=require_sources) for raw in dict.fromkeys(chosen)}
    facts = {raw: probe_audio_source(path) for raw, path in sources.items()} if require_sources else None
    audio_plan = compile_audio_plan(edl, source_info=facts)
    clips: list[PreviewClip] = []
    inputs: list[str] = []
    filter_parts: list[str] = []
    indices = {raw: index for index, raw in enumerate(sources)}
    for source in sources.values():
        inputs.extend(["-i", str(source)])
    for index, clip in enumerate(edl["clips"]):
        source_value = str(clip.get("source_file") or clip["candidate_files"][0])
        source = _safe_source(project, source_value, require_exists=require_sources)
        start, end = parse_time_range(clip["time_range"])
        duration = round(end - start, 3)
        source_start = float(clip["source_start_sec"])
        clips.append(PreviewClip(int(clip["slot"]), source_value, source_start, duration, start, end))
        filter_parts.append(
            f"[{indices[source_value]}:v:0]trim=start={source_start:.3f}:duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{index}]"
        )
    if video is not None:
        # Candidate video already carries the accepted visual/subtitle timing.
        # Its embedded audio is deliberately never mapped into the new mix.
        inputs.extend(["-i", str(video)])
        filter_parts = []
    concat_inputs = "".join(f"[v{index}]" for index in range(len(clips)))
    if video is None:
        filter_parts.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]")
    filter_parts.extend(_audio_filters(audio_plan, indices))
    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        f"{len(sources)}:v:0" if video is not None else "[outv]",
        *(["-map", "[outa]", "-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE)] if require_sources else []),
        "-t", str(audio_plan["duration_sec"]),
        "-c:v",
        "copy" if video is not None else "libx264",
        *([] if video is not None else ["-preset", "veryfast"]),
        "-movflags",
        "+faststart",
        str(output),
    ]
    return {
        "schema_version": "preview_render_plan_v1",
        "mode": "mixed_roughcut",
        "audio_plan": audio_plan,
        "project_ref": project.name,
        "output_name": output.name,
        "clips": [asdict(clip) for clip in clips],
        "command": command,
        "privacy": {"raw_media_upload": False, "local_execution_only": True},
    }


def execute_plan(plan: dict[str, Any]) -> None:
    if plan.get("audio_plan", {}).get("source_validation") != "passed":
        raise PreviewError("audio_source_info_required: 请确认素材可读并重新生成预览计划")
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
