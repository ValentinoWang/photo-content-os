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

if __package__:
    from .constants import (
        FORBIDDEN,
        HALF_PUNCT,
    )
else:
    try:
        from scripts.direct_video.constants import (
            FORBIDDEN,
            HALF_PUNCT,
        )
    except ImportError:
        from constants import (
            FORBIDDEN,
            HALF_PUNCT,
        )


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


def _px_declarations(declarations: str) -> dict[str, float | None]:
    values = {}
    for declaration in declarations.split(';'):
        name, separator, value = declaration.partition(':')
        if separator:
            match = re.fullmatch(r'(-?\d+(?:\.\d+)?)px', value.strip(), re.I)
            values[name.strip().lower()] = float(match[1]) if match else None
    return values


def _canvas_size(style_blocks: list[str], roots: list[dict]) -> tuple[float, float] | None:
    dimensions = {'width': set(), 'height': set()}
    root_styles = [attrs.get('style') or '' for attrs in roots]
    for sheet in style_blocks:
        sheet = re.sub(r'/\*.*?\*/', '', sheet, flags=re.S)
        for selector, declarations in re.findall(r'([^{}]+)\{([^{}]*)\}', sheet):
            if {'html', 'body'} & {part.strip().lower() for part in selector.split(',')}:
                root_styles.append(declarations)
    for declarations in root_styles:
        styles = _px_declarations(declarations)
        for name, values in dimensions.items():
            if name in styles:
                values.add(styles[name])
    if any(len(values) != 1 for values in dimensions.values()):
        return None
    width, height = (next(iter(values)) for values in dimensions.values())
    if any(value is None or not math.isfinite(value) or value <= 0 for value in (width, height)):
        return None
    return width, height


def _seconds(value: str | None) -> float | None:
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _interval(value: str) -> tuple[float, float] | None:
    start, _, end = value.partition('-')
    start, end = _seconds(start), _seconds(end)
    return (start, end) if start is not None and end is not None and end > start else None


class _ShotMarkup(HTMLParser):
    def __init__(self, boxed_classes):
        super().__init__()
        self.spans, self.hidden, self.marks = [], [], set()
        self.boxed_classes = boxed_classes
        self.roots, self.aesthetic_elements = [], []
        self.body = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'html', 'body'}:
            self.roots.append(attrs)
        if tag == 'body':
            self.body = attrs
        if {'data-motion-easing', 'data-key-landed', 'data-subtitle-safe'} & attrs.keys():
            self.aesthetic_elements.append(attrs)
        if tag == 'span':
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


def _aesthetic_warnings(markup: _ShotMarkup, duration: float, height: float | None) -> list[dict]:
    warnings = []

    def warn(code, message):
        if not any(item['code'] == code for item in warnings):
            warnings.append({'code': code, 'message': message})

    body = markup.body
    hold_spec = body.get('data-hold') or ''
    holds = [_interval(part) for part in hold_spec.split(',')] if hold_spec else []
    pauses = [interval for interval in holds if interval is not None]
    epsilon = 1e-6
    if 'data-batch-entrance' in body and (len(pauses) != len(holds) or not any(
        end + epsilon >= duration and duration - start >= 0.5 - epsilon for start, end in pauses
    )):
        warn('aesthetic_r2_tail_hold', 'R2：请把收尾停顿留到切镜，至少停半秒，并核对停顿区间。')
    if 'data-opening-arc' in body:
        opening = _interval(body.get('data-opening-arc') or '')
        if opening is None or min(opening[1], duration) - opening[0] < 3 - epsilon:
            warn('aesthetic_r3_opening_arc', 'R3：请给开场主体的完整动作至少三秒。')

    for attrs in markup.aesthetic_elements:
        if 'data-key-landed' in attrs:
            settled = _seconds(attrs.get('data-motion-end'))
            if settled is None or not any(
                start <= settled + epsilon and min(end, duration) - settled >= 1 - epsilon
                for start, end in pauses
            ):
                warn('aesthetic_r1_key_hold', 'R1：关键信息或字标落定后请静止至少一秒，并核对落定时刻。')
        if (attrs.get('data-motion-easing') or '').strip().lower() == 'linear':
            warn('aesthetic_r2_linear_motion', 'R2：飞入或滚动请使用非线性缓动。')
        if 'data-subtitle-safe' in attrs and height is not None:
            box = _px_declarations(attrs.get('style') or '')
            top, size = box.get('top'), box.get('height')
            if top is None or size is None or not math.isfinite(top + size) or size <= 0:
                warn('subtitle_safe_zone', '字幕安全区：标记的固定内容需要在行内样式声明像素位置和高度。')
            elif top + size > height * 0.8 + epsilon:
                warn('subtitle_safe_zone', '字幕安全区：请把标记的文字和关键图形移出画面底部五分之一。')
    return warnings


def lint(code: str, dialogue: str, duration: float, canvas: tuple[int, int] | None = None) -> dict:
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
    markup = _ShotMarkup(boxed_classes)
    markup.feed(code)
    if markup.marks:
        error('punctuation_unboxed', '问号和感叹号请放在全角居中的文字框中。')
    for number in sorted(set(re.findall(r'\d+(?:\.\d+)?%?', visible_text(code)))):
        if number not in dialogue and not re.fullmatch(r'\d{1,2}|(?:19|20)\d\d', number):
            warnings.append({'code': 'number_unspoken', 'message': f'画面数字 {number} 未出现在本镜口播，请核对出处和数量。'})
    expected = canvas
    canvas = _canvas_size(style_blocks, markup.roots)
    if canvas is None:
        error('canvas_size_unreadable', '读不到画布尺寸，请在 html 或 body 声明明确的像素宽和高。')
    elif expected is not None and (round(canvas[0]), round(canvas[1])) != tuple(expected):
        error('canvas_size_mismatch', f'画布必须是 {expected[0]}×{expected[1]}，按这个尺寸重新排版。')
    warnings.extend(_aesthetic_warnings(markup, duration, canvas[1] if canvas else None))
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
