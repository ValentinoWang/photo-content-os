#!/usr/bin/env python3
"""Review exported short videos and write Content OS output-review artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from llm_common import LLMError, creator_context_block, load_creator_context, parse_json_response, public_llm_error, generate_text
from media_common import OUTPUT_REVIEW_SAMPLING, now_iso, timestamp_label
from media_common import sample_times as _shared_sample_times

SCHEMA_VERSION = "output_review.v1"
RESULT_SCHEMA_VERSION = "output_review_result.v1"
RHYTHM_SYNC_SCHEMA_VERSION = "rhythm_sync_review.v1"
VLM_SCHEMA_VERSION = "local_output_vlm_semantic_review.v1"
BLACK_THRESHOLD = 18
WHITE_THRESHOLD = 242
MOTION_SAMPLE_FPS = 8.0
CREATIVE_STRATEGY_ALGORITHM_VERSION = "video_scoring_judgement.v3"
CREATIVE_STRATEGY_WEIGHTS_VERSION = "creative_strategy_weights.v3"
CREATIVE_STRATEGY_WEIGHTS: list[tuple[str, float]] = [
    ("rhythm", 0.35),
    ("platform_format", 0.10),
    ("opening_hook", 0.23),
    ("composition", 0.20),
    ("topic_strategy", 0.12),
]


PROFILE_WEIGHTS: dict[str, dict[str, float]] = {
    "single_person_stage_walk": {
        "step_sync": 0.40,
        "motion_sync": 0.25,
        "cut_sync": 0.15,
        "intro_effect": 0.10,
        "subject_presence": 0.10,
    },
    "pov_running": {
        "step_sync": 0.45,
        "global_motion_rhythm": 0.30,
        "cut_sync": 0.05,
        "intro_effect": 0.10,
        "stability": 0.10,
    },
    "split_screen_comparison": {
        "structural_match": 0.30,
        "action_node_sync": 0.25,
        "cut_sync": 0.15,
        "text_overlay_sync": 0.15,
        "step_sync": 0.10,
        "intro_effect": 0.05,
    },
    "sports_highlight": {
        "action_burst_sync": 0.35,
        "speed_change_sync": 0.25,
        "cut_sync": 0.20,
        "impact_sync": 0.15,
        "intro_effect": 0.05,
    },
    "talking_head": {
        "semantic_pause_sync": 0.30,
        "text_overlay_sync": 0.25,
        "expression_change": 0.15,
        "cut_sync": 0.15,
        "intro_hook": 0.15,
    },
    "general_bgm_edit": {
        "cut_sync": 0.25,
        "motion_sync": 0.25,
        "intro_effect": 0.15,
        "text_overlay_sync": 0.15,
        "beat_coverage": 0.10,
        "phase_consistency": 0.10,
    },
}


EVENT_TOLERANCE_SEC: dict[str, float] = {
    "scene_cut": 0.14,
    "transition_flash": 0.16,
    "step_motion_peak_proxy": 0.22,
    "global_motion_peak": 0.18,
    "text_overlay_change": 0.25,
    "intro_effect": 0.35,
}


class OutputReviewError(Exception):
    """Raised when output review cannot produce a valid artifact set."""


@dataclass(frozen=True)
class ReviewInput:
    version_name: str
    path: Path


@dataclass(frozen=True)
class ProjectContext:
    project_root: Path | None
    target_platforms: list[str]
    project_goal: str
    notes: list[str]
    creator_context: dict[str, Any] = field(default_factory=dict)


RECOMMENDATION_LABELS = {
    "publish": "建议发布（仍需人工确认）",
    "small_fix": "小幅修改后再确认",
    "recut": "需要重新剪辑",
    "reject": "暂不发布",
}
STATUS_LABELS = {
    "success": "已完成自动检查",
    "partial": "部分完成（能力缺失）",
    "blocked": "检查受阻",
    "pass": "通过",
    "warning": "有提醒",
    "fail": "未通过",
    "unknown": "待人工确认",
}
CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}
VLM_STATUS_LABELS = {"success": "已完成", "failed": "失败", "unavailable": "不可用", "not_requested": "未启用"}
TAG_LABELS = {
    "trend_remake": "翻拍版本",
    "split_screen": "分屏版本",
    "comparison": "对照版本",
    "single_subject": "单主体",
    "extended_cut": "加长版本",
    "horizontal_cut": "横屏版本",
    "outdoor_context": "户外场景",
    "stage_walk": "舞台移动",
    "first_person": "第一视角",
}
DIMENSION_LABELS = {
    "rhythm": "节奏",
    "platform_format": "平台画幅",
    "opening_hook": "开头钩子",
    "composition": "构图技术",
    "topic_strategy": "选题表达",
}
RISK_FLAG_LABELS = {
    "resolution_below_1080_short_side": "短边低于 1080，需确认清晰度",
    "mostly_black_frames": "检测到较多黑场",
    "audio_missing": "未检测到音频",
}


def humanize_risk_flag(flag: str) -> str:
    return RISK_FLAG_LABELS.get(flag, "存在技术风险，需查看指标附录")


def humanize_brief_fit(value: str) -> str:
    return {"high": "匹配度较高", "medium": "匹配度中等", "unknown": "尚未完成语义匹配", "low": "匹配度较低"}.get(value, "待人工确认")


def humanize_tag(tag: str) -> str:
    return TAG_LABELS.get(tag, "项目版本标签")


def humanize_rhythm_profile(value: str) -> str:
    return {
        "general_bgm_edit": "常规音乐剪辑",
        "single_person_stage_walk": "单主体移动",
        "pov_running": "第一视角移动",
        "split_screen_comparison": "分屏对照",
        "sports_highlight": "动作高光",
        "talking_head": "口播人物",
    }.get(value, "已配置的节奏模板" if value else "未启用")


def humanize_dimension(value: str) -> str:
    return DIMENSION_LABELS.get(value, "待确认维度")


def run_process(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OutputReviewError(f"command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result


def check_dependencies() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    errors = []
    if not ffmpeg:
        errors.append("ffmpeg_not_found")
    if not ffprobe:
        errors.append("ffprobe_not_found")
    return {
        "ffmpeg_available": bool(ffmpeg),
        "ffprobe_available": bool(ffprobe),
        "errors": errors,
        "warnings": [],
    }


def parse_rate(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            den = float(denominator)
            return float(numerator) / den if den else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def run_ffprobe(path: Path) -> dict[str, Any]:
    result = run_process(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise OutputReviewError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise OutputReviewError(f"ffprobe returned invalid JSON for {path}") from exc
    streams = data.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    format_info = data.get("format") or {}
    fps = parse_rate(video_stream.get("avg_frame_rate")) or parse_rate(video_stream.get("r_frame_rate"))
    return {
        "path": str(path),
        "duration_sec": round(float_or_none(format_info.get("duration")) or 0.0, 3),
        "width": int_or_none(video_stream.get("width")),
        "height": int_or_none(video_stream.get("height")),
        "fps": round(fps, 3) if fps else None,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "video_bitrate": int_or_none(video_stream.get("bit_rate")) or int_or_none(format_info.get("bit_rate")),
        "audio_bitrate": int_or_none(audio_stream.get("bit_rate")),
        "audio_sample_rate": int_or_none(audio_stream.get("sample_rate")),
        "audio_channels": int_or_none(audio_stream.get("channels")),
        "has_video": bool(video_stream),
        "has_audio": bool(audio_stream),
        "format_name": format_info.get("format_name"),
        "file_size_bytes": int_or_none(format_info.get("size")),
    }


def sample_times(duration: float) -> list[float]:
    return _shared_sample_times(duration, OUTPUT_REVIEW_SAMPLING)


def extract_uniform_frames(video_path: Path, output_dir: Path, duration: float) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("frame_*.jpg"):
        old.unlink()
    frames = []
    for index, seconds in enumerate(sample_times(duration), start=1):
        output = output_dir / f"frame_{index:04d}_{timestamp_label(seconds)}.jpg"
        result = run_process(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
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
                "scale='min(720,iw)':-2",
                str(output),
            ]
        )
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            frames.append(output)
    return frames


def extract_scene_change_frames(video_path: Path, output_dir: Path, max_frames: int = 64) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("scene_*.jpg"):
        old.unlink()
    output_pattern = output_dir / "scene_%04d.jpg"
    result = run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "select='gt(scene,0.25)',scale='min(720,iw)':-2",
            "-vsync",
            "vfr",
            "-frames:v",
            str(max_frames),
            str(output_pattern),
        ]
    )
    if result.returncode != 0:
        return []
    return sorted(output_dir.glob("scene_*.jpg"))


def load_image(path: Path) -> Any:
    try:
        from PIL import Image
    except Exception as exc:
        raise OutputReviewError("Pillow is required for image metrics and contact sheets") from exc
    return Image.open(path).convert("RGB")


def build_contact_sheet(frames: list[Path], output: Path, *, label_prefix: str) -> Path | None:
    if not frames:
        return None
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        raise OutputReviewError("Pillow is required for contact sheets") from exc
    thumb_w = 240
    label_h = 26
    cols = min(6, max(1, len(frames)))
    rows = math.ceil(len(frames) / cols)
    thumbs = []
    for frame in frames:
        image = Image.open(frame).convert("RGB")
        image.thumbnail((thumb_w, 160))
        canvas = Image.new("RGB", (thumb_w, 160 + label_h), "white")
        x = (thumb_w - image.width) // 2
        canvas.paste(image, (x, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, 164), f"{label_prefix} {frame.stem}", fill=(0, 0, 0))
        thumbs.append(canvas)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (160 + label_h)), "white")
    for index, thumb in enumerate(thumbs):
        col = index % cols
        row = index // cols
        sheet.paste(thumb, (col * thumb_w, row * (160 + label_h)))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88)
    return output


def edge_border_sizes(pixels: Any, width: int, height: int) -> tuple[int, int, int, int, float]:
    black = [
        [all(channel < BLACK_THRESHOLD for channel in pixels[x, y]) for x in range(width)]
        for y in range(height)
    ]
    row_ratio = [sum(row) / width for row in black]
    col_ratio = [sum(black[y][x] for y in range(height)) / height for x in range(width)]
    top = 0
    while top < height and row_ratio[top] > 0.96:
        top += 1
    bottom = 0
    while bottom < height - top and row_ratio[height - 1 - bottom] > 0.96:
        bottom += 1
    left = 0
    while left < width and col_ratio[left] > 0.96:
        left += 1
    right = 0
    while right < width - left and col_ratio[width - 1 - right] > 0.96:
        right += 1
    content_w = max(0, width - left - right)
    content_h = max(0, height - top - bottom)
    content_ratio = (content_w * content_h) / (width * height) if width and height else 0.0
    return top, bottom, left, right, content_ratio


def frame_stats(frame: Path) -> dict[str, Any]:
    image = load_image(frame)
    width, height = image.size
    pixels = image.load()
    total = width * height
    black_count = 0
    white_count = 0
    brightness_sum = 0
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3
            brightness_sum += brightness
            if r < BLACK_THRESHOLD and g < BLACK_THRESHOLD and b < BLACK_THRESHOLD:
                black_count += 1
            if r > WHITE_THRESHOLD and g > WHITE_THRESHOLD and b > WHITE_THRESHOLD:
                white_count += 1
    top, bottom, left, right, content_ratio = edge_border_sizes(pixels, width, height)
    return {
        "frame": str(frame),
        "width": width,
        "height": height,
        "black_ratio": round(black_count / total, 5),
        "white_ratio": round(white_count / total, 5),
        "mean_brightness": round(brightness_sum / total, 3),
        "top_border_px": top,
        "bottom_border_px": bottom,
        "left_border_px": left,
        "right_border_px": right,
        "content_bbox_ratio": round(content_ratio, 5),
    }


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def compute_image_metrics(frames: list[Path], probe: dict[str, Any]) -> dict[str, Any]:
    stats = [frame_stats(frame) for frame in frames]
    if not stats:
        return {
            "sampled_frame_count": 0,
            "black_frame_count": 0,
            "black_frame_ratio": 0.0,
            "flash_frame_count": 0,
            "overexposed_frame_ratio": 0.0,
            "letterbox_or_pillarbox_risk": "unknown",
            "median_black_border_ratio": 0.0,
            "frame_stats": [],
        }
    black_frames = [item for item in stats if item["black_ratio"] > 0.8]
    flash_frames = [item for item in stats if item["white_ratio"] > 0.75]
    overexposed = [item for item in stats if item["white_ratio"] > 0.25]
    border_ratios = [
        1.0 - float(item["content_bbox_ratio"])
        for item in stats
        if item["black_ratio"] <= 0.8
    ]
    heavy_border_frames = [value for value in border_ratios if value > 0.2]
    border_risk = "low"
    if border_ratios and len(heavy_border_frames) / len(border_ratios) > 0.3:
        border_risk = "high"
    elif border_ratios and len(heavy_border_frames) / len(border_ratios) > 0.1:
        border_risk = "medium"
    width = int(probe.get("width") or 0)
    height = int(probe.get("height") or 0)
    fps = float(probe.get("fps") or 0)
    bitrate = int(probe.get("video_bitrate") or 0)
    bpppf = round(bitrate / (width * height * fps), 6) if width and height and fps and bitrate else None
    compression_risk = "unknown"
    if bpppf is not None:
        if bpppf < 0.03:
            compression_risk = "high"
        elif bpppf < 0.07:
            compression_risk = "medium"
        else:
            compression_risk = "low"
    return {
        "sampled_frame_count": len(stats),
        "short_side": min(width, height) if width and height else None,
        "aspect_ratio": round(width / height, 3) if width and height else None,
        "target_aspect_ratio": "9:16",
        "bits_per_pixel_per_frame": bpppf,
        "compression_risk": compression_risk,
        "black_frame_count": len(black_frames),
        "black_frame_ratio": round(len(black_frames) / len(stats), 5),
        "flash_frame_count": len(flash_frames),
        "overexposed_frame_ratio": round(len(overexposed) / len(stats), 5),
        "median_black_border_ratio": round(median(border_ratios), 5),
        "letterbox_or_pillarbox_risk": border_risk,
        "median_top_border_px": int(median([item["top_border_px"] for item in stats])),
        "median_bottom_border_px": int(median([item["bottom_border_px"] for item in stats])),
        "median_left_border_px": int(median([item["left_border_px"] for item in stats])),
        "median_right_border_px": int(median([item["right_border_px"] for item in stats])),
        "median_content_bbox_ratio": round(median([item["content_bbox_ratio"] for item in stats]), 5),
        "frame_stats": stats,
    }


def parse_volumedetect(stderr: str) -> dict[str, Any]:
    mean = re.search(r"mean_volume:\s*([-0-9.]+)\s*dB", stderr)
    max_volume = re.search(r"max_volume:\s*([-0-9.]+)\s*dB", stderr)
    return {
        "mean_volume_db": float(mean.group(1)) if mean else None,
        "max_volume_db": float(max_volume.group(1)) if max_volume else None,
    }


def parse_ebur128(stderr: str) -> dict[str, Any]:
    integrated_matches = re.findall(r"I:\s*([-0-9.]+)\s*LUFS", stderr)
    lra_matches = re.findall(r"LRA:\s*([-0-9.]+)\s*LU", stderr)
    peak_matches = re.findall(r"Peak:\s*([-0-9.]+)\s*dBFS", stderr)
    return {
        "integrated_lufs": float(integrated_matches[-1]) if integrated_matches else None,
        "loudness_range_lu": float(lra_matches[-1]) if lra_matches else None,
        "true_peak_dbtp": float(peak_matches[-1]) if peak_matches else None,
    }


def parse_silencedetect(stderr: str) -> list[dict[str, float]]:
    starts = [float(value) for value in re.findall(r"silence_start:\s*([-0-9.]+)", stderr)]
    ends = [
        (float(end), float(duration))
        for end, duration in re.findall(r"silence_end:\s*([-0-9.]+)\s*\|\s*silence_duration:\s*([-0-9.]+)", stderr)
    ]
    segments = []
    for index, start in enumerate(starts):
        if index < len(ends):
            end, duration = ends[index]
            segments.append({"start": round(start, 3), "end": round(end, 3), "duration": round(duration, 3)})
    return segments


def extract_audio_wav(video_path: Path, wav_path: Path) -> bool:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
    )
    return result.returncode == 0 and wav_path.exists() and wav_path.stat().st_size > 0


def compute_bgm_structure(wav_path: Path) -> dict[str, Any]:
    if not wav_path.exists():
        return {"estimated_bpm": None, "bpm_confidence": "low", "energy_curve": [], "high_energy_segments": []}
    with wave.open(str(wav_path), "rb") as handle:
        frame_rate = handle.getframerate()
        total_frames = handle.getnframes()
        raw = handle.readframes(total_frames)
    if not raw:
        return {"estimated_bpm": None, "bpm_confidence": "low", "energy_curve": [], "high_energy_segments": []}
    samples = []
    for index in range(0, len(raw) - 1, 2):
        value = int.from_bytes(raw[index : index + 2], byteorder="little", signed=True)
        samples.append(value / 32768.0)
    window = max(1, frame_rate)
    energy_curve = []
    energies = []
    for start in range(0, len(samples), window):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        rms = math.sqrt(sum(sample * sample for sample in chunk) / len(chunk))
        rms_db = 20 * math.log10(max(rms, 1e-6))
        segment = {
            "start": round(start / frame_rate, 3),
            "end": round(min(start + window, len(samples)) / frame_rate, 3),
            "rms_db": round(rms_db, 3),
        }
        energy_curve.append(segment)
        energies.append(rms_db)
    if not energies:
        return {"estimated_bpm": None, "bpm_confidence": "low", "energy_curve": [], "high_energy_segments": []}
    threshold = median(energies) + 3.0
    high_energy_segments = [segment for segment in energy_curve if segment["rms_db"] >= threshold]
    peaks = []
    for index in range(1, len(energies)):
        if energies[index] - energies[index - 1] > 3.5:
            peaks.append(energy_curve[index]["start"])
    bpm = None
    confidence = "low"
    if len(peaks) >= 4:
        intervals = [peaks[index] - peaks[index - 1] for index in range(1, len(peaks)) if peaks[index] > peaks[index - 1]]
        interval = median(intervals)
        if interval > 0:
            bpm = int(round(60.0 / interval))
            while bpm < 70:
                bpm *= 2
            while bpm > 180:
                bpm = int(round(bpm / 2))
            confidence = "low"
    return {
        "estimated_bpm": bpm,
        "bpm_confidence": confidence,
        "energy_curve": energy_curve,
        "high_energy_segments": high_energy_segments,
        "suggested_cut_points": [round(value, 3) for value in peaks[:20]],
    }


def compute_audio_metrics(video_path: Path, probe: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    if not probe.get("has_audio"):
        return {
            "has_audio": False,
            "mean_volume_db": None,
            "max_volume_db": None,
            "integrated_lufs": None,
            "loudness_range_lu": None,
            "true_peak_dbtp": None,
            "silence_segments": [],
            "silence_ratio": None,
            "bgm_structure": compute_bgm_structure(Path("__missing__")),
        }
    volume = parse_volumedetect(
        run_process(["ffmpeg", "-hide_banner", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"]).stderr
    )
    ebur = parse_ebur128(
        run_process(["ffmpeg", "-hide_banner", "-i", str(video_path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]).stderr
    )
    silence_segments = parse_silencedetect(
        run_process(["ffmpeg", "-hide_banner", "-i", str(video_path), "-af", "silencedetect=noise=-35dB:d=0.5", "-f", "null", "-"]).stderr
    )
    duration = float(probe.get("duration_sec") or 0)
    silence_total = sum(segment["duration"] for segment in silence_segments)
    wav_path = output_dir / "audio_mono_22050.wav"
    bgm = compute_bgm_structure(wav_path) if extract_audio_wav(video_path, wav_path) else compute_bgm_structure(Path("__missing__"))
    return {
        "has_audio": True,
        **volume,
        **ebur,
        "silence_segments": silence_segments,
        "silence_ratio": round(silence_total / duration, 5) if duration else None,
        "estimated_bpm": bgm["estimated_bpm"],
        "bpm_confidence": bgm["bpm_confidence"],
        "bgm_structure": bgm,
    }


def normalize01(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def mad(values: list[float]) -> float:
    if not values:
        return 0.0
    center = median(values)
    return median([abs(value - center) for value in values])


def read_wav_samples(wav_path: Path) -> tuple[int, list[float]]:
    if not wav_path.exists():
        return 0, []
    with wave.open(str(wav_path), "rb") as handle:
        frame_rate = handle.getframerate()
        total_frames = handle.getnframes()
        raw = handle.readframes(total_frames)
    samples = [
        int.from_bytes(raw[index : index + 2], byteorder="little", signed=True) / 32768.0
        for index in range(0, len(raw) - 1, 2)
    ]
    return frame_rate, samples


def pick_local_peaks(series: list[tuple[float, float]], *, min_distance_sec: float, threshold: float) -> list[tuple[float, float]]:
    if len(series) < 3:
        return []
    candidates: list[tuple[float, float]] = []
    for index in range(1, len(series) - 1):
        time, value = series[index]
        if value < threshold:
            continue
        if value >= series[index - 1][1] and value >= series[index + 1][1]:
            candidates.append((time, value))
    candidates.sort(key=lambda item: item[1], reverse=True)
    selected: list[tuple[float, float]] = []
    for time, value in candidates:
        if all(abs(time - chosen_time) >= min_distance_sec for chosen_time, _ in selected):
            selected.append((time, value))
    return sorted(selected)


def estimate_bpm_from_times(times: list[float]) -> tuple[float | None, str]:
    if len(times) < 4:
        return None, "low"
    intervals = [
        times[index] - times[index - 1]
        for index in range(1, len(times))
        if 0.25 <= times[index] - times[index - 1] <= 1.5
    ]
    if len(intervals) < 3:
        return None, "low"
    interval = median(intervals)
    if interval <= 0:
        return None, "low"
    bpm = 60.0 / interval
    while bpm < 70:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    confidence = "medium" if mad(intervals) <= 0.18 else "low"
    return round(bpm, 3), confidence


def detect_audio_events(wav_path: Path, duration: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frame_rate, samples = read_wav_samples(wav_path)
    if not frame_rate or not samples:
        return [], {"estimated_bpm": None, "bpm_confidence": "low", "method": "wav_missing"}
    window = max(1, int(frame_rate * 0.05))
    hop = max(1, int(frame_rate * 0.025))
    energy_series: list[tuple[float, float]] = []
    for start in range(0, max(1, len(samples) - window), hop):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        rms = math.sqrt(sum(sample * sample for sample in chunk) / len(chunk))
        energy_series.append((round((start + window / 2) / frame_rate, 3), rms))
    if not energy_series:
        return [], {"estimated_bpm": None, "bpm_confidence": "low", "method": "empty_audio_series"}
    values = [value for _, value in energy_series]
    low = median(values)
    high = max(values)
    normalized_energy = [(time, normalize01(value, low, high)) for time, value in energy_series]
    onset_series: list[tuple[float, float]] = []
    for index in range(1, len(normalized_energy)):
        time, value = normalized_energy[index]
        prev = normalized_energy[index - 1][1]
        onset_series.append((time, max(0.0, value - prev)))
    onset_values = [value for _, value in onset_series]
    onset_threshold = max(0.08, median(onset_values) + mad(onset_values) * 2.5) if onset_values else 0.08
    energy_threshold = max(0.45, median([value for _, value in normalized_energy]) + mad([value for _, value in normalized_energy]) * 2.0)
    energy_peaks = pick_local_peaks(normalized_energy, min_distance_sec=0.22, threshold=energy_threshold)
    onset_peaks = pick_local_peaks(onset_series, min_distance_sec=0.16, threshold=onset_threshold)
    bpm, confidence = estimate_bpm_from_times([time for time, _ in onset_peaks] or [time for time, _ in energy_peaks])
    events: list[dict[str, Any]] = []
    event_id = 1
    for time, strength in energy_peaks[:80]:
        event_type = "accent_peak" if strength >= 0.78 else "energy_peak"
        events.append(
            {
                "id": f"a{event_id:04d}",
                "time": round(time, 3),
                "type": event_type,
                "strength": round(clamp01(strength), 3),
                "confidence": 0.72 if event_type == "accent_peak" else 0.62,
                "source": "rms_energy_peak",
            }
        )
        event_id += 1
    for time, strength in onset_peaks[:100]:
        events.append(
            {
                "id": f"a{event_id:04d}",
                "time": round(time, 3),
                "type": "onset_peak",
                "strength": round(clamp01(strength / max(onset_threshold, 1e-6)), 3),
                "confidence": 0.68,
                "source": "rms_onset_strength",
            }
        )
        event_id += 1
    if bpm and duration > 0:
        beat_interval = 60.0 / bpm
        beat_time = 0.0
        while beat_time <= duration:
            events.append(
                {
                    "id": f"a{event_id:04d}",
                    "time": round(beat_time, 3),
                    "type": "beat_grid",
                    "strength": 0.55,
                    "confidence": 0.50 if confidence == "low" else 0.66,
                    "source": "estimated_bpm_grid",
                }
            )
            event_id += 1
            beat_time += beat_interval
    events.sort(key=lambda item: (float(item["time"]), item["type"]))
    deduped: list[dict[str, Any]] = []
    for event in events:
        if event["type"] != "beat_grid":
            near = [
                existing
                for existing in deduped
                if existing["type"] != "beat_grid" and abs(float(existing["time"]) - float(event["time"])) < 0.035
            ]
            if near:
                best = max(near + [event], key=lambda item: (float(item["strength"]), float(item["confidence"])))
                for existing in near:
                    deduped.remove(existing)
                deduped.append(best)
                continue
        deduped.append(event)
    deduped.sort(key=lambda item: float(item["time"]))
    return deduped, {
        "estimated_bpm": bpm,
        "bpm_confidence": confidence,
        "method": "rms_energy_onset_grid_v1",
        "energy_peak_count": len(energy_peaks),
        "onset_peak_count": len(onset_peaks),
    }


def extract_motion_frames(video_path: Path, output_dir: Path, *, fps: float = MOTION_SAMPLE_FPS, max_frames: int = 360) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("motion_*.jpg"):
        old.unlink()
    output_pattern = output_dir / "motion_%04d.jpg"
    result = run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps},scale=240:-2",
            "-frames:v",
            str(max_frames),
            str(output_pattern),
        ]
    )
    if result.returncode != 0:
        return []
    return sorted(output_dir.glob("motion_*.jpg"))


def mean_abs_gray_diff(prev: Any, curr: Any, *, roi: tuple[float, float, float, float] | None = None) -> float:
    from PIL import ImageChops, ImageStat

    prev_gray = prev.convert("L")
    curr_gray = curr.convert("L")
    if roi:
        width, height = prev_gray.size
        left = int(width * roi[0])
        top = int(height * roi[1])
        right = int(width * roi[2])
        bottom = int(height * roi[3])
        prev_gray = prev_gray.crop((left, top, right, bottom))
        curr_gray = curr_gray.crop((left, top, right, bottom))
    diff = ImageChops.difference(prev_gray, curr_gray)
    return float(ImageStat.Stat(diff).mean[0]) / 255.0


def detect_scene_cut_events(video_path: Path, max_events: int = 120) -> list[dict[str, Any]]:
    result = run_process(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(video_path),
            "-vf",
            "select='gt(scene,0.25)',showinfo",
            "-frames:v",
            str(max_events),
            "-f",
            "null",
            "-",
        ]
    )
    events: list[dict[str, Any]] = []
    seen: set[float] = set()
    for line in result.stderr.splitlines():
        if "Parsed_showinfo" not in line or "pts_time:" not in line:
            continue
        time_match = re.search(r"pts_time:([-0-9.]+)", line)
        if not time_match:
            continue
        score_match = re.search(r"(?:scene_score|lavfi.scene_score)[:=]\s*([-0-9.]+)", line)
        time = round(float(time_match.group(1)), 3)
        score = clamp01(float(score_match.group(1))) if score_match else 0.65
        if time in seen:
            continue
        seen.add(time)
        events.append(
            {
                "id": f"v{len(events) + 1:04d}",
                "time": time,
                "type": "scene_cut",
                "strength": round(score, 3),
                "confidence": 0.72,
                "source": "ffmpeg_scene_select_showinfo",
            }
        )
    return events


def detect_visual_events(
    video_path: Path,
    version_dir: Path,
    probe: dict[str, Any],
    video_metrics: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = detect_scene_cut_events(video_path)
    next_id = len(events) + 1
    motion_frames = extract_motion_frames(video_path, version_dir / "rhythm_motion_frames")
    global_series: list[tuple[float, float]] = []
    roi_series: list[tuple[float, float]] = []
    text_series: list[tuple[float, float]] = []
    try:
        from PIL import Image
    except Exception as exc:
        raise OutputReviewError("Pillow is required for rhythm visual event detection") from exc
    for index in range(1, len(motion_frames)):
        prev = Image.open(motion_frames[index - 1]).convert("RGB")
        curr = Image.open(motion_frames[index]).convert("RGB")
        time = round(index / MOTION_SAMPLE_FPS, 3)
        global_motion = mean_abs_gray_diff(prev, curr)
        lower_center_motion = mean_abs_gray_diff(prev, curr, roi=(0.25, 0.45, 0.75, 0.95))
        upper_text_motion = mean_abs_gray_diff(prev, curr, roi=(0.05, 0.02, 0.95, 0.22))
        lower_text_motion = mean_abs_gray_diff(prev, curr, roi=(0.05, 0.72, 0.95, 0.98))
        relative_step_motion = max(0.0, lower_center_motion - global_motion * 0.35)
        text_overlay_motion = max(0.0, max(upper_text_motion, lower_text_motion) - global_motion * 0.25)
        global_series.append((time, global_motion))
        roi_series.append((time, relative_step_motion))
        text_series.append((time, text_overlay_motion))
    if global_series:
        global_values = [value for _, value in global_series]
        global_threshold = max(0.035, median(global_values) + mad(global_values) * 2.0)
        for time, strength in pick_local_peaks(global_series, min_distance_sec=0.18, threshold=global_threshold)[:100]:
            events.append(
                {
                    "id": f"v{next_id:04d}",
                    "time": round(time, 3),
                    "type": "global_motion_peak",
                    "strength": round(clamp01(strength / max(global_threshold * 2.5, 1e-6)), 3),
                    "confidence": 0.58,
                    "source": "frame_difference_global_motion",
                }
            )
            next_id += 1
    if text_series:
        text_values = [value for _, value in text_series]
        text_threshold = max(0.025, median(text_values) + mad(text_values) * 2.4)
        for time, strength in pick_local_peaks(text_series, min_distance_sec=0.25, threshold=text_threshold)[:60]:
            events.append(
                {
                    "id": f"v{next_id:04d}",
                    "time": round(time, 3),
                    "type": "text_overlay_change",
                    "strength": round(clamp01(strength / max(text_threshold * 2.0, 1e-6)), 3),
                    "confidence": 0.44,
                    "source": "top_bottom_band_frame_difference",
                    "notes": "顶部/底部字幕区变化代理，V1 不做 OCR，仅提示标题/字幕变化时间点。",
                }
            )
            next_id += 1
    if roi_series:
        roi_values = [value for _, value in roi_series]
        roi_threshold = max(0.025, median(roi_values) + mad(roi_values) * 2.0)
        for time, strength in pick_local_peaks(roi_series, min_distance_sec=0.25, threshold=roi_threshold)[:120]:
            normalized_strength = round(clamp01(strength / max(roi_threshold * 2.2, 1e-6)), 3)
            events.append(
                {
                    "id": f"v{next_id:04d}",
                    "time": round(time, 3),
                    "type": "step_motion_peak_proxy",
                    "strength": normalized_strength,
                    "confidence": 0.56,
                    "source": "lower_center_roi_frame_difference",
                    "notes": "下中部 ROI 相对运动峰，作为 V1 步点/身体起伏代理。",
                }
            )
            next_id += 1
            if normalized_strength >= 0.72:
                events.append(
                    {
                        "id": f"v{next_id:04d}",
                        "time": round(time, 3),
                        "type": "pose_keyframe",
                        "strength": normalized_strength,
                        "confidence": 0.38,
                        "source": "motion_peak_pose_keyframe_proxy",
                        "notes": "V1 姿态关键帧代理：由强身体运动峰推断，不等同于人体关键点模型。",
                    }
                )
                next_id += 1
    frame_stats_list = video_metrics.get("frame_stats") or []
    early_stats = [item for item in frame_stats_list[:4] if isinstance(item, dict)]
    if early_stats:
        first = early_stats[0]
        if first.get("black_ratio", 0) > 0.45 or first.get("white_ratio", 0) > 0.20 or first.get("mean_brightness", 128) > 205:
            events.append(
                {
                    "id": f"v{next_id:04d}",
                    "time": 0.25,
                    "type": "intro_effect",
                    "strength": 0.72,
                    "confidence": 0.52,
                    "source": "sampled_frame_brightness_proxy",
                    "notes": "开头存在黑场、过曝或亮度异常代理信号，需人工确认是否为设计效果。",
                }
            )
            next_id += 1
    events.sort(key=lambda item: float(item["time"]))
    for index, event in enumerate(events, start=1):
        event["id"] = f"v{index:04d}"
    return events, {
        "method": "ffmpeg_scene_select_plus_frame_difference_v1",
        "motion_frame_count": len(motion_frames),
        "camera_motion_compensation": "relative_roi_minus_global_frame_difference_v1",
        "split_screen_roi_proxy": "top_bottom_and_center_band_frame_difference_v1",
        "scene_cut_count": len([event for event in events if event["type"] == "scene_cut"]),
        "global_motion_peak_count": len([event for event in events if event["type"] == "global_motion_peak"]),
        "step_motion_peak_proxy_count": len([event for event in events if event["type"] == "step_motion_peak_proxy"]),
        "pose_keyframe_count": len([event for event in events if event["type"] == "pose_keyframe"]),
        "text_overlay_change_count": len([event for event in events if event["type"] == "text_overlay_change"]),
    }


def allowed_audio_event_types(visual_type: str) -> set[str]:
    if visual_type == "scene_cut":
        return {"accent_peak", "onset_peak", "energy_peak"}
    if visual_type == "step_motion_peak_proxy":
        return {"beat_grid", "onset_peak", "accent_peak"}
    if visual_type == "global_motion_peak":
        return {"accent_peak", "onset_peak", "energy_peak", "beat_grid"}
    if visual_type == "intro_effect":
        return {"accent_peak", "onset_peak", "energy_peak", "beat_grid"}
    if visual_type == "text_overlay_change":
        return {"beat_grid", "onset_peak", "accent_peak"}
    return {"accent_peak", "onset_peak", "energy_peak", "beat_grid"}


def event_tolerance(visual_type: str) -> float:
    return EVENT_TOLERANCE_SEC.get(visual_type, 0.18)


def alignment_score(delta: float, tolerance: float) -> float:
    sigma = max(tolerance / 2.0, 0.001)
    return math.exp(-((delta**2) / (2 * sigma**2)))


def align_audio_visual_events(audio_events: list[dict[str, Any]], visual_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[float, float, dict[str, Any], dict[str, Any], float, float]] = []
    for visual in visual_events:
        visual_time = float(visual["time"])
        tolerance = event_tolerance(str(visual["type"]))
        allowed = allowed_audio_event_types(str(visual["type"]))
        for audio in audio_events:
            if audio.get("type") not in allowed:
                continue
            audio_time = float(audio["time"])
            delta = visual_time - audio_time
            abs_delta = abs(delta)
            if abs_delta <= tolerance:
                score = alignment_score(delta, tolerance)
                strength_score = float(visual.get("strength") or 0.0) * float(audio.get("strength") or 0.0)
                candidates.append((abs_delta, -score * strength_score, visual, audio, delta, score))
    candidates.sort(key=lambda item: (item[0], item[1]))
    matched_visual: set[str] = set()
    matched_audio: set[str] = set()
    matches: list[dict[str, Any]] = []
    for abs_delta, _, visual, audio, delta, score in candidates:
        visual_id = str(visual["id"])
        audio_id = str(audio["id"])
        if visual_id in matched_visual or audio_id in matched_audio:
            continue
        matched_visual.add(visual_id)
        matched_audio.add(audio_id)
        matches.append(
            {
                "visual_event_id": visual_id,
                "audio_event_id": audio_id,
                "visual_time": round(float(visual["time"]), 3),
                "audio_time": round(float(audio["time"]), 3),
                "delta_sec": round(delta, 3),
                "abs_delta_sec": round(abs_delta, 3),
                "tolerance_sec": round(event_tolerance(str(visual["type"])), 3),
                "alignment_score": round(score, 3),
                "visual_type": visual["type"],
                "audio_type": audio["type"],
                "visual_strength": visual.get("strength"),
                "audio_strength": audio.get("strength"),
            }
        )
    matches.sort(key=lambda item: float(item["visual_time"]))
    return matches


def ratio_score(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def periodicity_score(step_events: list[dict[str, Any]], bpm: float | None) -> float:
    if len(step_events) < 3:
        return 0.0
    times = [float(event["time"]) for event in step_events]
    intervals = [
        times[index] - times[index - 1]
        for index in range(1, len(times))
        if times[index] > times[index - 1]
    ]
    if not intervals:
        return 0.0
    regularity = clamp01(1.0 - mad(intervals) / max(median(intervals), 0.001))
    if not bpm:
        return round(regularity * 0.7, 4)
    beat_interval = 60.0 / bpm
    interval = median(intervals)
    candidate_ratios = [1.0, 0.5, 2.0]
    best_ratio_error = min(abs(interval - beat_interval * ratio) / max(beat_interval * ratio, 0.001) for ratio in candidate_ratios)
    beat_fit = clamp01(1.0 - best_ratio_error)
    return round((regularity * 0.55) + (beat_fit * 0.45), 4)


def compute_dimension_score(
    visual_type: str,
    matches: list[dict[str, Any]],
    visual_events: list[dict[str, Any]],
) -> float:
    typed_visuals = [event for event in visual_events if event.get("type") == visual_type]
    if not typed_visuals:
        return 0.0
    typed_matches = [match for match in matches if match.get("visual_type") == visual_type]
    weighted = sum(
        float(match.get("alignment_score") or 0.0)
        * float(match.get("visual_strength") or 0.0)
        * float(match.get("audio_strength") or 0.0)
        for match in typed_matches
    )
    denominator = sum(float(event.get("strength") or 0.0) for event in typed_visuals) or len(typed_visuals)
    coverage = len(typed_matches) / len(typed_visuals)
    score = (weighted / max(denominator, 1e-6)) * 0.65 + coverage * 0.35
    return round(clamp01(score), 4)


def compute_fixability_score(matches: list[dict[str, Any]]) -> tuple[float, str]:
    deltas = [float(match["delta_sec"]) for match in matches]
    if len(deltas) < 2:
        return 0.0, "unknown"
    center = median(deltas)
    spread = mad(deltas)
    if abs(center) <= 0.12 and spread <= 0.06:
        return 0.86, "high"
    if abs(center) <= 0.20 and spread <= 0.12:
        return 0.62, "medium"
    return 0.28, "low"


def profile_dimension_value(key: str, dimensions: dict[str, float]) -> float:
    aliases = {
        "global_motion_rhythm": "motion_sync",
        "structural_match": "motion_sync",
        "action_node_sync": "motion_sync",
        "action_burst_sync": "motion_sync",
        "speed_change_sync": "motion_sync",
        "impact_sync": "motion_sync",
        "semantic_pause_sync": "text_overlay_sync",
        "expression_change": "intro_effect",
        "intro_hook": "intro_effect",
        "subject_presence": "intro_effect",
        "stability": "phase_consistency",
    }
    return dimensions.get(key, dimensions.get(aliases.get(key, ""), 0.0))


def score_rhythm_sync(
    *,
    profile: str,
    audio_events: list[dict[str, Any]],
    visual_events: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    probe: dict[str, Any],
    risk_flags: list[str],
    audio_meta: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    step_events = [event for event in visual_events if event.get("type") == "step_motion_peak_proxy"]
    scene_events = [event for event in visual_events if event.get("type") == "scene_cut"]
    motion_events = [event for event in visual_events if event.get("type") == "global_motion_peak"]
    intro_events = [event for event in visual_events if event.get("type") == "intro_effect"]
    step_matches = [match for match in matches if match.get("visual_type") == "step_motion_peak_proxy"]
    scene_matches = [match for match in matches if match.get("visual_type") == "scene_cut"]
    important_audio = [
        event
        for event in audio_events
        if event.get("type") in {"accent_peak", "onset_peak", "energy_peak"} and float(event.get("strength") or 0.0) >= 0.45
    ]
    matched_audio_ids = {str(match["audio_event_id"]) for match in matches}
    beat_coverage = ratio_score(len([event for event in important_audio if str(event["id"]) in matched_audio_ids]), len(important_audio))
    deltas = [float(match["delta_sec"]) for match in matches]
    median_delta = round(median(deltas), 4) if deltas else None
    mad_delta = round(mad(deltas), 4) if deltas else None
    phase_consistency = round(clamp01(1.0 - (mad_delta or 0.0) / 0.18), 4) if deltas else 0.0
    weighted_numerator = sum(
        float(match.get("alignment_score") or 0.0)
        * float(match.get("visual_strength") or 0.0)
        * float(match.get("audio_strength") or 0.0)
        for match in matches
    )
    weighted_denominator = sum(float(event.get("strength") or 0.0) for event in visual_events) or len(visual_events)
    weighted_sync = round(clamp01(weighted_numerator / max(weighted_denominator, 1e-6)), 4)
    fixability_score, fixability = compute_fixability_score(matches)
    dimensions = {
        "step_sync": compute_dimension_score("step_motion_peak_proxy", matches, visual_events),
        "cut_sync": compute_dimension_score("scene_cut", matches, visual_events),
        "motion_sync": compute_dimension_score("global_motion_peak", matches, visual_events),
        "pose_keyframe_sync": compute_dimension_score("pose_keyframe", matches, visual_events),
        "intro_effect": max(compute_dimension_score("intro_effect", matches, visual_events), 0.55 if intro_events else 0.0),
        "text_overlay_sync": compute_dimension_score("text_overlay_change", matches, visual_events),
        "beat_coverage": beat_coverage,
        "phase_consistency": phase_consistency,
        "fixability_score": round(fixability_score, 4),
        "periodicity_score": periodicity_score(step_events, audio_meta.get("estimated_bpm")),
        "weighted_sync": weighted_sync,
    }
    dimensions.update(
        {
            "structural_match": round(
                clamp01(dimensions["motion_sync"] * 0.45 + dimensions["text_overlay_sync"] * 0.25 + dimensions["cut_sync"] * 0.30),
                4,
            ),
            "action_node_sync": round(clamp01(dimensions["motion_sync"] * 0.40 + dimensions["step_sync"] * 0.35 + dimensions["pose_keyframe_sync"] * 0.25), 4),
            "global_motion_rhythm": dimensions["motion_sync"],
            "subject_presence": dimensions["intro_effect"],
            "stability": dimensions["phase_consistency"],
            "action_burst_sync": round(clamp01(dimensions["motion_sync"] * 0.65 + dimensions["pose_keyframe_sync"] * 0.35), 4),
            "speed_change_sync": dimensions["fixability_score"],
            "impact_sync": dimensions["cut_sync"],
            "semantic_pause_sync": dimensions["text_overlay_sync"],
            "expression_change": dimensions["intro_effect"],
            "intro_hook": dimensions["intro_effect"],
        }
    )
    profile_key = profile if profile in PROFILE_WEIGHTS else "general_bgm_edit"
    weights = PROFILE_WEIGHTS[profile_key]
    total_weight = sum(weights.values()) or 1.0
    weighted_total = sum(profile_dimension_value(key, dimensions) * weight for key, weight in weights.items()) / total_weight
    penalties: list[dict[str, Any]] = []
    if "mostly_black_frames" in risk_flags:
        penalties.append({"type": "mostly_black_frames", "value": 0.30, "reason": "大量黑场会压低可发布性。"})
    if "audio_missing" in risk_flags:
        penalties.append({"type": "audio_missing", "value": 0.25, "reason": "缺少音频，无法可靠评估卡点。"})
    width = int(probe.get("width") or 0)
    height = int(probe.get("height") or 0)
    if width > height and profile_key in {"split_screen_comparison", "general_bgm_edit"}:
        penalties.append({"type": "horizontal_platform_fit", "value": 0.06, "reason": "横屏直发抖音/小红书需确认竖屏包装。"})
    penalty_total = sum(float(item["value"]) for item in penalties)
    final_score = round(clamp01(weighted_total - penalty_total), 4)
    diagnostics = {
        "detected_audio_events": len(audio_events),
        "detected_visual_events": len(visual_events),
        "matched_events": len(matches),
        "detected_step_events": len(step_events),
        "matched_step_events": len(step_matches),
        "detected_scene_cuts": len(scene_events),
        "matched_scene_cuts": len(scene_matches),
        "detected_motion_events": len(motion_events),
        "median_delta_sec": median_delta,
        "mad_delta_sec": mad_delta,
        "fixability": fixability,
        "profile_used": profile_key,
        "profile_weights": weights,
        "penalties": penalties,
    }
    scores = {
        "final_score": final_score,
        **dimensions,
    }
    review_points = build_rhythm_review_points(visual_events, matches, scores, diagnostics)
    edit_suggestions = build_edit_suggestions(visual_events, audio_events, matches, diagnostics, scores, risk_flags)
    return scores, diagnostics, review_points, edit_suggestions


def nearest_audio_event(
    visual_event: dict[str, Any],
    audio_events: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float | None]:
    allowed = allowed_audio_event_types(str(visual_event.get("type")))
    candidates = [event for event in audio_events if event.get("type") in allowed]
    if not candidates:
        return None, None
    visual_time = float(visual_event.get("time") or 0.0)
    nearest = min(candidates, key=lambda event: abs(float(event.get("time") or 0.0) - visual_time))
    return nearest, round(visual_time - float(nearest.get("time") or 0.0), 3)


def build_edit_suggestions(
    visual_events: list[dict[str, Any]],
    audio_events: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    scores: dict[str, Any],
    risk_flags: list[str],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    median_delta = diagnostics.get("median_delta_sec")
    mad_delta = diagnostics.get("mad_delta_sec")
    if isinstance(median_delta, (int, float)) and isinstance(mad_delta, (int, float)):
        if diagnostics.get("fixability") in {"high", "medium"} and abs(float(median_delta)) >= 0.015:
            suggestions.append(
                {
                    "time": 0.0,
                    "action": "global_timeline_shift",
                    "target_time": round(-float(median_delta), 3),
                    "delta_sec": round(-float(median_delta), 3),
                    "reason": f"多数匹配事件整体偏移 {median_delta}s，MAD={mad_delta}s，可尝试整体平移画面或音频进行微调。",
                    "confidence": diagnostics.get("fixability"),
                }
            )
    weak_matched_ids = {str(match["visual_event_id"]) for match in matches if float(match.get("alignment_score") or 0.0) >= 0.45}
    unmatched_priority = [
        event
        for event in visual_events
        if event.get("type") in {"scene_cut", "step_motion_peak_proxy", "global_motion_peak", "text_overlay_change"}
        and str(event.get("id")) not in weak_matched_ids
    ]
    for event in unmatched_priority[:6]:
        nearest, delta = nearest_audio_event(event, audio_events)
        if nearest is None or delta is None:
            continue
        if abs(delta) > event_tolerance(str(event.get("type"))) * 1.8:
            continue
        action = "move_cut_to_nearest_beat" if event.get("type") == "scene_cut" else "micro_speed_or_timing_adjust"
        suggestions.append(
            {
                "time": round(float(event.get("time") or 0.0), 3),
                "action": action,
                "target_time": round(float(nearest.get("time") or 0.0), 3),
                "delta_sec": round(-delta, 3),
                "reason": f"{event.get('type')} 距离最近 {nearest.get('type')} 约 {abs(delta)}s，可人工确认是否需要贴到音乐事件。",
                "confidence": "medium" if abs(delta) <= 0.28 else "low",
            }
        )
    if "black_frame_detected" in risk_flags or "mostly_black_frames" in risk_flags:
        suggestions.append(
            {
                "time": 0.0,
                "action": "trim_black_frames",
                "target_time": None,
                "delta_sec": None,
                "reason": "检测到黑场帧，发布前建议检查片头/片尾并裁掉多余黑场。",
                "confidence": "medium",
            }
        )
    if float(scores.get("intro_effect") or 0.0) == 0.0:
        suggestions.append(
            {
                "time": 0.5,
                "action": "manual_intro_hook_review",
                "target_time": None,
                "delta_sec": None,
                "reason": "未检测到明显开头效果事件，建议人工确认首帧主体、标题和前 3 秒钩子是否足够强。",
                "confidence": "low",
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for item in suggestions:
        key = (str(item.get("action")), round(float(item.get("time") or 0.0), 1))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:10]


def build_timing_edit_path(
    visual_events: list[dict[str, Any]],
    audio_events: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    match_by_visual = {str(match["visual_event_id"]): match for match in matches}
    candidates: list[dict[str, Any]] = []
    for event in visual_events:
        if event.get("type") not in {"scene_cut", "global_motion_peak", "step_motion_peak_proxy", "pose_keyframe", "text_overlay_change"}:
            continue
        nearest, delta = nearest_audio_event(event, audio_events)
        if nearest is None or delta is None:
            continue
        match = match_by_visual.get(str(event.get("id")))
        sync = float(match.get("alignment_score") or 0.0) if match else alignment_score(delta, event_tolerance(str(event.get("type"))))
        base = sync * 0.65 + float(event.get("strength") or 0.0) * 0.25 + float(nearest.get("strength") or 0.0) * 0.10
        candidates.append(
            {
                "visual_event_id": event.get("id"),
                "audio_event_id": nearest.get("id"),
                "visual_time": round(float(event.get("time") or 0.0), 3),
                "target_time": round(float(nearest.get("time") or 0.0), 3),
                "delta_sec": round(-float(delta), 3),
                "visual_type": event.get("type"),
                "audio_type": nearest.get("type"),
                "node_score": round(clamp01(base), 4),
            }
        )
    candidates.sort(key=lambda item: float(item["visual_time"]))
    if not candidates:
        return []
    scores: list[float] = []
    prev_index: list[int | None] = []
    for index, candidate in enumerate(candidates):
        best_score = float(candidate["node_score"])
        best_prev: int | None = None
        for prior_index in range(index):
            gap = float(candidate["visual_time"]) - float(candidates[prior_index]["visual_time"])
            if gap < 0.35:
                continue
            continuity_bonus = 0.08 if gap <= 3.0 else 0.02
            trial = scores[prior_index] + float(candidate["node_score"]) + continuity_bonus
            if trial > best_score:
                best_score = trial
                best_prev = prior_index
        scores.append(best_score)
        prev_index.append(best_prev)
    best_end = max(range(len(scores)), key=lambda index: scores[index])
    path_indices: list[int] = []
    cursor: int | None = best_end
    while cursor is not None:
        path_indices.append(cursor)
        cursor = prev_index[cursor]
    path_indices.reverse()
    path = [candidates[index] for index in path_indices[-12:]]
    for order, item in enumerate(path, start=1):
        item["order"] = order
        item["suggested_operation"] = "cut_or_speed_anchor" if item["visual_type"] == "scene_cut" else "speed_anchor"
    return path


def build_rhythm_review_points(
    visual_events: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    scores: dict[str, Any],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    strongest_matches = sorted(matches, key=lambda item: (float(item.get("alignment_score") or 0.0), -float(item.get("abs_delta_sec") or 0.0)), reverse=True)[:5]
    for match in strongest_matches:
        points.append(
            {
                "time": match["visual_time"],
                "type": f"{match['visual_type']}_matched",
                "severity": "info",
                "reason": f"{match['visual_type']} 与 {match['audio_type']} 相差 {match['abs_delta_sec']}s。",
            }
        )
    matched_visual_ids = {str(match["visual_event_id"]) for match in matches}
    missed = [
        event
        for event in visual_events
        if event.get("type") in {"scene_cut", "step_motion_peak_proxy", "global_motion_peak"}
        and str(event.get("id")) not in matched_visual_ids
    ][:5]
    for event in missed:
        points.append(
            {
                "time": event["time"],
                "type": f"{event['type']}_unmatched",
                "severity": "warning",
                "reason": f"{event['type']} 未匹配到相邻音乐事件，建议人工看是否错拍或检测噪声。",
            }
        )
    if diagnostics.get("fixability") in {"high", "medium"} and diagnostics.get("median_delta_sec") is not None:
        points.append(
            {
                "time": 0.0,
                "type": "fixability",
                "severity": "info",
                "reason": f"匹配偏移中位数 {diagnostics['median_delta_sec']}s，可修复性 {diagnostics['fixability']}。",
            }
        )
    if scores.get("intro_effect", 0) > 0:
        points.append(
            {
                "time": 0.5,
                "type": "intro_hook",
                "severity": "info",
                "reason": "请人工确认首帧主体、背景和开头效果是否适合作为封面/前 3 秒钩子。",
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[float, str]] = set()
    for point in sorted(points, key=lambda item: float(item["time"])):
        key = (round(float(point["time"]), 1), str(point["type"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(point)
    return deduped[:12]


def extract_rhythm_review_frames(video_path: Path, review_points: list[dict[str, Any]], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("review_*.jpg"):
        old.unlink()
    paths: list[str] = []
    for index, point in enumerate(review_points[:8], start=1):
        seconds = max(0.0, float(point.get("time") or 0.0))
        output = output_dir / f"review_{index:02d}_{timestamp_label(seconds)}_{point.get('type', 'point')}.jpg"
        result = run_process(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
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
                "scale='min(720,iw)':-2",
                str(output),
            ]
        )
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            paths.append(str(output))
    return paths


def evaluate_brief_fit(brief: Path | None, script: Path | None, publish_pack: Path | None) -> dict[str, Any]:
    available = [path for path in [brief, script, publish_pack] if path and path.exists() and path.stat().st_size > 0]
    if not available:
        return {
            "current_brief_fit": "unknown",
            "brief_fit_method": "metadata_only",
            "brief_fit_confidence": "low",
            "content_confidence": "low",
            "human_decision_required": True,
            "notes": ["未提供可用于内容对照的 Brief / Script / Publish Pack。"],
        }
    return {
        "current_brief_fit": "unknown",
        "brief_fit_method": "brief_script_publish_pack_available_without_ocr_asr",
        "brief_fit_confidence": "low",
        "content_confidence": "low",
        "human_decision_required": True,
        "notes": ["已读取内容上下文路径，但 v1 未做完整 OCR/ASR/视觉语义审片，内容匹配需人工确认。"],
    }


def normalize_platforms(text: str) -> list[str]:
    aliases = {
        "抖音": "抖音",
        "小红书": "小红书",
        "视频号": "视频号",
        "B站": "B站",
        "B 站": "B站",
        "bilibili": "B站",
        "快手": "快手",
        "朋友圈": "朋友圈",
        "YouTube": "YouTube",
        "youtube": "YouTube",
    }
    label_match = re.search(r"(?:发布平台|目标平台|platform)\s*[:：]\s*(.*)$", text, flags=re.IGNORECASE)
    if label_match:
        text = label_match.group(1)
        if not text.strip():
            return []
    elif re.search(r"(?:发布平台|目标平台)\s*$", text):
        return []
    platforms: list[str] = []
    for raw in re.split(r"[,，、/|;；]+", text):
        token = raw.strip().strip("`*_- ")
        if not token or token in {"发布平台", "目标平台", "platform"}:
            continue
        name = aliases.get(token) or aliases.get(token.lower()) or token
        if name not in platforms:
            platforms.append(name)
    return platforms


def load_project_context(project_root: Path | None) -> ProjectContext:
    if not project_root:
        return ProjectContext(project_root=None, target_platforms=[], project_goal="", notes=["未提供项目根目录。"])
    readme = project_root / "readme.md"
    if not readme.exists():
        return ProjectContext(project_root=project_root, target_platforms=[], project_goal="", notes=[f"未找到项目 readme：{readme}"])
    text = readme.read_text(encoding="utf-8")
    profile = load_creator_context(project_root, brief_text=text)
    platforms: list[str] = normalize_platforms(profile.get("platforms", ""))
    goal = profile.get("project_goal", "")
    notes: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "发布平台" in line:
            line_platforms = normalize_platforms(line)
            for platform in line_platforms:
                if platform not in platforms:
                    platforms.append(platform)
            known = {"抖音", "小红书", "视频号", "B站", "快手", "朋友圈", "YouTube"}
            if not line_platforms or set(line_platforms) - known:
                notes.append("未识别发布平台，请人工确认平台适配。")
        elif "剪辑目标" in line and not goal:
            goal = line.split("：", 1)[-1].strip() if "：" in line else line.split(":", 1)[-1].strip()
    if not platforms:
        notes.append("项目 readme 未写明发布平台。")
    if not goal:
        notes.append("项目 readme 未写明剪辑目标。")
    return ProjectContext(project_root=project_root, target_platforms=platforms, project_goal=goal, notes=notes, creator_context=profile)


def load_bgm_review(video_path: Path, bgm_review_dir: Path | None) -> dict[str, Any] | None:
    if not bgm_review_dir:
        return None
    candidates = [
        bgm_review_dir / f"{video_path.stem}.json",
        bgm_review_dir / f"{video_path.name}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise OutputReviewError(f"invalid bgm review json: {candidate}") from exc
            if not isinstance(data, dict):
                raise OutputReviewError(f"invalid bgm review object: {candidate}")
            return data
    return None


def score_from_ratio(value: Any) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return max(0, min(100, int(round(float(value) * 100))))


def infer_narrative_tags(name: str) -> list[str]:
    tag_rules = [
        ("翻拍", "trend_remake"),
        ("上下", "split_screen"),
        ("分屏", "split_screen"),
        ("对照", "comparison"),
        ("单人", "single_subject"),
        ("加长", "extended_cut"),
        ("横屏", "horizontal_cut"),
        ("户外", "outdoor_context"),
        ("舞台", "stage_walk"),
        ("第一视角", "first_person"),
    ]
    tags: list[str] = []
    for keyword, tag in tag_rules:
        if keyword in name and tag not in tags:
            tags.append(tag)
    return tags


def platform_format_score(probe: dict[str, Any], context: ProjectContext, tags: list[str]) -> dict[str, Any]:
    width = int(probe.get("width") or 0)
    height = int(probe.get("height") or 0)
    if not width or not height:
        return {"score": None, "format": "unknown", "notes": ["缺少分辨率，无法判断平台画幅。"]}
    if not context.target_platforms:
        return {"score": None, "format": "unknown", "notes": ["项目未提供目标平台，无法判断平台画幅。"]}
    ratio = width / height
    is_vertical = height > width
    is_squareish = 0.85 <= ratio <= 1.15
    score = 70
    notes: list[str] = []
    short_video_platforms = {"抖音", "小红书", "快手", "视频号", "朋友圈"}
    if short_video_platforms & set(context.target_platforms):
        if is_vertical:
            score = 90 if 0.55 <= ratio <= 0.8 else 82
            matched = "、".join(platform for platform in context.target_platforms if platform in short_video_platforms)
            notes.append(f"目标平台包含{matched}，竖屏画幅更适合直接发布。")
        elif is_squareish:
            score = 74
            matched = "、".join(platform for platform in context.target_platforms if platform in short_video_platforms)
            notes.append(f"目标平台包含{matched}，近方形可用但需确认版式。")
        else:
            score = 55
            matched = "、".join(platform for platform in context.target_platforms if platform in short_video_platforms)
            notes.append(f"目标平台包含{matched}，横屏发布前需要确认是否做竖屏包装或上下分屏。")
    elif context.target_platforms:
        notes.append(f"目标平台为{'、'.join(context.target_platforms)}，需人工确认画幅适配。")
    if "horizontal_cut" in tags:
        notes.append("文件名标注横屏版本，平台分数仅代表直发适配，不否定横屏用途。")
    if "split_screen" in tags:
        notes.append("上下/分屏版本需要人工确认上下关系是否清楚。")
    return {
        "score": score,
        "format": "vertical" if is_vertical else "horizontal" if width > height else "square",
        "aspect_ratio": round(ratio, 3),
        "target_platforms": context.target_platforms,
        "notes": notes,
    }


def composition_score(video_metrics: dict[str, Any]) -> dict[str, Any]:
    score = 80
    notes: list[str] = []
    short_side = video_metrics.get("short_side")
    if isinstance(short_side, int) and short_side < 1080:
        score -= 20
        notes.append("短边低于 1080，发布前确认清晰度。")
    border_risk = video_metrics.get("letterbox_or_pillarbox_risk")
    if border_risk == "high":
        score -= 25
        notes.append("黑边/留边风险高，需复核构图。")
    elif border_risk == "medium":
        score -= 10
        notes.append("存在中等黑边/留边风险。")
    compression = video_metrics.get("compression_risk")
    if compression == "high":
        score -= 15
        notes.append("压缩风险高。")
    elif compression == "medium":
        score -= 6
        notes.append("压缩风险中等。")
    return {"score": max(0, min(100, score)), "notes": notes}


def hook_score(bgm_review: dict[str, Any] | None) -> dict[str, Any]:
    if not bgm_review:
        return {"score": None, "notes": ["未提供 BGM/时间轴审阅报告，无法判断开头钩子信号。"]}
    visual = bgm_review.get("visual", {})
    intro = visual.get("intro_effect_proxy", {})
    events = bgm_review.get("timeline_events", [])
    early_events = [
        event
        for event in events
        if isinstance(event.get("timestamp_sec"), (int, float))
        and float(event["timestamp_sec"]) <= 3.0
        and event.get("type") in {"scene_change", "visual_motion_peak", "step_motion_peak_proxy", "text_overlay_proxy_appears", "subject_proxy_appears"}
    ]
    score = 45
    notes: list[str] = []
    if intro.get("candidate_intentional_blur_or_overexposure"):
        score += 18
        notes.append("开头存在效果型虚焦/过曝或低细节提示，可作为钩子但需人工确认观感。")
    if early_events:
        score += min(25, len(early_events) * 5)
        notes.append(f"前 3 秒检测到 {len(early_events)} 个画面/步点/字幕事件。")
    else:
        notes.append("前 3 秒缺少明显画面事件，钩子可能偏弱。")
    return {"score": max(0, min(100, score)), "early_event_count": len(early_events), "notes": notes}


def rhythm_score(bgm_review: dict[str, Any] | None) -> dict[str, Any]:
    if not bgm_review:
        return {"score": None, "notes": ["未提供 BGM/卡点审阅报告。"]}
    step_alignment = bgm_review.get("step_alignment", {})
    scene_alignment = bgm_review.get("alignment", {})
    step_ratio = step_alignment.get("matched_ratio")
    scene_ratio = scene_alignment.get("matched_ratio")
    step_score = score_from_ratio(step_ratio)
    scene_score = score_from_ratio(scene_ratio)
    numeric_scores = [value for value in [step_score, scene_score] if value is not None]
    if not numeric_scores:
        return {"score": None, "notes": ["BGM 报告中缺少可用的步点/切点对齐比例。"]}
    if step_score is not None and scene_score is not None:
        score = int(round(step_score * 0.85 + scene_score * 0.15))
    elif step_score is not None:
        score = step_score
    else:
        score = scene_score
    notes = []
    if step_score is not None:
        notes.append(f"步点代理贴近音频峰：{step_alignment.get('matched_step_count')}/{step_alignment.get('step_peak_count')}，比例 {step_ratio}。")
    if scene_score is not None:
        notes.append(f"切点贴近音频峰比例：{scene_ratio}。")
    if step_score is not None and scene_score is not None:
        notes.append("有步点代理时，节奏分以步点为主，切点只做辅助，避免单个硬切误导版本排序。")
    return {
        "score": score,
        "step_score": step_score,
        "scene_score": scene_score,
        "estimated_bpm": bgm_review.get("rhythm", {}).get("estimated_bpm"),
        "notes": notes,
    }


def topic_strategy_score(version_name: str, context: ProjectContext, tags: list[str]) -> dict[str, Any]:
    score = 50
    notes: list[str] = []
    if "trend_remake" in tags:
        score += 15
        notes.append("文件名体现爆款翻拍方向。")
    if "single_subject" in tags or "split_screen" in tags or "comparison" in tags:
        score += 15
        notes.append("文件名体现明确版本策略。")
    goal_tokens = [token for token in re.findall(r"[\w\u4e00-\u9fff]{2,}", context.project_goal) if token not in {"视频", "内容", "项目"}]
    if goal_tokens and any(token in version_name for token in goal_tokens):
        score += 10
        notes.append("文件名与项目目标存在字面匹配。")
    if not notes:
        notes.append("仅从文件名无法判断选题匹配，需要结合关键帧/脚本审阅。")
    return {"score": max(0, min(100, score)), "tags": tags, "notes": notes, "confidence": "low"}


def person_state_review(tags: list[str]) -> dict[str, Any]:
    expected: list[str] = []
    if "single_subject" in tags:
        expected.append("确认单一主体是否清楚、状态是否自然、有无可持续观看的动作线。")
    if "split_screen" in tags or "comparison" in tags:
        expected.append("确认两侧主体动作关系、身份对照或翻拍关系是否一眼看懂。")
    if not expected:
        expected.append("确认主要人物是否出现、状态是否适合发布。")
    return {
        "status": "needs_visual_semantic_review",
        "method": "not_automated_in_v1",
        "expected_checks": expected,
    }


def creative_review_for_version(
    *,
    version_name: str,
    probe: dict[str, Any],
    video_metrics: dict[str, Any],
    bgm_review: dict[str, Any] | None,
    context: ProjectContext,
) -> dict[str, Any]:
    tags = infer_narrative_tags(version_name)
    dimensions = {
        "topic_strategy": topic_strategy_score(version_name, context, tags),
        "platform_format": platform_format_score(probe, context, tags),
        "composition": composition_score(video_metrics),
        "opening_hook": hook_score(bgm_review),
        "rhythm": rhythm_score(bgm_review),
        "person_state": person_state_review(tags),
    }
    weighted = CREATIVE_STRATEGY_WEIGHTS
    total_weight = 0.0
    weighted_score = 0.0
    for key, weight in weighted:
        value = dimensions[key].get("score")
        if isinstance(value, (int, float)):
            weighted_score += float(value) * weight
            total_weight += weight
    missing = [key for key, _ in weighted if dimensions[key].get("score") is None]
    coverage_ratio = total_weight / sum(weight for _, weight in weighted)
    score = round(weighted_score / total_weight, 1) if not missing and total_weight else None
    needs_semantic = dimensions["person_state"]["status"] != "automated"
    confidence = "low" if missing or needs_semantic else "medium"
    return {
        "score": score,
        "confidence": confidence,
        "algorithm_version": CREATIVE_STRATEGY_ALGORITHM_VERSION,
        "weights_version": CREATIVE_STRATEGY_WEIGHTS_VERSION,
        "weights": dict(CREATIVE_STRATEGY_WEIGHTS),
        "narrative_tags": tags,
        "dimensions": dimensions,
        "status": "complete" if not missing else "partial",
        "human_review_required": True,
        "available_weight_ratio": round(coverage_ratio, 3),
        "missing_dimensions": missing,
        "coverage_note": (
            "策略分基于全部规则维度。"
            if not missing
            else f"策略分未出具：仅有 {coverage_ratio:.0%} 权重可用，缺少：{'、'.join(humanize_dimension(key) for key in missing)}。"
        ),
        "semantic_gap": "人物状态、真实构图美感、选题表达仍需关键帧/LLM 或人工复核。",
    }


def compact_version_context(versions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, version in enumerate(versions, start=1):
        creative = version.get("creative_review", {})
        dimensions = creative.get("dimensions", {})
        rows.append(
            {
                "image_index": index,
                "version_name": version.get("version_name"),
                "duration_sec": version.get("probe", {}).get("duration_sec"),
                "resolution": f"{version.get('probe', {}).get('width')}x{version.get('probe', {}).get('height')}",
                "technical_status": version.get("technical_status"),
                "risk_flags": version.get("risk_flags", []),
                "rule_score": creative.get("score"),
                "rule_dimensions": {
                    key: value.get("score")
                    for key, value in dimensions.items()
                    if isinstance(value, dict) and "score" in value
                },
                "narrative_tags": creative.get("narrative_tags", []),
            }
        )
    return rows


def vlm_review_system_prompt() -> str:
    return """你是短视频成片语义审阅员。你会看到多个 contact sheet，每张图对应一个候选成片版本。
你的任务是基于画面语义审阅人物状态、真实构图美感、开头钩子、选题表达和平台发布观感。
只能根据可见画面和提供的上下文判断；不能臆造视频里看不到的细节。
不要替用户最终发布，只输出可复核的 JSON。"""


def review_creator_context_block(context: ProjectContext) -> str:
    if context.creator_context:
        instruction = "以下字段是项目明确提供的账号上下文，只能作为口吻、平台和题材边界约束，不能覆盖素材事实。"
        return instruction + "\n\n" + json.dumps(context.creator_context, ensure_ascii=False, indent=2)
    if context.project_root:
        return creator_context_block(context.project_root)
    return "项目未提供账号人设资料；不得自行猜测。"


def vlm_review_user_prompt(context: ProjectContext, versions: list[dict[str, Any]]) -> str:
    payload = {
        "schema_version": VLM_SCHEMA_VERSION,
        "project_goal": context.project_goal,
        "target_platforms": context.target_platforms,
        "image_mapping": compact_version_context(versions),
        "required_output": {
            "schema_version": VLM_SCHEMA_VERSION,
            "preferred_version": "版本名",
            "confidence": "low|medium|high",
            "versions": [
                {
                    "version_name": "必须和 image_mapping 中完全一致",
                    "overall_score": "0-100",
                    "person_state_score": "0-100",
                    "composition_aesthetic_score": "0-100",
                    "opening_hook_score": "0-100",
                    "topic_expression_score": "0-100",
                    "platform_publish_fit_score": "0-100",
                    "strengths": ["可见优点"],
                    "weaknesses": ["可见问题"],
                    "publish_risks": ["发布风险"],
                    "manual_review_focus": ["需要人工回看确认的点"],
                }
            ],
            "global_notes": ["全局备注"],
        },
    }
    return (
        "请审阅随 prompt 附带的 contact sheet 图片。图片顺序与 image_mapping 的 image_index 一一对应。\n"
        "评分口径：人物状态看主体是否清楚自然、有记忆点；构图美感看主体位置、空间关系、画面稳定和观感；"
        "开头钩子看前几格是否能立刻建立问题/反差/动作；选题表达看是否服务项目目标；"
        "平台发布观感看是否适合目标平台的快速浏览。\n"
        "请只输出裸 JSON，不要 Markdown 代码围栏，不要解释过程。\n"
        "账号上下文只用于口吻和平台适配，不得覆盖画面事实；未提供字段写‘未提供，需人工确认’。\n\n"
        + review_creator_context_block(context)
        + "\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def run_vlm_semantic_review(
    *,
    versions: list[dict[str, Any]],
    context: ProjectContext,
    output_dir: Path,
    model: str | None,
    reasoning_effort: str | None,
    provider: str | None,
) -> dict[str, Any]:
    image_paths = [
        Path(version.get("artifacts", {}).get("contact_sheet", ""))
        for version in versions
        if version.get("artifacts", {}).get("contact_sheet")
    ]
    if not image_paths:
        return {
            "schema_version": VLM_SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "contact_sheet_missing",
            "versions": [],
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "vlm_semantic_prompt.json"
    prompt_path.write_text(
        json.dumps(
            {
                "system_prompt": vlm_review_system_prompt(),
                "user_prompt": vlm_review_user_prompt(context, versions),
                "images": [str(path) for path in image_paths],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        text = generate_text(
            system_prompt=vlm_review_system_prompt(),
            user_prompt=vlm_review_user_prompt(context, versions),
            image_paths=image_paths,
            model=model,
            reasoning_effort=reasoning_effort,
            provider=provider,
        )
        raw_path = output_dir / "vlm_semantic_raw.md"
        raw_path.write_text(text + "\n", encoding="utf-8")
        data = parse_json_response(text, salvage=True, require=dict)
    except (LLMError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema_version": VLM_SCHEMA_VERSION,
            "status": "failed",
            "reason": public_llm_error(exc),
            "prompt_path": str(prompt_path),
            "versions": [],
        }
    data.setdefault("schema_version", VLM_SCHEMA_VERSION)
    data["status"] = "success"
    data["prompt_path"] = str(prompt_path)
    json_path = output_dir / "vlm_semantic_review.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_vlm_semantic_markdown(output_dir / "vlm_semantic_review.md", data)
    return data


def numeric_score(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return max(0.0, min(100.0, float(value)))
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return None


def apply_vlm_semantic_review(versions: list[dict[str, Any]], vlm_review: dict[str, Any] | None) -> None:
    if not vlm_review:
        return
    review_status = str(vlm_review.get("status") or "unavailable")
    if review_status != "success":
        reason = str(vlm_review.get("reason") or "VLM 语义审阅未返回可用结果。")
        for version in versions:
            creative = version.get("creative_review", {})
            if not isinstance(creative, dict):
                continue
            if isinstance(creative.get("score"), (int, float)):
                creative["rule_score"] = creative["score"]
            creative["score"] = None
            creative["confidence"] = "low"
            creative["status"] = "partial"
            missing_capabilities = creative.setdefault("missing_capabilities", [])
            if "vlm_semantic_review" not in missing_capabilities:
                missing_capabilities.append("vlm_semantic_review")
            creative["coverage_note"] = f"策略分未出具：VLM 语义审阅不可用（{reason}）。"
        return
    by_name = {
        item.get("version_name"): item
        for item in vlm_review.get("versions", [])
        if isinstance(item, dict) and item.get("version_name")
    }
    for version in versions:
        creative = version.get("creative_review", {})
        semantic = by_name.get(version.get("version_name"))
        if not semantic:
            if isinstance(creative, dict):
                creative["score"] = None
                creative["confidence"] = "low"
                creative["status"] = "partial"
                creative["coverage_note"] = "策略分未出具：VLM 语义审阅没有返回该版本。"
            continue
        semantic_score = numeric_score(semantic.get("overall_score"))
        creative["vlm_semantic_review"] = semantic
        creative["score_before_vlm"] = creative.get("score")
        if semantic_score is not None and isinstance(creative.get("score"), (int, float)):
            creative["score"] = round(float(creative["score"]) * 0.55 + semantic_score * 0.45, 1)
            creative["confidence"] = "medium" if vlm_review.get("confidence") in {"medium", "high"} else "low"
        else:
            creative["score"] = None
            creative["confidence"] = "low"
            creative["status"] = "partial"
            creative["coverage_note"] = "策略分未出具：规则维度或 VLM 总分不完整。"
        dimensions = creative.setdefault("dimensions", {})
        person_score = numeric_score(semantic.get("person_state_score"))
        if person_score is not None:
            dimensions["person_state"] = {
                "status": "automated_vlm_review",
                "method": "codex_vlm_contact_sheet",
                "score": round(person_score, 1),
                "notes": semantic.get("manual_review_focus", []),
            }
        composition_score_value = numeric_score(semantic.get("composition_aesthetic_score"))
        if composition_score_value is not None:
            dimensions["composition_aesthetic"] = {
                "score": round(composition_score_value, 1),
                "method": "codex_vlm_contact_sheet",
            }


def write_vlm_semantic_markdown(path: Path, review: dict[str, Any]) -> None:
    lines = [
        "# VLM 语义审阅",
        "",
        f"- status: `{review.get('status')}`",
        f"- preferred_version: `{review.get('preferred_version', '')}`",
        f"- confidence: `{review.get('confidence', '')}`",
        "",
        "| 版本 | 总分 | 人物状态 | 构图美感 | 开头钩子 | 选题表达 | 平台观感 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in review.get("versions", []):
        lines.append(
            "| {name} | {overall} | {person} | {composition} | {hook} | {topic} | {platform} |".format(
                name=item.get("version_name", ""),
                overall=item.get("overall_score", ""),
                person=item.get("person_state_score", ""),
                composition=item.get("composition_aesthetic_score", ""),
                hook=item.get("opening_hook_score", ""),
                topic=item.get("topic_expression_score", ""),
                platform=item.get("platform_publish_fit_score", ""),
            )
        )
    lines.extend(["", "## 备注", ""])
    for note in review.get("global_notes", []):
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def risk_flags_for(probe: dict[str, Any], video_metrics: dict[str, Any], audio_metrics: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    short_side = video_metrics.get("short_side")
    if isinstance(short_side, int) and short_side < 1080:
        flags.append("resolution_below_1080_short_side")
    if isinstance(short_side, int) and short_side < 360:
        flags.append("resolution_below_360_short_side")
    if float(probe.get("duration_sec") or 0) < 1:
        flags.append("duration_too_short")
    fps = probe.get("fps")
    if isinstance(fps, (int, float)) and fps < 20:
        flags.append("frame_rate_below_20")
    if video_metrics.get("black_frame_ratio", 0) > 0.8:
        flags.append("mostly_black_frames")
    elif video_metrics.get("black_frame_count", 0) > 0:
        flags.append("black_frame_detected")
    if video_metrics.get("flash_frame_count", 0) > 0:
        flags.append("flash_frame_detected")
    if video_metrics.get("overexposed_frame_ratio", 0) > 0.25:
        flags.append("overexposure_risk")
    if video_metrics.get("letterbox_or_pillarbox_risk") == "high":
        flags.append("heavy_letterbox_or_pillarbox")
    if video_metrics.get("compression_risk") == "high":
        flags.append("compression_risk_high")
    if not audio_metrics.get("has_audio"):
        flags.append("audio_missing")
    true_peak = audio_metrics.get("true_peak_dbtp")
    if isinstance(true_peak, (int, float)) and true_peak > -1:
        flags.append("audio_true_peak_above_minus_1_dbtp")
    max_volume = audio_metrics.get("max_volume_db")
    if isinstance(max_volume, (int, float)) and max_volume >= 0:
        flags.append("audio_max_volume_at_or_above_0_db")
    lufs = audio_metrics.get("integrated_lufs")
    if isinstance(lufs, (int, float)) and lufs > -12:
        flags.append("integrated_lufs_too_loud")
    if isinstance(lufs, (int, float)) and lufs < -20:
        flags.append("integrated_lufs_too_quiet")
    silence_ratio = audio_metrics.get("silence_ratio")
    if isinstance(silence_ratio, (int, float)) and silence_ratio > 0.2:
        flags.append("silence_ratio_high")
    return flags


def technical_status_for(probe: dict[str, Any], video_metrics: dict[str, Any], audio_metrics: dict[str, Any], flags: list[str]) -> str:
    if not probe.get("has_video"):
        return "fail"
    if "duration_too_short" in flags or "resolution_below_360_short_side" in flags or "mostly_black_frames" in flags:
        return "fail"
    if audio_metrics.get("max_volume_db") is not None and audio_metrics.get("max_volume_db") >= 0 and audio_metrics.get("true_peak_dbtp", -99) > 1:
        return "fail"
    warning_flags = set(flags) - {"black_frame_detected"}
    return "warning" if warning_flags else "pass"


def map_recommendation(
    *,
    task_status: str,
    technical_status: str,
    current_brief_fit: str,
    human_decision_required: bool,
) -> dict[str, Any]:
    if task_status != "success":
        return {"recommendation": "reject", "publish_as_final": False, "human_decision_required": True}
    if technical_status == "fail":
        return {"recommendation": "reject", "publish_as_final": False, "human_decision_required": True}
    if current_brief_fit == "low" and technical_status == "pass":
        return {"recommendation": "recut", "publish_as_final": False, "human_decision_required": True}
    if current_brief_fit == "unknown":
        return {"recommendation": "small_fix", "publish_as_final": False, "human_decision_required": True}
    if technical_status == "warning":
        return {"recommendation": "small_fix", "publish_as_final": False, "human_decision_required": True}
    if technical_status == "pass" and current_brief_fit == "high" and not human_decision_required:
        return {"recommendation": "publish", "publish_as_final": True, "human_decision_required": False}
    return {"recommendation": "small_fix", "publish_as_final": False, "human_decision_required": True}


def review_one(input_video: ReviewInput, output_root: Path, *, bgm_review_dir: Path | None, context: ProjectContext) -> dict[str, Any]:
    version_dir = output_root / input_video.version_name
    probe = run_ffprobe(input_video.path)
    frames = extract_uniform_frames(input_video.path, version_dir / "frames", float(probe.get("duration_sec") or 0))
    scene_frames = extract_scene_change_frames(input_video.path, version_dir / "scene_frames")
    contact_sheet = build_contact_sheet(frames, version_dir / "contact_sheet.jpg", label_prefix=input_video.version_name)
    scene_sheet = build_contact_sheet(scene_frames, version_dir / "scene_change_sheet.jpg", label_prefix=input_video.version_name)
    video_metrics = compute_image_metrics(frames, probe)
    audio_metrics = compute_audio_metrics(input_video.path, probe, version_dir)
    flags = risk_flags_for(probe, video_metrics, audio_metrics)
    technical_status = technical_status_for(probe, video_metrics, audio_metrics, flags)
    bgm_review = load_bgm_review(input_video.path, bgm_review_dir)
    creative_review = creative_review_for_version(
        version_name=input_video.version_name,
        probe=probe,
        video_metrics=video_metrics,
        bgm_review=bgm_review,
        context=context,
    )
    return {
        "version_name": input_video.version_name,
        "path": str(input_video.path),
        "task_status": "success",
        "technical_status": technical_status,
        "probe": probe,
        "video_metrics": video_metrics,
        "audio_metrics": audio_metrics,
        "creative_review": creative_review,
        "risk_flags": flags,
        "artifacts": {
            "contact_sheet": str(contact_sheet) if contact_sheet else "",
            "scene_change_sheet": str(scene_sheet) if scene_sheet else "",
            "audio_wav": str(version_dir / "audio_mono_22050.wav") if (version_dir / "audio_mono_22050.wav").exists() else "",
        },
    }


def version_rank(version: dict[str, Any], current_brief_fit: str) -> tuple[int, int, int, int]:
    status_score = {"pass": 0, "warning": 1, "fail": 2, "unknown": 3}.get(version.get("technical_status"), 3)
    brief_score = {"high": 0, "medium": 1, "unknown": 2, "low": 3}.get(current_brief_fit, 2)
    risk_count = len(version.get("risk_flags") or [])
    short_side = version.get("video_metrics", {}).get("short_side") or 0
    return status_score, brief_score, risk_count, -int(short_side)


def write_metrics_json(path: Path, metrics: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_result_yaml(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(result, handle, allow_unicode=True, sort_keys=False)


def write_markdown_report(path: Path, metrics: dict[str, Any], result: dict[str, Any]) -> None:
    versions = metrics["versions"]
    rows = "\n".join(
        "| {name} | `{path}` | {duration} 秒 | {width}x{height} | {fps} | {status} | {flags} |".format(
            name=version["version_name"],
            path=version["path"],
            duration=version["probe"].get("duration_sec"),
            width=version["probe"].get("width"),
            height=version["probe"].get("height"),
            fps=version["probe"].get("fps"),
            status=STATUS_LABELS.get(version["technical_status"], "待人工确认"),
            flags=", ".join(humanize_risk_flag(flag) for flag in version["risk_flags"]) or "无",
        )
        for version in versions
    )
    strategy_rows = "\n".join(
        "| {name} | {score} | {rule_score} | {vlm_score} | {confidence} | {rhythm} | {platform} | {hook} | {composition} | {topic} | {tags} |".format(
            name=version["version_name"],
            score=version.get("creative_review", {}).get("score"),
            rule_score=version.get("creative_review", {}).get("score_before_vlm", version.get("creative_review", {}).get("score")),
            vlm_score=version.get("creative_review", {}).get("vlm_semantic_review", {}).get("overall_score", ""),
            confidence=CONFIDENCE_LABELS.get(version.get("creative_review", {}).get("confidence"), "待确认"),
            rhythm=version.get("creative_review", {}).get("dimensions", {}).get("rhythm", {}).get("score"),
            platform=version.get("creative_review", {}).get("dimensions", {}).get("platform_format", {}).get("score"),
            hook=version.get("creative_review", {}).get("dimensions", {}).get("opening_hook", {}).get("score"),
            composition=version.get("creative_review", {}).get("dimensions", {}).get("composition", {}).get("score"),
            topic=version.get("creative_review", {}).get("dimensions", {}).get("topic_strategy", {}).get("score"),
            tags=", ".join(
                humanize_tag(tag) for tag in version.get("creative_review", {}).get("narrative_tags", [])
            ) or "无",
        )
        for version in versions
    )
    preferred_creative = metrics.get("creative_review", {}).get("preferred_by_strategy", {})
    vlm_review = metrics.get("creative_review", {}).get("vlm_semantic_review") or {}
    rhythm_sync = metrics.get("rhythm_sync") or {}
    rhythm_rows = "\n".join(
        "| {rank} | {name} | {final} | {structural} | {action_node} | {step} | {pose} | {cut} | {motion} | {text} | {phase} | {intro} | {fix_score} | {fix} |".format(
            rank=item.get("rank"),
            name=item.get("version_name"),
            final=item.get("final_score"),
            structural=item.get("structural_match"),
            action_node=item.get("action_node_sync"),
            step=item.get("step_sync"),
            pose=item.get("pose_keyframe_sync"),
            cut=item.get("cut_sync"),
            motion=item.get("motion_sync"),
            text=item.get("text_overlay_sync"),
            phase=item.get("phase_consistency"),
            intro=item.get("intro_effect"),
            fix_score=item.get("fixability_score"),
            fix=item.get("fixability"),
        )
        for item in rhythm_sync.get("ranked_versions", [])
    )
    if not rhythm_rows:
        rhythm_rows = "|  | 未启用 |  |  |  |  |  |  |  |  |  |  |  |  |"
    preferred_strategy = preferred_creative.get("version_name", "")
    strategy_review = preferred_creative.get("creative_review", {})
    missing_dimensions = strategy_review.get("missing_dimensions", [])
    coverage_note = strategy_review.get("coverage_note", "策略分需结合人工确认。")
    recommendation_label = RECOMMENDATION_LABELS.get(result.get("recommendation"), "待人工确认")
    technical_label = STATUS_LABELS.get(result.get("technical_status"), "待人工确认")
    task_label = STATUS_LABELS.get(result.get("task_status"), "待人工确认")
    brief_fit_label = humanize_brief_fit(result.get("current_brief_fit", ""))
    risk_labels = ", ".join(humanize_risk_flag(flag) for flag in result.get("risk_flags", [])) or "未发现已登记的技术风险"
    confidence_label = CONFIDENCE_LABELS.get(preferred_creative.get("confidence"), "待人工确认")
    vlm_status_label = VLM_STATUS_LABELS.get(vlm_review.get("status", "not_requested"), "待人工确认")
    artifact_lines = "\n".join(
        f"- {version['version_name']} 画面采样图：`{version['artifacts'].get('contact_sheet', '')}`\n"
        f"- {version['version_name']} 场景变化采样图：`{version['artifacts'].get('scene_change_sheet', '')}`"
        for version in versions
    )
    text = f"""---
spec_version: content_os_v0.1
doc_type: output_video_review
project_id: {metrics["task"]["project_id"]}
idea_id: {metrics["task"]["idea_id"]}
task_id: {metrics["task"]["task_id"]}
status: reviewed_by_automation
writer_agent: mac_openclaw
owner_agent: mac_openclaw
next_owner: {result["next_owner"]}
reviewed_at: {metrics["task"]["created_at"]}
---

# 成片质检：{metrics["task"]["project_id"]}

## 发布判断

- 发布建议：**{recommendation_label}**
- 技术检查：{technical_label}；任务状态：{task_label}
- 推荐版本：`{result["preferred_version"]}`
- 策略参考版本：`{preferred_strategy}`（分数 {preferred_creative.get("score", "待定")}）
- 内容匹配：{brief_fit_label}
- 需要人工确认：{("是" if result["human_decision_required"] else "否")}
- 重要提醒：{result["reason"]}
- 技术风险：{risk_labels}

## 质检对象

| 版本 | 文件 | 时长 | 分辨率 | 帧率 | 技术状态 | 风险 |
|---|---|---:|---|---:|---|---|
{rows}

自动检查依据：视频属性、采样画面和音频统计。

## 技术检查

- 任务状态：{task_label}
- 技术状态：{technical_label}
- 技术风险：{risk_labels}
- 推荐版本：`{result["preferred_version"]}`

自动检查依据：视频属性、响度/静音统计和采样画面。

## 画面结构检查

{artifact_lines}

自动检查依据：均匀采样和场景变化采样。限制：未做完整 OCR 时间轴。

## 音频检查

优先版本 `{result["preferred_version"]}` 的音频指标见 `metrics.json`。BGM BPM / 能量只作为结构提示，不直接判断情绪。

自动检查依据：音频响度和能量统计。

## 作品策略审阅

| 版本 | 策略分 | 规则分 | VLM分 | 置信度 | 节奏 | 平台画幅 | 开头钩子 | 构图技术 | 选题表达 | 识别标签 |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
{strategy_rows}

- 策略参考版本：`{preferred_strategy}`
- 策略分：`{preferred_creative.get("score", "")}`；置信度：{confidence_label}
- 策略覆盖：{coverage_note}
- VLM 语义审阅：{vlm_status_label}
- VLM 参考版本：`{vlm_review.get("preferred_version", "")}`
- 局限：语义审阅基于采样画面，最终发布由人确认。

自动检查依据：BGM/卡点资料（如有）、项目平台目标、视频属性和采样画面。{("缺少维度：" + "、".join(humanize_dimension(key) for key in missing_dimensions) if missing_dimensions else "")}

## 节奏同步复核

- 是否启用节奏同步：{("是" if result.get("rhythm_sync_enabled") else "否")}
- 节奏同步版本：{humanize_rhythm_profile(result.get("rhythm_profile", ""))}
- 节奏参考版本：`{result.get("rhythm_preferred_version", "") or "未启用"}`
- 节奏报告：`{result.get("rhythm_report_path", "") or "未生成"}`

| 排名 | 版本 | 最终分 | 结构匹配 | 动作节点 | 步点同步 | 姿态同步 | 切点同步 | 动作同步 | 字幕同步 | 阶段一致 | 开头效果 | 可修复分 | 可修复性 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
{rhythm_rows}

自动检查依据：音频能量、场景变化和画面事件的一对一时间对齐。限制：节奏事件是代理指标，最终发布仍需人工确认封面、标题和人物状态。

## 与 Brief / Script 匹配度

- Brief / Script 匹配度：{brief_fit_label}
- 匹配方式：已读取可用文字资料，未做完整 OCR、ASR 和视觉语义审片
- 匹配置信度：{CONFIDENCE_LABELS.get(result["brief_fit_confidence"], "待人工确认")}

限制：未做完整 OCR、ASR 和视觉语义审片，内容判断需人工确认。

## 机器指标附录

```text
{result["metrics_path"]}
```
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def artifact_relative(path: Path, base: Path | None) -> str:
    if base:
        try:
            return str(path.resolve().relative_to(base.resolve()))
        except ValueError:
            pass
    return str(path)


def safe_artifact_name(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value, flags=re.UNICODE).strip("._")
    return cleaned or "version"


def write_json_artifact(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def analyze_rhythm_sync_version(
    version: dict[str, Any],
    *,
    profile: str,
    rhythm_root: Path,
    artifact_base: Path | None,
) -> dict[str, Any]:
    version_name = str(version["version_name"])
    video_path = Path(version["path"])
    version_dir = rhythm_root / safe_artifact_name(version_name)
    version_dir.mkdir(parents=True, exist_ok=True)
    raw_wav = str(version.get("artifacts", {}).get("audio_wav") or "")
    wav_path = Path(raw_wav) if raw_wav else Path("__missing__")
    audio_events, audio_meta = detect_audio_events(wav_path, float(version.get("probe", {}).get("duration_sec") or 0.0))
    visual_events, visual_meta = detect_visual_events(
        video_path,
        version_dir,
        version.get("probe", {}),
        version.get("video_metrics", {}),
    )
    matches = align_audio_visual_events(audio_events, visual_events)
    edit_path = build_timing_edit_path(visual_events, audio_events, matches)
    scores, diagnostics, review_points, edit_suggestions = score_rhythm_sync(
        profile=profile,
        audio_events=audio_events,
        visual_events=visual_events,
        matches=matches,
        probe=version.get("probe", {}),
        risk_flags=version.get("risk_flags", []),
        audio_meta=audio_meta,
    )
    review_frame_paths = extract_rhythm_review_frames(video_path, review_points, version_dir / "review_frames")
    audio_events_path = version_dir / "audio_events.json"
    visual_events_path = version_dir / "visual_events.json"
    matches_path = version_dir / "matches.json"
    write_json_artifact(audio_events_path, audio_events)
    write_json_artifact(visual_events_path, visual_events)
    write_json_artifact(matches_path, matches)
    return {
        "version_name": version_name,
        "path": str(video_path),
        "profile": profile if profile in PROFILE_WEIGHTS else "general_bgm_edit",
        "scores": scores,
        "diagnostics": diagnostics,
        "review_points": review_points,
        "edit_suggestions": edit_suggestions,
        "edit_path": edit_path,
        "audio_meta": audio_meta,
        "visual_meta": visual_meta,
        "artifacts": {
            "audio_events": artifact_relative(audio_events_path, artifact_base),
            "visual_events": artifact_relative(visual_events_path, artifact_base),
            "matches": artifact_relative(matches_path, artifact_base),
            "review_frames": [artifact_relative(Path(path), artifact_base) for path in review_frame_paths],
        },
    }


def compare_rhythm_sync_versions(
    versions: list[dict[str, Any]],
    *,
    profile: str,
    rhythm_root: Path,
    artifact_base: Path | None,
) -> dict[str, Any]:
    rhythm_root.mkdir(parents=True, exist_ok=True)
    analyzed = [
        analyze_rhythm_sync_version(version, profile=profile, rhythm_root=rhythm_root, artifact_base=artifact_base)
        for version in versions
    ]
    ranked = sorted(
        analyzed,
        key=lambda item: (-float(item.get("scores", {}).get("final_score") or 0.0), item["version_name"]),
    )
    preferred = ranked[0] if ranked else {}
    return {
        "schema_version": RHYTHM_SYNC_SCHEMA_VERSION,
        "profile": profile if profile in PROFILE_WEIGHTS else "general_bgm_edit",
        "requested_profile": profile,
        "preferred_version": preferred.get("version_name", ""),
        "human_decision_required": True,
        "method": {
            "audio_events": "rms_energy_onset_grid_v1",
            "visual_events": "ffmpeg_scene_select_plus_frame_difference_v1",
            "step_motion": "lower_center_roi_frame_difference_proxy",
            "matching": "one_to_one_greedy_signed_delta",
            "scoring": "profile_weighted_event_alignment_with_penalties",
        },
        "versions": analyzed,
        "ranked_versions": [
            {
                "rank": index,
                "version_name": item["version_name"],
                "final_score": item["scores"].get("final_score"),
                "step_sync": item["scores"].get("step_sync"),
                "cut_sync": item["scores"].get("cut_sync"),
                "motion_sync": item["scores"].get("motion_sync"),
                "pose_keyframe_sync": item["scores"].get("pose_keyframe_sync"),
                "structural_match": item["scores"].get("structural_match"),
                "action_node_sync": item["scores"].get("action_node_sync"),
                "intro_effect": item["scores"].get("intro_effect"),
                "text_overlay_sync": item["scores"].get("text_overlay_sync"),
                "phase_consistency": item["scores"].get("phase_consistency"),
                "fixability_score": item["scores"].get("fixability_score"),
                "fixability": item["diagnostics"].get("fixability"),
            }
            for index, item in enumerate(ranked, start=1)
        ],
        "limitations": [
            "V1 使用 ROI/帧差代理，不等于真实人体姿态步点。",
            "上下分屏、多人、手持横移和推拉镜头可能造成误判。",
            "节奏同步结果不等于最终发布判断，封面、标题、人物状态仍需人工确认。",
        ],
    }


def write_rhythm_sync_report(path: Path, report: dict[str, Any]) -> None:
    rows = "\n".join(
        "| {rank} | {name} | {final} | {structural} | {action_node} | {step} | {pose} | {cut} | {motion} | {text} | {phase} | {intro} | {fix_score} | {fix} |".format(
            rank=item["rank"],
            name=item["version_name"],
            final=item["final_score"],
            structural=item.get("structural_match"),
            action_node=item.get("action_node_sync"),
            step=item["step_sync"],
            pose=item.get("pose_keyframe_sync"),
            cut=item["cut_sync"],
            motion=item["motion_sync"],
            text=item.get("text_overlay_sync"),
            phase=item.get("phase_consistency"),
            intro=item["intro_effect"],
            fix_score=item.get("fixability_score"),
            fix=item["fixability"],
        )
        for item in report.get("ranked_versions", [])
    )
    if not rows:
        rows = "|  |  |  |  |  |  |  |  |  |  |  |  |  |  |"
    points_lines: list[str] = []
    suggestion_lines: list[str] = []
    edit_path_lines: list[str] = []
    for version in report.get("versions", []):
        for point in version.get("review_points", [])[:6]:
            points_lines.append(
                "| {version} | {time} | {type} | {severity} | {reason} |".format(
                    version=version["version_name"],
                    time=point.get("time"),
                    type=point.get("type"),
                    severity=point.get("severity"),
                    reason=point.get("reason"),
                )
            )
        for suggestion in version.get("edit_suggestions", [])[:5]:
            suggestion_lines.append(
                "| {version} | {time} | {action} | {target} | {delta} | {confidence} | {reason} |".format(
                    version=version["version_name"],
                    time=suggestion.get("time", ""),
                    action=suggestion.get("action", ""),
                    target=suggestion.get("target_time", ""),
                    delta=suggestion.get("delta_sec", ""),
                    confidence=suggestion.get("confidence", ""),
                    reason=suggestion.get("reason", ""),
                )
            )
        for node in version.get("edit_path", [])[:8]:
            edit_path_lines.append(
                "| {version} | {order} | {visual_time} | {target_time} | {operation} | {visual_type} | {audio_type} | {score} |".format(
                    version=version["version_name"],
                    order=node.get("order", ""),
                    visual_time=node.get("visual_time", ""),
                    target_time=node.get("target_time", ""),
                    operation=node.get("suggested_operation", ""),
                    visual_type=node.get("visual_type", ""),
                    audio_type=node.get("audio_type", ""),
                    score=node.get("node_score", ""),
                )
            )
    if not points_lines:
        points_lines.append("|  |  |  |  |  |")
    if not suggestion_lines:
        suggestion_lines.append("|  |  |  |  |  |  |  |")
    if not edit_path_lines:
        edit_path_lines.append("|  |  |  |  |  |  |  |  |")
    artifact_lines = "\n".join(
        "- {name}: audio `{audio}`, visual `{visual}`, matches `{matches}`".format(
            name=version["version_name"],
            audio=version.get("artifacts", {}).get("audio_events", ""),
            visual=version.get("artifacts", {}).get("visual_events", ""),
            matches=version.get("artifacts", {}).get("matches", ""),
        )
        for version in report.get("versions", [])
    )
    text = f"""# 成片节奏同步复核

- schema_version: `{report.get("schema_version")}`
- profile: `{report.get("profile")}`
- requested_profile: `{report.get("requested_profile")}`
- preferred_version_by_rhythm: `{report.get("preferred_version")}`
- human_decision_required: `{str(report.get("human_decision_required")).lower()}`

## 版本排名

| 排名 | 版本 | final_score | structural | action_node | step_sync | pose_sync | cut_sync | motion_sync | text_sync | phase | intro | fixability_score | fixability |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{rows}

## 人工审看点

| 版本 | 时间 | 类型 | 级别 | 建议 |
| --- | ---: | --- | --- | --- |
{chr(10).join(points_lines)}

## 改片建议

| 版本 | 时间 | 操作 | 目标时间 | 调整量 | 置信度 | 原因 |
| --- | ---: | --- | ---: | ---: | --- | --- |
{chr(10).join(suggestion_lines)}

## 动态路径候选

| 版本 | 顺序 | 画面时间 | 目标音乐时间 | 操作 | 画面事件 | 音频事件 | 节点分 |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
{chr(10).join(edit_path_lines)}

## 产物

{artifact_lines}

## 发布判断边界

节奏同步评估只证明音频事件和画面事件的对齐程度。是否 Final、是否发布，还必须人工确认封面、标题、主体状态、平台画幅和账号表达。

## 限制

{chr(10).join(f"- {item}" for item in report.get("limitations", []))}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def review_output_video(
    *,
    task_id: str,
    project_id: str,
    idea_id: str,
    videos: list[ReviewInput],
    output_root: Path,
    report_output: Path,
    metrics_output: Path,
    result_output: Path,
    brief: Path | None,
    script: Path | None,
    publish_pack: Path | None,
    artifact_base: Path | None = None,
    project_root: Path | None = None,
    bgm_review_dir: Path | None = None,
    rhythm_sync: bool = False,
    rhythm_profile: str = "general_bgm_edit",
    rhythm_output_root: Path | None = None,
    run_vlm_review: bool = False,
    require_production_capabilities: bool = False,
    vlm_output_root: Path | None = None,
    vlm_model: str | None = None,
    vlm_reasoning_effort: str | None = None,
    vlm_provider: str | None = None,
) -> dict[str, Any]:
    if not videos:
        raise OutputReviewError("at least one output video is required")
    dependency_status = check_dependencies()
    if dependency_status["errors"]:
        content = evaluate_brief_fit(brief, script, publish_pack)
        result = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "task_status": "blocked",
            "technical_status": "unknown",
            "preferred_version": videos[0].version_name,
            "current_brief_fit": content["current_brief_fit"],
            "brief_fit_method": content["brief_fit_method"],
            "brief_fit_confidence": content["brief_fit_confidence"],
            "recommendation": "reject",
            "publish_as_final": False,
            "human_decision_required": True,
            "reason": "自动检查所需的本机依赖未就绪，请先补齐运行环境后重试。",
            "next_owner": "human_editor",
            "risk_flags": dependency_status["errors"],
            "metrics_path": artifact_relative(metrics_output, artifact_base),
            "report_path": artifact_relative(report_output, artifact_base),
            "contact_sheet_path": "",
            "scene_change_sheet_path": "",
        }
        write_result_yaml(result_output, result)
        return result
    for item in videos:
        if not item.path.exists() or item.path.stat().st_size == 0:
            raise OutputReviewError(f"output video missing or empty: {item.path}")
    output_root.mkdir(parents=True, exist_ok=True)
    context = load_project_context(project_root)
    versions = [review_one(video, output_root, bgm_review_dir=bgm_review_dir, context=context) for video in videos]
    rhythm_report: dict[str, Any] | None = None
    rhythm_metrics_output = (rhythm_output_root or output_root / "rhythm_sync") / "rhythm_sync_metrics.json"
    rhythm_result_output = (rhythm_output_root or output_root / "rhythm_sync") / "rhythm_sync_result.yaml"
    rhythm_report_output = (rhythm_output_root or output_root / "rhythm_sync") / "rhythm_sync_report.md"
    if rhythm_sync:
        rhythm_root = rhythm_output_root or output_root / "rhythm_sync"
        rhythm_report = compare_rhythm_sync_versions(
            versions,
            profile=rhythm_profile,
            rhythm_root=rhythm_root,
            artifact_base=artifact_base,
        )
        write_json_artifact(rhythm_metrics_output, rhythm_report)
        write_result_yaml(rhythm_result_output, rhythm_report)
        write_rhythm_sync_report(rhythm_report_output, rhythm_report)
    vlm_report: dict[str, Any] | None = None
    vlm_root = vlm_output_root or metrics_output.parent / "vlm_semantic_review"
    if run_vlm_review:
        vlm_report = run_vlm_semantic_review(
            versions=versions,
            context=context,
            output_dir=vlm_root,
            model=vlm_model,
            reasoning_effort=vlm_reasoning_effort,
            provider=vlm_provider,
        )
        apply_vlm_semantic_review(versions, vlm_report)
    content = evaluate_brief_fit(brief, script, publish_pack)
    preferred = sorted(versions, key=lambda version: version_rank(version, content["current_brief_fit"]))[0]
    creative_candidates = [
        version
        for version in versions
        if isinstance(version.get("creative_review", {}).get("score"), (int, float))
    ]
    creative_preferred = (
        sorted(creative_candidates, key=lambda version: (-float(version["creative_review"]["score"]), version["version_name"]))[0]
        if creative_candidates
        else preferred
    )
    partial_reasons: list[str] = []
    if require_production_capabilities:
        partial_reasons = [
            f"{version['version_name']}：{version.get('creative_review', {}).get('coverage_note', '策略审阅能力不完整。')}"
            for version in versions
            if version.get("creative_review", {}).get("status") != "complete"
        ]
        if run_vlm_review and vlm_report and vlm_report.get("status") != "success":
            partial_reasons.append(f"VLM 语义审阅：{vlm_report.get('reason') or vlm_report.get('status')}")
    task_status = "success" if not partial_reasons else "partial"
    rec = map_recommendation(
        task_status=task_status,
        technical_status=preferred["technical_status"],
        current_brief_fit=content["current_brief_fit"],
        human_decision_required=content["human_decision_required"],
    )
    risk_flags = sorted(set(flag for version in versions for flag in version.get("risk_flags", [])))
    reason = (
        "技术检查已完成；内容匹配、标题封面和最终版本仍需人工确认。"
        if task_status == "success"
        else "自动检查部分完成；未出具策略分，补齐以下能力后重新审阅：" + "；".join(partial_reasons)
    )
    rhythm_available = all(
        version.get("creative_review", {}).get("dimensions", {}).get("rhythm", {}).get("score") is not None
        for version in versions
    )
    capability_status = {
        "project_context": {
            "status": "available" if context.target_platforms else "partial",
            "reason": "" if context.target_platforms else "项目未提供可识别的目标平台。",
        },
        "bgm_review": {
            "status": "available" if rhythm_available else "partial",
            "reason": "" if rhythm_available else "缺少可用的 BGM/卡点审阅数据。",
        },
        "rhythm_sync": {"status": "success" if rhythm_sync else "not_requested", "reason": ""},
        "vlm_semantic_review": {
            "status": vlm_report.get("status") if vlm_report else "not_requested",
            "reason": vlm_report.get("reason", "") if vlm_report else "",
        },
    }
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "task_status": task_status,
        "technical_status": preferred["technical_status"],
        "preferred_version": preferred["version_name"],
        "current_brief_fit": content["current_brief_fit"],
        "brief_fit_method": content["brief_fit_method"],
        "brief_fit_confidence": content["brief_fit_confidence"],
        "recommendation": rec["recommendation"],
        "publish_as_final": rec["publish_as_final"],
        "human_decision_required": rec["human_decision_required"],
        "reason": reason,
        "next_owner": "human_editor",
        "risk_flags": risk_flags,
        "review_capability_status": capability_status,
        "partial_reasons": partial_reasons,
        "metrics_path": artifact_relative(metrics_output, artifact_base),
        "report_path": artifact_relative(report_output, artifact_base),
        "strategy_preferred_version": creative_preferred["version_name"],
        "strategy_preferred_score": creative_preferred.get("creative_review", {}).get("score"),
        "strategy_confidence": creative_preferred.get("creative_review", {}).get("confidence"),
        "rhythm_sync_enabled": rhythm_sync,
        "rhythm_profile": rhythm_report.get("profile") if rhythm_report else "",
        "rhythm_preferred_version": rhythm_report.get("preferred_version") if rhythm_report else "",
        "rhythm_metrics_path": artifact_relative(rhythm_metrics_output, artifact_base) if rhythm_sync else "",
        "rhythm_result_path": artifact_relative(rhythm_result_output, artifact_base) if rhythm_sync else "",
        "rhythm_report_path": artifact_relative(rhythm_report_output, artifact_base) if rhythm_sync else "",
        "vlm_review_enabled": run_vlm_review,
        "vlm_review_status": vlm_report.get("status") if vlm_report else "",
        "vlm_preferred_version": vlm_report.get("preferred_version") if vlm_report else "",
        "vlm_review_path": artifact_relative(vlm_root / "vlm_semantic_review.json", artifact_base) if run_vlm_review else "",
        "contact_sheet_path": artifact_relative(Path(preferred["artifacts"].get("contact_sheet") or ""), artifact_base)
        if preferred["artifacts"].get("contact_sheet")
        else "",
        "scene_change_sheet_path": artifact_relative(Path(preferred["artifacts"].get("scene_change_sheet") or ""), artifact_base)
        if preferred["artifacts"].get("scene_change_sheet")
        else "",
    }
    metrics = {
        "schema_version": SCHEMA_VERSION,
        "task": {
            "task_id": task_id,
            "project_id": project_id,
            "idea_id": idea_id,
            "created_at": now_iso(),
        },
        "inputs": {
            "output_video_path": str(videos[0].path),
            "compare_video_paths": [str(item.path) for item in videos[1:]],
            "project_brief_path": str(brief) if brief else "",
            "script_path": str(script) if script else "",
            "publish_pack_path": str(publish_pack) if publish_pack else "",
            "project_root": str(project_root) if project_root else "",
            "bgm_review_dir": str(bgm_review_dir) if bgm_review_dir else "",
            "rhythm_sync": rhythm_sync,
            "rhythm_profile": rhythm_profile,
            "vlm_review": run_vlm_review,
            "require_production_capabilities": require_production_capabilities,
            "vlm_output_root": str(vlm_root) if run_vlm_review else "",
        },
        "execution": {**dependency_status, "task_status": task_status, "errors": [], "warnings": dependency_status["warnings"] + partial_reasons},
        "review_method": {
            "technical_probe": "ffprobe",
            "frame_sampling": "ffmpeg_uniform_sampling",
            "scene_detection": "ffmpeg_scene_select",
            "image_statistics": "python_pillow",
            "audio_loudness": "ffmpeg_ebur128_volumedetect_silencedetect",
            "audio_structure": "lightweight_rms_energy",
            "ocr": "none",
            "asr": "none",
            "semantic_review": "metadata_and_context_only",
            "human_review": "not_performed",
            "rhythm_sync": "internal_event_alignment_v1" if rhythm_sync else "not_requested",
            "vlm_semantic_review": "codex_cli_images_contact_sheets" if run_vlm_review else "not_requested",
        },
        "versions": versions,
        "probe": preferred["probe"],
        "video_metrics": preferred["video_metrics"],
        "audio_metrics": preferred["audio_metrics"],
        "content_metrics": {
            "ocr_method": "none",
            "asr_method": "none",
            "vision_review_method": "sampled_frames_without_semantic_model",
            "brief_fit_method": content["brief_fit_method"],
            "current_brief_fit": content["current_brief_fit"],
            "content_confidence": content["content_confidence"],
            "notes": content["notes"],
        },
        "creative_review": {
            "context": {
                "project_root": str(context.project_root) if context.project_root else "",
                "target_platforms": context.target_platforms,
                "project_goal": context.project_goal,
                "notes": context.notes,
                "creator_context": context.creator_context,
            },
            "preferred_by_strategy": {
                "version_name": creative_preferred["version_name"],
                "score": creative_preferred.get("creative_review", {}).get("score"),
                "confidence": creative_preferred.get("creative_review", {}).get("confidence"),
                "algorithm_version": creative_preferred.get("creative_review", {}).get("algorithm_version"),
                "weights_version": creative_preferred.get("creative_review", {}).get("weights_version"),
                "weights": creative_preferred.get("creative_review", {}).get("weights"),
                "human_review_required": creative_preferred.get("creative_review", {}).get("human_review_required"),
            },
            "method": {
                "algorithm_version": CREATIVE_STRATEGY_ALGORITHM_VERSION,
                "weights_version": CREATIVE_STRATEGY_WEIGHTS_VERSION,
                "rhythm": "optional bgm-review JSON step/cut alignment",
                "platform_format": "project readme target platforms + ffprobe aspect ratio",
                "opening_hook": "bgm-review intro/timeline proxies",
                "composition": "Pillow sampled-frame technical composition proxies",
                "topic_strategy": "filename/project-goal lexical tags",
                "person_state": "not automated; requires visual semantic review",
                "vlm_semantic_review": "codex_vlm_contact_sheet" if run_vlm_review else "not_requested",
            },
            "vlm_semantic_review": vlm_report,
            "semantic_vlm_review": vlm_report,
            "capability_status": capability_status,
        },
        "rhythm_sync": rhythm_report,
        "risk_flags": risk_flags,
        "review_result": result,
        "artifacts": {
            "markdown_report": artifact_relative(report_output, artifact_base),
            "contact_sheet": result["contact_sheet_path"],
            "scene_change_sheet": result["scene_change_sheet_path"],
            "result_yaml": artifact_relative(result_output, artifact_base),
            "rhythm_sync_metrics": artifact_relative(rhythm_metrics_output, artifact_base) if rhythm_sync else "",
            "rhythm_sync_result": artifact_relative(rhythm_result_output, artifact_base) if rhythm_sync else "",
            "rhythm_sync_report": artifact_relative(rhythm_report_output, artifact_base) if rhythm_sync else "",
            "vlm_semantic_json": artifact_relative(vlm_root / "vlm_semantic_review.json", artifact_base) if run_vlm_review else "",
            "vlm_semantic_markdown": artifact_relative(vlm_root / "vlm_semantic_review.md", artifact_base) if run_vlm_review else "",
        },
    }
    write_metrics_json(metrics_output, metrics)
    write_result_yaml(result_output, result)
    write_markdown_report(report_output, metrics, result)
    return result


def parse_video_arg(value: str, default_name: str) -> ReviewInput:
    if "=" in value:
        name, raw = value.split("=", 1)
        version_name = name.strip() or default_name
        path = Path(raw.strip()).expanduser().resolve()
    else:
        version_name = default_name
        path = Path(value).expanduser().resolve()
    return ReviewInput(version_name=version_name, path=path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--video", required=True, help="Primary video path, or name=/path/video.mp4")
    parser.add_argument("--compare-video", action="append", default=[], help="Comparison video path, or name=/path/video.mp4")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--metrics-output", required=True, type=Path)
    parser.add_argument("--result-output", required=True, type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--publish-pack", type=Path)
    parser.add_argument("--artifact-base", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--bgm-review-dir", type=Path)
    parser.add_argument("--rhythm-sync", action="store_true", help="Generate rhythm-sync event alignment artifacts and ranking")
    parser.add_argument("--profile", default="general_bgm_edit", help="Rhythm-sync profile, e.g. split_screen_comparison")
    parser.add_argument("--rhythm-output-root", type=Path, help="Optional rhythm-sync artifact root; defaults to output-root/rhythm_sync")
    parser.add_argument("--run-vlm-review", action="store_true", help="Use Codex VLM on contact sheets for semantic output review")
    parser.add_argument("--require-production-capabilities", action="store_true", help="Mark the result partial when production review capabilities are unavailable")
    parser.add_argument("--vlm-output-root", type=Path, help="Optional VLM semantic review artifact root")
    parser.add_argument("--vlm-model", help="Optional model override for VLM semantic review")
    parser.add_argument("--vlm-reasoning-effort", help="Optional reasoning effort override for VLM semantic review")
    parser.add_argument("--vlm-provider", help="Optional provider override; image review currently expects codex_cli")
    args = parser.parse_args()

    videos = [parse_video_arg(args.video, "current")]
    for index, value in enumerate(args.compare_video, start=1):
        videos.append(parse_video_arg(value, f"compare_{index}"))
    try:
        result = review_output_video(
            task_id=args.task_id,
            project_id=args.project_id,
            idea_id=args.idea_id,
            videos=videos,
            output_root=args.output_root.expanduser().resolve(),
            report_output=args.report_output.expanduser().resolve(),
            metrics_output=args.metrics_output.expanduser().resolve(),
            result_output=args.result_output.expanduser().resolve(),
            brief=args.brief.expanduser().resolve() if args.brief else None,
            script=args.script.expanduser().resolve() if args.script else None,
            publish_pack=args.publish_pack.expanduser().resolve() if args.publish_pack else None,
            artifact_base=args.artifact_base.expanduser().resolve() if args.artifact_base else None,
            project_root=args.project_root.expanduser().resolve() if args.project_root else None,
            bgm_review_dir=args.bgm_review_dir.expanduser().resolve() if args.bgm_review_dir else None,
            rhythm_sync=args.rhythm_sync,
            rhythm_profile=args.profile,
            rhythm_output_root=args.rhythm_output_root.expanduser().resolve() if args.rhythm_output_root else None,
            run_vlm_review=args.run_vlm_review,
            require_production_capabilities=args.require_production_capabilities,
            vlm_output_root=args.vlm_output_root.expanduser().resolve() if args.vlm_output_root else None,
            vlm_model=args.vlm_model,
            vlm_reasoning_effort=args.vlm_reasoning_effort,
            vlm_provider=args.vlm_provider,
        )
    except (OutputReviewError, LLMError) as exc:
        raise SystemExit(f"错误：{public_llm_error(exc) if isinstance(exc, LLMError) else '成片质检失败，请检查输入后重试。'}") from exc
    print(f"task_status={result['task_status']}")
    print(f"technical_status={result['technical_status']}")
    print(f"recommendation={result['recommendation']}")
    if result.get("rhythm_sync_enabled"):
        print(f"rhythm_preferred_version={result.get('rhythm_preferred_version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
