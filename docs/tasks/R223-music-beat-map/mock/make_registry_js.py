"""把仓库根目录的 music-analysis.registry.json 转成设计稿能用 file:// 直接加载的 registry.js。
registry.js 是生成物，不要手改；改清单后重跑：python3 make_registry_js.py"""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
registry = json.loads((here.parents[3] / 'music-analysis.registry.json').read_text(encoding='utf-8'))
(here / 'registry.js').write_text(
    '// 由仓库根目录 music-analysis.registry.json 生成，不要手改；改清单后运行 make_registry_js.py。\n'
    f'window.MUSIC_REGISTRY={json.dumps(registry, ensure_ascii=False, separators=(",", ":"))};\n', encoding='utf-8')
