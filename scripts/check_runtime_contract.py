#!/usr/bin/env python3
"""Cross-platform deterministic runtime contract check."""

from __future__ import annotations

import argparse
import compileall
import importlib.metadata
import sys
from pathlib import Path

MINIMUM = (3, 11)
PINNED = {
    "opentimelineio": "0.18.1",
    "pyjianyingdraft": "0.2.6",
}


def check_runtime(scripts_dir: Path, *, strict_packages: bool = True) -> list[str]:
    messages: list[str] = []
    if sys.version_info < MINIMUM:
        raise RuntimeError(f"Python {MINIMUM[0]}.{MINIMUM[1]} or newer is required; found {sys.version.split()[0]}")
    messages.append(f"python={sys.version.split()[0]}")
    if not compileall.compile_dir(str(scripts_dir), quiet=1):
        raise RuntimeError(f"compileall failed: {scripts_dir}")
    messages.append("compileall=ok")
    if strict_packages:
        for package, expected in PINNED.items():
            actual = importlib.metadata.version(package)
            if actual != expected:
                raise RuntimeError(f"{package} version mismatch: expected {expected}, got {actual}")
        messages.append("packages=ok")
    forbidden_encodings = ("encoding=" + "\"mbcs\"", "encoding=" + "'mbcs'")
    for path in scripts_dir.rglob("*.py"):
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden_encodings):
            raise RuntimeError(f"platform-default mbcs encoding is disallowed: {path}")
    messages.append("encoding_contract=ok")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scripts-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--skip-package-pins", action="store_true")
    args = parser.parse_args()
    for message in check_runtime(args.scripts_dir.resolve(), strict_packages=not args.skip_package_pins):
        print(message)
    print("Runtime contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
