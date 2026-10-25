#!/usr/bin/env python3
"""把 direct.html 的每个状态导出成 design-states.html，再生成文案表和设计编号合同 contract.json。

用法（仓库根目录）：uv run --with playwright python docs/tasks/R276-direct-video-opus/design/export_states.py
依赖 Harness Engineering Core 的 check_design_contract.py（环境变量 HARNESS_CORE 可改位置）。
"""
import asyncio, html, os, subprocess, sys
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
PAGE = (HERE / 'direct.html').as_uri()
EXTRACTOR = Path(os.environ.get('HARNESS_CORE', '~/Desktop/Opensource_Tool/Harness_Engineering/Core')).expanduser() / 'skills/ui-copy-quality/scripts/check_design_contract.py'
COLLECT = """() => { const app = document.querySelector('#app').cloneNode(true);
  app.querySelectorAll('iframe').forEach(n => { n.removeAttribute('srcdoc'); n.removeAttribute('title'); });
  app.querySelectorAll('pre').forEach(n => n.textContent = '');   // 代码是设计数据，不是文案
  return app.innerHTML; }"""


async def main() -> None:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
        except Exception:
            browser = await p.chromium.launch(channel='chrome')
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto(PAGE + '#s=empty&chrome=0')
        states = await page.evaluate('() => STATES')
        parts = []
        for key, _label in states:
            await page.evaluate(f"() => {{ location.hash = 's={key}&chrome=0'; }}")
            await page.wait_for_timeout(300)
            parts.append(f'<section data-design-state="{html.escape(key)}">{await page.evaluate(COLLECT)}</section>')
        await browser.close()
    out = HERE / 'design-states.html'
    out.write_text('<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><title>脚本直出 · 逐状态导出</title></head><body>\n' + '\n'.join(parts) + '\n</body></html>\n', encoding='utf-8')
    subprocess.run([sys.executable, str(EXTRACTOR), 'extract', str(out), '--out', str(HERE / 'contract.json')], check=True)
    print('导出', len(parts), '个状态 →', out.name, '和 contract.json')


asyncio.run(main())
