"""Build an editable Concat project and export its actual timeline."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
from tempfile import TemporaryDirectory
import time

from review_output_video import read_srt_cues
from .concat_mcp import ConcatMCP
from .interface import BackendError, CloseResult, Description, Probe
from .kdenlive_render import FPS, frames, plan_ranges, probe_media, remap_span, seconds, srt_timestamp
from .otio_kdenlive import sha256_file, write_json
from .precut import executable_cuts


_PROJECT = "concat-project"
_RECEIPT = "render-result.json"
_LOG = "concat-mcp.jsonl"
MIN_RETAINED_SECONDS = 0.2
MIN_CAPTION_SECONDS = 0.3


def _app() -> Path:
    return Path(os.environ.get("CONTENT_OS_CONCAT_APP", "/Applications/Concat.app")).expanduser().resolve()


def _require_app(app: Path):
    binary = app / "Contents/MacOS/concat"
    try:
        mode = binary.stat().st_mode
    except FileNotFoundError as exc:
        raise BackendError("concat_app_unavailable") from exc
    except OSError as exc:
        raise BackendError(f"concat_app_unreadable:{exc}") from exc
    if not stat.S_ISREG(mode) or not os.access(binary, os.X_OK):
        raise BackendError("concat_app_not_executable")


def _display_dimensions(video: dict) -> tuple[int, int]:
    width, height = video["width"], video["height"]
    rotation = None
    for side in video.get("side_data_list") or ():
        if isinstance(side, dict) and side.get("rotation") is not None:
            rotation = side["rotation"]
            break
    if rotation is None and isinstance(video.get("tags"), dict):
        rotation = video["tags"].get("rotate")
    try:
        angle = round(float(rotation)) % 360 if rotation is not None else 0
    except (TypeError, ValueError):
        angle = 0
    return (height, width) if angle in (90, 270) else (width, height)


def _timeline(state: dict, source: Path) -> dict:
    timeline = state["timeline"]
    media = {row["id"]: Path(row["path"]) for row in state["media"]}
    clips = sorted(timeline["clips"], key=lambda clip: clip["start"])
    ranges, captions, overlays = [], [], []
    for clip in clips:
        if clip["kind"] == "text":
            captions.append({key: clip[key] for key in ("start", "end", "text")})
        elif clip["kind"] == "video":
            path = media[clip["media"]]
            start = clip["sourceStart"]
            end = start + clip["duration"] * clip.get("speed", 1)
            if path.resolve() == source:
                ranges.append({"source_start": start, "source_end": end, "output_start": clip["start"]})
            else:
                overlays.append({"path": str(path), "start": clip["start"], "end": clip["end"],
                                 "source_start": start})
    return {"time_map": ranges, "captions": captions, "animations": overlays,
            "duration": timeline["duration"], "fps": state["project"]["fps"]}


def _map_captions(cues: list[tuple[float, float, str]], ranges: list[dict]) -> list[dict]:
    mapped = sorted(
        (
            {"start": a, "end": b, "text": text}
            for start, end, text in cues
            for a, b, _ in remap_span(start, end, ranges)
            if b > a
        ),
        key=lambda cue: (cue["start"], cue["end"]),
    )
    merged: list[dict] = []
    max_gap = 1 / FPS + 1e-9
    for cue in mapped:
        if (merged
                and merged[-1]["text"] == cue["text"]
                and cue["start"] - merged[-1]["end"] <= max_gap):
            merged[-1]["end"] = max(merged[-1]["end"], cue["end"])
        else:
            merged.append(cue)
    return [cue for cue in merged if cue["end"] - cue["start"] >= MIN_CAPTION_SECONDS - 1e-9]


def _write_captions(path: Path, captions: list[dict]) -> Path | None:
    if not captions:
        return None
    path.write_text("\n\n".join(
        f"{i}\n{srt_timestamp(cue['start'])} --> {srt_timestamp(cue['end'])}\n{cue['text']}"
        for i, cue in enumerate(captions, 1)) + "\n", encoding="utf-8")
    return path


def _retained_ranges(ranges: list[dict], min_seconds: float = MIN_RETAINED_SECONDS) -> list[dict]:
    min_frames = math.ceil(min_seconds * FPS - 1e-9)
    kept, output = [], 0
    for span in sorted(ranges, key=lambda row: row["source_start"]):
        start, end = frames(span["source_start"]), frames(span["source_end"])
        if end - start < min_frames:
            continue
        kept.append({"source_start": start / FPS, "source_end": end / FPS, "output_start": output / FPS})
        output += end - start
    if not kept:
        raise BackendError("all_source_removed")
    return kept


def _removed_ranges(ranges: list[dict], duration: float) -> list[tuple[int, int]]:
    cuts = []
    cursor = 0
    total = frames(duration)
    for span in sorted(ranges, key=lambda row: row["source_start"]):
        start, end = frames(span["source_start"]), frames(span["source_end"])
        if start > cursor:
            cuts.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < total:
        cuts.append((cursor, total))
    return cuts


def _cut_source(call, state: dict, cuts: list[tuple[int, int]], duration: float):
    total = frames(duration)
    for frame in sorted({frame for cut in cuts for frame in cut} - {0, total}):
        clips = state["timeline"]["clips"]
        at = frame / FPS
        clip_ids = [clip["id"] for clip in clips if clip["start"] < at < clip["end"]]
        if len(clip_ids) != 1:
            raise BackendError(f"concat_split_target_invalid:{at}")
        state = call("clips_split", clipIds=clip_ids, time=at)
    if cuts:
        clip_ids = []
        for clip in state["timeline"]["clips"]:
            start, end = frames(clip["sourceStart"]), frames(clip["sourceStart"] + clip["duration"])
            if any(a <= start and end <= b for a, b in cuts):
                clip_ids.append(clip["id"])
        if len(clip_ids) != len(cuts):
            raise BackendError("concat_remove_targets_invalid")
        call("clips_remove", clipIds=clip_ids, ripple=True)


def _add_overlays(call, animations: list[dict], suggestions: dict, ranges: list[dict],
                  source_length: float, width: int, height: int, track: str | None):
    for animation in animations:
        path = Path(animation["path"]).expanduser().resolve()
        if path.suffix.lower() != ".mov":
            raise BackendError("concat_overlay_mov_required")
        imported = call("media_import", file=str(path))
        media_id = imported["createdId"]
        media = next(row for row in imported["media"] if row["id"] == media_id)
        length = media["duration"]
        if "animation_id" in animation and "start" not in animation:
            matches = [row for row in suggestions["suggestions"] if row.get("type") == "animation"
                       and row.get("animation_id") == animation["animation_id"]]
            if len(matches) != 1 or matches[0].get("ambiguous") is True:
                raise BackendError("animation_position_missing_or_ambiguous")
            start = seconds(matches[0]["start"])
            end = min(seconds(matches[0]["end"]), start + length)
        else:
            start = seconds(animation["start"])
            end = seconds(animation.get("end", start + length))
        if end <= start or end > source_length + 1e-6 or end - start > length + 1e-6:
            raise BackendError("animation_range_invalid")
        for left, right, offset in remap_span(start, end, ranges):
            if frames(left) == frames(right):
                continue
            if track is None:
                track = call("track_add")["createdId"]
            clip = call("clip_add", mediaId=media_id, trackId=track, start=left)["createdId"]
            tail = offset + right - left - length
            if tail < -1e-6:
                call("clip_trim", clipId=clip, edge="end", delta=tail)
            if offset > 1e-6:
                call("clip_trim", clipId=clip, edge="start", delta=offset)
                call("clips_move", moves=[{"clipId": clip, "trackId": track, "start": left}])
            if "geometry" in animation:
                x, y, w, h = (animation["geometry"][key] for key in ("x", "y", "width", "height"))
                if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
                    raise BackendError("animation_geometry_invalid")
                fit = min(width / media["width"], height / media["height"])
                call("clip_transform", clipId=clip, stretchX=w / (fit * media["width"]),
                     stretchY=h / (fit * media["height"]),
                     offsetX=(x + w / 2) / width - 0.5, offsetY=(y + h / 2) / height - 0.5)
            # A fresh lane per placement prevents a temporarily untrimmed clip from moving its neighbors.
            track = None


def _export(mcp: ConcatMCP, project: Path, output: Path, state: dict, timeout: float) -> dict:
    width, height = state["project"]["width"], state["project"]["height"]
    deadline = time.monotonic() + timeout
    started = mcp.call("export_start", {"path": str(project), "output": str(output),
                                       "width": width, "height": height}, timeout=min(15, timeout))
    while (remaining := deadline - time.monotonic()) > 0:
        result = mcp.call("export_wait", {"job": started["job"], "timeoutSeconds": min(60, remaining)},
                          timeout=remaining)
        if result["state"] == "done":
            if not output.is_file() or output.stat().st_size == 0:
                raise BackendError("concat_export_output_missing")
            return result
        if result["state"] not in {"queued", "running", "started"}:
            raise BackendError(f"concat_export_failed:{result}")
    raise BackendError("concat_timeout:export_wait")


def _owned_project(directory: Path) -> tuple[Path, dict]:
    directory = directory.expanduser().resolve()
    if directory.name == _PROJECT:
        directory = directory.parent
    project = directory / _PROJECT
    try:
        receipt = json.loads((directory / _RECEIPT).read_text(encoding="utf-8"))
        if (receipt["editor_backend"] != "concat" or receipt["status"] != "candidate"
                or Path(receipt["project_dir"]) != project or not (project / "concat.json").is_file()):
            raise BackendError("concat_owned_project_required")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BackendError(f"concat_project_read_failed:{exc}") from exc
    return project, receipt


def _read_timeline(mcp: ConcatMCP, project: Path) -> dict:
    mcp.call("project_open", {"path": str(project)})
    return mcp.call("timeline_read", {"path": str(project)})


class Backend:
    def __init__(self):
        self._readbacks = {}

    def describe(self) -> Description:
        return {"id": "concat", "display_name": "Concat", "license": "AGPL-3.0", "capabilities": {
            "automatic_first_cut": True, "transparent_overlay": True, "chinese_subtitle_burn_in": True,
            "web_refine": False, "undo": True, "read_back": True, "export_formats": ["mp4"],
        }}

    def probe(self) -> Probe:
        result: Probe = {"id": "concat", "installed": False, "version": None, "runnable": False,
                         "status": "unavailable", "reason": None}
        try:
            app = _app()
            _require_app(app)
            result["installed"] = True
            with TemporaryDirectory(prefix="concat-probe-") as scratch:
                root = Path(scratch)
                with ConcatMCP(app, root, root / _LOG) as mcp:
                    info = mcp.call("concat_version", {})
            if not info.get("concat") or info.get("mcp", {}).get("mode") != "headless":
                raise BackendError(f"concat_probe_response_invalid:{info}")
            result.update(version=info["concat"], runnable=True, status="online")
        except (OSError, BackendError) as exc:
            result["reason"] = str(exc)
            if not result["installed"] and result["reason"] != "concat_app_unavailable":
                result["status"] = "unknown"
        return result

    def render(self, *, source: Path, suggestions_path: Path, output_dir: Path,
               subtitles: Path | None = None, animations: list[dict] | None = None,
               project_id: str = "spoken-test", project_revision: int = 1,
               timeout_seconds: float = 300) -> dict:
        if (not isinstance(project_id, str) or not project_id.strip()
                or type(project_revision) is not int or project_revision < 1):
            raise BackendError("render_project_identity_invalid")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise BackendError("concat_timeout_invalid")
        output_dir = output_dir.expanduser().resolve()
        try:
            output_dir.mkdir(parents=True)
        except FileExistsError as exc:
            raise BackendError("output_directory_already_exists") from exc
        source = source.expanduser().resolve()
        suggestions_path = suggestions_path.expanduser().resolve()
        subtitles = subtitles.expanduser().resolve() if subtitles else None
        project = output_dir / _PROJECT
        receipt = {"editor_backend": "concat", "status": "failed", "project_id": project_id,
                   "project_revision": project_revision, "source": str(source),
                   "project_dir": str(project), "call_log": str(output_dir / _LOG),
                   "output": None, "manifest": None, "checks": None,
                   "time_map": None, "duration": None, "frames": None, "removed_seconds": None}
        try:
            app = _app()
            _require_app(app)
            suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
            readback = self._readbacks.get(suggestions_path)
            if readback:
                original, digest, saved_source, identity, revision = readback
                if (source, project_id, project_revision) != (saved_source, identity, revision):
                    raise BackendError("concat_readback_identity_mismatch")
                shutil.copytree(original, project, symlinks=True,
                                ignore=shutil.ignore_patterns("concat.lock", "concat.opened.json", "cache"))
                if sha256_file(project / "concat.json") != digest:
                    raise BackendError("concat_project_changed_since_readback")
            elif isinstance(suggestions, dict) and "concat_readback" in suggestions:
                raise BackendError("concat_readback_session_required")

            paths = [(source, "original_video"), (suggestions_path, "edit_suggestions")]
            if subtitles is not None:
                paths.append((subtitles, "source_subtitles"))
            paths.extend((Path(row["path"]).expanduser().resolve(), "teaching_animation") for row in animations or [])
            inputs = [{"path": str(path), "sha256": sha256_file(path), "role": role} for path, role in paths]
            output = output_dir / "candidate.mp4"
            with ConcatMCP(app, output_dir, output_dir / _LOG) as mcp:
                if readback:
                    state = _read_timeline(mcp, project)
                    source_info = next(row for row in state["media"] if Path(row["path"]).resolve() == source)
                    cuts = _removed_ranges(_timeline(state, source)["time_map"], source_info["duration"])
                    executed = None
                else:
                    state, cuts, executed = self._build(mcp, project, source, suggestions, subtitles, animations or [])
                actual = _timeline(state, source)
                if not actual["time_map"]:
                    raise BackendError("concat_source_clips_missing")
                render = _export(mcp, project, output, state, timeout_seconds)
                mcp.call("project_close", {"path": str(project), "save": False})

            caption_path = _write_captions(output_dir / "subtitles.srt", actual["captions"])
            manifest = output_dir / "candidate.mp4.manifest.json"
            write_json(manifest, {
                "contract": "video_pipeline_manifest.v1", "inputs": inputs, "time_map": actual["time_map"],
                "output": {"path": str(output), "sha256": sha256_file(output)},
                "duration": actual["duration"], "fps": actual["fps"], "width": state["project"]["width"],
                "height": state["project"]["height"], "subtitles": str(caption_path) if caption_path else None,
                "subtitle_burned_in": bool(caption_path), "subtitle_bottom_ratio": 0.85 if caption_path else None,
                "animation_placements": actual["animations"], "executed_cuts": executed or [],
            })
            receipt.update(status="candidate", manifest=str(manifest), output=str(output), time_map=actual["time_map"],
                           duration=actual["duration"], frames=render.get("frame"),
                           removed_seconds=sum(end - start for start, end in cuts) / FPS)
        except (OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
            receipt["reason"] = str(exc) or f"concat_invalid_state:{type(exc).__name__}"
            write_json(output_dir / _RECEIPT, receipt)
            if isinstance(exc, BackendError):
                raise
            raise BackendError(receipt["reason"]) from exc
        write_json(output_dir / _RECEIPT, receipt)
        return receipt

    @staticmethod
    def _build(mcp, project: Path, source: Path, suggestions: dict, subtitles: Path | None, animations: list[dict]):
        executable = executable_cuts(suggestions)
        video = next((row for row in probe_media(source)["streams"] if row.get("codec_type") == "video"), None)
        if video is None:
            raise BackendError("source_video_missing")
        width, height = _display_dimensions(video)
        state = mcp.call("project_create", {
            "location": str(project.parent), "name": project.name,
            "video": {"width": width, "height": height, "rateNum": FPS, "rateDen": 1},
        })

        def call(tool, **args):
            return mcp.call(tool, {"path": str(project), **args})

        tracks = sorted(state["timeline"]["tracks"], key=lambda row: row["index"])
        imported = call("media_import", file=str(source))
        media_id = imported["createdId"]
        length = next(row["duration"] for row in imported["media"] if row["id"] == media_id)
        ranges, _ = plan_ranges({**suggestions, "suggestions": executable}, length)
        ranges = _retained_ranges(ranges)
        cuts = _removed_ranges(ranges, length)
        state = call("clip_add", mediaId=media_id, trackId=tracks[0]["id"], start=0)
        _cut_source(call, state, cuts, length)
        _add_overlays(call, animations, suggestions, ranges, length, width, height,
                      tracks[1]["id"] if len(tracks) > 1 else None)
        if subtitles:
            captions = _map_captions(read_srt_cues(subtitles), ranges)
            if captions:
                call("captions_add", captions=captions)
        call("project_save")
        actual = call("timeline_read")
        got = _timeline(actual, source)["time_map"]
        fields = ("source_start", "source_end", "output_start")
        if len(got) != len(ranges) or any(
                frames(a[key]) != frames(b[key]) for a, b in zip(got, ranges) for key in fields):
            raise BackendError("concat_first_cut_readback_mismatch")
        executed = [{"kind": "retake" if any(item["type"] == "repetition"
                     and frames(item["start"]) < end and frames(item["end"]) > start for item in executable)
                     else "silence", "startSeconds": start / FPS, "endSeconds": end / FPS}
                    for start, end in cuts]
        return actual, cuts, executed

    def open_for_refine(self, *, project_dir: Path) -> dict:
        project, _ = _owned_project(project_dir)
        app = _app()
        _require_app(app)
        try:
            subprocess.run(["/usr/bin/open", "-n", "-a", str(app), "--args", "--project", str(project)],
                           check=True, capture_output=True, text=True, timeout=15)
        except subprocess.CalledProcessError as exc:
            raise BackendError(f"concat_open_failed:{exc.returncode}:{exc.stderr.strip()}") from exc
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BackendError(f"concat_open_failed:{exc}") from exc
        return {"editor_backend": "concat", "opened": True, "local_only": True}

    def read_back(self, *, project_dir: Path) -> dict:
        project, receipt = _owned_project(project_dir)
        app = _app()
        _require_app(app)
        try:
            native = project / "concat.json"
            digest = sha256_file(native)
            with ConcatMCP(app, project.parent, project.parent / _LOG) as mcp:
                state = _read_timeline(mcp, project)
                mcp.call("project_close", {"path": str(project), "save": False})
            if sha256_file(native) != digest:
                raise BackendError("concat_project_changed_during_readback")
            source = Path(receipt["source"])
            actual = _timeline(state, source)
            stem = project.parent / f"readback-{digest}"
            subtitles = _write_captions(stem.with_suffix(".srt"), actual["captions"])
            suggestions = stem.with_suffix(".json")
            write_json(suggestions, {"concat_readback": digest, "time_map": actual["time_map"]})
            identity, revision = receipt["project_id"], receipt["project_revision"]
            self._readbacks[suggestions] = (project, digest, source, identity, revision)
            kwargs = {"source": source, "project_id": identity, "project_revision": revision,
                      "suggestions_path": suggestions, "subtitles": subtitles, "animations": actual["animations"]}
            return {**actual, "engine_revision": digest, "render_kwargs": kwargs}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, BackendError):
                raise
            raise BackendError(f"concat_readback_failed:{exc}") from exc

    def close(self) -> CloseResult:
        # Each MCP call group owns and reaps its child before returning. LaunchServices owns GUI sessions.
        return {"id": "concat", "started_pids": [], "remaining_pids": []}
