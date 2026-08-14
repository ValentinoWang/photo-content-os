#!/usr/bin/env python3
"""Extract uniformly sampled video frames for AI visual analysis."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path

from media_common import eligible_item, load_manifest, project_path, relative_posix, safe_slug, save_manifest


def timestamp_label(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    total_seconds, ms = divmod(millis, 1000)
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}-{minutes:02d}-{sec:02d}-{ms:03d}"
    return f"{minutes:02d}-{sec:02d}-{ms:03d}"


def is_dense_video(item: dict[str, object]) -> bool:
    text = f"{item.get('filename', '')} {item.get('relative_path', '')}"
    return any(token in text for token in ("比赛", "校运会", "高燃", "起跑", "冲线", "运动", "赛事", "操场"))


def sample_times(duration: float, dense: bool, max_frames: int) -> list[float]:
    if duration <= 0:
        return [0.5]
    interval = 1.0 if dense else 2.0
    wanted = max(1, math.ceil(duration / interval))
    count = min(max_frames, wanted)
    if count == 1:
        return [min(max(duration * 0.5, 0.2), max(duration - 0.1, 0.0))]
    start = min(0.4, duration * 0.15)
    end = max(duration - min(0.4, duration * 0.15), start)
    step = (end - start) / (count - 1)
    return [round(start + i * step, 3) for i in range(count)]


def extract_one(video_path: Path, output_dir: Path, duration: float, dense: bool, max_frames: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("frame_*.jpg"):
        old.unlink()

    frames: list[Path] = []
    for index, seconds in enumerate(sample_times(duration, dense, max_frames), start=1):
        output = output_dir / f"frame_{index:04d}_{timestamp_label(seconds)}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            "scale='min(1280,iw)':-2",
            str(output),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            frames.append(output)
    return frames


def prune_stale_keyframe_dirs(keyframe_root: Path, expected_names: set[str]) -> int:
    removed = 0
    for child in keyframe_root.iterdir():
        if child.is_dir() and child.name not in expected_names:
            shutil.rmtree(child)
            removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="按时长均匀抽取视频关键帧")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--max-frames", type=int, default=40, help="单个视频最多抽取帧数")
    parser.add_argument("--include-derived", action="store_true", help="同时分析 80/91 等派生目录中的媒体")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found. Run 99_System_OpenClaw/scripts/00_install_deps.sh or install ffmpeg.")

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    keyframe_root = project / "_ai_analysis" / "keyframes"
    keyframe_root.mkdir(parents=True, exist_ok=True)

    videos = [
        item
        for item in manifest["items"]
        if item.get("media_type") == "video" and eligible_item(item, include_derived=args.include_derived)
    ]
    expected_dirs = {f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}" for item in videos}
    pruned = prune_stale_keyframe_dirs(keyframe_root, expected_dirs)
    if pruned:
        print(f"已清理陈旧关键帧目录：{pruned} 个")

    for item in videos:
        rel = item["relative_path"]
        video_path = project / rel
        if not video_path.exists():
            raise FileNotFoundError(f"manifest item no longer exists: {video_path}")
        duration = float(item.get("duration_sec") or 0)
        dense = is_dense_video(item)
        out_dir = keyframe_root / f"{item['media_id']}_{safe_slug(Path(rel).stem)}"
        frames = extract_one(video_path, out_dir, duration, dense, args.max_frames)
        item["keyframe_dir"] = relative_posix(out_dir, project)
        item["keyframe_count"] = len(frames)
        item["keyframes"] = [relative_posix(frame, project) for frame in frames]
        item["keyframe_strategy"] = "dense_1s" if dense else "normal_2s"
        print(f"{rel}: {len(frames)} frames")

    save_manifest(project, manifest)
    print(f"关键帧抽取完成：{keyframe_root}")


if __name__ == "__main__":
    main()
