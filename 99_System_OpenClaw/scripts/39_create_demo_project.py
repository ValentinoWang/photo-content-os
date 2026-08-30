#!/usr/bin/env python3
"""Create and scan a synthetic project without touching personal media."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from media_common import manifest_path as _manifest_path
from runtime_paths import repository_root as _repository_root

SAMPLE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
SAMPLE_NAMES = (
    "01_项目开场.png",
    "02_人物互动.png",
    "03_细节补充.png",
)


def repository_root() -> Path:
    """L-15: delegates to the marker-based runtime_paths.repository_root,
    anchored at this file, instead of this script's former hardcoded
    parents[2]."""
    return _repository_root(Path(__file__))


def run_script(script: Path, project: Path) -> None:
    subprocess.run([sys.executable, str(script), str(project)], check=True)


def create_demo(workspace_root: Path, project_name: str) -> dict[str, object]:
    project = workspace_root / "01_Project_Workspace" / "00_Demo_试用" / project_name
    if project.exists():
        raise FileExistsError(f"demo project already exists: {project}")

    source_dir = project / "00_Inbox_待分类"
    source_dir.mkdir(parents=True)
    for name in SAMPLE_NAMES:
        (source_dir / name).write_bytes(SAMPLE_PNG)

    scripts_dir = Path(__file__).resolve().parent
    run_script(scripts_dir / "13_ensure_project_structure.py", project)
    run_script(scripts_dir / "01_scan_media_manifest.py", project)

    manifest_path = _manifest_path(project)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != len(SAMPLE_NAMES):
        raise RuntimeError(f"demo manifest has unexpected item count: {manifest_path}")
    if not all(item.get("analysis_eligible") is True for item in items):
        raise RuntimeError(f"demo manifest contains ineligible sample media: {manifest_path}")

    return {
        "status": "passed",
        "project_dir": str(project.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "media_count": len(items),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="创建不含私人数据的照片整理试用项目")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=repository_root() / "demo_workspace",
        help="试用工作区；默认写入仓库内已被 Git 忽略的 demo_workspace",
    )
    parser.add_argument(
        "--project-name",
        default=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_照片整理试用",
        help="试用项目目录名；已存在时拒绝覆盖",
    )
    args = parser.parse_args()

    result = create_demo(args.workspace_root.expanduser().resolve(), args.project_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
