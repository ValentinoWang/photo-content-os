"""来源：用户技能 direct-video-shots/scripts/lint_shots.py。

规则部分借自 HeyGen HyperFrames（Apache-2.0）。静态检查不代替视觉审片。
"""
from __future__ import annotations

import argparse
import json
import math
from html.parser import HTMLParser
from pathlib import Path
import re

FORBIDDEN = ('Math.random', 'setTimeout', 'setInterval', 'requestAnimationFrame',
             'fetch(', 'XMLHttpRequest', 'WebSocket', '<video', '<audio', '@import', 'url(')
HALF_PUNCT = re.compile(r'(?<=[一-鿿])[?!,:;]|[?!,:;](?=[一-鿿])')


def visible_text(html: str, sep: str = ' ') -> str:
    html = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    return re.sub(r'<[^>]+>', sep, html)


def declared_seconds(code: str) -> float | None:
    match = re.search(r'\bconst\s+D\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*[;,]', code)
    return float(match[1]) if match else None


def _centered_box(declarations: str) -> bool:
    styles = dict(part.strip().lower().split(':', 1) for part in declarations.split(';') if ':' in part)
    styles = {k.strip(): v.strip() for k, v in styles.items()}
    return styles.get('width') == '1em' and styles.get('text-align') == 'center' and styles.get('display') in {'inline-block', 'block'}


class _Punctuation(HTMLParser):
    def __init__(self, boxed_classes):
        super().__init__()
        self.spans, self.hidden, self.marks = [], [], set()
        self.boxed_classes = boxed_classes

    def handle_starttag(self, tag, attrs):
        if tag == 'span':
            attrs = dict(attrs)
            classes = set((attrs.get('class') or '').split())
            self.spans.append(bool(classes & (self.boxed_classes | {'fw'})) or _centered_box(attrs.get('style') or ''))
        if tag in {'script', 'style'}:
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if tag == 'span' and self.spans:
            self.spans.pop()
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_data(self, data):
        if not self.hidden and not any(self.spans):
            self.marks.update(re.findall(r'[？！]', data))


def lint(code: str, dialogue: str, duration: float) -> dict:
    errors, warnings = [], []

    def error(key, message):
        errors.append({'code': key, 'message': message})

    if not code.lower().startswith('<!doctype html>'):
        error('doctype_missing', '代码必须以 HTML 文档声明开头。')
    if len(code) >= 100000:
        error('code_too_large', '这一镜的代码必须少于十万字。')
    if 'window.seekFrame' not in code:
        error('seek_frame_missing', '缺少逐帧绘制入口。')
    if not re.search(r'data-role\s*=\s*[\'"]header[\'"]', code):
        error('header_missing', '页眉必须包在带有页眉标记的元素里。')
    for token in FORBIDDEN:
        if token.lower() in code.lower():
            error('forbidden_runtime', f'请移除渲染器不支持的写法：{token}。')
    # SVG namespace URIs are identifiers, not resource loads.
    resources = re.sub(r'xmlns(?::\w+)?\s*=\s*[\'"][^\'"]*[\'"]', '', code)
    external_attribute = re.search(r'\b(?:src|href)\s*=\s*[\'"](?:https?://|//|/|file:)', resources, re.I)
    # createElementNS also takes these standard namespace identifiers. They
    # do not load a resource; src/href and network APIs remain prohibited.
    identifiers_removed = re.sub(r'([\'"])http://www\.w3\.org/(?:2000/svg|1999/xlink)\1', '""', resources)
    if external_attribute or re.search(r'https?://', identifiers_removed, re.I):
        error('external_resource', '请移除外部资源，使用单文件内联图形。')
    d = declared_seconds(code)
    if d is None or not math.isfinite(d) or d <= 0:
        error('duration_missing', '请声明有效的这一镜时长常量。')
    elif duration < 0.7 * d - 1e-6:
        errors.append({'code': 'animation_cut_short', 'message': '动画长于实际镜头，请按实测时长重排。', 'atSeconds': duration})
    elif abs(duration - d) > 0.05:
        warnings.append({'code': 'duration_differs', 'message': '代码时长与这一镜时长不同，请核对节奏。'})
    tight = re.sub(r'\s+', '', visible_text(code, ''))
    if HALF_PUNCT.search(tight):
        error('half_width_punctuation', '中文相邻标点请使用全角。')
    style_blocks = re.findall(r'<style\b[^>]*>(.*?)</style>', code, re.S | re.I)
    boxed_classes = {name for css in style_blocks for name, declarations in re.findall(r'\.([\w-]+)\s*\{([^{}]*)\}', css) if _centered_box(declarations)}
    punctuation = _Punctuation(boxed_classes)
    punctuation.feed(code)
    if punctuation.marks:
        error('punctuation_unboxed', '问号和感叹号请放在全角居中的文字框中。')
    for number in sorted(set(re.findall(r'\d+(?:\.\d+)?%?', visible_text(code)))):
        if number not in dialogue and not re.fullmatch(r'\d{1,2}|(?:19|20)\d\d', number):
            warnings.append({'code': 'number_unspoken', 'message': f'画面数字 {number} 未出现在本镜口播，请核对出处和数量。'})
    return {'errors': errors, 'warnings': warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots_dir', type=Path)
    parser.add_argument('--storyboard', type=Path)
    parser.add_argument('--durations', type=Path)
    args = parser.parse_args()
    try:
        files = sorted(args.shots_dir.glob('[0-9][0-9].html'))
        if not files:
            raise ValueError('没有可检查的镜头文件。')
        dialogue = {s['shotId']: s['dialogue'] for s in json.loads(args.storyboard.read_text())['shots']} if args.storyboard else {}
        data = json.loads(args.durations.read_text()) if args.durations else {}
        durations = data.get('seconds') or {k: v / data['fps'] for k, v in data.get('frames', {}).items()}
        results = {}
        for file in files:
            code = file.read_text(encoding='utf-8')
            if args.durations and file.stem not in durations:
                raise ValueError('时长文件缺少镜头。')
            results[file.stem] = lint(code, dialogue.get(file.stem, ''), durations.get(file.stem, declared_seconds(code) or 0))
        print(json.dumps(results, ensure_ascii=False))
        return int(any(r['errors'] for r in results.values()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'errors': [{'code': 'input_invalid', 'message': str(exc)}]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
