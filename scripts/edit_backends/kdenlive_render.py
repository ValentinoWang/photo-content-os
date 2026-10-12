#!/usr/bin/env python3
"""Execute explicitly permitted spoken-edit suggestions using bundled MLT/melt."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from edit_backends.otio_kdenlive import (
    ContractError, FPS, TimelineClip, frames, make_otio_timeline, require_otio,
    sha256_file, write_json, write_kdenlive_project, timeline_tractor,
)


def review_module():
    name = "pipeline_output_review"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / "review_output_video.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def melt_executable() -> str | None:
    configured = os.environ.get("CONTENT_OS_MELT_EXECUTABLE")
    if configured is not None:
        path = Path(configured).expanduser().resolve()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    bundled = Path("/Applications/kdenlive.app/Contents/MacOS/melt")
    return str(bundled) if bundled.is_file() and os.access(bundled, os.X_OK) else shutil.which("melt")


def probe_media(path: Path) -> dict:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                                capture_output=True, text=True, check=True, timeout=30)
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise ContractError("media_probe_failed") from exc


def seconds(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ContractError("suggestion_time_invalid")
    return float(value)


def plan_ranges(suggestions: dict, duration: float) -> tuple[list[dict], list[dict]]:
    """Return frame-aligned retained ranges; review-only suggestions never cut."""
    total = frames(duration)
    if total <= 0:
        raise ContractError("source_duration_invalid")
    items = suggestions.get("suggestions")
    if not isinstance(items, list):
        raise ContractError("suggestions_list_required")
    cuts, ignored = [], []
    for item in items:
        if not isinstance(item, dict):
            raise ContractError("suggestion_invalid")
        if item.get("type") not in {"silence", "repetition"}:
            continue
        start, end = seconds(item.get("start")), seconds(item.get("end"))
        if end <= start or end > duration + 1e-6:
            raise ContractError("suggestion_range_invalid")
        if item.get("auto_cut_allowed") is not True or suggestions.get("auto_cut_allowed") is False:
            ignored.append(item)
            continue
        if item["type"] == "repetition" and (suggestions.get("precision") != "word" or item.get("precision", "word") != "word"):
            raise ContractError("repetition_requires_word_timing")
        if "cut" in item and item["cut"] != {"start": start, "end": end}:
            raise ContractError("suggestion_cut_range_mismatch")
        a, b = frames(start), min(total, frames(end))
        if b <= a:
            raise ContractError("cut_shorter_than_frame")
        cuts.append((a, b))
    merged = []
    for a, b in sorted(cuts):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    retained, cursor, output = [], 0, 0
    for a, b in [*merged, (total, total)]:
        if a > cursor:
            retained.append({"source_start": cursor / FPS, "source_end": a / FPS, "output_start": output / FPS})
            output += a - cursor
        cursor = b
    if not retained:
        raise ContractError("all_source_removed")
    return retained, ignored


def remap_span(start: float, end: float, ranges: list[dict]) -> list[tuple[float, float, float]]:
    spans = []
    for item in ranges:
        a, b = max(start, item["source_start"]), min(end, item["source_end"])
        if b > a:
            spans.append((item["output_start"] + a - item["source_start"],
                          item["output_start"] + b - item["source_start"], a - start))
    return spans


def srt_timestamp(seconds_value: float) -> str:
    value = round(seconds_value * 1000)
    h, value = divmod(value, 3600000)
    m, value = divmod(value, 60000)
    sec, ms = divmod(value, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"


def remap_subtitles(source: Path, destination: Path, ranges: list[dict], duration: float):
    cues = review_module().read_srt_cues(source)
    previous = 0
    mapped = []
    for start, end, text in cues:
        if start < previous or end > duration + 1e-6:
            raise ContractError("subtitle_source_timeline_invalid")
        previous = end
        for a, b, _ in remap_span(start, end, ranges):
            if round(b * 1000) > round(a * 1000):
                mapped.append((a, b, text))
    if not mapped:
        raise ContractError("no_subtitles_retained")
    destination.write_text("\n\n".join(
        f"{i}\n{srt_timestamp(a)} --> {srt_timestamp(b)}\n{text}"
        for i, (a, b, text) in enumerate(mapped, 1)) + "\n", encoding="utf-8")


def build_timeline(*, source: Path, suggestions: dict, subtitles: Path | None,
                   animations: list[dict], output_dir: Path, project_id: str, project_revision: int) -> dict:
    metadata = probe_media(source)
    video = next((v for v in metadata["streams"] if v.get("codec_type") == "video"), None)
    audio = next((v for v in metadata["streams"] if v.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise ContractError("source_requires_video_and_audio")
    duration = float(video.get("duration") or metadata["format"]["duration"])
    ranges, ignored = plan_ranges(suggestions, duration)
    inputs = [{"path": str(source), "sha256": sha256_file(source), "role": "original_video"}]
    clips = [TimelineClip(str(i), r["output_start"], r["output_start"] + r["source_end"] - r["source_start"],
                          "", str(source), "", source_start=r["source_start"])
             for i, r in enumerate(ranges)]
    output_duration = clips[-1].end
    width, height = int(video["width"]), int(video["height"])
    placements = []
    for index, animation in enumerate(animations):
        path = Path(animation["path"]).expanduser().resolve()
        if not path.is_file():
            raise ContractError("animation_missing")
        info = probe_media(path)
        stream = next((v for v in info["streams"] if v.get("codec_type") == "video"), None)
        if stream is None:
            raise ContractError("animation_video_missing")
        clip_duration = float(stream.get("duration") or info["format"]["duration"])
        if "animation_id" in animation:
            matches = [item for item in suggestions["suggestions"] if item.get("type") == "animation"
                       and item.get("animation_id") == animation["animation_id"]]
            if len(matches) != 1 or matches[0].get("ambiguous") is True:
                raise ContractError("animation_position_missing_or_ambiguous")
            start = seconds(matches[0]["start"])
            end = min(seconds(matches[0]["end"]), start + clip_duration)
        else:
            start = seconds(animation["start"])
            end = seconds(animation.get("end", start + clip_duration))
        if end <= start or end > duration + 1e-6 or end - start > clip_duration + 1 / FPS:
            raise ContractError("animation_range_invalid")
        geometry = animation.get("geometry", {"x": 0, "y": 0, "width": stream["width"], "height": stream["height"]})
        if not isinstance(geometry, dict) or set(geometry) != {"x", "y", "width", "height"} or any(type(v) is not int for v in geometry.values()):
            raise ContractError("animation_geometry_invalid")
        x, y, w, h = (geometry[k] for k in ("x", "y", "width", "height"))
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
            raise ContractError("animation_geometry_invalid")
        inputs.append({"path": str(path), "sha256": sha256_file(path), "role": "teaching_animation"})
        for a, b, offset in remap_span(start, end, ranges):
            if frames(b) > frames(a):
                placements.append({"animation_id": animation.get("animation_id"), "start": a, "end": b,
                                   "geometry": geometry})
                clips.append(TimelineClip(f"animation-{index}", a, b, "", str(path), "", source_start=offset, layer="overlay", geometry=(x, y, w, h)))
    otio = require_otio()
    timeline = make_otio_timeline(otio, project_id, project_revision, {}, clips, None)
    otio_path = output_dir / "timeline.otio"
    otio.adapters.write_to_file(timeline, str(otio_path))
    mlt_path = output_dir / "timeline.kdenlive"
    width, height = int(video["width"]), int(video["height"])
    if width % 2 or height % 2:
        raise ContractError("h264_requires_even_dimensions")
    write_kdenlive_project(mlt_path, timeline, project_id, project_revision, width=width, height=height)
    root = ET.parse(mlt_path).getroot()
    tractor = timeline_tractor(root)
    tractor.set("in", "0")
    tractor.set("out", str(frames(output_duration) - 1))
    for transition in list(tractor.findall("transition")):
        transition.set("in", "0")
        transition.set("out", str(frames(output_duration) - 1))
    subtitle_output = None
    if subtitles is not None:
        inputs.append({"path": str(subtitles), "sha256": sha256_file(subtitles), "role": "source_subtitles"})
        subtitle_output = output_dir / "subtitles.srt"
        remap_subtitles(subtitles, subtitle_output, ranges, duration)
        filt = ET.SubElement(tractor, "filter", {"in": "0", "out": str(frames(output_duration) - 1)})
        for name, value in {"mlt_service": "subtitle", "resource": str(subtitle_output),
                            "geometry": "0%/80%:100%x20%:100", "halign": "centre", "valign": "middle",
                            "family": "PingFang SC", "size": str(max(16, height // 25)),
                            "fgcolour": "0xffffffff", "olcolour": "0x000000ff", "outline": "1"}.items():
            ET.SubElement(filt, "property", {"name": name}).text = value
    mlt_path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    cuts, cursor = [], 0.0
    for r in [*ranges, {"source_start": frames(duration)/FPS, "source_end": frames(duration)/FPS}]:
        if r["source_start"] > cursor:
            contributors = [i for i in suggestions["suggestions"] if i.get("auto_cut_allowed") is True
                            and i.get("type") in {"silence", "repetition"}
                            and frames(i["start"])/FPS < r["source_start"] and frames(i["end"])/FPS > cursor]
            if not contributors:
                raise ContractError("executed_cut_evidence_missing")
            cuts.append({"kind": "retake" if any(i["type"] == "repetition" for i in contributors) else "silence",
                         "startSeconds": cursor, "endSeconds": r["source_start"]})
        cursor = r["source_end"]
    return {"executed_cuts": cuts, "animation_placements": placements,
            "inputs": inputs, "fps": float(FPS), "width": width, "height": height,
            "duration": output_duration, "audio_tracks": 1, "video_tracks": 1, "time_map": ranges,
            "subtitles": str(subtitle_output) if subtitle_output else None, "assets": [],
            "subtitle_burned_in": subtitles is not None, "subtitle_bottom_ratio": 0.8 if subtitles else 0,
            "ignored_review_only": ignored, "removed_seconds": frames(duration) / FPS - output_duration}


def render(*, source: Path, suggestions_path: Path, output_dir: Path, subtitles: Path | None = None,
           animations: list[dict] | None = None, project_id: str = "spoken-test", project_revision: int = 1,
           timeout_seconds: float = 300) -> dict:
    if not isinstance(project_id, str) or not project_id.strip() or type(project_revision) is not int or project_revision < 1:
        raise ContractError("render_project_identity_invalid")
    source = source.expanduser().resolve()
    suggestions_path = suggestions_path.expanduser().resolve()
    subtitles = subtitles.expanduser().resolve() if subtitles else None
    output_dir = output_dir.expanduser().resolve()
    melt = melt_executable()
    if not melt:
        raise ContractError("melt_unavailable")
    if output_dir.exists():
        raise ContractError("output_directory_already_exists")
    output_dir.mkdir(parents=True)
    result_path = output_dir / "render-result.json"
    result = {"status": "failed", "editor_backend": "otio_kdenlive", "project_id": project_id,
              "project_revision": project_revision}
    try:
        suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
        manifest = build_timeline(source=source, suggestions=suggestions, subtitles=subtitles,
                                  animations=animations or [], output_dir=output_dir,
                                  project_id=project_id, project_revision=project_revision)
        manifest["inputs"].append({"path": str(suggestions_path), "sha256": sha256_file(suggestions_path), "role": "edit_suggestions"})
        manifest_path = output_dir / "candidate.mp4.manifest.json"
        # Persist producer input hashes before the renderer touches any media.
        write_json(output_dir / "render-plan.json", manifest)
        output = output_dir / "candidate.mp4"
        command = [melt, str(output_dir / "timeline.kdenlive"), "-consumer", f"avformat:{output}",
                   "vcodec=libx264", "acodec=aac", "pix_fmt=yuv420p", "crf=20", "ab=192k",
                   "ar=48000", "real_time=-1", "threads=2", f"out={frames(manifest['duration']) - 1}"]
        with (output_dir / "melt.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       timeout=timeout_seconds, check=False,
                                       env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        if completed.returncode or not output.is_file() or output.stat().st_size == 0:
            raise ContractError("melt_render_failed")
        manifest.update(contract="video_pipeline_manifest.v1", output={"path": str(output), "sha256": sha256_file(output)})
        write_json(manifest_path, manifest)
        checks = review_module().check_pipeline_manifest(manifest_path)
        result.update(status="candidate" if checks["status"] == "passed" else "failed", checks=checks,
                      manifest=str(manifest_path), output=str(output), duration=manifest["duration"],
                      frames=frames(manifest["duration"]), removed_seconds=manifest["removed_seconds"])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result["reason"] = str(exc) if isinstance(exc, ContractError) else type(exc).__name__
        write_json(result_path, result)
        raise ContractError(result["reason"]) from exc
    write_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--suggestions", required=True, type=Path)
    parser.add_argument("--subtitles", type=Path)
    parser.add_argument("--animations", type=Path, help='JSON list of {path,animation_id} or {path,start,end} in original-video seconds')
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-id", default="spoken-test")
    parser.add_argument("--project-revision", default=1, type=int)
    parser.add_argument("--timeout", default=300, type=float)
    args = parser.parse_args()
    try:
        result = render(source=args.source, suggestions_path=args.suggestions, subtitles=args.subtitles,
                        animations=json.loads(args.animations.read_text()) if args.animations else [],
                        output_dir=args.output_dir, project_id=args.project_id,
                        project_revision=args.project_revision, timeout_seconds=args.timeout)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
