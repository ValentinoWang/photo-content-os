#!/usr/bin/env python3
"""Check that the local execution outline, docs, and scripts README share one contract."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from media_common import missing_markers


REQUIRED_SCRIPTS = [
    "01_scan_media_manifest.py",
    "02_extract_keyframes.py",
    "03_extract_audio.sh",
    "04_generate_ai_prompt.py",
    "05_write_content_summary.py",
    "07_validate_media_decisions.py",
    "08_plan_additions_merge.py",
    "09_apply_additions_merge.py",
    "10_run_additions_merge.sh",
    "11_rename_media_file.py",
    "12_select_repeat_photo_groups.py",
    "13_ensure_project_structure.py",
    "14_distribute_group_photos_by_name.py",
    "15_register_reusable_asset.py",
    "36_validate_review_capability_registry.py",
    "30_check_obsidian_doc_sync.py",
    "run_analyze_project.sh",
]

OUTLINE_MARKERS = [
    "99_System_OpenClaw/scripts/",
    "制度工具根",
    "本地素材根",
    "L1 本地素材根",
    "L2 主题集合",
    "L3 项目根",
    "L4 内容目录",
    "01_Project_Workspace",
    "项目根",
    "项目 L3 源文件",
    "80 精选副本",
    "iCloudReady",
    "_ai_analysis",
    "media_manifest.json",
    "keyframes",
    "prompts",
    "summaries",
    "media_decision_warnings.md",
    "additions_merge_plan",
    "11_rename_media_file.py",
    "12_select_repeat_photo_groups.py",
    "13_ensure_project_structure.py",
    "14_distribute_group_photos_by_name.py",
    "15_register_reusable_asset.py",
    "80_To_iCloudPhotos_精选入库",
    "01_Project_Selected_项目精选",
    "03_Memorial_纪念资产",
    "04_Reusable_To_iPhone_手机常用复用素材",
    "连拍原始组_保留",
    "Memorial_人生节点",
    "93_GroupPhoto_Distribution_合照发放",
    "02_Asset_Library",
    "07_decision_tables_决策表",
    "素材高频情形决策表",
    "07.01_高频情形决策表",
    "08_usage_guides_使用指南",
    "08.01_只有tags灵感想法_从信号到项目包",
    "08.02_已有拍摄素材但未立项_Mac_Inbox落盘",
    "08.03_已有项目包和本地素材_绑定任务队列",
    "08.04_素材已进正式项目_分析匹配分镜EDL",
    "08.05_需要进入剪映或成片复核_导入包与验收",
    "03_Jianying_Active_Drafts",
    "HyperFrames",
    "native_import_packs",
    "official_backups",
    "拼图素材暂存",
    "最大信息保留",
    "aliyun_sync_manifest.md",
]

README_MARKERS = [
    "00_本地素材与剪映HyperFrames流转总纲.md",
    "制度层",
    "执行层",
    "本地素材根",
    "01_Project_Workspace",
    "_ai_analysis",
    "media_decision_warnings.md",
    "additions_merge_plan",
    "11_rename_media_file.py",
    "12_select_repeat_photo_groups.py",
    "13_ensure_project_structure.py",
    "14_distribute_group_photos_by_name.py",
    "15_register_reusable_asset.py",
    "80_To_iCloudPhotos_精选入库",
    "01_Project_Selected_项目精选",
    "03_Memorial_纪念资产",
    "04_Reusable_To_iPhone_手机常用复用素材",
    "连拍原始组_保留",
    "Memorial_人生节点",
    "93_GroupPhoto_Distribution_合照发放",
    "02_Asset_Library",
    "07_decision_tables_决策表",
    "素材决策表",
    "07.xx",
    "08_usage_guides_使用指南",
    "08.xx",
    "03_Jianying_Active_Drafts",
    "HyperFrames",
    "native_import_packs",
    "official_backups",
    "拼图素材暂存",
    "最大信息保留",
    "doc_sync_contract.json",
    "30_check_obsidian_doc_sync.py",
    "run_analyze_project.sh",
]


def read_child_docs(root: Path) -> str:
    docs_candidates = [
        root / "99_System_OpenClaw" / "docs",
        root / "docs",
    ]
    docs_dir = next((candidate for candidate in docs_candidates if candidate.exists()), None)
    if docs_dir is None:
        return ""
    if not docs_dir.is_dir():
        raise NotADirectoryError(f"expected docs directory but found file: {docs_dir}")
    parts: list[str] = []
    for path in sorted(docs_dir.rglob("*.md")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def resolve_scripts_dir(root: Path) -> Path:
    candidates = [
        root / "99_System_OpenClaw" / "scripts",
        root / "scripts",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise NotADirectoryError(f"missing scripts directory under: {root}")


def main() -> None:
    parser = argparse.ArgumentParser(description="检查脚本与大纲的闭环契约")
    parser.add_argument("root_dir", nargs="?", default=".", help="本地素材根目录，包含 99_System_OpenClaw/docs/ 和 99_System_OpenClaw/scripts/")
    parser.add_argument("--skip-obsidian-sync", action="store_true", help="只检查本地执行总纲/脚本契约，跳过 Obsidian 协议同步检查")
    args = parser.parse_args()

    root = Path(args.root_dir).expanduser().resolve()
    outline = root / "99_System_OpenClaw" / "docs" / "00_本地素材与剪映HyperFrames流转总纲.md"
    scripts_dir = resolve_scripts_dir(root)
    readme = scripts_dir / "README.md"

    if not outline.exists():
        raise FileNotFoundError(f"missing outline: {outline}")
    if not readme.exists():
        raise FileNotFoundError(f"missing scripts README: {readme}")
    missing_scripts = [name for name in REQUIRED_SCRIPTS if not (scripts_dir / name).exists()]
    if missing_scripts:
        raise FileNotFoundError(f"missing required scripts: {', '.join(missing_scripts)}")

    outline_text = outline.read_text(encoding="utf-8")
    child_docs_text = read_child_docs(root)
    contract_text = outline_text + "\n\n" + child_docs_text
    readme_text = readme.read_text(encoding="utf-8")
    outline_missing = missing_markers(contract_text, OUTLINE_MARKERS)
    readme_missing = missing_markers(readme_text, README_MARKERS)

    if outline_missing or readme_missing:
        details = []
        if outline_missing:
            details.append(f"00_本地素材与剪映HyperFrames流转总纲.md missing markers: {', '.join(outline_missing)}")
        if readme_missing:
            details.append(f"99_System_OpenClaw/scripts/README.md missing markers: {', '.join(readme_missing)}")
        raise RuntimeError("; ".join(details))

    if not args.skip_obsidian_sync:
        obsidian_sync_script = scripts_dir / "30_check_obsidian_doc_sync.py"
        if not obsidian_sync_script.exists():
            raise FileNotFoundError(f"missing Obsidian sync checker: {obsidian_sync_script}")
        subprocess.run(
            [sys.executable, str(obsidian_sync_script), "--local-root", str(root)],
            check=True,
        )

    print("00_本地素材与剪映HyperFrames流转总纲.md ↔ scripts 闭环契约检查通过")


if __name__ == "__main__":
    main()
