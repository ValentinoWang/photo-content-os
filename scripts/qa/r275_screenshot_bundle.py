#!/usr/bin/env python3
"""Stitch captured R275 dialog content and link the original, unmodified screenshots."""
import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import hashlib
import html
import json
from pathlib import Path
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--images', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
images, evidence = args.images.resolve(), args.evidence.resolve()
assert not images.is_relative_to(Path(__file__).resolve().parents[2]), 'raster evidence must stay outside the repository'
manifest = json.loads((evidence / 'screenshot-manifest.json').read_text())
coverage = json.loads((evidence / 'dialog-scroll-coverage.json').read_text())
m = coverage['metrics']; scale = m['dpr']
canvas = Image.new('RGB', (round(m['width'] * scale), round(m['total'] * scale)))
end = 0
sources = []
for index, offset in enumerate(coverage['offsets'], 1):
    assert offset <= end, 'gap in captured dialog coverage'
    source = images / f'confirm-eight-part-{index}.png'
    frame = Image.open(source).convert('RGB')
    skip = max(0, end - offset)
    finish = m['total'] if index == len(coverage['offsets']) else min(offset + m['height'] - 12, m['total'])
    if finish > end:
        x, y = round(m['x'] * scale), round((m['y'] + skip) * scale)
        clip = frame.crop((x, y, x + canvas.width, y + round((finish - end) * scale)))
        canvas.paste(clip, (0, round(end * scale)))
        end = finish
    sources.append({'file': source.name, 'offset': offset, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
assert end == m['total'], 'dialog bottom was not captured'
combined = images / 'confirm-eight-list-complete.png'
canvas.save(combined)
manifest['screenshots'] = [s for s in manifest['screenshots'] if s['state'] != 'confirm-eight-list-complete']
manifest['screenshots'].append({'state': 'confirm-eight-list-complete', 'path': str(combined), 'output_dimensions': {'width': canvas.width, 'height': canvas.height}, 'sha256': hashlib.sha256(combined.read_bytes()).hexdigest(), 'coverage': 'complete scrollable dialog list, top to bottom', 'derived_from': sources})
# A fixed toolbar can cover middle rows in Chromium fullPage output. Use real scrolled
# viewport frames, placing the final toolbar only in the bottom padding of the page.
phone = json.loads((evidence / 'phone-scroll-coverage.json').read_text())
pm = phone['metrics']; ps = pm['dpr']; phone_end = 0; phone_sources = []
phone_canvas = Image.new('RGB', (780, round(pm['total'] * ps)))
for index, offset in enumerate(phone['offsets'], 1):
    source = images / f'selection-390-scroll-{index}.png'
    frame = Image.open(source).convert('RGB')
    assert offset <= phone_end
    last = index == len(phone['offsets'])
    finish = pm['total'] if last else min(pm['total'], offset + int(pm['bar_top']) - 48)
    assert finish >= phone_end
    clip = frame.crop((0, round((phone_end-offset)*ps), frame.width, round((finish-offset)*ps)))
    phone_canvas.paste(clip, (0, round(phone_end*ps)))
    phone_end = finish
    phone_sources.append({'file': source.name, 'offset': offset, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
assert phone_end == pm['total']
phone_file = images / 'selection-390-full.png'; phone_canvas.save(phone_file)
for item in manifest['screenshots']:
    if item['path'] == str(phone_file):
        item.update(sha256=hashlib.sha256(phone_file.read_bytes()).hexdigest(), derived_from=phone_sources,
                    coverage='complete real 390px page from overlapping viewport frames; fixed toolbar appears once in bottom padding')
states = ['pick-other', 'confirm-other', 'deleted-other', 'partial-fail', 'confirm-lzu', 'projects-recent', 'recent']
for state in states:
    source = images / 'design' / f'{state}.png'
    assert source.is_file()
    manifest.setdefault('design_references', {})[state] = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
for item in manifest['screenshots']:
    source = Path(item['path'])
    assert source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == item['sha256']
(evidence / 'screenshot-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
rows = []
for state in states:
    rows.append(f'<section><h2>{html.escape(state)}</h2><div class="pair"><a href="design/{state}.png"><b>设计稿</b><img src="design/{state}.png"></a><a href="{state}.png"><b>实现</b><img src="{state}.png"></a></div></section>')
extras = [item for item in manifest['screenshots'] if item['state'] not in states]
rows.append('<section><h2>边界状态与手机完整页面</h2><div class="extras">' + ''.join(f'<a href="{html.escape(Path(item["path"]).name)}">{html.escape(item["state"])}<img src="{html.escape(Path(item["path"]).name)}"></a>' for item in extras) + '</div></section>')
gallery = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>删除作品 · 阶段 B 对照</title><style>body{font:15px system-ui;background:#f3f5f8;color:#17232b;margin:24px}h1{font-size:24px}h2{font-size:17px}section{margin:28px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.extras{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}a{display:block;color:inherit;overflow-wrap:anywhere}img{display:block;width:100%;height:auto;margin-top:8px;border:1px solid #b8c4cb}@media(max-width:700px){.pair{grid-template-columns:1fr}}</style><h1>删除作品 · 阶段 B 对照</h1><p>截图来自隔离临时数据。点击原图查看完整尺寸；编号图片为同一确认列表的连续滚动部分。</p>' + ''.join(rows)
(images / 'gallery.html').write_text(gallery)
print(json.dumps({'screenshots': len(manifest['screenshots']), 'references': len(states), 'stitched_dimensions': canvas.size, 'hashes_match': True, 'gallery': str(images / 'gallery.html')}, ensure_ascii=False))
