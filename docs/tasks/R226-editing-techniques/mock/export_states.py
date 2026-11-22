"""Export each design state of the R226 mock into design-states.html (no image URLs)."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

mock = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
STATES = [
    'cut-no-music',
    'cut-arranging',
    'cut-failed',
    'cut-ready',
    'cut-occurrence',
    'cut-custom',
    'cut-partial',
    'cut-multi',
    'cut-multi-swap',
    'cut-presets',
    'cut-mine',
    'cut-editor',
    'cut-editor-chatcut',
    'cut-add-song',
    'cut-replace-song',
    'cut-beat-queued',
    'cut-beat-analyzing',
    'cut-failed-unreadable',
    'cut-failed-missing',
    'cut-failed-short',
    'cut-rearrange-failed',
    'cut-editor-unsupported',
    'cut-presets-unreadable',
    'cut-partial-none',
    'cut-bed-short',
    'cut-stacked',
    'cut-editor-kdenlive-missing',
    'cut-editor-chatcut-connected',
    'cut-editor-guide-missing',
    'cut-editor-openfilm',
    'cut-editor-unreadable',
    'cut-presets-unreadable-mine',
    'cut-drafting',
    'cut-drafted',
    'cut-drafted-guide',
    'cut-draft-stale',
]
parts = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    pg = b.new_page(viewport={'width': 1440, 'height': 1000})
    pg.goto(mock.as_uri())
    pg.wait_for_timeout(600)
    for s in STATES:
        pg.evaluate('s => go(s)', s)
        pg.wait_for_timeout(400)
        assert pg.eval_on_selector('#screen', 'e => e.dataset.designState') == s, s
        html = pg.eval_on_selector('#app', 'e => e.innerHTML')
        html = re.sub(r'\s(src|srcset|poster)="[^"]*"', '', html)
        html = re.sub(r'url\([^)]*\)', 'none', html)
        parts.append(f'<section data-design-state="{s}">{html}</section>')
    b.close()
out.write_text('<!doctype html><html lang="zh-CN"><body>' + ''.join(parts) + '</body></html>', encoding='utf-8')
print(out, len(parts))
