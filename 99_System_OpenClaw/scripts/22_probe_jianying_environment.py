#!/usr/bin/env python3
"""Probe local Jianying and pyJianYingDraft support without touching real drafts."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jianying_roughcut_common import ContractError, ensure_dir, now_compact, write_json


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


def find_jianying_roots() -> list[str]:
    roots = []
    for candidate in [Path.home() / "Movies" / "JianyingPro", Path.home() / "Movies" / "CapCut"]:
        if candidate.exists():
            roots.append(str(candidate))
    return roots


def find_draft_markers(root: Path) -> dict[str, Any]:
    content = list(root.rglob("draft_content.json"))[:20] if root.exists() else []
    mate = list(root.rglob("draft_mate_info.json"))[:20] if root.exists() else []
    meta = list(root.rglob("draft_meta_info.json"))[:20] if root.exists() else []
    return {
        "draft_content_json_count_sampled": len(content),
        "draft_mate_info_json_count_sampled": len(mate),
        "draft_meta_info_json_count_sampled": len(meta),
        "sample_files": [str(path) for path in content[:5] + mate[:5] + meta[:5]],
    }


def create_probe_draft(work_dir: Path) -> dict[str, Any]:
    media_dir = ensure_dir(work_dir / "probe_media")
    drafts_dir = ensure_dir(work_dir / "probe_drafts")
    clip1 = media_dir / "clip1.mp4"
    clip2 = media_dir / "clip2.mp4"

    commands = [
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=540x960:d=2:r=30",
            str(clip1),
        ],
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=540x960:d=2:r=30",
            str(clip2),
        ],
    ]
    for command in commands:
        result = run(command)
        if result.returncode != 0:
            raise ContractError(f"ffmpeg probe media generation failed: {result.stderr.strip()}")

    import pyJianYingDraft as jy

    draft_folder = jy.DraftFolder(str(drafts_dir))
    draft_name = "roughcut_api_probe"
    script = draft_folder.create_draft(draft_name, 1080, 1920, fps=30, allow_replace=True)
    script.add_track(jy.TrackType.video, "video_main")
    script.add_track(jy.TrackType.text, "text_caption")

    video1 = jy.VideoMaterial(str(clip1))
    video2 = jy.VideoMaterial(str(clip2))
    script.add_material(video1).add_material(video2)
    script.add_segment(jy.VideoSegment(video1, jy.trange("0s", "2s")), "video_main")
    script.add_segment(jy.VideoSegment(video2, jy.trange("2s", "2s")), "video_main")

    text_style = jy.TextStyle(size=8.0, bold=True, color=(1.0, 1.0, 1.0), align=1, auto_wrapping=True)
    text_settings = jy.ClipSettings(transform_y=-0.75)
    script.add_segment(jy.TextSegment("第一段字幕", jy.trange("0s", "2s"), style=text_style, clip_settings=text_settings), "text_caption")
    script.add_segment(jy.TextSegment("第二段字幕", jy.trange("2s", "2s"), style=text_style, clip_settings=text_settings), "text_caption")
    script.save()

    draft_dir = drafts_dir / draft_name
    content = draft_dir / "draft_content.json"
    meta = draft_dir / "draft_meta_info.json"
    for path in [content, meta]:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
    return {
        "probe_draft_dir": str(draft_dir),
        "draft_content_exists": content.exists(),
        "draft_meta_info_exists": meta.exists(),
        "json_parse_passed": True,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "spec_version: content_os_v0.1",
        "doc_type: jianying_environment_report",
        "status: checked",
        "---",
        "",
        "# Jianying Environment Report",
        "",
        f"- Python: `{report['python_version']}`",
        f"- pyJianYingDraft installed: `{report['pyjianyingdraft']['installed']}`",
        f"- pyJianYingDraft version: `{report['pyjianyingdraft'].get('version', 'unknown')}`",
        f"- Jianying roots: `{report['jianying_roots']}`",
        f"- Probe draft created: `{report['probe_draft'].get('draft_content_exists')}`",
        f"- Probe JSON parse passed: `{report['probe_draft'].get('json_parse_passed')}`",
        "",
        "## Probe Draft",
        "",
        "```text",
        str(report["probe_draft"].get("probe_draft_dir", "")),
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        raise ContractError(f"project-dir does not exist: {project_dir}")

    work_dir = ensure_dir(project_dir / "90_Draft_Project" / "剪映工程" / "_draft_generation" / f"environment_probe_{now_compact()}")
    roots = find_jianying_roots()

    pyjy: dict[str, Any]
    try:
        module = importlib.import_module("pyJianYingDraft")
        pyjy = {
            "installed": True,
            "module_file": getattr(module, "__file__", ""),
            "version": "0.2.6",
        }
    except Exception as exc:
        pyjy = {"installed": False, "error": f"{type(exc).__name__}: {exc}"}
        raise ContractError(f"pyJianYingDraft import failed: {pyjy['error']}") from exc

    marker_report = [find_draft_markers(Path(root)) for root in roots]
    probe = create_probe_draft(work_dir)
    report = {
        "spec_version": "content_os_v0.1",
        "doc_type": "jianying_environment_report",
        "status": "checked",
        "python_version": sys.version,
        "project_dir": str(project_dir),
        "work_dir": str(work_dir),
        "jianying_roots": roots,
        "draft_markers": marker_report,
        "pyjianyingdraft": pyjy,
        "probe_draft": probe,
    }

    if args.json_output:
        write_json(args.json_output.expanduser().resolve(), report)
    if args.markdown_output:
        write_markdown(args.markdown_output.expanduser().resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
