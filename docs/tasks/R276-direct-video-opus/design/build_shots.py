#!/usr/bin/env python3
"""把 R131 实跑时 Opus 写的 7 镜 HTML 打包成 shots-data.js，给设计稿预览用。

来源（上游仓库，只读）：自媒体创作Agent/docs/development/video-practice-hiatus/{storyboard.json,shots/NN.html}
用法：python3 build_shots.py [上游仓库根目录]
"""
import json, re, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'Desktop/创业项目/自媒体创作Agent').expanduser()
src = root / 'docs/development/video-practice-hiatus'
story = json.loads((src / 'storyboard.json').read_text(encoding='utf-8'))
shots = []
for s in story['shots']:
    html = (src / 'shots' / f"{s['shotId']}.html").read_text(encoding='utf-8')
    m = re.search(r'const\s+D\s*=\s*([0-9.]+)', html)
    shots.append({'shotId': s['shotId'], 'dialogue': s['dialogue'], 'visual': s.get('visual', ''),
                  'estimatedSeconds': s.get('estimatedSeconds'), 'D': float(m.group(1)) if m else s.get('estimatedSeconds'),
                  'html': html})
out = Path(__file__).with_name('shots-data.js')
out.write_text('// 生成文件：R131 实跑时 Opus 写的 7 镜代码（build_shots.py 生成，不手改）\nwindow.R131 = ' + json.dumps({'title': story['title'], 'shots': shots}, ensure_ascii=False) + ';\n', encoding='utf-8')
print(out, len(shots), sum(len(s['html']) for s in shots))
