#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 INSTANCE_ROOT [--dsh-home PATH] [--max-submissions N] [--base-url HTTPS_ORIGIN]" >&2
    exit 2
fi
provider="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/wanxiang-provider" && pwd -P)"
exec python3 - "$provider" "$@" <<'PY'
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("provider", type=Path)
parser.add_argument("instance", type=Path)
parser.add_argument("--dsh-home", type=Path)
parser.add_argument("--max-submissions", type=int)
parser.add_argument("--base-url", default="https://dashscope.aliyuncs.com")
args = parser.parse_args()
instance = args.instance.resolve()
if not (instance / "app/scripts/video-harness/launch.sh").is_file():
    parser.error("INSTANCE_ROOT must contain the DreamVerse checkout at app/.")
state = (args.dsh_home or instance / "state").resolve()
profile = state / "profiles/video-harness"
if not (profile / "cordis.yml").is_file():
    parser.error("Initialize the video-harness profile before installing the provider.")
if args.max_submissions is not None and args.max_submissions < 1:
    parser.error("--max-submissions must be positive.")
origin = urlsplit(args.base_url)
if (origin.scheme != "https" or not (origin.hostname or "").endswith(".aliyuncs.com")
        or origin.username or origin.password or origin.path not in ("", "/") or origin.query or origin.fragment):
    parser.error("--base-url must be an HTTPS Aliyun DashScope origin.")

patch_path = profile / "cordis.patch.yml"
current = patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""
start = "# BEGIN production-desk wanxiang-provider"
end = "# END production-desk wanxiang-provider"
managed = re.compile(rf"(?m)^{re.escape(start)}\n[\s\S]*?^{re.escape(end)}\n?")
base = managed.sub("", current)
if start in base or end in base:
    parser.error("The existing Wanxiang profile patch has an incomplete managed block.")
if re.search(r"(?m)^\s*(?:-\s*)?id:\s*['\"]?dv-wanxiang-provider\b", base):
    parser.error("The profile already registers a Wanxiang provider outside the managed block.")
if base.strip() == "[]":
    base = ""
lines = [
    start, "- insert:", "    - id: dv-wanxiang-provider",
    "      name: '@dv/wanxiang-provider'", "      config:",
    "        baseUrl: " + json.dumps(args.base_url),
    "        stateDir: " + json.dumps(str(state / "wanxiang-receipts"), ensure_ascii=False),
]
if args.max_submissions is not None:
    lines.append(f"        maxSubmissions: {args.max_submissions}")
block = "\n".join([*lines, end, ""])
scope = profile / "node_modules/@dv"
scope.mkdir(parents=True, exist_ok=True)
link = scope / "wanxiang-provider"
if link.is_symlink():
    if link.resolve() != args.provider:
        parser.error("The provider link already points at a different checkout.")
elif link.exists():
    parser.error("The provider path exists and is not a symlink.")
else:
    link.symlink_to(args.provider, target_is_directory=True)
with tempfile.NamedTemporaryFile(dir=profile, prefix=".wanxiang-patch-", delete=False, mode="w", encoding="utf-8") as handle:
    handle.write((base.rstrip() + "\n\n" if base.strip() else "") + block)
    temporary = handle.name
try:
    os.replace(temporary, patch_path)
finally:
    Path(temporary).unlink(missing_ok=True)
print("Wanxiang provider linked. Restart the DreamVerse service to load it.")
PY
