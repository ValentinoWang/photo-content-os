#!/usr/bin/env python3
"""Export the canonical desktop OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.api_contract import build_openapi  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=SYSTEM_ROOT / "schemas" / "desktop_openapi.json",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"desktop OpenAPI is stale: {args.output}", file=sys.stderr)
            return 1
        print(f"desktop OpenAPI is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
