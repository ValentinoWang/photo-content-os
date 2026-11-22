#!/bin/bash
# usage: lint-one.sh <html> ; lint.py takes a shots directory, so stage the file as 01.html
set -o pipefail
d=$(mktemp -d) || exit 1
cp "$1" "$d/01.html" || { rm -rf "$d"; exit 1; }
.venv/bin/python scripts/direct_video/lint.py "$d"; rc=$?
rm -rf "$d"; exit $rc
