#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 INSTANCE_ROOT [--provider wanxiang|seedance|both] [--dsh-home PATH] [--max-submissions N] [--base-url HTTPS_ORIGIN]" >&2
    exit 2
fi
provider="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 - "$provider" "$@" <<'PY'
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("provider_path", type=Path)
parser.add_argument("instance", type=Path)
parser.add_argument("--dsh-home", type=Path)
parser.add_argument("--provider", choices=["wanxiang", "seedance", "both"], default="both")
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
if current.strip() == "[]":
    current = ""
selected = ["wanxiang", "seedance"] if args.provider == "both" else [args.provider]
for name in selected:
    start = f"# BEGIN production-desk {name}-provider"
    end = f"# END production-desk {name}-provider"
    managed = re.compile(rf"(?m)^{re.escape(start)}\n[\s\S]*?^{re.escape(end)}\n?")
    matches = list(managed.finditer(current))
    base = managed.sub("", current)
    if len(matches) > 1 or start in base or end in base:
        parser.error(f"The existing {name} profile patch has an incomplete or duplicate managed block.")
    if re.search(rf"(?m)^\s*(?:-\s*)?id:\s*['\"]?dv-{name}-provider\b", base):
        parser.error(f"The profile already registers a {name} provider outside the managed block.")
    source = (args.provider_path / f"{name}-provider").resolve()
    lines = [start, "- insert:", f"    - id: dv-{name}-provider",
             f"      name: '@dv/{name}-provider'", "      config:",
             "        baseUrl: " + json.dumps(args.base_url if name == "wanxiang" else "https://ark.cn-beijing.volces.com"),
             "        stateDir: " + json.dumps(str(state / f"{name}-receipts"), ensure_ascii=False)]
    if args.max_submissions is not None:
        lines.append(f"        maxSubmissions: {args.max_submissions}")
    block = "\n".join([*lines, end, ""])
    if matches:
        current = managed.sub(lambda _match: block, current, count=1)
    else:
        current = (current.rstrip() + "\n\n" if current.strip() else "") + block
    scope = profile / "node_modules/@dv"
    scope.mkdir(parents=True, exist_ok=True)
    link = scope / f"{name}-provider"
    if link.is_symlink():
        if link.resolve() != source:
            parser.error("The provider link already points at a different checkout.")
    elif link.exists():
        parser.error("The provider path exists and is not a symlink.")
    else:
        link.symlink_to(source, target_is_directory=True)
with tempfile.NamedTemporaryFile(dir=profile, prefix=".provider-patch-", delete=False, mode="w", encoding="utf-8") as handle:
    handle.write(current)
    temporary = handle.name
try:
    os.replace(temporary, patch_path)
finally:
    Path(temporary).unlink(missing_ok=True)
print("Selected providers linked. Restart the DreamVerse service to load them.")
PY
