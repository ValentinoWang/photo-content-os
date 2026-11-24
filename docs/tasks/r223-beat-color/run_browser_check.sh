#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)
cd "$root"

if [[ ${1:-} != --remote && ${1:-} != --sandbox ]]; then
    # This task worktree predates the photo-content-os-* naming convention.
    export RBOX_LOCAL_ROOT="$root"
    export RBOX_WITH=evidence/2026-10-21/R223-music-beat-map/phase-b
    exec "$root/.agents/skills/photo-remote-dev-box/scripts/rbox" run "$root" -- \
        /bin/bash "$root/docs/tasks/r223-beat-color/run_browser_check.sh" --remote "$@"
fi

mode=$1
shift
runtime=${R223_DEVBOX_RUNTIME:-/root/pco}
python="$runtime/.venv/bin/python"
node="$runtime/.tools/node/bin/node"
design_evidence=evidence/2026-10-21/R223-music-beat-map/phase-b

if [[ $mode == --remote ]]; then
    chrome="$runtime/.tools/browsers/chromium-1228/chrome-linux64"
    test -x "$chrome/chrome"
    mkdir -p "$TMPDIR/r223-opt/google"
    ln -s "$chrome" "$TMPDIR/r223-opt/google/chrome"
    exec unshare --mount --propagation private /bin/bash "${BASH_SOURCE[0]}" --sandbox "$@"
fi

# The protected check requests channel: 'chrome'. Expose the pinned browser
# in this mount namespace only, as in the prior R223 baseline run.
mount --bind "$TMPDIR/r223-opt" /opt
export PW_REQ="$runtime/.tools/browser-runtime/node_modules/playwright/index.js"
"$node" --version
/opt/google/chrome/chrome --version

run_browser() (
    source_root=$1
    revision=$2
    scratch=$(mktemp -d "$TMPDIR/r223.XXXXXX")
    studio_pid=
    cleanup() {
        if [[ -n $studio_pid ]]; then
            kill "$studio_pid" 2>/dev/null || true
            wait "$studio_pid" 2>/dev/null || true
        fi
        rm -rf -- "$scratch"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    cd "$source_root"
    printf 'Studio source: %s\n' "$revision"
    export LOCAL_MEDIA_ROOT="$scratch/media"
    mkdir "$LOCAL_MEDIA_ROOT"
    ffmpeg -v error -f lavfi -i sine=frequency=440 -t 180 "$LOCAL_MEDIA_ROOT/test-tone.wav"
    "$python" - "$scratch" > "$scratch/studio.log" 2>&1 <<'PY' &
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "scripts"))
from music_library.cache import write_json
from music_library.library import MusicLibrary
from studio.music_analysis import failure
from studio.server import serve

scratch = Path(sys.argv[1])
media = Path(os.environ["LOCAL_MEDIA_ROOT"])
library = MusicLibrary(media)
audio = media / "test-tone.wav"
_, template = library.import_local(audio)
fixture = json.loads(Path("tests/fixtures/r223/frontend/music.json").read_text())
tracks = []
for item in fixture["tracks"]:
    # The fixed IDs belong to the browser fixtures. Studio streams the
    # generated WAV through the normal audio route for those IDs.
    identifier = item["file_sha256"]
    track = {**template, "file_sha256": identifier, "title": item["title"]}
    directory = library.root / identifier
    directory.mkdir()
    (directory / track["audio_file"]).hardlink_to(audio)
    write_json(directory / "track.json", track)
    write_json(directory / "analysis.json", dict(
        schema_version=1, file_sha256=identifier,
        duration_seconds=track["duration_seconds"], registry_version=1,
        beat=failure("worker_error"), tags=failure("worker_error"),
    ))
    tracks.append(track)
original = library.root / template["file_sha256"]
(original / template["audio_file"]).unlink()
(original / "track.json").unlink()
original.rmdir()
write_json(library.root / "index.json", {"schema_version": 2, "tracks": tracks})

def ready(url):
    temporary = scratch / "url.tmp"
    temporary.write_text(url.rstrip("/"))
    temporary.rename(scratch / "url")

with serve(state_dir=scratch / "state", port=0, on_ready=ready) as server:
    server.serve_forever()
PY
    studio_pid=$!
    for ((i = 0; i < 100; i++)); do
        [[ -s $scratch/url ]] && break
        kill -0 "$studio_pid" 2>/dev/null || break
        sleep .2
    done
    if [[ ! -s $scratch/url ]]; then
        tail -n 40 "$scratch/studio.log" >&2
        return 1
    fi
    STUDIO_URL=$(cat "$scratch/url")
    export STUDIO_URL
    [[ $STUDIO_URL != *:8765 ]]
    "$node" "$root/scripts/verify_r223_interactions.mjs"
    if [[ ${3:-} == --with-beat-map ]]; then
        "$node" "$root/tests/test_r223_beat_map.mjs"
    fi
)

if (( $# )); then
    # Run the same current check against the Studio and fixtures of each ref.
    for ref in "$@"; do
        revision=$(git rev-parse --verify "$ref^{commit}")
        source_root=$(mktemp -d "$TMPDIR/r223-source.XXXXXX")
        git archive "$revision" scripts studio schemas templates third_party tests/fixtures/r223 \
            music-analysis.registry.json review-capabilities.registry.json requirements-dev.txt \
            | tar -x -C "$source_root"
        run_browser "$source_root" "$revision"
    done
else
    run_browser "$root" "$(git rev-parse HEAD)" --with-beat-map
    design_root=$(mktemp -d "$TMPDIR/r223-design.XXXXXX")
    mkdir -p "$design_root/$(dirname -- "$design_evidence")"
    cp -R "$design_evidence" "$design_root/$design_evidence"
    ln -s "$root/docs" "$design_root/docs"
    cd "$design_root"
    export DESIGN_CONTRACT_CHECKER="$HARNESS_CORE/skills/ui-copy-quality/scripts/check_design_contract.py"
    "$python" "$root/scripts/check_r223_design.py"
fi
