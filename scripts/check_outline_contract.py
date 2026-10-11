#!/usr/bin/env python3
"""Check that the local execution outline, docs, and scripts README share one contract."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from document_contract_common import missing_markers


REQUIRED_SCRIPTS = [
    "scan_media_manifest.py",
    "extract_keyframes.py",
    "extract_audio.sh",
    "generate_ai_prompt.py",
    "write_content_summary.py",
    "validate_media_decisions.py",
    "plan_additions_merge.py",
    "apply_additions_merge.py",
    "run_additions_merge.sh",
    "rename_media_file.py",
    "select_repeat_photo_groups.py",
    "ensure_project_structure.py",
    "distribute_group_photos_by_name.py",
    "register_reusable_asset.py",
    "validate_review_capability_registry.py",
    "check_obsidian_doc_sync.py",
    "run_analyze_project.sh",
]

OUTLINE_MARKERS = [
    "scripts/",
    "制度工具根",
    "本地素材根",
    "L1 本地素材根",
    "L2 主题集合",
    "L3 项目根",
    "L4 内容目录",
    "projects",
    "项目根",
    "项目 L3 源文件",
    "80 精选副本",
    "iCloudReady",
    "ai-analysis",
    "media-manifest.json",
    "keyframes",
    "prompts",
    "summaries",
    "media-decision-warnings.md",
    "additions-merge-plan",
    "rename_media_file.py",
    "select_repeat_photo_groups.py",
    "ensure_project_structure.py",
    "distribute_group_photos_by_name.py",
    "register_reusable_asset.py",
    "icloud-selected",
    "project-selected",
    "memorial",
    "phone-reusable",
    "连拍原始组_保留",
    "memorial",
    "group-photo-distribution",
    "library",
    "decision-tables",
    "素材高频情形决策表",
    "frequent-decisions",
    "usage-guides",
    "ideas-to-project",
    "footage-to-inbox",
    "project-queue-binding",
    "analysis-storyboard-edl",
    "editing-handoff-review",
    "jianying-drafts",
    "HyperFrames",
    "native-import-packs",
    "official-backups",
    "collage-assets",
    "最大信息保留",
    "aliyun-sync-manifest.md",
]

README_MARKERS = [
    "media-workflow.md",
    "制度层",
    "执行层",
    "本地素材根",
    "projects",
    "ai-analysis",
    "media-decision-warnings.md",
    "additions-merge-plan",
    "rename_media_file.py",
    "select_repeat_photo_groups.py",
    "ensure_project_structure.py",
    "distribute_group_photos_by_name.py",
    "register_reusable_asset.py",
    "icloud-selected",
    "project-selected",
    "memorial",
    "phone-reusable",
    "连拍原始组_保留",
    "memorial",
    "group-photo-distribution",
    "library",
    "decision-tables",
    "素材决策表",
    "07.xx",
    "usage-guides",
    "08.xx",
    "jianying-drafts",
    "HyperFrames",
    "native-import-packs",
    "official-backups",
    "collage-assets",
    "最大信息保留",
    "doc-sync-contract.json",
    "check_obsidian_doc_sync.py",
    "run_analyze_project.sh",
]


def read_child_docs(root: Path) -> str:
    docs_candidates = [
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
        root / "scripts",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise NotADirectoryError(f"missing scripts directory under: {root}")


def main() -> None:
    parser = argparse.ArgumentParser(description="检查脚本与大纲的闭环契约")
    parser.add_argument("root_dir", nargs="?", default=".", help="本地素材根目录，包含 docs/ 和 scripts/")
    parser.add_argument("--skip-obsidian-sync", action="store_true", help="只检查本地执行总纲/脚本契约，跳过 Obsidian 协议同步检查")
    args = parser.parse_args()

    root = Path(args.root_dir).expanduser().resolve()
    outline = root / "docs" / "media-workflow.md"
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
            details.append(f"media-workflow.md missing markers: {', '.join(outline_missing)}")
        if readme_missing:
            details.append(f"scripts/README.md missing markers: {', '.join(readme_missing)}")
        raise RuntimeError("; ".join(details))

    if not args.skip_obsidian_sync:
        obsidian_sync_script = scripts_dir / "check_obsidian_doc_sync.py"
        if not obsidian_sync_script.exists():
            raise FileNotFoundError(f"missing Obsidian sync checker: {obsidian_sync_script}")
        subprocess.run(
            [sys.executable, str(obsidian_sync_script), "--local-root", str(root)],
            check=True,
        )

    print("media-workflow.md ↔ scripts 闭环契约检查通过")


if __name__ == "__main__":
    main()
