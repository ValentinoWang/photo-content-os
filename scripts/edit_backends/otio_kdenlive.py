#!/usr/bin/env python3
"""Create and verify the optional Content OS OTIO/Kdenlive editing handoff.

This backend deliberately produces an open timeline instead of a Jianying
draft.  It never chooses another backend: missing editor software or invalid
media is reported as a blocking error to the caller.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from edl_contract import EDLContractError  # noqa: E402
from edl_contract import normalise_edl  # noqa: E402
from audio_plan import audio_operations, compile_audio_plan, gain_at, probe_audio_source  # noqa: E402
from runtime_paths import local_media_root  # noqa: E402
from edl_contract import parse_seconds as _canonical_parse_seconds  # noqa: E402
from edl_contract import parse_time_range as _canonical_parse_time_range  # noqa: E402
from media import file_sha256 as sha256_file  # noqa: E402
from media import is_raw360_path  # noqa: E402
from media import read_json_object  # noqa: E402


class ContractError(ValueError):
    """Input or output violates the Content OS editing-handoff contract."""


FPS = 30

# Composition stack, bottom first.  A background bed sits under the main cut and
# overlays composite on top of it, so this order is also the MLT track order.
LAYER_STACK = ("background", "primary", "overlay")
DEFAULT_LAYER = "primary"

# Only the primary track carries the "one thing at a time" rule; overlay and
# background clips are expected to run underneath or on top of it.
EXCLUSIVE_LAYERS = frozenset({"primary"})

LAYER_TRACK_NAMES = {
    "background": "背景",
    "primary": "主画面",
    "overlay": "叠加",
}


@dataclass(frozen=True)
class TimelineClip:
    slot: str
    start: float
    end: float
    caption: str
    candidate: str
    note: str
    source_start: float = 0.0
    layer: str = DEFAULT_LAYER
    role: str = ""
    geometry: tuple[int, int, int, int] | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class TimelineTrack:
    layer: str
    lane: int
    clips: tuple[TimelineClip, ...]

    @property
    def name(self) -> str:
        base = LAYER_TRACK_NAMES.get(self.layer, self.layer)
        return base if self.lane == 1 else f"{base} {self.lane}"


def read_json(path: Path) -> dict[str, Any]:
    return read_json_object(path, error=ContractError)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def revision_basis_descriptor(
    path: Path,
    *,
    project_id: str,
    project_revision: int,
) -> dict[str, str]:
    """Return a hash-bound, identity-checked confirmed revision request."""

    resolved = path.expanduser().resolve()
    basis = read_json(resolved)
    if basis.get("spec_version") != "content_os_v0.2" or basis.get("doc_type") != "confirmed_revision_basis":
        raise ContractError("revision basis is not a confirmed Content OS v0.2 revision")
    if (
        basis.get("project_id") != project_id
        or basis.get("project_revision") != project_revision
        or basis.get("editor_backend") != "otio_kdenlive"
    ):
        raise ContractError("revision basis does not match project_id, project_revision, or editor_backend")
    change_request_id = basis.get("change_request_id")
    if not isinstance(change_request_id, str) or not change_request_id.strip():
        raise ContractError("revision basis requires a non-empty change_request_id")
    summary = basis.get("change_summary")
    if not isinstance(summary, dict) or any(
        not isinstance(summary.get(key), str) or not summary[key].strip()
        for key in ("requested_location", "requested_change", "reason")
    ):
        raise ContractError("revision basis requires a structured change_summary")
    return {
        "path": str(resolved),
        "sha256": sha256_file(resolved),
        "change_request_id": change_request_id.strip(),
    }


def write_result(path: Path | None, data: dict[str, Any]) -> None:
    if path is not None:
        write_json(path, data)
    print(json.dumps(data, ensure_ascii=False))


def parse_time_range(value: str) -> tuple[float, float]:
    """Parse the canonical "start-end" seconds string produced by edl_contract.

    Delegates to the shared edl_contract implementation so this backend
    accepts the same format the canonical EDL producers actually emit
    (e.g. "0.000-2.000"), instead of requiring a bespoke trailing "s".
    """
    try:
        return _canonical_parse_time_range(value, path="time_range")
    except EDLContractError as exc:
        raise ContractError(f"invalid clip time_range: {value!r}: {exc}") from exc


def is_raw360(value: str) -> bool:
    """Delegates to the shared media.is_raw360_path (see L-02 dedup).

    This backend only ever has a candidate path string here (no full
    manifest item), so it calls is_raw360_path rather than is_raw360_item.
    Note this is a deliberate narrowing versus the previous implementation:
    the old RAW360_TOKENS matched ".osv"/".lrf" and "不可直用"/"360原始" as
    bare substrings anywhere in the string, which could misjudge an
    unrelated file whose name or directory happened to contain those
    characters. is_raw360_path matches extensions by exact suffix and path
    tokens as whole, specific phrases instead. Since this is the one backend
    that hard-fails the whole timeline generation on a raw-360 match (see
    load_edl below), reducing false positives here is the safer default.
    """
    return is_raw360_path(value)


def candidate_resource(candidate: str) -> str:
    """Return a Kdenlive/OTIO-friendly resource URL without losing Unicode."""
    source = Path(candidate).expanduser()
    if source.is_absolute():
        return source.as_uri()
    return "file://" + quote(candidate, safe="/%:@+,-._~()")


def load_edl(edl_path: Path, project_id: str, project_revision: int) -> tuple[dict[str, Any], list[TimelineClip]]:
    edl = read_json(edl_path)
    if edl.get("doc_type") != "edit_decision_list":
        raise ContractError("EDL doc_type must be edit_decision_list")
    actual_project_id = str(edl.get("project_id") or "")
    if actual_project_id != project_id:
        raise ContractError(f"EDL project_id mismatch: expected {project_id}, got {actual_project_id or 'empty'}")
    if project_revision < 1:
        raise ContractError("project_revision must be a positive integer")
    raw_clips = edl.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise ContractError("EDL clips must be a non-empty list")

    clips: list[TimelineClip] = []
    # Overlap is judged per composition layer.  A v1 EDL has no `layer` on any
    # clip, so everything lands on "primary" and this stays the pre-v2 check.
    previous_end_by_layer: dict[str, float] = {}
    for index, raw in enumerate(raw_clips, start=1):
        if not isinstance(raw, dict):
            raise ContractError(f"EDL clip #{index} must be an object")
        start, end = parse_time_range(str(raw.get("time_range") or ""))
        layer = str(raw.get("layer") or DEFAULT_LAYER)
        if layer not in LAYER_STACK:
            raise ContractError(
                f"EDL clip #{index} has unknown layer {layer!r}; expected one of {', '.join(LAYER_STACK)}"
            )
        if layer in EXCLUSIVE_LAYERS and start < previous_end_by_layer.get(layer, 0.0):
            raise ContractError(
                f"EDL clip #{index} overlaps the preceding clip on the {layer} layer"
            )
        candidates = raw.get("candidate_files")
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], str):
            raise ContractError(f"EDL clip #{index} needs a first candidate_files entry")
        candidate = candidates[0].strip()
        if not candidate:
            raise ContractError(f"EDL clip #{index} has an empty candidate")
        if is_raw360(candidate):
            raise ContractError(
                f"EDL clip #{index} selects raw 360 media; export a reframed editable video before timeline generation"
            )
        try:
            source_start = _canonical_parse_seconds(
                raw.get("source_start_sec", 0), path=f"clips[{index - 1}].source_start_sec"
            )
        except EDLContractError as exc:
            raise ContractError(f"invalid EDL clip #{index} source_start_sec: {exc}") from exc
        clips.append(
            TimelineClip(
                slot=str(raw.get("slot") or index),
                start=start,
                end=end,
                caption=str(raw.get("caption") or "").strip(),
                candidate=candidate,
                note=str(raw.get("edit_note") or "").strip(),
                source_start=source_start,
                layer=layer,
                role=str(raw.get("role") or "").strip(),
            )
        )
        previous_end_by_layer[layer] = end
    return edl, clips


def clips_by_layer(clips: list[TimelineClip]) -> list[TimelineTrack]:
    """Partition logical layers into non-overlapping physical tracks.

    Empty layers are dropped so a v1 EDL still produces exactly one track.
    Within a logical layer, each clip uses the first lane whose previous clip
    has ended. This preserves legal overlay/background overlaps without moving
    either clip on the timeline.
    """
    grouped: list[TimelineTrack] = []
    for layer in LAYER_STACK:
        members = sorted(
            (clip for clip in clips if clip.layer == layer),
            key=lambda item: (item.start, item.end, item.slot),
        )
        lanes: list[list[TimelineClip]] = []
        lane_ends: list[float] = []
        for clip in members:
            for lane_index, lane_end in enumerate(lane_ends):
                if clip.start >= lane_end:
                    lanes[lane_index].append(clip)
                    lane_ends[lane_index] = clip.end
                    break
            else:
                lanes.append([clip])
                lane_ends.append(clip.end)
        grouped.extend(
            TimelineTrack(layer=layer, lane=lane_index, clips=tuple(lane_clips))
            for lane_index, lane_clips in enumerate(lanes, start=1)
        )
    return grouped


def require_otio() -> Any:
    try:
        import opentimelineio as otio
    except ImportError as exc:
        raise ContractError(
            "OpenTimelineIO is not installed for this Python runtime; install it in the runner environment before using otio_kdenlive"
        ) from exc
    return otio


def frames(seconds: float) -> int:
    return int(round(seconds * FPS))


def clip_frame_range(clip: TimelineClip) -> tuple[int, int]:
    start_frame = frames(clip.start)
    end_frame = frames(clip.end)
    if end_frame <= start_frame:
        raise ContractError(
            f"EDL clip {clip.slot} is shorter than one frame at {FPS} fps"
        )
    return start_frame, end_frame


def plain_metadata(value: Any) -> dict[str, Any]:
    """OTIO keeps metadata in AnyDictionary, which is mapping-like not dict."""
    try:
        return {str(key): value[key] for key in value}
    except (TypeError, KeyError):
        return {}


def make_otio_track(
    otio: Any,
    project_id: str,
    project_revision: int,
    timeline_track: TimelineTrack,
) -> Any:
    """Build one non-overlapping physical track in composition order."""
    track = otio.schema.Track(
        name=timeline_track.name, kind=otio.schema.TrackKind.Video
    )
    track.metadata["content_os"] = {
        "layer": timeline_track.layer,
        "physical_lane": timeline_track.lane,
    }
    cursor_frame = 0
    for clip in timeline_track.clips:
        clip_start_frame, clip_end_frame = clip_frame_range(clip)
        duration_frames = clip_end_frame - clip_start_frame
        if clip_start_frame > cursor_frame:
            track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, FPS),
                duration=otio.opentime.RationalTime(clip_start_frame - cursor_frame, FPS),
            )))
        external = otio.schema.ExternalReference(
            target_url=candidate_resource(clip.candidate),
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(frames(clip.source_start), FPS),
                duration=otio.opentime.RationalTime(duration_frames, FPS),
            ),
        )
        segment = otio.schema.Clip(
            name=f"{clip.slot}_{Path(clip.candidate).name}",
            media_reference=external,
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(frames(clip.source_start), FPS),
                duration=otio.opentime.RationalTime(duration_frames, FPS),
            ),
        )
        segment.metadata["content_os"] = {
            "project_id": project_id,
            "project_revision": project_revision,
            "slot": clip.slot,
            "timeline_start_sec": clip.start,
            "source_start_sec": clip.source_start,
            "candidate_file": clip.candidate,
            "edit_note": clip.note,
            "media_exists_at_generation": Path(clip.candidate).expanduser().exists(),
            "layer": clip.layer,
            "physical_lane": timeline_track.lane,
            **({"role": clip.role} if clip.role else {}),
            **({"geometry": list(clip.geometry)} if clip.geometry else {}),
        }
        track.append(segment)
        if clip.caption:
            track.markers.append(otio.schema.Marker(
                name=clip.caption,
                marked_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(clip_start_frame, FPS),
                    duration=otio.opentime.RationalTime(duration_frames, FPS),
                ),
                color=otio.schema.Marker.Color.YELLOW,
            ))
        cursor_frame = clip_end_frame
    return track


def make_otio_timeline(
    otio: Any,
    project_id: str,
    project_revision: int,
    edl: dict[str, Any],
    clips: list[TimelineClip],
    revision_basis: dict[str, str] | None,
    *,
    audio_plan: dict[str, Any] | None = None,
    audio_sources: dict[str, str] | None = None,
) -> Any:
    grouped = clips_by_layer(clips)
    timeline = otio.schema.Timeline(name=f"{project_id}_r{project_revision}")
    for timeline_track in grouped:
        timeline.tracks.append(
            make_otio_track(otio, project_id, project_revision, timeline_track)
        )
    logical_layers = list(dict.fromkeys(track.layer for track in grouped))
    timeline.metadata["content_os"] = {
        "spec_version": "content_os_v0.2",
        "project_id": project_id,
        "project_revision": project_revision,
        "editor_backend": "otio_kdenlive",
        "source_edl": str(edl.get("project_id") or project_id),
        "fps": FPS,
        "layers": logical_layers,
        "physical_track_count": len(grouped),
    }
    if revision_basis is not None:
        timeline.metadata["content_os"]["revision_basis"] = revision_basis
    if audio_plan is not None:
        if audio_plan.get("source_validation") != "passed":
            raise ContractError("audio_source_preflight_required")
        for lane in range(audio_plan["physical_track_count"]):
            track = otio.schema.Track(name=f"声音 {lane + 1}", kind=otio.schema.TrackKind.Audio)
            track.metadata["content_os"] = {"layer": "audio", "physical_lane": lane + 1}
            cursor = 0
            for sound in sorted((s for s in audio_plan["segments"] if s["physical_track"] == lane), key=lambda s: s["timeline_start_sec"]):
                candidate = (audio_sources or {}).get(sound['source'], sound['source'])
                start, end = frames(sound["timeline_start_sec"]), frames(sound["timeline_end_sec"])
                if end <= start:
                    raise ContractError("audio_shorter_than_frame; use a longer sound segment")
                if start < cursor:
                    raise ContractError("audio_quantized_lane_overlap")
                if start > cursor:
                    track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(
                        otio.opentime.RationalTime(0, FPS), otio.opentime.RationalTime(start - cursor, FPS))))
                item = otio.schema.Clip(name=sound["id"], media_reference=otio.schema.ExternalReference(target_url=candidate_resource(candidate)),
                                        source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(frames(sound["source_start_sec"]), FPS),
                                                                             otio.opentime.RationalTime(end - start, FPS)))
                item.metadata["content_os"] = {"audio_segment": sound, "candidate_file": candidate,
                                                "timeline_start_frame": start, "timeline_start_sec": sound["timeline_start_sec"]}
                track.append(item)
                cursor = end
            timeline.tracks.append(track)
        timeline.metadata["content_os"]["audio_plan"] = audio_plan
        timeline.metadata["content_os"]["audio_sources"] = audio_sources or {}
        timeline.metadata["content_os"]["physical_track_count"] = len(timeline.tracks)
    return timeline


def plain_data(value):
    """Convert OTIO's JSON metadata containers without losing nested arrays."""
    if hasattr(value, "items"):
        return {str(k): plain_data(v) for k, v in value.items()}
    if not isinstance(value, (str, bytes)) and hasattr(value, "__iter__"):
        return [plain_data(v) for v in value]
    return value


def prepare_edl_audio(edl: dict[str, Any], media_root: Path | None = None):
    """Resolve explicitly selected sources, then consume the frozen compiler."""
    try:
        normalized = normalise_edl(edl)
        root = local_media_root(media_root)
        def resolve(value):
            source = Path(value).expanduser()
            source = source.resolve() if source.is_absolute() else (root / source).resolve()
            if is_raw360(str(source)) or not source.is_file():
                raise ContractError("audio_source_missing_or_raw360; select readable editable media")
            return str(source)
        for clip in normalized["clips"]:
            source = resolve(clip.get("source_file") or clip["candidate_files"][0])
            clip.update(source_file=source, candidate_files=[source])
        for section in ("audio_beds", "music"):
            for track in normalized.get(section, []):
                track["source"] = resolve(track["source"])
        sources = {c["source_file"] for c in normalized["clips"] if not c.get("audio_mute")}
        sources.update(t["source"] for section in ("audio_beds", "music") for t in normalized.get(section, []))
        info = {source: probe_audio_source(Path(source)) for source in sources}
        plan = compile_audio_plan(normalized, source_info=info)
    except EDLContractError as exc:
        raise ContractError(str(exc)) from exc
    clips = [TimelineClip(str(c["slot"]), *parse_time_range(c["time_range"]), c["caption"], c["source_file"], c["edit_note"],
                          source_start=c["source_start_sec"], layer=c.get("layer", DEFAULT_LAYER), role=c.get("role", "")) for c in normalized["clips"]]
    return normalized, clips, plan


def audio_level_keyframes(sound: dict[str, Any], duration_frames: int) -> str:
    """MLT volume ramps from the previous frame's amplitude to this frame's.

    Sampling the frozen envelope at frame ends compensates that one-frame
    evaluation lag. Zero is represented below PCM resolution (-120 dB).
    """
    start = sound["timeline_start_sec"]
    end = sound["timeline_end_sec"]
    values = []
    for frame in range(duration_frames):
        time = min(end, start + (frame + 1) / FPS)
        gain = gain_at(sound, time)
        level = 20 * math.log10(gain) if gain > 1e-6 else -120.0
        values.append(f"{frame}={level:.9f}")
    return ";".join(values)


def timeline_manifest(
    project_id: str,
    project_revision: int,
    clips: list[TimelineClip],
    otio_path: Path,
    revision_basis: dict[str, str] | None,
) -> dict[str, Any]:
    physical_tracks = clips_by_layer(clips)
    lane_by_clip = {
        id(clip): timeline_track.lane
        for timeline_track in physical_tracks
        for clip in timeline_track.clips
    }
    manifest = {
        "doc_type": "otio_kdenlive_handoff_manifest",
        "spec_version": "content_os_v0.2",
        "project_id": project_id,
        "project_revision": project_revision,
        "editor_backend": "otio_kdenlive",
        "otio": str(otio_path),
        "fps": FPS,
        "clips": [
            {
                "slot": clip.slot,
                "timeline_start_sec": clip.start,
                "duration_sec": clip.duration,
                "source_start_sec": clip.source_start,
                "candidate_file": clip.candidate,
                "needs_relink": not Path(clip.candidate).expanduser().exists(),
                "caption": clip.caption,
                "layer": clip.layer,
                "physical_lane": lane_by_clip[id(clip)],
                **({"role": clip.role} if clip.role else {}),
            }
            for clip in clips
        ],
        "layers": list(dict.fromkeys(track.layer for track in physical_tracks)),
        "physical_tracks": [
            {
                "layer": track.layer,
                "physical_lane": track.lane,
                "name": track.name,
            }
            for track in physical_tracks
        ],
    }
    if revision_basis is not None:
        manifest["revision_basis"] = revision_basis
    return manifest


def write_handoff_readme(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# 可编辑时间线交接",
        "",
        f"- 项目：{manifest['project_id']}",
        f"- 版本：{manifest['project_revision']}",
        "- 交接方式：可编辑时间线",
        "- 打开方式：在 Kdenlive 打开 `timeline.kdenlive`；缺失素材按 `manifest.json` 中的候选路径重新链接。",
        "- 注意：本版本不自动替换为其他剪辑方式；若要切换，请先在 Media Bot 确认修改影响并新建项目版本。",
        "",
        "## 片段",
        "",
        "| 顺序 | 开始（秒） | 时长（秒） | 素材 | 字幕 |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for clip in manifest["clips"]:
        lines.append(
            f"| {clip['slot']} | {clip['timeline_start_sec']:.3f} | {clip['duration_sec']:.3f} | {clip['candidate_file']} | {clip['caption']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_otio(args: argparse.Namespace) -> int:
    otio = require_otio()
    project_id = args.project_id.strip()
    storyboard = args.storyboard.resolve()
    if not storyboard.is_file() or not storyboard.read_text(encoding="utf-8").strip():
        raise ContractError("Storyboard is missing or empty")
    edl = read_json(args.edl.resolve())
    audio_plan = None
    if audio_operations(edl):
        if edl.get("project_id") != project_id or edl.get("project_revision", args.project_revision) != args.project_revision:
            raise ContractError("edl_project_identity_mismatch")
        edl, clips, audio_plan = prepare_edl_audio(edl)
    else:
        edl, clips = load_edl(args.edl.resolve(), project_id, args.project_revision)
    revision_basis = (
        revision_basis_descriptor(args.revision_basis, project_id=project_id, project_revision=args.project_revision)
        if args.revision_basis is not None
        else None
    )
    output_root = args.output_root.resolve() / str(args.project_revision)
    output_root.mkdir(parents=True, exist_ok=True)
    otio_path = output_root / "timeline.otio"
    timeline = make_otio_timeline(otio, project_id, args.project_revision, edl, clips, revision_basis, audio_plan=audio_plan)
    otio.adapters.write_to_file(timeline, str(otio_path))
    manifest = timeline_manifest(project_id, args.project_revision, clips, otio_path, revision_basis)
    if audio_plan is not None:
        manifest["audio_plan"] = audio_plan
    manifest_path = output_root / "manifest.json"
    write_json(manifest_path, manifest)
    write_handoff_readme(output_root / "剪辑交接说明.md", manifest)
    write_result(
        args.result_output,
        {
            "status": "done",
            "project_id": project_id,
            "project_revision": args.project_revision,
            "editor_backend": "otio_kdenlive",
            "otio": str(otio_path),
            "manifest": str(manifest_path),
            "storyboard": str(storyboard),
            "clip_count": len(clips),
            "needs_relink_count": sum(clip["needs_relink"] for clip in manifest["clips"]),
        },
    )
    return 0


def kdenlive_executable() -> str | None:
    configured = os.environ.get("CONTENT_OS_KDENLIVE_EXECUTABLE")
    if configured is not None:
        candidate = Path(configured).expanduser()
        return str(candidate.resolve()) if candidate.is_file() and os.access(candidate, os.X_OK) else None
    executable = shutil.which("kdenlive")
    if executable:
        return executable
    bundled = Path("/Applications/kdenlive.app/Contents/MacOS/kdenlive")
    return str(bundled) if bundled.is_file() and os.access(bundled, os.X_OK) else None


KDENLIVE_REOPEN_PROBE_SECONDS = 2.0
KDENLIVE_SHUTDOWN_TIMEOUT_SECONDS = 5.0


def probe_kdenlive_version(executable: str) -> str:
    try:
        probe = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError(f"Kdenlive version probe failed: {exc}") from exc
    if probe.returncode != 0:
        raise ContractError(f"Kdenlive version probe failed with exit code {probe.returncode}")
    lines = (probe.stdout or probe.stderr).strip().splitlines()
    if not lines:
        raise ContractError("Kdenlive version probe returned no version")
    return lines[0]


def probe_kdenlive_reopen(executable: str, project_path: Path) -> None:
    """Open the project in the real application and require it to stay open."""

    try:
        process = subprocess.Popen(
            [executable, "--no-welcome", str(project_path)],
            cwd=project_path.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ContractError(f"Kdenlive project reopen probe failed: {exc}") from exc
    try:
        return_code = process.wait(timeout=KDENLIVE_REOPEN_PROBE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            process.terminate()
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=KDENLIVE_SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=KDENLIVE_SHUTDOWN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as exc:
                raise ContractError("Kdenlive project reopen probe could not stop the application") from exc
        return
    raise ContractError(
        "Kdenlive project reopen probe failed: "
        f"application exited with code {return_code} before the project remained open"
    )


def safe_xml_resource(candidate: str) -> str:
    return str(Path(candidate).expanduser()) if Path(candidate).is_absolute() else candidate


def xml_properties(element, values):
    for name, value in values.items():
        ET.SubElement(element, "property", {"name": name}).text = str(value)


def timeline_tractor(root):
    for element in root.findall("tractor"):
        if element.find("property[@name='content_os:timeline']") is not None:
            return element
    master = next((t for t in root.findall("tractor") if t.find("property[@name='kdenlive:projectTractor']") is not None), None)
    if master is not None:
        track = master.find("track")
        if track is not None:
            sequence = root.find(f"tractor[@id='{track.get('producer')}']")
            if sequence is not None:
                return sequence
    raise ContractError("kdenlive_sequence_missing")


def wrap_kdenlive_document(root, sequence, playlist_ids, project_id, revision, total):
    """Give the render graph the editable bin/track/sequence structure Kdenlive reads."""
    if total <= 0:
        raise ContractError("kdenlive_empty_timeline")
    sequence_id = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"content-os:{project_id}:{revision}")) + "}"
    sequence.set("id", sequence_id)
    sequence.set("in", "0")
    sequence.set("out", str(total - 1))
    xml_properties(sequence, {"content_os:timeline": 1, "kdenlive:uuid": sequence_id,
                             "kdenlive:clipname": project_id})
    root.remove(sequence)
    explicit_audio = root.find("property[@name='content_os:audio_plan']") is not None
    resources = {}
    for producer in root.findall("producer"):
        resource = producer.find("property[@name='resource']").text
        # Timeline audio has its own bin item: sharing the video's bin ID makes
        # Kdenlive rebuild it from the effect-free video producer on save.
        segment = producer.findtext("property[@name='content_os:audio_segment_id']")
        bin_id = resources.setdefault((resource, segment), str(len(resources) + 4))
        xml_properties(producer, {"mlt_service": "avformat", "kdenlive:id": bin_id})
    background = ET.Element("producer", {"id": "black", "in": "0", "out": str(total - 1)})
    xml_properties(background, {"mlt_service": "color", "resource": "black", "length": total,
                                "eof": "continue", "kdenlive:playlistid": "black_track"})
    root.insert(1, background)
    # Kdenlive expects a track tractor with two playlists for each editing lane.
    for index, playlist_id in enumerate(playlist_ids):
        playlist = root.find(f"playlist[@id='{playlist_id}']")
        for entry in playlist.findall("entry"):
            producer = root.find(f"producer[@id='{entry.get('producer')}']")
            xml_properties(entry, {"kdenlive:id": producer.find("property[@name='kdenlive:id']").text})
        empty_id = f"empty{index}"
        ET.SubElement(root, "playlist", {"id": empty_id})
        track = ET.SubElement(root, "tractor", {"id": f"track{index}", "in": "0", "out": str(total - 1)})
        name = playlist.find("property[@name='kdenlive:track_name']").text
        xml_properties(track, {"kdenlive:timeline_active": 1, "kdenlive:track_name": name})
        audio = playlist.find("property[@name='kdenlive:audio_track']") is not None
        if audio:
            xml_properties(track, {"kdenlive:audio_track": 1})
        hidden = "video" if audio else "audio"
        ET.SubElement(track, "track", {"producer": playlist_id, "hide": hidden})
        ET.SubElement(track, "track", {"producer": empty_id, "hide": hidden})
    original_tracks = sequence.findall("track")
    for index, track in enumerate(original_tracks):
        track.set("producer", f"track{index}")
        if explicit_audio:
            playlist = root.find(f"playlist[@id='{playlist_ids[index]}']")
            track.set("hide", "video" if playlist.find("property[@name='kdenlive:audio_track']") is not None else "audio")
    sequence.insert(0, ET.Element("track", {"producer": "black"}))
    for transition in sequence.findall("transition"):
        for name in ("a_track", "b_track"):
            prop = transition.find(f"property[@name='{name}']")
            prop.text = str(int(prop.text) + 1)
    # Keep primary audio as an independent, editable lane; overlay audio is muted.
    primary = next((root.find(f"playlist[@id='{pid}']") for pid in playlist_ids
                    if root.find(f"playlist[@id='{pid}']/property[@name='content_os:layer']").text == "primary"), None)
    if primary is not None and not explicit_audio:
        import copy
        audio = copy.deepcopy(primary)
        audio.set("id", "audio_playlist")
        for prop in list(audio.findall("property")):
            audio.remove(prop)
        xml_properties(audio, {"kdenlive:audio_track": 1})
        root.append(audio)
        ET.SubElement(root, "playlist", {"id": "audio_empty"})
        audio_track = ET.SubElement(root, "tractor", {"id": "audio_track", "in": "0", "out": str(total - 1)})
        xml_properties(audio_track, {"kdenlive:audio_track": 1, "kdenlive:timeline_active": 1})
        ET.SubElement(audio_track, "track", {"producer": "audio_playlist", "hide": "video"})
        ET.SubElement(audio_track, "track", {"producer": "audio_empty", "hide": "video"})
        ET.SubElement(sequence, "track", {"producer": "audio_track", "hide": "video"})
    if explicit_audio:
        for index, playlist_id in enumerate(playlist_ids):
            playlist = root.find(f"playlist[@id='{playlist_id}']")
            if playlist.find("property[@name='kdenlive:audio_track']") is not None:
                mix = ET.SubElement(sequence, "transition", {"in": "0", "out": str(total - 1)})
                xml_properties(mix, {"mlt_service": "mix", "a_track": 0, "b_track": index + 1,
                                     "always_active": 1, "sum": 1, "internal_added": 237, "accepts_blanks": 1})
    root.append(sequence)
    main_bin = ET.SubElement(root, "playlist", {"id": "main_bin"})
    xml_properties(main_bin, {"kdenlive:docproperties.uuid": sequence_id,
                             "kdenlive:docproperties.version": "1.1", "xml_retain": 1,
                             "kdenlive:docproperties.projectid": project_id,
                             "kdenlive:docproperties.content_os_revision": revision,
                             "content_os.project_revision": revision})
    ET.SubElement(main_bin, "entry", {"producer": sequence_id, "in": "0", "out": str(total - 1)})
    seen = set()
    for producer in root.findall("producer"):
        prop = producer.find("property[@name='kdenlive:id']")
        if prop is not None and prop.text not in seen:
            seen.add(prop.text)
            ET.SubElement(main_bin, "entry", {"producer": producer.get("id"), "in": "0"})
    master = ET.SubElement(root, "tractor", {"id": "project_tractor", "in": "0", "out": str(total - 1)})
    xml_properties(master, {"kdenlive:projectTractor": 1})
    ET.SubElement(master, "track", {"producer": sequence_id, "in": "0", "out": str(total - 1)})


def write_kdenlive_project(path: Path, otio_data: Any, project_id: str, project_revision: int, *, width: int = 1080, height: int = 1920) -> int:
    if width <= 0 or height <= 0:
        raise ContractError("timeline dimensions must be positive")
    root = ET.Element("mlt", {"LC_NUMERIC": "C", "version": "7.39.0", "producer": "main_bin", "title": f"{project_id}_r{project_revision}"})
    ET.SubElement(root, "profile", {"description": f"Content OS {width}x{height} {FPS} fps", "width": str(width), "height": str(height), "frame_rate_num": str(FPS), "frame_rate_den": "1", "progressive": "1", "sample_aspect_num": "1", "sample_aspect_den": "1", "display_aspect_num": str(width), "display_aspect_den": str(height)})
    ET.SubElement(root, "property", {"name": "kdenlive:docproperties.projectid"}).text = project_id
    ET.SubElement(root, "property", {"name": "content_os.project_revision"}).text = str(project_revision)
    tracks = list(otio_data.tracks)
    explicit_audio = "audio_plan" in plain_metadata(otio_data.metadata).get("content_os", {})
    if explicit_audio:
        xml_properties(root, {"content_os:audio_plan": "audio_plan_v1", "content_os:audio_envelope_resolution_sec": 1 / FPS})
    if not tracks:
        raise ContractError("OTIO timeline has no tracks")

    # One MLT playlist per OTIO track, in the timeline's own order.  OTIO stacks
    # tracks bottom-first and so does MLT, so the order carries straight over.
    count = 0
    playlist_ids: list[str] = []
    for track_index, track in enumerate(tracks):
        playlist_id = f"playlist{track_index}"
        playlist_ids.append(playlist_id)
        playlist = ET.SubElement(root, "playlist", {"id": playlist_id})
        track_metadata = plain_metadata(track.metadata).get("content_os", {})
        track_metadata = plain_metadata(track_metadata)
        layer = str(track_metadata.get("layer") or "")
        audio_track = track.kind == "Audio"
        if audio_track:
            xml_properties(playlist, {"kdenlive:audio_track": 1})
        if layer:
            ET.SubElement(
                playlist, "property", {"name": "content_os:layer"}
            ).text = layer
        lane = track_metadata.get("physical_lane")
        if lane is not None:
            ET.SubElement(
                playlist, "property", {"name": "content_os:physical_lane"}
            ).text = str(lane)
        ET.SubElement(
            playlist, "property", {"name": "kdenlive:track_name"}
        ).text = str(track.name or layer or playlist_id)
        for item in track:
            if item.__class__.__name__ == "Gap":
                ET.SubElement(playlist, "blank", {"length": str(item.source_range.duration.to_frames())})
                continue
            if item.__class__.__name__ != "Clip":
                continue
            reference = item.media_reference
            target = str(getattr(reference, "target_url", ""))
            metadata = plain_metadata(item.metadata).get("content_os", {})
            candidate = str(metadata.get("candidate_file") or target)
            producer_id = f"producer{count}"
            source_in = int(item.source_range.start_time.to_frames())
            duration_frames = int(item.source_range.duration.to_frames())
            if duration_frames <= 0:
                raise ContractError(f"OTIO clip {item.name!r} has no positive source duration")
            source_out = source_in + duration_frames - 1
            producer = ET.SubElement(
                root,
                "producer",
                {"id": producer_id, "in": "0", "out": str(source_out)},
            )
            ET.SubElement(producer, "property", {"name": "resource"}).text = safe_xml_resource(candidate)
            ET.SubElement(producer, "property", {"name": "kdenlive:clipname"}).text = item.name
            ET.SubElement(producer, "property", {"name": "content_os:needs_relink"}).text = "1" if not Path(candidate).expanduser().exists() else "0"
            if audio_track:
                sound = plain_data(metadata["audio_segment"])
                xml_properties(producer, {"content_os:audio_segment_id": sound["id"]})
                volume = ET.SubElement(producer, "filter", {"in": str(source_in), "out": str(source_out)})
                xml_properties(volume, {"mlt_service": "volume", "kdenlive_id": "volume", "kdenlive:ix": 1,
                                        "level": audio_level_keyframes(sound, duration_frames)})
                # Volume initializes its first frame at the current level. A
                # persistent sample ramp supplies that frame without relying on
                # MLT's private cache, which native XML saves deliberately omit.
                fade = ET.SubElement(producer, "filter", {"in": str(source_in), "out": str(source_in)})
                xml_properties(fade, {"mlt_service": "avfilter.afade", "kdenlive_id": "fadein", "internal_added": 1,
                                      "av.type": "in", "av.start_time": metadata["timeline_start_frame"] / FPS,
                                      "av.duration": 1 / FPS})
            if metadata.get("geometry"):
                x, y, w, h = metadata["geometry"]
                transform = ET.SubElement(producer, "filter", {"in": "0", "out": str(source_out)})
                xml_properties(transform, {"mlt_service": "affine", "kdenlive:id": "affine",
                                           "transition.rect": f"{x} {y} {w} {h} 1",
                                           "transition.distort": 1, "transition.fill": 1,
                                           "transition.b_scaled": 1, "transition.valign": "top",
                                           "transition.halign": "left"})

            ET.SubElement(
                playlist,
                "entry",
                {"producer": producer_id, "in": str(source_in), "out": str(source_out)},
            )
            count += 1

    # MLT resolves producer references while reading XML, in document order.
    # Referenced media must precede every playlist that consumes it.
    for playlist_id in playlist_ids:
        playlist = root.find(f"playlist[@id='{playlist_id}']")
        root.remove(playlist)
        root.append(playlist)
    tractor = ET.SubElement(root, "tractor", {"id": "tractor0"})
    for playlist_id in playlist_ids:
        ET.SubElement(tractor, "track", {"producer": playlist_id})
    # Without an explicit compositing transition MLT simply shows the topmost
    # track opaque, which would hide everything beneath an overlay.  Blend each
    # track above the bottom one onto the accumulated result instead.
    for track_index in range(1, len(playlist_ids)):
        if tracks[track_index].kind == "Audio":
            continue
        transition = ET.SubElement(
            tractor,
            "transition",
            {"id": f"transition{track_index - 1}"},
        )
        for name, value in {"a_track": "0", "b_track": str(track_index), "mlt_service": "frei0r.cairoblend"}.items():
            ET.SubElement(transition, "property", {"name": name}).text = value
    wrap_kdenlive_document(root, tractor, playlist_ids, project_id, project_revision,
                           int(otio_data.duration().to_frames()))
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    return count


def generate_kdenlive(args: argparse.Namespace) -> int:
    otio = require_otio()
    if args.project_revision < 1:
        raise ContractError("project_revision must be a positive integer")
    otio_path = args.otio.resolve()
    timeline = otio.adapters.read_from_file(str(otio_path))
    metadata = plain_metadata(plain_metadata(timeline.metadata).get("content_os"))
    if metadata.get("project_id") != args.project_id:
        raise ContractError("OTIO project_id does not match requested project_id")
    if metadata.get("project_revision") != args.project_revision:
        raise ContractError("OTIO project_revision does not match requested project_revision")
    output_root = args.output_root.resolve() / str(args.project_revision)
    output_root.mkdir(parents=True, exist_ok=True)
    kdenlive_path = output_root / "timeline.kdenlive"
    clip_count = write_kdenlive_project(kdenlive_path, timeline, args.project_id, args.project_revision)
    write_result(
        args.result_output,
        {
            "status": "done",
            "project_id": args.project_id,
            "project_revision": args.project_revision,
            "editor_backend": "otio_kdenlive",
            "kdenlive_project": str(kdenlive_path),
            "clip_count": clip_count,
            "kdenlive_available": bool(kdenlive_executable()),
        },
    )
    return 0


def validate(args: argparse.Namespace) -> int:
    otio = require_otio()
    if args.project_revision < 1:
        raise ContractError("project_revision must be a positive integer")
    timeline = otio.adapters.read_from_file(str(args.otio.resolve()))
    metadata = plain_metadata(timeline.metadata).get("content_os", {})
    if metadata.get("project_id") != args.project_id or metadata.get("project_revision") != args.project_revision:
        raise ContractError("OTIO identity does not match project_id/project_revision")
    metadata_basis = metadata.get("revision_basis")
    if metadata_basis is not None:
        basis_metadata = plain_metadata(metadata_basis)
        if not basis_metadata:
            raise ContractError("OTIO revision basis metadata must be an object")
        path_value = basis_metadata.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ContractError("OTIO revision basis metadata has no path")
        actual_basis = revision_basis_descriptor(
            Path(path_value), project_id=args.project_id, project_revision=args.project_revision
        )
        if basis_metadata != actual_basis:
            raise ContractError("OTIO revision basis has changed since timeline generation")
        manifest = read_json(args.otio.resolve().with_name("manifest.json"))
        if manifest.get("revision_basis") != actual_basis:
            raise ContractError("OTIO manifest does not match the confirmed revision basis")
    try:
        root = ET.parse(args.kdenlive.resolve()).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ContractError(f"cannot reopen Kdenlive project: {exc}") from exc
    if root.tag != "mlt":
        raise ContractError("Kdenlive project root must be mlt")
    xml_project_id = next((element.text for element in root.findall("property") if element.attrib.get("name") == "kdenlive:docproperties.projectid"), None)
    xml_revision = next((element.text for element in root.findall("property") if element.attrib.get("name") == "content_os.project_revision"), None)
    if xml_project_id != args.project_id or xml_revision != str(args.project_revision):
        raise ContractError("Kdenlive project identity does not match project_id/project_revision")
    # Compare every track, not just the first: an overlay track that silently
    # failed to serialise would otherwise validate clean.
    otio_tracks = list(timeline.tracks)
    if not otio_tracks:
        raise ContractError("OTIO timeline has no tracks")
    xml_playlists = [p for p in root.findall("./playlist") if p.find("property[@name='content_os:layer']") is not None]
    if len(xml_playlists) != len(otio_tracks):
        raise ContractError(
            f"Kdenlive track count does not match OTIO: {len(xml_playlists)} playlists vs {len(otio_tracks)} tracks"
        )
    producers = {producer.attrib.get("id"): producer for producer in root.findall("./producer")}
    total_entries = 0
    for track_index, track in enumerate(otio_tracks):
        playlist = root.find(f"./playlist[@id='playlist{track_index}']")
        if playlist is None:
            raise ContractError(f"Kdenlive playlist{track_index} is missing")
        track_metadata = plain_metadata(plain_metadata(track.metadata).get("content_os"))
        xml_layer = next(
            (element.text for element in playlist.findall("property") if element.attrib.get("name") == "content_os:layer"),
            None,
        )
        xml_lane = next(
            (element.text for element in playlist.findall("property") if element.attrib.get("name") == "content_os:physical_lane"),
            None,
        )
        if xml_layer != str(track_metadata.get("layer") or ""):
            raise ContractError(f"Kdenlive playlist{track_index} layer does not match OTIO")
        if xml_lane != str(track_metadata.get("physical_lane") or ""):
            raise ContractError(f"Kdenlive playlist{track_index} physical lane does not match OTIO")

        xml_items = [element for element in list(playlist) if element.tag in {"blank", "entry"}]
        otio_items = [item for item in list(track) if item.__class__.__name__ in {"Gap", "Clip"}]
        if len(xml_items) != len(otio_items):
            raise ContractError(f"Kdenlive playlist{track_index} layout does not match OTIO track {track_index}")
        timeline_cursor = 0
        for item_index, (xml_item, otio_item) in enumerate(zip(xml_items, otio_items)):
            duration_frames = int(otio_item.source_range.duration.to_frames())
            if otio_item.__class__.__name__ == "Gap":
                if xml_item.tag != "blank" or xml_item.attrib.get("length") != str(duration_frames):
                    raise ContractError(
                        f"Kdenlive playlist{track_index} gap #{item_index} does not match OTIO"
                    )
                timeline_cursor += duration_frames
                continue
            if xml_item.tag != "entry":
                raise ContractError(f"Kdenlive playlist{track_index} clip #{item_index} is not an entry")
            clip_metadata = plain_metadata(plain_metadata(otio_item.metadata).get("content_os"))
            try:
                timeline_start = clip_metadata["timeline_start_frame"] / FPS if "timeline_start_frame" in clip_metadata else _canonical_parse_seconds(
                    clip_metadata.get("timeline_start_sec"),
                    path=f"tracks[{track_index}].clips[{item_index}].timeline_start_sec",
                )
            except EDLContractError as exc:
                raise ContractError(f"OTIO clip has invalid timeline position metadata: {exc}") from exc
            if clip_metadata.get("timeline_start_frame", frames(timeline_start)) != timeline_cursor:
                raise ContractError(
                    f"Kdenlive playlist{track_index} clip #{item_index} changed timeline position"
                )
            source_in = int(otio_item.source_range.start_time.to_frames())
            source_out = source_in + duration_frames - 1
            expected_trim = {"in": str(source_in), "out": str(source_out)}
            if any(xml_item.attrib.get(key) != value for key, value in expected_trim.items()):
                raise ContractError(
                    f"Kdenlive playlist{track_index} clip #{item_index} source trim does not match OTIO"
                )
            producer = producers.get(xml_item.attrib.get("producer"))
            if producer is None or producer.attrib.get("in") != "0" or int(producer.attrib.get("out", "-1")) < source_out:
                raise ContractError(
                    f"Kdenlive playlist{track_index} clip #{item_index} producer trim does not match OTIO"
                )
            if track.kind == "Audio":
                expected = audio_level_keyframes(plain_data(clip_metadata["audio_segment"]), duration_frames)
                volume = producer.find("filter/property[@name='level']")
                resource = producer.find("property[@name='resource']")
                if volume is None or volume.text != expected or resource is None or resource.text != clip_metadata["candidate_file"]:
                    raise ContractError("Kdenlive audio source/gain does not match OTIO")
            timeline_cursor += duration_frames
            total_entries += 1
    if not total_entries:
        raise ContractError("Kdenlive project has no clips")
    tractor_tracks = [t for t in timeline_tractor(root).findall("track") if t.get("producer", "").startswith("track")]
    if len(tractor_tracks) != len(otio_tracks):
        raise ContractError("Kdenlive tractor does not reference every playlist")
    audio_plan = plain_data(metadata.get("audio_plan"))
    if audio_plan is not None:
        from edit_backends.kdenlive_readback import audio_graph_differences
        _, mismatches = audio_graph_differences(root, args.kdenlive.resolve().parent, audio_plan,
                                                plain_data(metadata.get('audio_sources', {})))
        if mismatches:
            raise ContractError(f"Kdenlive audio graph does not match OTIO: {', '.join(mismatches)}")
    kdenlive = kdenlive_executable()
    if not kdenlive:
        raise ContractError("Kdenlive executable is unavailable; validation is blocked")
    version = probe_kdenlive_version(kdenlive)
    probe_kdenlive_reopen(kdenlive, args.kdenlive.resolve())
    validation_path = args.result_output.resolve() if args.result_output else args.kdenlive.resolve().with_name("timeline_validation.json")
    validation = {
        "doc_type": "otio_kdenlive_validation",
        "spec_version": "content_os_v0.2",
        "status": "passed",
        "project_id": args.project_id,
        "project_revision": args.project_revision,
        "editor_backend": "otio_kdenlive",
        "otio_reopened": True,
        "kdenlive_project_reopened": True,
        "kdenlive_reopen_probe": "application_process",
        "kdenlive_reopen_probe_seconds": KDENLIVE_REOPEN_PROBE_SECONDS,
        "clip_count": total_entries,
        "track_count": len(otio_tracks),
        "kdenlive_available": True,
        "kdenlive_version": version,
    }
    write_result(validation_path, validation)
    return 0


def generate_edl_project(args: argparse.Namespace) -> int:
    from edit_backends.kdenlive_render import generate_from_edl
    result = generate_from_edl(edl_path=args.edl, output_dir=args.output_dir, media_root=args.media_root,
                               project_id=args.project_id, project_revision=args.project_revision)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    edl_command = commands.add_parser("generate-edl", help="从规范剪辑方案生成带混音的可编辑工程")
    edl_command.add_argument("--project-id", required=True)
    edl_command.add_argument("--project-revision", required=True, type=int)
    edl_command.add_argument("--edl", required=True, type=Path)
    edl_command.add_argument("--output-dir", required=True, type=Path)
    edl_command.add_argument("--media-root", type=Path)
    edl_command.set_defaults(func=generate_edl_project)
    generate = commands.add_parser("generate-otio")
    generate.add_argument("--project-id", required=True)
    generate.add_argument("--project-revision", type=int, required=True)
    generate.add_argument("--edl", type=Path, required=True)
    generate.add_argument("--storyboard", type=Path, required=True)
    generate.add_argument("--output-root", type=Path, required=True)
    generate.add_argument("--revision-basis", type=Path)
    generate.add_argument("--result-output", type=Path)
    generate.set_defaults(func=generate_otio)
    kdenlive = commands.add_parser("generate-kdenlive")
    kdenlive.add_argument("--project-id", required=True)
    kdenlive.add_argument("--project-revision", type=int, required=True)
    kdenlive.add_argument("--otio", type=Path, required=True)
    kdenlive.add_argument("--output-root", type=Path, required=True)
    kdenlive.add_argument("--result-output", type=Path)
    kdenlive.set_defaults(func=generate_kdenlive)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--project-id", required=True)
    validate_parser.add_argument("--project-revision", type=int, required=True)
    validate_parser.add_argument("--otio", type=Path, required=True)
    validate_parser.add_argument("--kdenlive", type=Path, required=True)
    validate_parser.add_argument("--result-output", type=Path)
    validate_parser.set_defaults(func=validate)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
