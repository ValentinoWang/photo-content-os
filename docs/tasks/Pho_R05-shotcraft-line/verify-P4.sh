#!/bin/bash
# P4: unit tests + real-track plan and premix (no render)
set -o pipefail
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line || exit 1
.venv/bin/python -m pytest -q tests/test_pho_r05_promo_plan.py || exit 1
out=$(mktemp -d) || exit 1
cat > "$out/spec.json" <<'J'
{"track_id": "891759d6a9fc", "fps": 30, "width": 1920, "height": 1080, "start_bar": 9,
 "shots": [{"id": "01", "html": "01.html", "bars": 2}, {"id": "02", "html": "02.html", "bars": 2}, {"id": "03", "html": "03.html", "bars": 4}],
 "fade_out_seconds": 1.0}
J
tid=$(ls /Users/vsiyo/Desktop/照片筛选/library/music | grep '^891759d6a9fc'); sed -i '' "s/891759d6a9fc/$tid/" "$out/spec.json"
.venv/bin/python scripts/direct_video/promo_plan.py --spec "$out/spec.json" --media-root /Users/vsiyo/Desktop/照片筛选 --out "$out/plan" || { rm -rf "$out"; exit 1; }
.venv/bin/python - "$out/plan" <<'P' ; rc=$?
import json, sys, wave
from pathlib import Path
sys.path.insert(0, 'scripts/video_render')
import compose
plan = Path(sys.argv[1])
m = json.loads((plan / 'compose-manifest.json').read_text())
compose.audio_inputs(m)
with wave.open(m['narration_wav']) as w:
    print('frames', [s['frames'] for s in m['shots']], 'wav_s', round(w.getnframes() / w.getframerate(), 3))
P
rm -rf "$out"; exit $rc
