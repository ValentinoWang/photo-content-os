#!/usr/bin/env python3
"""Plan and apply repeat-photo group merging from a 待增加 folder."""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from media_common import (
    ANALYSIS_DIR,
    IMAGE_EXTS,
    ensure_project_additions_dir,
    is_hidden_or_analysis,
    now_iso,
    path_inside as inside,
    project_path,
    relative_posix,
)
from project_bootstrap_common import run_project_analysis as run_analysis


SUPPORTED_IMAGE_EXTS = IMAGE_EXTS - {".heic", ".heif"}
PLAN_NAME = "repeat_photo_selection_plan.json"


def resolve_additions(project: Path, value: str | None) -> Path:
    additions = Path(value).expanduser().resolve() if value else project / "待增加"
    if not additions.exists():
        raise FileNotFoundError(f"additions dir not found: {additions}")
    if not additions.is_dir():
        raise NotADirectoryError(f"additions path is not a directory: {additions}")
    if additions.name != "待增加":
        raise RuntimeError(f"for safety, additions dir must be named 待增加: {additions}")
    return ensure_project_additions_dir(additions, project)


def default_output_dir(project: Path) -> Path:
    return project / ANALYSIS_DIR / "repeat_photo_additions" / "current"


def image_files(additions: Path) -> list[Path]:
    return sorted(
        path
        for path in additions.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_IMAGE_EXTS
        and not is_hidden_or_analysis(path, additions)
    )


def media_number(path: Path) -> int | None:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    return int(digits) if digits else None


def generate_contact_sheets(files: list[Path], additions: Path, output_dir: Path) -> list[Path]:
    contact_dir = output_dir / "contact_sheets"
    if contact_dir.exists():
        shutil.rmtree(contact_dir)
    contact_dir.mkdir(parents=True, exist_ok=True)
    if not files:
        return []

    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow is required to generate repeat-photo contact sheets") from exc

    thumb_w, thumb_h = 220, 165
    label_h = 30
    cols, rows = 5, 4
    per_sheet = cols * rows
    sheets: list[Path] = []
    for sheet_index in range(math.ceil(len(files) / per_sheet)):
        batch = files[sheet_index * per_sheet : (sheet_index + 1) * per_sheet]
        canvas = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
        draw = ImageDraw.Draw(canvas)
        for index, path in enumerate(batch):
            x0 = (index % cols) * thumb_w
            y0 = (index // cols) * (thumb_h + label_h)
            try:
                image = Image.open(path)
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((thumb_w, thumb_h))
                canvas.paste(image, (x0 + (thumb_w - image.width) // 2, y0 + (thumb_h - image.height) // 2))
                draw.text((x0 + 4, y0 + thumb_h + 3), path.stem, fill=(0, 0, 0))
            except Exception as exc:
                draw.text((x0 + 4, y0 + 10), f"{path.name}\n{exc}", fill=(180, 0, 0))
        output = contact_dir / f"sheet_{sheet_index + 1:02d}_{batch[0].stem}_{batch[-1].stem}.jpg"
        canvas.save(output, quality=90)
        sheets.append(output)
    return sheets


def create_plan(project: Path, additions: Path, output_dir: Path) -> dict[str, object]:
    files = image_files(additions)
    sheets = generate_contact_sheets(files, additions, output_dir)
    items = []
    for index, path in enumerate(files, start=1):
        number = media_number(path)
        items.append(
            {
                "status": "blocked",
                "source_relative_path": relative_posix(path, additions),
                "source_filename": path.name,
                "source_number": number,
                "action": None,
                "target_section": None,
                "group_id": None,
                "scene": None,
                "role": None,
                "state": "未修",
                "target_relative_path": None,
                "reason": "待根据联系表分配：merge / raw；不做高光筛选，不生成删除候选。",
            }
        )
    return {
        "plan_version": 1,
        "generated_at": now_iso(),
        "project_dir": str(project),
        "additions_dir": str(additions),
        "contact_sheets": [relative_posix(sheet, project) for sheet in sheets],
        "retention_policy": "项目素材库不做 AI 高光筛选；L3 项目归档层使用 补充01/补充02 和 未修/待修复 等状态；代表/情绪/封面候选只用于 80 或发布层。",
        "instructions": "把每个 item 的 status 改成 pending，并填写 action/target_section/group_id/scene/role/reason。action 可选 merge、raw；L3 归档层 role 建议填写 补充01、补充02 等。",
        "items": items,
    }


def write_plan(plan: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / PLAN_NAME
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_plan(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"repeat photo selection plan not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError(f"invalid repeat photo selection plan: {path}")
    return data


def role_filename(item: dict[str, object], source: Path) -> str:
    scene = str(item.get("scene") or "").strip()
    group_id = str(item.get("group_id") or "").strip()
    role = str(item.get("role") or "").strip()
    state = str(item.get("state") or "未修").strip()
    if not scene or not group_id or not role:
        raise RuntimeError(f"missing scene/group_id/role for {item.get('source_relative_path')}")
    return f"{scene}_{group_id}_{role}_{state}{source.suffix.upper()}"


def target_for_item(project: Path, additions: Path, item: dict[str, object]) -> Path:
    source = additions / str(item["source_relative_path"])
    action = item.get("action")
    explicit_target = item.get("target_relative_path")
    if action in {"merge", "selected"}:
        if explicit_target:
            return project / str(explicit_target)
        section = str(item.get("target_section") or "").strip()
        if not section:
            raise RuntimeError(f"missing target_section for merge item: {item.get('source_relative_path')}")
        return project / section / role_filename(item, source)
    if action == "raw":
        if explicit_target:
            return project / str(explicit_target)
        return project / "00_RawVault_不可直用" / "Raw_待处理" / role_filename(item, source)
    raise RuntimeError(f"unsupported action for {item.get('source_relative_path')}: {action}")


def selected_items(plan: dict[str, object]) -> list[dict[str, object]]:
    return [item for item in plan["items"] if item.get("status") == "pending"]


def validate_operations(project: Path, additions: Path, plan: dict[str, object]) -> list[dict[str, object]]:
    blocked = [item for item in plan["items"] if item.get("status") == "blocked"]
    if blocked:
        raise RuntimeError(f"{len(blocked)} repeat-photo items are still blocked; fill roles or remove them from the plan first")
    items = selected_items(plan)
    if not items:
        return []
    operations: list[dict[str, object]] = []
    targets: set[Path] = set()
    for item in items:
        source = additions / str(item["source_relative_path"])
        if not source.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        if not inside(source, additions):
            raise RuntimeError(f"source escapes additions_dir: {source}")
        target = target_for_item(project, additions, item)
        if not inside(target, project):
            raise RuntimeError(f"target escapes project_dir: {target}")
        if target.exists():
            raise FileExistsError(f"target already exists: {target}")
        resolved = target.resolve()
        if resolved in targets:
            raise RuntimeError(f"duplicate target path: {target}")
        targets.add(resolved)
        operations.append({"item": item, "source": source, "target": target})
    return operations


def apply_operations(operations: list[dict[str, object]]) -> None:
    for operation in operations:
        target = operation["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(operation["source"]), str(target))


def append_log(project: Path, additions: Path, operations: list[dict[str, object]]) -> None:
    if not operations:
        return
    log = project / "重复组合照筛选记录.md"
    lines = []
    if log.exists():
        lines.append(log.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.append("# 重复组合照筛选记录")
        lines.append("")
    counts: dict[str, int] = {}
    for operation in operations:
        action = str(operation["item"].get("action"))
        counts[action] = counts.get(action, 0) + 1
    lines.extend(
        [
            f"## 待增加重复照片整理 {now_iso()}",
            "",
            f"- 来源目录：{additions}",
            f"- L3 主题目录合并：{counts.get('merge', 0) + counts.get('selected', 0)} 张",
            f"- Raw 待处理：{counts.get('raw', 0)} 张",
            "",
            "| 来源 | 去向 | 动作 | 角色 | 依据 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for operation in operations:
        item = operation["item"]
        target = operation["target"]
        if inside(target, project):
            target_label = relative_posix(target, project)
        else:
            target_label = str(target)
        lines.append(
            "| {source} | {target} | {action} | {role} | {reason} |".format(
                source=item["source_relative_path"],
                target=target_label,
                action=item.get("action"),
                role=item.get("role") or "",
                reason=item.get("reason") or "",
            )
        )
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clear_additions(additions: Path) -> None:
    for child in additions.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="为重复照片/合照待增加目录生成合并计划，并按计划合并")
    parser.add_argument("project_dir", help="正式项目目录")
    parser.add_argument("--additions-dir", help="待增加目录，默认是 项目/待增加")
    parser.add_argument("--plan", action="store_true", help="只生成联系表和筛选计划，不移动文件")
    parser.add_argument("--apply", action="store_true", help="应用已填写好的 repeat_photo_selection_plan.json")
    parser.add_argument("--plan-path", help="自定义计划文件路径；应用时默认读取 _ai_analysis/repeat_photo_additions/current/repeat_photo_selection_plan.json")
    parser.add_argument("--skip-analysis", action="store_true", help="应用后不重跑 run_analyze_project.sh")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    additions = resolve_additions(project, args.additions_dir)
    output_dir = default_output_dir(project)
    plan_path = Path(args.plan_path).expanduser().resolve() if args.plan_path else output_dir / PLAN_NAME

    if args.apply:
        plan = load_plan(plan_path)
        if Path(str(plan.get("project_dir"))).resolve() != project:
            raise RuntimeError("plan project_dir does not match")
        if Path(str(plan.get("additions_dir"))).resolve() != additions:
            raise RuntimeError("plan additions_dir does not match")
        operations = validate_operations(project, additions, plan)
        apply_operations(operations)
        append_log(project, additions, operations)
        clear_additions(additions)
        print(f"已应用重复照片筛选计划：{len(operations)} 个文件")
        print(f"待增加目录已清空：{additions}")
        if not args.skip_analysis:
            run_analysis(project)
        return

    plan = create_plan(project, additions, output_dir)
    written = write_plan(plan, output_dir)
    print(f"重复照片筛选计划已生成：{written}")
    print(f"联系表目录：{output_dir / 'contact_sheets'}")
    print(f"共发现待处理图片：{len(plan['items'])} 张")
    if not args.plan:
        print("这是需要角色判断的重复照片流程；请先填写计划，再加 --apply 执行。")


if __name__ == "__main__":
    main()
