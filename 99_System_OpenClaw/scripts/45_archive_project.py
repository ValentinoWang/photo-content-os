#!/usr/bin/env python3
"""Validate and record a project cold-archive candidate without moving media."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from media_common import ANALYSIS_DIR, file_sha256 as sha256_file, now_iso, project_path, safe_slug


EXCLUDED_TOP_LEVELS = {"App_WorkCache", "待增加", "80_To_iCloudPhotos_精选入库", "05_Archive_Cold_Storage", "02_Asset_Library"}
REQUIRED_DIRS = {"90_Draft_Project", "91_Output", "92_Aliyun_SyncReady"}


def readiness(project: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    final_dir = project / "91_Output" / "Final"
    sync_checklist = project / "92_Aliyun_SyncReady" / "项目同步检查清单.md"
    additions = project / "待增加"
    checks.append({"id": "project_dirs", "passed": all((project / d).is_dir() for d in REQUIRED_DIRS), "evidence": [d for d in sorted(REQUIRED_DIRS) if (project / d).is_dir()]})
    checks.append({"id": "final_output", "passed": final_dir.is_dir() and any(p.is_file() for p in final_dir.iterdir()), "evidence": [p.relative_to(project).as_posix() for p in final_dir.iterdir() if p.is_file()] if final_dir.is_dir() else []})
    checks.append({"id": "sync_checklist", "passed": sync_checklist.is_file() and "[ ]" not in sync_checklist.read_text(encoding="utf-8"), "evidence": [sync_checklist.relative_to(project).as_posix()] if sync_checklist.is_file() else []})
    checks.append({"id": "pending_additions", "passed": additions.is_dir() and not any(p for p in additions.iterdir() if not p.name.startswith(".")), "evidence": [p.relative_to(project).as_posix() for p in additions.iterdir() if not p.name.startswith(".")] if additions.is_dir() else []})
    return {"ready": all(bool(c["passed"]) for c in checks), "checked_at": now_iso(), "checks": checks}


def build_manifest(project: Path, gate: dict[str, Any]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(project.rglob("*")):
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(project).parts):
            continue
        rel = path.relative_to(project)
        if rel.parts[0] in EXCLUDED_TOP_LEVELS or rel.parts[0] == ANALYSIS_DIR:
            continue
        files.append({"path": rel.as_posix(), "size": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": 1, "tool": "45_archive_project", "generated_at": now_iso(), "project": project.name, "readiness": gate, "files": files}


def index_card(project: Path, gate: dict[str, Any], manifest: dict[str, Any]) -> str:
    date = project.name[:8] if project.name[:8].isdigit() else "YYYYMMDD"
    status = "cold_archived" if gate["ready"] else "cooling"
    return f"""# {project.name} 归档索引卡\n\n项目名称：{project.name}\n归档状态：{status}\n生成时间：{manifest['generated_at']}\n归档准入：{'通过' if gate['ready'] else '未通过'}\n\n## 证据\n\n- 归档清单：`05_Archive_Cold_Storage/{date}_{safe_slug(project.name)}/archive_manifest.json`\n- 项目内文件数：{len(manifest['files'])}\n- 说明：本卡由 `45_archive_project.py` 生成；云盘、移动硬盘回读和恢复演练仍需独立证据。\n\n## 人工补充\n\n- 检索关键词：\n- iCloud 照片入口：\n- 阿里云盘镜像路径及回读时间：\n- 移动硬盘卷标及路径：\n- 恢复演练证据：\n"""


def verify_target(manifest_path: Path, target: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checked = 0
    for item in manifest.get("files", []):
        relative = Path(str(item["path"]))
        candidate = (target / relative).resolve()
        try:
            candidate.relative_to(target.resolve())
        except ValueError:
            failures.append(f"path escapes target: {relative}")
            continue
        checked += 1
        if not candidate.is_file():
            failures.append(f"missing: {relative}")
            continue
        if candidate.stat().st_size != int(item["size"]):
            failures.append(f"size mismatch: {relative}")
            continue
        if sha256_file(candidate) != item["sha256"]:
            failures.append(f"sha256 mismatch: {relative}")
    return {"status": "passed" if not failures else "blocked", "checked": checked, "failures": failures, "target": str(target)}


def restore_from_manifest(manifest_path: Path, source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"restore destination already exists: {destination}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    destination.mkdir(parents=True)
    copied = 0
    failures: list[str] = []
    for item in manifest.get("files", []):
        relative = Path(str(item["path"]))
        source_file = (source / relative).resolve()
        try:
            source_file.relative_to(source.resolve())
        except ValueError:
            failures.append(f"path escapes source: {relative}")
            continue
        if not source_file.is_file():
            failures.append(f"missing: {relative}")
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target)
        copied += 1
    verification = verify_target(manifest_path, destination)
    if failures:
        verification["status"] = "blocked"
        verification["failures"] = failures + list(verification["failures"])
    verification["copied"] = copied
    verification["source"] = str(source)
    verification["destination"] = str(destination)
    return verification


def prune_plan(project: Path, manifest_path: Path, index_card_path: Path, receipts: list[Path]) -> dict[str, Any]:
    blockers: list[str] = []
    gate = readiness(project)
    if not gate["ready"]:
        blockers.append("archive readiness is not passed")
    if not manifest_path.is_file():
        blockers.append("archive manifest is missing")
    if not index_card_path.is_file():
        blockers.append("archive index card is missing")
    for receipt in receipts:
        if not receipt.is_file():
            blockers.append(f"replica receipt is missing: {receipt}")
        elif json.loads(receipt.read_text(encoding="utf-8")).get("status") != "passed":
            blockers.append(f"replica receipt is not passed: {receipt}")
    return {"status": "ready" if not blockers else "blocked", "blockers": blockers, "delete_candidates": [] if blockers else ["project source files require explicit human confirmation"], "safe": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="检查项目归档准入并生成归档清单/索引卡")
    parser.add_argument("project_dir")
    parser.add_argument("--write", action="store_true", help="写入项目内归档清单和索引卡；不移动或删除素材")
    parser.add_argument("--verify-target", type=Path, help="按已有 archive_manifest.json 校验一个目标副本")
    parser.add_argument("--write-receipt", type=Path, help="将目标副本校验结果写入指定回执文件")
    parser.add_argument("--manifest", type=Path, help="归档清单路径；供回读、恢复和瘦身计划使用")
    parser.add_argument("--restore-from", type=Path, help="按归档清单从目标副本恢复到新目录")
    parser.add_argument("--restore-to", type=Path, help="恢复目标目录，必须不存在")
    parser.add_argument("--prune-plan", action="store_true", help="仅生成瘦身阻断计划，不删除文件")
    parser.add_argument("--index-card", type=Path, help="归档索引卡路径")
    parser.add_argument("--receipt", action="append", type=Path, default=[], help="副本回读回执，可重复指定")
    args = parser.parse_args()
    project = project_path(args.project_dir)
    manifest_path = args.manifest or project / "05_Archive_Cold_Storage" / "YYYY_Completed_Projects" / project.name / "archive_manifest.json"
    if args.verify_target:
        result = verify_target(manifest_path, args.verify_target)
        if args.write_receipt:
            args.write_receipt.parent.mkdir(parents=True, exist_ok=True)
            args.write_receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["receipt"] = str(args.write_receipt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["status"] == "passed" else 2)
    if args.restore_from:
        if not args.restore_to:
            parser.error("--restore-from requires --restore-to")
        result = restore_from_manifest(manifest_path, args.restore_from, args.restore_to)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["status"] == "passed" else 2)
    if args.prune_plan:
        index_path = args.index_card or project / "02_Asset_Library" / "Project_Archive_Index" / f"{project.name}.archive.md"
        result = prune_plan(project, manifest_path, index_path, args.receipt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["status"] == "ready" else 2)
    gate = readiness(project)
    manifest = build_manifest(project, gate)
    result = {"project": str(project), "readiness": gate, "manifest_file_count": len(manifest["files"]), "written": False}
    if args.write:
        archive_dir = project / "05_Archive_Cold_Storage" / "YYYY_Completed_Projects" / project.name
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "archive_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index_dir = project / "02_Asset_Library" / "Project_Archive_Index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / f"{project.name}.archive.md").write_text(index_card(project, gate, manifest), encoding="utf-8")
        result["written"] = True
        result["archive_manifest"] = str(archive_dir / "archive_manifest.json")
        result["index_card"] = str(index_dir / f"{project.name}.archive.md")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if gate["ready"] else 2)


if __name__ == "__main__":
    main()
