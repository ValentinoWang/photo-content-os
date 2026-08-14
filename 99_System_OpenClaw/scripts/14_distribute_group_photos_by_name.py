#!/usr/bin/env python3
"""Copy group photos into per-person delivery folders from a CSV mapping."""

from __future__ import annotations

import argparse
import csv
import filecmp
import re
import shutil
from pathlib import Path

from media_common import media_id, now_iso, project_path, relative_posix, safe_slug


DISTRIBUTION_DIR = "93_GroupPhoto_Distribution_合照发放"
DEFAULT_MAPPING_NAME = "合照发放清单.csv"
UNKNOWN_NAME_TOKENS = {"", "?", "？", "待确认", "未知", "unknown", "Unknown", "UNKNOWN"}
MAPPING_TEMPLATE = "photo_path,names,note\n"
README_TEMPLATE = """# 合照发放

- 在 `合照发放清单.csv` 中填写 `photo_path,names,note`。
- `photo_path` 使用项目内相对路径；`names` 用 `、` 分隔多人。
- 执行 `python3 99_System_OpenClaw/scripts/14_distribute_group_photos_by_name.py "项目目录"` 后，会把照片复制到 `按姓名/姓名/`。
- 姓名为空或写 `待确认` 的照片会复制到 `待确认姓名/`。
"""


def inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def parse_names(value: str) -> list[str]:
    raw_names = [name.strip() for name in re.split(r"[\n\r、，,;；/|]+", value or "")]
    names = []
    seen = set()
    for name in raw_names:
        if name in UNKNOWN_NAME_TOKENS:
            continue
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def resolve_photo(project: Path, distribution_root: Path, value: str) -> Path:
    text = (value or "").strip()
    if not text:
        raise RuntimeError("合照发放清单存在空 photo_path")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    if not inside(path, project):
        raise RuntimeError(f"photo_path must stay inside project: {path}")
    if inside(path, distribution_root):
        raise RuntimeError(f"photo_path cannot point back into distribution output: {path}")
    if not path.exists():
        raise FileNotFoundError(f"photo_path not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"photo_path is not a file: {path}")
    return path


def unique_target(target_dir: Path, source: Path, project: Path) -> Path:
    target = target_dir / source.name
    if not target.exists():
        return target
    if filecmp.cmp(source, target, shallow=False):
        return target
    suffix = source.suffix
    rel_id = media_id(relative_posix(source, project))
    target = target_dir / f"{source.stem}_{rel_id}{suffix}"
    index = 2
    while target.exists() and not filecmp.cmp(source, target, shallow=False):
        target = target_dir / f"{source.stem}_{rel_id}_{index}{suffix}"
        index += 1
    return target


def read_rows(mapping_path: Path) -> list[dict[str, str]]:
    if not mapping_path.exists():
        raise FileNotFoundError(f"mapping CSV not found: {mapping_path}")
    with mapping_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"photo_path", "names"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"mapping CSV missing columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def ensure_distribution_scaffold(distribution_root: Path) -> None:
    distribution_root.mkdir(parents=True, exist_ok=True)
    (distribution_root / "按姓名").mkdir(parents=True, exist_ok=True)
    (distribution_root / "待确认姓名").mkdir(parents=True, exist_ok=True)
    mapping_path = distribution_root / DEFAULT_MAPPING_NAME
    readme_path = distribution_root / "README.md"
    if not mapping_path.exists():
        mapping_path.write_text(MAPPING_TEMPLATE, encoding="utf-8")
    if not readme_path.exists():
        readme_path.write_text(README_TEMPLATE, encoding="utf-8")


def append_log(distribution_root: Path, entries: list[dict[str, str]], dry_run: bool) -> None:
    if dry_run or not entries:
        return
    log_path = distribution_root / "合照发放记录.md"
    lines = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 合照发放记录", ""])
    lines.extend(
        [
            f"## 发放执行 {now_iso()}",
            "",
            "| 原图 | 姓名 | 发放副本 | 备注 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            "| {source} | {name} | {target} | {note} |".format(
                source=entry["source"],
                name=entry["name"],
                target=entry["target"],
                note=entry["note"],
            )
        )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def distribute(project_dir: str, mapping: str | None, output_dir: str | None, dry_run: bool) -> list[dict[str, str]]:
    project = project_path(project_dir)
    distribution_root = project / DISTRIBUTION_DIR
    ensure_distribution_scaffold(distribution_root)
    mapping_path = Path(mapping).expanduser().resolve() if mapping else distribution_root / DEFAULT_MAPPING_NAME
    named_root = Path(output_dir).expanduser().resolve() if output_dir else distribution_root / "按姓名"
    if not inside(named_root, project):
        raise RuntimeError(f"output directory must stay inside project: {named_root}")
    unknown_root = distribution_root / "待确认姓名"
    rows = read_rows(mapping_path)
    entries: list[dict[str, str]] = []

    for index, row in enumerate(rows, start=2):
        source = resolve_photo(project, distribution_root, row.get("photo_path", ""))
        names = parse_names(row.get("names", ""))
        if not names:
            names = ["待确认姓名"]
        note = (row.get("note") or "").strip()
        for name in names:
            target_dir = unknown_root if name == "待确认姓名" else named_root / safe_slug(name)
            target = unique_target(target_dir, source, project)
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(source, target)
            entries.append(
                {
                    "source": relative_posix(source, project),
                    "name": name,
                    "target": relative_posix(target, project),
                    "note": note or f"mapping row {index}",
                }
            )

    append_log(distribution_root, entries, dry_run)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="按姓名复制合照发放副本")
    parser.add_argument("project_dir", help="项目目录")
    parser.add_argument("--mapping", help=f"发放 CSV，默认 {DISTRIBUTION_DIR}/{DEFAULT_MAPPING_NAME}")
    parser.add_argument("--output-dir", help=f"姓名目录，默认 {DISTRIBUTION_DIR}/按姓名")
    parser.add_argument("--dry-run", action="store_true", help="只检查并打印计划，不复制文件")
    args = parser.parse_args()

    entries = distribute(args.project_dir, args.mapping, args.output_dir, args.dry_run)
    action = "计划" if args.dry_run else "完成"
    print(f"合照发放{action}：{len(entries)} 份副本")
    for entry in entries:
        print(f"{entry['name']}: {entry['source']} -> {entry['target']}")


if __name__ == "__main__":
    main()
