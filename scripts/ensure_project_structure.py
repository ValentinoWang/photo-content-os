#!/usr/bin/env python3
"""Ensure a project has the standard workflow directories from the local media flow outline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from media_common import ANALYSIS_DIR, MEDIA_EXTS, now_iso, path_inside as inside, project_path, relative_posix


PROJECT_DIRS = [
    "work-cache",
    "icloud-selected",
    "icloud-selected/project-selected",
    "icloud-selected/cover-candidates",
    "icloud-selected/memorial",
    "icloud-selected/phone-reusable",
    "icloud-selected/live-photo-groups",
    "icloud-selected/final-output",
    "icloud-selected/pending-review",
    "draft-project",
    "draft-project/edit-handoff",
    "draft-project/hyperframes",
    "draft-project/hyperframes/src",
    "draft-project/hyperframes/render-logs",
    "output",
    "output/v1",
    "output/v2",
    "output/final",
    "output/hyperframes",
    "sync-ready",
    "sync-ready/outsourcing-pack",
    "additions",
]

WORKCACHE_DIRS = [
    "wink-exports",
    "color-exports",
    "collage-assets",
    "collage-exports",
    "publishing-images",
    "dji-exports",
    "insta360-exports",
    "hyperframes-render-cache",
    "transcode",
]

PLACEHOLDER_FILES = {
    "icloud-selected/README.md": "# iCloud Photos 精选入库\n\n本目录只放准备导入 Mac 照片 App / iCloud 照片的精选副本，不保存全量项目素材。\n\n- `project-selected/`：项目代表照片、视频、情绪瞬间。\n- `cover-candidates/`：封面、首图、海报候选。\n- `memorial/`：超脱项目本身的人生节点、身份节点、重要关系和重要成果。\n- `phone-reusable/`：未来经常要在 iPhone / 移动端剪辑调用的通用素材。\n- `live-photo-groups/`：准备回导照片 App 的 HEIC/MOV/XMP 同名 Live Photo 组。\n- `final-output/`：Final、发布版、高光回看短片。\n- `pending-review/`：暂不确定归类的入库候选；确认后移动到 01-06。\n",
    "draft-project/project-notes.md": "# 工程说明\n\n- 剪辑交接文件按项目版本保存到 `edit-handoff/<项目版本>/`。\n- 默认生成标准剪辑交接包；选择可编辑时间线时，生成开放时间线和 Kdenlive 工程。两种方式不会自动切换。\n- 旧剪映资料如已存在，只作为历史证据保留；新项目结构不再创建旧剪映导入目录。\n- HyperFrames 源工程放 `draft-project/hyperframes/`；导出素材放 `output/hyperframes/` 或回填 L3。\n- `work-cache/` 是本项目专属临时加工区，不作为长期成品区，也不等同于 `80/90/91/92` 的正式去向。\n- 拼图时从 L3 复制选中原图到 `work-cache/collage-assets`，成品先放 `work-cache/collage-exports`；人工确认后再回填 L3、`icloud-selected` 或 `output`。\n",
    "draft-project/materials-used.md": "# 使用素材记录\n\n| 素材 | 用途 | 备注 |\n| --- | --- | --- |\n",
    "draft-project/edit-handoff/README.md": "# 剪辑交接版本\n\n- 每个项目版本保存为一个不可覆盖的子目录，例如 `1/`、`2/`。\n- 标准剪辑交接包包含片段清单、字幕和交接说明。\n- 可编辑时间线包含时间线、Kdenlive 工程和回读校验。\n- 改脚本、镜头、顺序、时长或素材前，先通过 Media Bot 提交并确认修改；不要覆盖旧版本。\n",
    "draft-project/hyperframes/README.md": "# HyperFrames\n\n- `src/`：HyperFrames 源工程、prompt、组件配置。\n- `render-logs/`：渲染记录、审核记录、错误记录。\n- 导出的 MP4/PNG/透明叠加素材放入 `output/hyperframes/` 或回填 L3。\n- HyperFrames 源工程不是剪映草稿，进入剪映的只应是导出的媒体文件。\n",
    "sync-ready/sync-checklist.md": "# 项目同步检查清单\n\n- [ ] L3 根部项目可用素材已整理\n- [ ] icloud-selected只放 iCloudReady 内容，且已归入 01-06 子目录\n- [ ] draft-project 已包含工程说明、导入包、官方备份包或 HyperFrames 源工程\n- [ ] output 已放成片和必要的 HyperFrames 导出素材\n- [ ] 如需合照发放，已运行 distribute_group_photos_by_name.py 生成发放副本\n- [ ] additions 不进入阿里云盘镜像\n- [ ] 剪映真实草稿活动根不进入阿里云盘镜像\n- [ ] work-cache 只保留必要的临时加工副本，不作为远程长期镜像\n- [ ] ai-analysis 清单、summary、plan、project_overview 已同步；keyframes/audio 按空间情况处理\n",
    "aliyun-sync-manifest.md": "# 阿里云盘同步记录\n\n- 同步方向：Mac 本地项目文件夹 -> 阿里云盘远程镜像\n- 不同步：additions、未完成临时转码文件、软件缓存、本地删除复核区、剪映真实草稿活动根、work-cache 中未确认的临时加工副本\n- draft-project 可以同步工程说明、导入包、官方备份包和 HyperFrames 源工程；不代表真实剪映活动草稿也在项目内。\n- ai-analysis 默认同步清单、summary、plan、project_overview；keyframes/audio 可按空间情况排除。\n",
}

PROTECTED_TOP_LEVEL_DIRS = {
    "raw-vault",
    "work-cache",
    "icloud-selected",
    "draft-project",
    "output",
    "sync-ready",
    "group-photo-distribution",
    ANALYSIS_DIR,
    "additions",
}


def workcache_root_for_project(project: Path) -> Path:
    return project / "work-cache"


def is_inbox_batch_path(project: Path) -> bool:
    return any(parent.name == "inbox" for parent in [project, *project.parents])


def ensure_structure(project: Path) -> tuple[list[Path], list[Path], list[Path], Path]:
    created_dirs: list[Path] = []
    created_workcache_dirs: list[Path] = []
    created_files: list[Path] = []
    workcache_root = workcache_root_for_project(project)

    for relative in PROJECT_DIRS:
        path = project / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(path)
        elif not path.is_dir():
            raise NotADirectoryError(f"expected directory but found file: {path}")

    for relative in WORKCACHE_DIRS:
        path = workcache_root / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_workcache_dirs.append(path)
        elif not path.is_dir():
            raise NotADirectoryError(f"expected directory but found file: {path}")

    for relative, content in PLACEHOLDER_FILES.items():
        path = project / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created_files.append(path)
        elif not path.is_file():
            raise IsADirectoryError(f"expected file but found directory: {path}")

    return created_dirs, created_workcache_dirs, created_files, workcache_root


def load_l3_plan(project: Path, plan_path: str) -> dict[str, object]:
    path = Path(plan_path).expanduser()
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"L3 structure plan not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        plan = json.load(f)
    if not isinstance(plan, dict):
        raise ValueError(f"invalid L3 structure plan: {path}")
    plan_project = plan.get("project_dir")
    if plan_project and Path(str(plan_project)).expanduser().resolve() != project.resolve():
        raise RuntimeError("plan project_dir does not match the provided project_dir")
    return plan


def ensure_plan_folder(project: Path, relative: str) -> Path:
    path = (project / relative).resolve()
    if not inside(path, project):
        raise RuntimeError(f"folder escapes project_dir: {relative}")
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f"expected directory but found file: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def plan_moves(plan: dict[str, object]) -> list[dict[str, object]]:
    moves = plan.get("moves")
    if not isinstance(moves, list):
        raise ValueError("L3 structure plan must contain a moves list")
    return [move for move in moves if isinstance(move, dict)]


def append_l3_structure_log(project: Path, moved: list[dict[str, object]], plan: dict[str, object]) -> None:
    if not moved:
        return
    log_path = project / "material-organization.md"
    lines: list[str] = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 素材整理记录", ""])
    lines.extend(
        [
            f"## L3 结构计划执行记录 {now_iso()}",
            "",
            f"- 计划来源：{plan.get('source', 'LLM/人工全局结构分析')}",
            f"- 计划说明：{plan.get('rationale', '')}",
            "",
            "| 原位置 | 新位置 | 依据 |",
            "| --- | --- | --- |",
        ]
    )
    for move in moved:
        lines.append(f"| {move['from']} | {move['to']} | {move.get('reason', '')} |")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_l3_plan(project: Path, plan: dict[str, object]) -> list[dict[str, object]]:
    folders = plan.get("folders", [])
    if not isinstance(folders, list):
        raise ValueError("L3 structure plan folders must be a list")
    for folder in folders:
        if isinstance(folder, str):
            ensure_plan_folder(project, folder)
        elif isinstance(folder, dict) and isinstance(folder.get("path"), str):
            ensure_plan_folder(project, str(folder["path"]))
        else:
            raise ValueError(f"invalid folder entry in L3 structure plan: {folder!r}")

    moved: list[dict[str, object]] = []
    planned_targets: set[str] = set()
    for move in plan_moves(plan):
        source_rel = str(move.get("from", ""))
        target_rel = str(move.get("to", ""))
        if not source_rel or not target_rel:
            raise ValueError(f"invalid move entry in L3 structure plan: {move!r}")

        source = (project / source_rel).resolve()
        target = (project / target_rel).resolve()
        if not inside(source, project):
            raise RuntimeError(f"source escapes project_dir: {source_rel}")
        if not inside(target, project):
            raise RuntimeError(f"target escapes project_dir: {target_rel}")
        if not source.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        if not source.is_file():
            raise IsADirectoryError(f"source is not a file: {source}")
        if source.suffix.lower() not in MEDIA_EXTS:
            raise RuntimeError(f"source is not a supported media/metadata file: {source.name}")
        if str(target) in planned_targets:
            raise RuntimeError(f"duplicate target in L3 structure plan: {target_rel}")
        planned_targets.add(str(target))
        if source == target:
            continue
        if target.exists():
            raise FileExistsError(f"target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append(
            {
                "from": source_rel,
                "to": relative_posix(target, project),
                "reason": move.get("reason", ""),
            }
        )
    append_l3_structure_log(project, moved, plan)
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="补齐项目标准工作流目录")
    parser.add_argument("project_dir", help="项目目录")
    parser.add_argument("--apply-l3-plan", help="执行由 LLM/人工全局分析确认的 L3 结构计划 JSON")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    if is_inbox_batch_path(project):
        raise SystemExit(
            "error: ensure_project_structure.py 只能用于 projects 下的正式项目，"
            "不能直接作用于 inbox 批次。\n"
            f"请先运行：python3 {Path(__file__).resolve().parent / 'ensure_project_from_inbox_batch.py'} \"{project}\""
        )
    created_dirs, created_workcache_dirs, created_files, workcache_root = ensure_structure(project)
    print(f"项目结构检查完成：{project}")
    print(f"新建项目目录：{len(created_dirs)} 个")
    print(f"项目级 WorkCache：{workcache_root}")
    print(f"新建 WorkCache 目录：{len(created_workcache_dirs)} 个")
    print(f"新建文件：{len(created_files)} 个")
    for path in created_dirs:
        print(f"dir  {path.relative_to(project)}")
    for path in created_workcache_dirs:
        print(f"workcache {path.relative_to(workcache_root)}")
    for path in created_files:
        print(f"file {path.relative_to(project)}")

    if args.apply_l3_plan:
        plan = load_l3_plan(project, args.apply_l3_plan)
        moved = apply_l3_plan(project, plan)
        print(f"已执行 L3 结构计划：{len(moved)} 个文件")
        for move in moved:
            print(f"move {move['from']} -> {move['to']}")


if __name__ == "__main__":
    main()
