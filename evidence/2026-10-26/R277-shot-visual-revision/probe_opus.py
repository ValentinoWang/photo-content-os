import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from llm_common import generate_text

started = time.monotonic()
record = {'stdinTTY': sys.stdin.isatty(), 'stdoutTTY': sys.stdout.isatty(),
          'account': os.environ.get('CLAUDE_CONFIG_DIR'), 'model': 'claude-opus-5-5'}
try:
    record['result'] = generate_text(
        provider='claude_cli', model='claude-opus-5-5',
        system_prompt='请只描述所附图片实际可见的画面。不要使用工具。',
        user_prompt='这张关键帧写了什么，有什么图形？请用两句中文回答。',
        image_paths=[Path.home() / '.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/poster-02.jpg'],
    )
    record['ok'] = True
except Exception as exc:
    record.update(ok=False, error=str(exc))
record['elapsedSeconds'] = round(time.monotonic() - started, 3)
Path(__file__).with_name('opus-image-probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
print(json.dumps(record, ensure_ascii=False), flush=True)
