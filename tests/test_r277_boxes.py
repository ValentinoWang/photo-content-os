"""DOM geometry uses the same browser/frame clock as keyframe rendering."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from direct_video.media import LocalMedia

pytestmark = pytest.mark.skipif(not os.getenv('VIDEO_RENDER_PLAYWRIGHT_MODULE'), reason='Pinned Playwright/browser required for DOM measurement')


def test_r276_shot02_boxes_at_poster_frame_and_chinese_names(tmp_path):
    source = (ROOT / 'docs/tasks/R276-direct-video-opus/design/shots-data.js').read_text()
    shot = json.loads(source.split('window.R131 = ', 1)[1].rsplit(';', 1)[0])['shots'][1]
    # Two real browser frames: 0 and exactly .8D, using the renderer's existing
    # frame_clock_scale. The original scene code and timings are unchanged.
    extra = '''<div id="hidden-opacity" style="opacity:0;width:100px;height:100px">隐藏</div>
<div style="opacity:0"><div id="hidden-parent" style="width:100px;height:100px">隐藏</div></div>
<div id="hidden-display" style="display:none">隐藏</div>
<div id="hidden-size" style="width:0;height:0;overflow:hidden">隐藏</div>
<div id="long-text" style="position:absolute;top:1600px;width:800px;height:80px">一二三四五六七八九十甲乙丙丁戊</div>
<div id="empty-shape" style="position:absolute;top:1750px;width:100px;height:100px"></div>'''
    html = tmp_path / '02.html'
    html.write_text(shot['html'].replace('</body>', extra + '</body>'))
    request = {'width': 1080, 'height': 1920, 'fps': 30, 'frames': 2, 'timeout_seconds': 30,
               'assets_dir': str(tmp_path), 'html': str(html), 'fonts': [{'path': '/System/Library/Fonts/STHeiti Medium.ttc'}],
               'frame_clock_scale': shot['D'] * .8 * 30,
               'browser_executable': os.environ.get('VIDEO_RENDER_BROWSER')}
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(request))
    output = tmp_path / 'frames'
    run = subprocess.run(['node', str(ROOT / 'scripts/video_render/render-frames.mjs'), str(path), str(output)],
                         capture_output=True, text=True, timeout=45)
    assert run.returncode == 0, run.stdout + run.stderr
    boxes = json.loads((output / 'boxes.json').read_text())
    by_id = {row['id']: row for row in boxes}
    assert not {'hidden-opacity', 'hidden-parent', 'hidden-display', 'hidden-size'} & by_id.keys()
    assert by_id['b1']['name'] == '「约 50%」柱子'
    assert by_id['b2']['name'] == '「约 25%」柱子'
    assert by_id['long-text']['name'] == '「一二三四五六七八九十甲乙」'
    assert by_id['empty-shape']['name'] == f'第 {boxes.index(by_id["empty-shape"]) + 1} 块'
    for sid in ('b1', 'b2'):
        rect = by_id[sid]
        assert rect['w'] == 280 and rect['h'] > 0
        assert 0 <= rect['x'] < 1080 and 0 <= rect['y'] < 1920
    assert by_id['b1']['h'] == pytest.approx(2 * by_id['b2']['h'])


def test_local_render_stores_boxes_and_three_review_frames(tmp_path):
    folder = tmp_path / 'shots'
    folder.mkdir()
    (folder / '01.html').write_text('''<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="moving" style="position:absolute;width:100px;height:100px">图形</div>
<script>window.seekFrame=(f,fps)=>{document.getElementById('moving').style.left=(f*10)+'px';};</script></body></html>''')
    media = LocalMedia()
    media.render(tmp_path, {'shotId': '01', 'estimatedSeconds': .2, 'measuredSeconds': None})
    boxes = json.loads((tmp_path / 'boxes/01.json').read_text())
    assert boxes[0]['x'] == 40  # floor(.8 * 6) = frame 4
    images = media.review_frames(tmp_path, {'shotId': '01'})
    assert len(images) == 3 and all(p.is_file() for p in images)
    from PIL import Image
    for path in images:
        with Image.open(path) as image:
            assert min(image.size) <= 360
