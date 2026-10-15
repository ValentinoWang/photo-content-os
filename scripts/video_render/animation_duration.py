"""Inspect literal HTML animation durations without executing author scripts."""
from fractions import Fraction
from html.parser import HTMLParser
import math
from pathlib import Path
import re


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = dict(attrs).get('type', '').lower() in (
                '', 'module', 'text/javascript', 'application/javascript')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False
            self.parts.append(';')

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


# Comments and strings are tokens so text examples never become declarations.
_TOKENS = re.compile(r'''/\*[\s\S]*?\*/|//[^\r\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[\w$]+|[^\s]''')
_NUMBER = re.compile(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')


def declared_duration(html):
    """None means absent; unsupported/ambiguous D declarations are errors."""
    parser = _Scripts(); parser.feed(html)
    tokens = [t for t in _TOKENS.findall(''.join(parser.parts)) if not t.startswith(('//', '/*'))]
    found = []
    for index, token in enumerate(tokens):
        if token != 'const':
            continue
        position = index+1
        while position < len(tokens):
            name = tokens[position]; position += 1
            if position >= len(tokens) or tokens[position] != '=':
                if name == 'D':
                    raise ValueError('const D 缺少数值初始化')
                break
            position += 1; expression = []; depth = 0
            while position < len(tokens):
                token = tokens[position]
                if depth == 0 and token in (',', ';'):
                    break
                depth += int(token in ('(', '[', '{'))-int(token in (')', ']', '}'))
                expression.append(token); position += 1
            if name == 'D':
                value = ''.join(expression)
                if not re.fullmatch(r'[+-]?' + _NUMBER.pattern, value):
                    raise ValueError('const D 必须声明为正有限数值字面量')
                if not math.isfinite(float(value)) or float(value) <= 0:
                    raise ValueError('const D 必须声明为正有限数值字面量')
                found.append(Fraction(value))
            if position >= len(tokens) or tokens[position] != ',':
                break
            position += 1
    if len(found) > 1:
        raise ValueError('多个 const D 声明，无法确定动画时长')
    return found[0] if found else None


def animation_duration_checks(manifest):
    shots = []
    for shot in manifest['shots']:
        actual = Fraction(shot['frames'], manifest['fps'])
        entry = {'shotId': shot['id'], 'actualSeconds': float(actual), 'declaredSeconds': None, 'minimumSeconds': None}
        try:
            declared = declared_duration(Path(shot['html']).read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as error:
            entry.update(status='failed', code='animation_duration_invalid', reason=f"{shot['id']} 镜：无法读取/解析 const D：{error}")
        else:
            if declared is None:
                entry.update(status='not_declared', reason='未声明 const D，跳过时长检查')
            else:
                minimum = declared * Fraction(7, 10)
                entry.update(declaredSeconds=float(declared), minimumSeconds=float(minimum))
                if actual < minimum:
                    entry.update(status='failed', code='animation_duration_too_short',
                                 reason=f"{shot['id']} 镜：实际时长 {float(actual):.6f} 秒 < 0.7·D {float(minimum):.6f} 秒（D={float(declared):.6f}）；请按实测时长修订动画代码后重试")
                else:
                    entry.update(status='passed')
        shots.append(entry)
    status = 'failed' if any(s['status']=='failed' for s in shots) else 'partial' if any(s['status']=='not_declared' for s in shots) else 'passed'
    return {'status': status, 'minimumRatio': 0.7, 'shots': shots}
