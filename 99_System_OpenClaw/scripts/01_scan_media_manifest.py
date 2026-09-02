#!/usr/bin/env python3
"""Scan a project folder and write _ai_analysis/media_manifest.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from media_common import (
    IMAGE_EXTS,
    MEDIA_EXTS,
    METADATA_EXTS,
    VIDEO_EXTS,
    discover_live_groups,
    file_sha256,
    image_info_for_image,
    is_hidden_or_analysis,
    lifecycle_for,
    live_status_for,
    manifest_path,
    media_id,
    now_iso,
    project_path,
    relative_posix,
    save_manifest,
    source_type,
    video_info,
)


RAW_REASON_TOKENS = {
    "原始": "original_reference",
    "录屏": "screen_record_reference",
    "模糊待选": "blur_review",
    "待截取": "trim_needed",
    "待修复": "repair_needed",
    "待防抖": "stabilization_needed",
    "待降噪": "denoise_needed",
    "待转码": "transcode_needed",
    "待重构": "reframe_needed",
    "半组": "incomplete_group",
    "待确认": "needs_confirmation",
}

LOW_RESOLUTION_TOKENS = ("低清", "低分辨率")
VAGUE_QUALITY_TOKENS = ("低质", "画质差")


def issue(severity: str, code: str, message: str, action: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "action": action}


def measured_resolution_flag(width: object, height: object) -> str | None:
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    short_side = min(width, height)
    if short_side < 720:
        return "low_resolution_below_720p"
    if short_side >= 1080:
        return "full_hd_or_better"
    return "hd_720p_or_better"


def assess_decision(item: dict[str, object]) -> None:
    text = f"{item['filename']} {item['relative_path']}"
    resolution_flag = measured_resolution_flag(item.get("width"), item.get("height"))
    quality_flags: list[str] = []
    decision_issues: list[dict[str, str]] = []
    decision_notes: list[str] = []

    if resolution_flag:
        quality_flags.append(resolution_flag)
    if "模糊" in text:
        quality_flags.append("filename_says_blur_review")
    if "待截取" in text:
        quality_flags.append("filename_says_trim_needed")

    raw_tokens = [label for token, label in RAW_REASON_TOKENS.items() if token in text]

    if any(token in text for token in LOW_RESOLUTION_TOKENS):
        if resolution_flag is None:
            decision_issues.append(
                issue(
                    "ERROR",
                    "filename_low_resolution_without_probe_evidence",
                    "文件名使用了“低清/低分辨率”，但脚本没有读到可验证的分辨率。",
                    "先用 ffprobe / sips 读取分辨率；无法证明低清时改用“待截取、待防抖、模糊待选”等具体原因。",
                )
            )
        elif resolution_flag != "low_resolution_below_720p":
            decision_issues.append(
                issue(
                    "ERROR",
                    "filename_low_resolution_conflicts_with_metadata",
                    "文件名使用了“低清/低分辨率”，但素材短边达到 720p 或以上。",
                    "删除“低清”判断；如果只是开头/结尾不可用，改成“待截取”。如果画面抖，改成“待防抖”。",
                )
            )

    if any(token in text for token in VAGUE_QUALITY_TOKENS):
        decision_issues.append(
            issue(
                "ERROR",
                "filename_uses_vague_quality_label",
                "文件名使用了“低质/画质差”这类不可复核判断。",
                "改成可复核状态：低分辨率待选（仅短边 < 720p）、模糊待选、待截取、待防抖、待降噪、待修复或待转码。",
            )
        )

    raw_naming_exception = (
        item.get("source_type") in {"DJI", "Insta360", "Live Photo"}
        or bool(item.get("live_photo_status"))
        or any(part in str(item.get("relative_path", "")) for part in ("DJI360_原始全景", "Insta360_原始全景", "LivePhoto半组待补齐"))
    )

    if item["lifecycle"] == "raw_or_pending" and not raw_tokens and not raw_naming_exception:
        decision_issues.append(
            issue(
                "ERROR",
                "raw_pending_without_reason_token",
                "素材放在 Raw_待处理，但文件名没有写明不可直用原因。",
                "在文件名中加入具体原因，例如：原始、录屏、模糊待选、待截取、待修复、待防抖、待降噪、待转码或待重构。",
            )
        )
    elif item["lifecycle"] == "raw_or_pending" and not raw_tokens and raw_naming_exception:
        decision_notes.append("DJI / Insta360 / Live Photo 原始关联组可保持原名；不可直用原因应写在文件夹名或 readme。")

    if item["lifecycle"] == "primary" and "待截取" in text:
        decision_notes.append("素材保留在 L3 根部，但需要剪辑师截取可用片段。")

    item["quality_flags"] = quality_flags
    item["raw_decision_tokens"] = raw_tokens
    item["decision_issues"] = decision_issues
    item["decision_notes"] = decision_notes


def scan_project(project_dir: str) -> dict[str, object]:
    project = project_path(project_dir)
    candidates = [
        path
        for path in project.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTS and not is_hidden_or_analysis(path, project)
    ]
    live_groups = discover_live_groups(candidates, project)
    items: list[dict[str, object]] = []

    for path in sorted(candidates, key=lambda p: relative_posix(p, project)):
        ext = path.suffix.lower()
        rel = relative_posix(path, project)
        lifecycle = lifecycle_for(path, project)
        live_status, live_role, _live_group_id = live_status_for(path, project, live_groups)
        try:
            stat = path.stat()
        except OSError:
            stat = None

        if ext in VIDEO_EXTS:
            media_type = "video"
        elif ext in IMAGE_EXTS:
            media_type = "image"
        elif ext in METADATA_EXTS:
            media_type = "metadata"
        else:
            raise AssertionError(f"unexpected media extension: {path}")

        item: dict[str, object] = {
            "media_id": media_id(rel),
            "filename": path.name,
            "stem": path.stem,
            "relative_path": rel,
            "absolute_path": str(path),
            "extension": ext,
            "size_mb": round(stat.st_size / 1024 / 1024, 3) if stat else None,
            "media_type": media_type,
            "lifecycle": lifecycle,
            "analysis_eligible": lifecycle == "primary" and media_type in {"video", "image"},
            "source_type": source_type(path.name, rel, live_status),
            "live_photo_status": live_status,
            "live_photo_role": live_role,
            "duration_sec": None,
            "width": None,
            "height": None,
            "has_audio": None,
            "location_raw": None,
            "gps_latitude": None,
            "gps_longitude": None,
            "gps_altitude": None,
            "gps_horizontal_accuracy": None,
            "sha256": None,
            "image_readable": None,
            "image_health": "not_applicable",
            "image_health_reason": None,
            "exif_location": None,
        }

        try:
            item["sha256"] = file_sha256(path)
        except OSError:
            item["sha256"] = None

        if media_type == "video":
            item.update(video_info(path))
        elif media_type == "image":
            if item["sha256"] is None:
                item["image_readable"] = False
                item["image_health"] = "unreadable"
                item["image_health_reason"] = "read_error"
                item["exif_location"] = {
                    "state": "unknown",
                    "latitude": None,
                    "longitude": None,
                    "altitude": None,
                    "horizontal_accuracy": None,
                }
            else:
                image_info = image_info_for_image(path)
                item.update(image_info)
            if isinstance(item.get("exif_location"), dict):
                location = item["exif_location"]
                item["gps_latitude"] = location["latitude"]
                item["gps_longitude"] = location["longitude"]
                item["gps_altitude"] = location["altitude"]
                item["gps_horizontal_accuracy"] = location["horizontal_accuracy"]

        assess_decision(item)
        items.append(item)

    manifest = {
        "project_dir": str(project),
        "generated_at": now_iso(),
        "manifest_version": 2,
        "notes": "analysis_eligible=false means the file is tracked but skipped by default to avoid duplicate analysis.",
        "items": items,
    }
    save_manifest(project, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描项目素材并生成 media_manifest.json")
    parser.add_argument("project_dir", help="项目文件夹路径")
    args = parser.parse_args()

    manifest = scan_project(args.project_dir)
    project = Path(manifest["project_dir"])
    total = len(manifest["items"])
    eligible = sum(1 for item in manifest["items"] if item.get("analysis_eligible"))
    print(f"扫描完成：{manifest_path(project)}")
    print(f"共发现媒体/元数据：{total} 个；默认进入 AI 分析：{eligible} 个")


if __name__ == "__main__":
    main()
