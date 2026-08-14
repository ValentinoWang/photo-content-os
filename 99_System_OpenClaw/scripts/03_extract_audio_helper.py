#!/usr/bin/env python3
"""Extract mono WAV audio from manifest videos that contain audio streams."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from media_common import eligible_item, load_manifest, project_path, relative_posix, safe_slug, save_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="提取视频音频，为后续转写准备")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("include_derived_marker", nargs="?", default="")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found. Run 99_System_OpenClaw/scripts/00_install_deps.sh or install ffmpeg.")

    include_derived = args.include_derived_marker == "--include-derived"
    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    audio_root = project / "_ai_analysis" / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)

    for item in manifest["items"]:
        if item.get("media_type") != "video" or not eligible_item(item, include_derived=include_derived):
            continue
        if not item.get("has_audio"):
            item["audio_extract_status"] = "skipped_no_audio"
            continue

        rel = item["relative_path"]
        video_path = project / rel
        out_file = audio_root / f"{item['media_id']}_{safe_slug(Path(rel).stem)}.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(out_file),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if result.returncode != 0 or not out_file.exists():
            raise RuntimeError(f"failed to extract audio: {video_path}")
        item["audio_path"] = relative_posix(out_file, project)
        item["audio_extract_status"] = "ok"
        print(f"{rel}: audio -> {out_file.name}")

    save_manifest(project, manifest)
    print(f"音频提取完成：{audio_root}")


if __name__ == "__main__":
    main()
