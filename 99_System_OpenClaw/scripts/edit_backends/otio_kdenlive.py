#!/usr/bin/env python3
"""Create and verify the optional Content OS OTIO/Kdenlive editing handoff.

This backend deliberately produces an open timeline instead of a Jianying
draft.  It never chooses another backend: missing editor software or invalid
media is reported as a blocking error to the caller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from edl_contract import EDLContractError  # noqa: E402
from edl_contract import parse_time_range as _canonical_parse_time_range  # noqa: E402


class ContractError(ValueError):
    """Input or output violates the Content OS editing-handoff contract."""


RAW360_TOKENS = ("rawvault", "不可直用", "360原始", "reframe_needed", ".osv", ".lrf")
FPS = 30


@dataclass(frozen=True)
class TimelineClip:
    slot: str
    start: float
    end: float
    caption: str
    candidate: str
    note: str

    @property
    def duration(self) -> float:
        return self.end - self.start


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    lowered = value.lower()
    return any(token in lowered for token in RAW360_TOKENS)


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
    previous_end = 0.0
    for index, raw in enumerate(raw_clips, start=1):
        if not isinstance(raw, dict):
            raise ContractError(f"EDL clip #{index} must be an object")
        start, end = parse_time_range(str(raw.get("time_range") or ""))
        if start < previous_end:
            raise ContractError(f"EDL clip #{index} overlaps the preceding clip")
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
        clips.append(
            TimelineClip(
                slot=str(raw.get("slot") or index),
                start=start,
                end=end,
                caption=str(raw.get("caption") or "").strip(),
                candidate=candidate,
                note=str(raw.get("edit_note") or "").strip(),
            )
        )
        previous_end = end
    return edl, clips


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


def plain_metadata(value: Any) -> dict[str, Any]:
    """OTIO keeps metadata in AnyDictionary, which is mapping-like not dict."""
    try:
        return {str(key): value[key] for key in value}
    except (TypeError, KeyError):
        return {}


def make_otio_timeline(
    otio: Any,
    project_id: str,
    project_revision: int,
    edl: dict[str, Any],
    clips: list[TimelineClip],
    revision_basis: dict[str, str] | None,
) -> Any:
    track = otio.schema.Track(name="主画面", kind=otio.schema.TrackKind.Video)
    cursor = 0.0
    for clip in clips:
        if clip.start > cursor:
            track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, FPS),
                duration=otio.opentime.RationalTime(frames(clip.start - cursor), FPS),
            )))
        external = otio.schema.ExternalReference(
            target_url=candidate_resource(clip.candidate),
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, FPS),
                duration=otio.opentime.RationalTime(frames(clip.duration), FPS),
            ),
        )
        segment = otio.schema.Clip(
            name=f"{clip.slot}_{Path(clip.candidate).name}",
            media_reference=external,
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, FPS),
                duration=otio.opentime.RationalTime(frames(clip.duration), FPS),
            ),
        )
        segment.metadata["content_os"] = {
            "project_id": project_id,
            "project_revision": project_revision,
            "slot": clip.slot,
            "timeline_start_sec": clip.start,
            "candidate_file": clip.candidate,
            "edit_note": clip.note,
            "media_exists_at_generation": Path(clip.candidate).expanduser().exists(),
        }
        track.append(segment)
        if clip.caption:
            track.markers.append(otio.schema.Marker(
                name=clip.caption,
                marked_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(frames(clip.start), FPS),
                    duration=otio.opentime.RationalTime(frames(clip.duration), FPS),
                ),
                color=otio.schema.Marker.Color.YELLOW,
            ))
        cursor = clip.end

    timeline = otio.schema.Timeline(name=f"{project_id}_r{project_revision}")
    timeline.tracks.append(track)
    timeline.metadata["content_os"] = {
        "spec_version": "content_os_v0.2",
        "project_id": project_id,
        "project_revision": project_revision,
        "editor_backend": "otio_kdenlive",
        "source_edl": str(edl.get("project_id") or project_id),
        "fps": FPS,
    }
    if revision_basis is not None:
        timeline.metadata["content_os"]["revision_basis"] = revision_basis
    return timeline


def timeline_manifest(
    project_id: str,
    project_revision: int,
    clips: list[TimelineClip],
    otio_path: Path,
    revision_basis: dict[str, str] | None,
) -> dict[str, Any]:
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
                "candidate_file": clip.candidate,
                "needs_relink": not Path(clip.candidate).expanduser().exists(),
                "caption": clip.caption,
            }
            for clip in clips
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
    edl, clips = load_edl(args.edl.resolve(), project_id, args.project_revision)
    revision_basis = (
        revision_basis_descriptor(args.revision_basis, project_id=project_id, project_revision=args.project_revision)
        if args.revision_basis is not None
        else None
    )
    output_root = args.output_root.resolve() / str(args.project_revision)
    output_root.mkdir(parents=True, exist_ok=True)
    otio_path = output_root / "timeline.otio"
    timeline = make_otio_timeline(otio, project_id, args.project_revision, edl, clips, revision_basis)
    otio.adapters.write_to_file(timeline, str(otio_path))
    manifest = timeline_manifest(project_id, args.project_revision, clips, otio_path, revision_basis)
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
    executable = shutil.which("kdenlive")
    if executable:
        return executable
    bundled = Path("/Applications/kdenlive.app/Contents/MacOS/kdenlive")
    return str(bundled) if bundled.is_file() else None


def safe_xml_resource(candidate: str) -> str:
    return str(Path(candidate).expanduser()) if Path(candidate).is_absolute() else candidate


def write_kdenlive_project(path: Path, otio_data: Any, project_id: str, project_revision: int) -> int:
    root = ET.Element("mlt", {"LC_NUMERIC": "C", "version": "7.28.0", "title": f"{project_id}_r{project_revision}"})
    ET.SubElement(root, "profile", {"description": "HD Vertical 1080p 30 fps", "width": "1080", "height": "1920", "frame_rate_num": "30", "frame_rate_den": "1", "progressive": "1", "sample_aspect_num": "1", "sample_aspect_den": "1", "display_aspect_num": "9", "display_aspect_den": "16"})
    ET.SubElement(root, "property", {"name": "kdenlive:docproperties.projectid"}).text = project_id
    ET.SubElement(root, "property", {"name": "content_os.project_revision"}).text = str(project_revision)
    playlist = ET.SubElement(root, "playlist", {"id": "playlist0"})
    count = 0
    tracks = list(otio_data.tracks)
    if not tracks:
        raise ContractError("OTIO timeline has no tracks")
    for item in tracks[0]:
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
        producer = ET.SubElement(root, "producer", {"id": producer_id, "in": "0", "out": str(max(0, int(item.source_range.duration.to_frames()) - 1))})
        ET.SubElement(producer, "property", {"name": "resource"}).text = safe_xml_resource(candidate)
        ET.SubElement(producer, "property", {"name": "kdenlive:clipname"}).text = item.name
        ET.SubElement(producer, "property", {"name": "content_os:needs_relink"}).text = "1" if not Path(candidate).expanduser().exists() else "0"
        ET.SubElement(playlist, "entry", {"producer": producer_id, "in": "0", "out": str(max(0, int(item.source_range.duration.to_frames()) - 1))})
        count += 1
    tractor = ET.SubElement(root, "tractor", {"id": "tractor0"})
    ET.SubElement(tractor, "track", {"producer": "playlist0"})
    ET.SubElement(tractor, "property", {"name": "kdenlive:docproperties.documentversion"}).text = "1"
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
    entries = root.findall("./playlist[@id='playlist0']/entry")
    otio_clips = [item for item in list(timeline.tracks[0]) if item.__class__.__name__ == "Clip"]
    if len(entries) != len(otio_clips) or not entries:
        raise ContractError("Kdenlive playlist clip count does not match OTIO")
    kdenlive = kdenlive_executable()
    version = "not_installed"
    if kdenlive:
        probe = subprocess.run([kdenlive, "--version"], capture_output=True, text=True, timeout=20, check=False)
        version = (probe.stdout or probe.stderr).strip().splitlines()[0] if probe.returncode == 0 else "present_but_unavailable"
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
        "clip_count": len(entries),
        "kdenlive_available": bool(kdenlive),
        "kdenlive_version": version,
    }
    write_result(validation_path, validation)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
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
