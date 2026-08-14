#!/usr/bin/env python3
"""Migrate Content OS project facts to v0.2 without deleting historical evidence.

Only `00_项目总览.md` is changed.  Old task/result files remain untouched: the
v0.2 Runner will reject their v0.1 format rather than silently replay them.
Use --apply only after reviewing the dry-run report.
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


V2_STATUSES = {"captured", "planned", "edit_ready", "editing", "final_ready", "published"}
STATUS_LABELS = {
    "captured": "已收集（captured）",
    "planned": "已规划（planned）",
    "edit_ready": "可开始剪辑（edit_ready）",
    "editing": "剪辑中（editing）",
    "final_ready": "成片待发（final_ready）",
    "published": "已发布（published）",
}
BACKEND_LABELS = {
    "handoff_pack": "标准剪辑（handoff_pack）",
    "otio_kdenlive": "可编辑时间线（otio_kdenlive）",
}
OWNER_LABELS = {
    "human": "人工负责人",
    "cloud_openclaw": "云端协作",
    "mac_openclaw": "Mac 协作",
}
LEGACY_STATUS_MAP = {
    "brief_ready": "planned",
    "local_project_linked": "planned",
    "materials_analyzed": "planned",
    "materials_matched": "planned",
    "storyboard_ready": "planned",
    "script_publish_pack_draft_ready": "planned",
    "roughcut_plan_ready": "planned",
    "native_import_pack_ready": "planned",
    "draft_open_checked": "planned",
    "editing": "editing",
    "output_reviewed": "editing",
    "final_ready": "final_ready",
    "published": "published",
    "reviewed": "published",
}


class MigrationError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectMigration:
    path: Path
    project_id: str
    old_status: str
    new_status: str
    changed: bool


def split_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise MigrationError(f"项目总览缺少 YAML 头部：{path}")
    closing = text.find("\n---", 4)
    if closing < 0:
        raise MigrationError(f"项目总览 YAML 头部没有结束：{path}")
    data = yaml.safe_load(text[4:closing])
    if not isinstance(data, dict):
        raise MigrationError(f"项目总览 YAML 头部必须是对象：{path}")
    return data, text[closing + 4 :].lstrip("\n")


def render_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    return "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n" + body.lstrip("\n")


def next_status(old_status: str) -> str:
    if old_status in V2_STATUSES:
        return old_status
    if old_status in LEGACY_STATUS_MAP:
        return LEGACY_STATUS_MAP[old_status]
    raise MigrationError(f"没有为旧项目阶段提供迁移映射：{old_status!r}")


def migrated_frontmatter(frontmatter: dict[str, Any], old_status: str, today: str) -> dict[str, Any]:
    project_id = str(frontmatter.get("project_id") or "").strip()
    if not project_id:
        raise MigrationError("项目总览缺少 project_id")
    result = dict(frontmatter)
    result["spec_version"] = "content_os_v0.2"
    result["doc_type"] = "project_overview"
    result["status"] = next_status(old_status)
    result["project_revision"] = int(result.get("project_revision") or 1)
    if result["project_revision"] < 1:
        raise MigrationError(f"项目版本必须为正整数：{project_id}")
    result["editor_backend"] = str(result.get("editor_backend") or "handoff_pack")
    if result["editor_backend"] not in {"handoff_pack", "otio_kdenlive"}:
        raise MigrationError(f"不支持的剪辑交接方式：{project_id}")
    result["blocked"] = bool(result.get("blocked", False))
    result["blocked_reason"] = str(result.get("blocked_reason") or "")
    result["reviewed_at"] = result.get("reviewed_at") or None
    result["output_review_path"] = str(result.get("output_review_path") or "")
    result["post_url"] = str(result.get("post_url") or "")
    result["updated_at"] = today
    result["migration_source_status"] = str(result.get("migration_source_status") or old_status)
    return result


def migration_note(old_status: str, new_status: str, today: str) -> str:
    return (
        "\n## v0.2 迁移记录\n\n"
        f"- {today}：项目阶段从历史记录 `{old_status}` 迁移为当前阶段 `{new_status}`。\n"
        "- 旧剪映相关文件和旧任务仅作为历史证据保留；它们不会被 v0.2 Runner 执行。\n"
        "- 当前版本默认使用“标准剪辑交接包”。若要改为“可编辑时间线”，请先通过 Media Bot 提交并确认修改。\n"
    )


def migrate_project(path: Path, *, apply: bool, today: str) -> ProjectMigration:
    frontmatter, body = split_frontmatter(path)
    old_status = str(frontmatter.get("status") or "").strip()
    new_frontmatter = migrated_frontmatter(frontmatter, old_status, today)
    project_id = str(new_frontmatter["project_id"])
    changed = frontmatter != new_frontmatter
    note_marker = "## v0.2 迁移记录"
    if note_marker not in body:
        body += migration_note(old_status, str(new_frontmatter["status"]), today)
        changed = True
    if apply and changed:
        path.write_text(render_frontmatter(new_frontmatter, body), encoding="utf-8")
    return ProjectMigration(path, project_id, old_status, str(new_frontmatter["status"]), changed)


def parse_frontmatter_for_projection(path: Path) -> dict[str, Any]:
    frontmatter, _ = split_frontmatter(path)
    return frontmatter


def generate_registry(project_paths: list[Path], registry_path: Path, today: str, *, apply: bool) -> str:
    records: list[dict[str, Any]] = []
    for path in project_paths:
        data = parse_frontmatter_for_projection(path)
        if data.get("spec_version") != "content_os_v0.2":
            continue
        records.append(data)
    records.sort(key=lambda item: str(item["project_id"]))
    lines = [
        "---",
        "doc_type: project_registry_projection",
        "spec_version: content_os_v0.2",
        f"generated_at: {today}",
        "generated_from: 08_内容项目/*/00_项目总览.md",
        "write_policy: generated_only",
        "---",
        "",
        "# 项目登记（自动生成）",
        "",
        "本页由项目总览生成，用于查看，不能直接改项目阶段或版本。需要修改请在 Media Bot 中提交。",
        "",
        "| 项目 | 阶段 | 版本 | 剪辑交接方式 | 负责人 | 下一步 | 阻塞原因 |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {project_id} | {status} | {revision} | {backend} | {owner} | {next_owner} | {blocked_reason} |".format(
                project_id=record["project_id"],
                status=STATUS_LABELS.get(str(record.get("status") or ""), str(record.get("status") or "")),
                revision=record.get("project_revision", ""),
                backend=BACKEND_LABELS.get(str(record.get("editor_backend") or ""), str(record.get("editor_backend") or "")),
                owner=OWNER_LABELS.get(str(record.get("owner_agent") or ""), str(record.get("owner_agent") or "")),
                next_owner=str(record.get("next_action") or OWNER_LABELS.get(str(record.get("next_owner") or ""), str(record.get("next_owner") or ""))),
                blocked_reason=str(record.get("blocked_reason") or "").replace("|", "\\|"),
            )
        )
    text = "\n".join(lines) + "\n"
    if apply:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="实际写入项目总览与自动登记页")
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args()
    vault_root = args.vault_root.expanduser().resolve()
    project_paths = sorted((vault_root / "08_内容项目").glob("*/00_项目总览.md"))
    if not project_paths:
        raise SystemExit("未找到项目总览")
    try:
        reports = [migrate_project(path, apply=args.apply, today=args.today) for path in project_paths]
        if args.apply:
            generate_registry(project_paths, vault_root / "90_索引与注册表" / "project_registry.md", args.today, apply=True)
    except MigrationError as exc:
        raise SystemExit(f"blocked: {exc}") from exc
    action = "已写入" if args.apply else "演练"
    for report in reports:
        marker = "会更新" if report.changed else "无需更新"
        print(f"{action} {report.project_id}: {report.old_status} -> {report.new_status}（{marker}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
