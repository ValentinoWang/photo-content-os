#!/usr/bin/env python3
"""Apply a confirmed 待增加 merge plan."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from media_common import ANALYSIS_DIR, ensure_project_additions_dir, now_iso, path_inside as inside, project_path
from project_bootstrap_common import run_project_analysis as run_analysis


PLAN_NAME = "additions_merge_plan.json"


def load_plan(additions_dir: Path, plan_path: str | None) -> dict[str, object]:
    path = Path(plan_path).expanduser().resolve() if plan_path else additions_dir / ANALYSIS_DIR / PLAN_NAME
    if not path.exists():
        raise FileNotFoundError(f"merge plan not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        plan = json.load(f)
    if not isinstance(plan, dict) or "items" not in plan:
        raise ValueError(f"invalid merge plan: {path}")
    return plan


def selected_items(plan: dict[str, object], apply_all_pending: bool) -> list[dict[str, object]]:
    allowed = {"approved"}
    if apply_all_pending:
        allowed.add("pending")
    return [item for item in plan["items"] if item.get("status") in allowed]


def append_merge_log(target_project: Path, moved: list[dict[str, object]]) -> None:
    if not moved:
        return
    log_path = target_project / "素材整理记录.md"
    lines = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 素材整理记录", ""])
    lines.extend(
        [
            f"## 待增加合并记录 {now_iso()}",
            "",
            "| 来源 | 合并后位置 | 说明 |",
            "| --- | --- | --- |",
        ]
    )
    for item in moved:
        lines.append(
            "| {source} | {target} | {reason} |".format(
                source=item["source_relative_path"],
                target=item["target_relative_path"],
                reason=item.get("classification_reason", ""),
            )
        )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_plan(
    additions_dir: Path,
    target_project: Path,
    plan: dict[str, object],
    apply_all_pending: bool,
    allow_review_items: bool,
    dry_run: bool,
) -> list[dict[str, object]]:
    items = selected_items(plan, apply_all_pending)
    if not items:
        raise RuntimeError("no approved items to apply. Set status=approved or pass --apply-all-pending after confirming the plan.")

    moved: list[dict[str, object]] = []
    for item in items:
        if item.get("needs_review") and not allow_review_items:
            raise RuntimeError(f"item needs review before apply: {item.get('source_relative_path')}")
        source = additions_dir / str(item["source_relative_path"])
        target = target_project / str(item["target_relative_path"])
        if not inside(source, additions_dir):
            raise RuntimeError(f"source escapes additions_dir: {source}")
        if not inside(target, target_project):
            raise RuntimeError(f"target escapes target_project: {target}")
        if not source.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        if target.exists():
            raise FileExistsError(f"target already exists: {target}")

        print(f"{source} -> {target}")
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        moved.append(item)
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="执行已经确认的待增加合并计划")
    parser.add_argument("additions_dir", help="待增加素材目录")
    parser.add_argument("target_project_dir", help="目标正式项目目录")
    parser.add_argument("--plan", help="自定义 additions_merge_plan.json 路径")
    parser.add_argument("--apply-all-pending", action="store_true", help="确认整表无误后，把 pending 条目也作为已批准执行")
    parser.add_argument("--allow-review-items", action="store_true", help="允许执行 needs_review=true 的条目")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要移动的文件，不真正移动")
    parser.add_argument("--skip-analysis", action="store_true", help="合并后不自动重跑 run_analyze_project.sh")
    args = parser.parse_args()

    additions_dir = project_path(args.additions_dir)
    target_project = project_path(args.target_project_dir)
    ensure_project_additions_dir(additions_dir, target_project)
    plan = load_plan(additions_dir, args.plan)
    if Path(plan.get("additions_dir", additions_dir)).resolve() != additions_dir:
        raise RuntimeError("plan additions_dir does not match the provided additions_dir")
    if Path(plan.get("target_project_dir", target_project)).resolve() != target_project:
        raise RuntimeError("plan target_project_dir does not match the provided target_project_dir")

    moved = apply_plan(
        additions_dir,
        target_project,
        plan,
        args.apply_all_pending,
        args.allow_review_items,
        args.dry_run,
    )
    if args.dry_run:
        print("dry run complete; no files moved.")
        return
    append_merge_log(target_project, moved)
    print(f"已合并素材：{len(moved)} 个")
    if moved and not args.skip_analysis:
        run_analysis(target_project)


if __name__ == "__main__":
    main()
