#!/usr/bin/env python3
"""Validate naming and Raw_待处理 decisions recorded in the media manifest."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from media_common import load_manifest, now_iso, project_path


SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def format_dimensions(item: dict[str, object]) -> str:
    width = item.get("width")
    height = item.get("height")
    if width and height:
        return f"{width} x {height}"
    return "未知"


def collect_issues(manifest: dict[str, object]) -> list[tuple[dict[str, object], dict[str, str]]]:
    collected: list[tuple[dict[str, object], dict[str, str]]] = []
    for item in manifest["items"]:
        if "decision_issues" not in item:
            raise RuntimeError("manifest lacks decision_issues; rerun 01_scan_media_manifest.py before validation.")
        for issue in item["decision_issues"]:
            collected.append((item, issue))
    return sorted(
        collected,
        key=lambda pair: (
            SEVERITY_ORDER.get(pair[1].get("severity", "INFO"), 99),
            str(pair[0].get("relative_path", "")),
            pair[1].get("code", ""),
        ),
    )


def write_report(project: Path, issues: list[tuple[dict[str, object], dict[str, str]]]) -> Path:
    report = project / "_ai_analysis" / "media_decision_warnings.md"
    report.parent.mkdir(parents=True, exist_ok=True)

    counts = Counter(issue.get("severity", "INFO") for _, issue in issues)
    status = "通过" if not issues else "需处理"
    lines = [
        "# 素材判别校验报告",
        "",
        f"- 生成时间：{now_iso()}",
        f"- 校验结果：{status}",
        f"- ERROR：{counts.get('ERROR', 0)}",
        f"- WARNING：{counts.get('WARNING', 0)}",
        f"- INFO：{counts.get('INFO', 0)}",
        "",
        "## 规则",
        "",
        "- “低清/低分辨率”只能在短边低于 720p 时使用；短边达到 720p 或以上不能叫低清。",
        "- 不使用“低质/画质差”这类不可复核判断，必须改成具体原因。",
        "- 普通照片 / 普通视频进入 `Raw_待处理` 时，文件名必须写明不可直用原因，例如：录屏、模糊待选、待截取、待修复、待防抖、待降噪、待转码、待重构。",
        "- DJI / Insta360 / Live Photo 原始关联组不强制改名，原因写入所在文件夹名或 readme。",
        "- 有清楚画面、只是需要裁掉开头或结尾的素材，应放在 L3 根部并使用 `_待截取`。",
        "",
    ]

    if issues:
        lines.extend(
            [
                "## 需处理项",
                "",
                "| 级别 | 文件 | 分辨率 | 问题 | 建议 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item, issue in issues:
            lines.append(
                "| {severity} | {path} | {dimensions} | {message} | {action} |".format(
                    severity=issue.get("severity", "INFO"),
                    path=item.get("relative_path"),
                    dimensions=format_dimensions(item),
                    message=issue.get("message", ""),
                    action=issue.get("action", ""),
                )
            )
        lines.append("")
    else:
        lines.extend(["## 需处理项", "", "无。", ""])

    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="校验 Raw_待处理、低清、低质等命名判断是否可复核")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--report-only", action="store_true", help="只生成报告，即使存在 ERROR 也不返回失败")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    issues = collect_issues(manifest)
    report = write_report(project, issues)
    errors = [issue for _, issue in issues if issue.get("severity") == "ERROR"]

    if issues:
        print(f"素材判别校验发现 {len(issues)} 项问题，报告：{report}")
        for item, issue in issues:
            print(f"[{issue.get('severity')}] {item.get('relative_path')} - {issue.get('code')}: {issue.get('message')}")
    else:
        print(f"素材判别校验通过：{report}")

    if errors and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
