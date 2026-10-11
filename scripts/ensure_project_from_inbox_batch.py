#!/usr/bin/env python3
"""Create or resolve a formal project shell for an Inbox batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_bootstrap_common import ensure_formal_project_for_batch
from runtime_paths import workspace_root as _shared_workspace_root


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = _shared_workspace_root(Path(__file__))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_dir", type=Path, help="00_Inbox_Mac_Intake 下的事件批次目录")
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT, help="本地素材根目录")
    parser.add_argument("--topic", default="", help="可选：覆盖项目剪辑目标 / 主题")
    parser.add_argument("--platform", default="", help="可选：目标平台")
    parser.add_argument("--content-type", default="", help="可选：内容类型")
    parser.add_argument("--creation-run-id", default="", help="可选：云端 creation_run_id")
    parser.add_argument("--feishu-doc-link", default="", help="可选：飞书文档链接")
    args = parser.parse_args()

    task = {
        "topic": args.topic,
        "platform": args.platform,
        "content_type": args.content_type,
        "creation_run_id": args.creation_run_id,
        "feishu_doc_link": args.feishu_doc_link,
        "batch_id": args.batch_dir.expanduser().resolve().name,
    }
    result = ensure_formal_project_for_batch(
        args.batch_dir,
        task={key: value for key, value in task.items() if value},
        workspace_root=args.workspace_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
