"""Verbatim direct captions and legible rendering on the decoded frame clock."""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import platform
import unicodedata

from edit_backends.kdenlive_render import probe_media, review_module
from openclaw_product_contract import ProductContractError


def _reject():
    raise ProductContractError('photo_subtitle_projection_rejected')


def _rate(fps):
    try:
        rate = Fraction(str(fps))
        if rate <= 0:
            _reject()
        return rate
    except (ValueError, ZeroDivisionError, TypeError):
        _reject()


def _frame(seconds, rate):
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        _reject()
    return round(Fraction(str(seconds)) * rate)


def _chunks(text):
    if not isinstance(text, str) or not text.strip() or '\x00' in text:
        _reject()
    if len(text) <= 28:
        return [text]
    result, pending = [], ''
    # Retain punctuation and every spoken character. A clause without a comma
    # still needs bounded chunks to respect the two-line caption geometry.
    for clause in re.findall(r'[^，,]*[，,]|[^，,]+$', text):
        if pending and len(pending) + len(clause) > 28:
            result.append(pending); pending = ''
        while len(clause) > 28:
            result.append(clause[:28]); clause = clause[28:]
        pending += clause
    if pending:
        result.append(pending)
    if ''.join(result) != text:
        _reject()
    return result


def _lines(text):
    # Raw cue text is retained separately. Only the burnt display omits these
    # terminal marks; timing and the returned spoken text must not change.
    flat = text.replace('\r', '').replace('\n', '').rstrip('。，')
    forbidden_start = '。，、：；！？」）,.!?;:)]}》】”’'
    forbidden_end = '（「《【“‘([{'
    if not flat or flat[0] in forbidden_start:
        _reject()
    if len(flat) <= 14:
        return [flat]
    candidates = []
    for split in range(max(1, len(flat)-14), min(14, len(flat)-1)+1):
        first, second = flat[:split], flat[split:]
        if (abs(len(first)-len(second)) > 4 or second[0] in forbidden_start
            or first[-1] in forbidden_end
            or any(sum(not unicodedata.category(ch).startswith('P') and not ch.isspace()
                       for ch in line) < 4 for line in [first, second])):
            continue
        candidates.append((not unicodedata.category(first[-1]).startswith('P'),
                           abs(len(first)-len(second)), split))
    if not candidates:
        _reject()
    split = min(candidates)[2]
    return [flat[:split], flat[split:]]


def _cut_fragments(text, bounds):
    """Partition at frame cuts without orphaning punctuation or spoken text."""
    count = len(bounds)-1

    @lru_cache(None)
    def partition(index, offset):
        if index == count-1:
            try:
                _lines(text[offset:])
                return (text[offset:],)
            except ProductContractError:
                return None
        target = len(text)*(bounds[index+1]-bounds[0])/(bounds[-1]-bounds[0])
        choices = sorted(range(offset+1, len(text)-(count-index-1)+1), key=lambda n: (abs(n-target), n))
        for end in choices:
            piece = text[offset:end]
            try:
                _lines(piece)
            except ProductContractError:
                continue
            tail = partition(index+1, end)
            if tail is not None:
                return (piece, *tail)
        return None

    # Very short text cannot always be divided into valid display fragments.
    # Repeat it as a new cue per shot rather than discard speech coverage.
    return partition(0, 0) or (text,)*count


def _plan(spans, cuts, rate, total_frames):
    if type(total_frames) is not int or total_frames < 2:
        _reject()
    result, previous_end = [], 0
    for start, end, text in spans:
        if not isinstance(text, str):
            _reject()
        text = text.replace('\r', '').replace('\n', '')
        start_frame, end_frame = _frame(start, rate), _frame(end, rate)
        if end <= start or start_frame < previous_end:
            _reject()
        parts = _chunks(text); cursor = 0
        for part in parts:
            a = _frame(start + (end-start)*cursor/len(text), rate)
            cursor += len(part)
            b = _frame(start + (end-start)*cursor/len(text), rate)
            b = min(b, total_frames-1)
            if b <= a or (result and a < result[-1]['endFrame']):
                _reject()
            bounds = [a, *[cut for cut in cuts if a < cut < b], b]
            for left, right, fragment in zip(bounds, bounds[1:], _cut_fragments(part, bounds)):
                # Exclusive ends retire the previous cue at the cut; its
                # remaining text starts as a new cue on the very next frame.
                result.append({'startFrame': left, 'endFrame': right, 'text': fragment, 'lines': _lines(fragment)})
        previous_end = end_frame
    if not result:
        _reject()
    return result


def build_subtitle_cues(descriptor, *, fps, total_frames):
    rate = _rate(fps)
    cuts = sorted({_frame(row['shot']['endSeconds'], rate) for row in descriptor['shots']})
    narration = descriptor.get('narration')
    timings = narration.get('sentenceTimings') if isinstance(narration, dict) else None
    if timings is not None and not isinstance(timings, list):
        _reject()
    if timings:
        spans = [(t['startSeconds'], t['endSeconds'], t['text']) for t in timings]
        if descriptor.get('script') is not None:
            spoken = ''.join(t[2] for t in spans)
            if ''.join(spoken.split()) != ''.join(descriptor['script'].split()):
                _reject()
    else:
        spans = [(r['shot']['startSeconds'], r['shot']['endSeconds'], r['subtitle'])
                 for r in descriptor['shots'] if r['subtitle']]
    return _plan(spans, cuts, rate, total_frames)


def _srt_stamp(frame, rate):
    # SRT has only millisecond precision. Round down for export; rendering uses
    # the exact frame sidecar, so neither SRT nor ASS rounding controls a cut.
    ms = int(Fraction(frame * 1000, 1) / rate)
    seconds, ms = divmod(ms, 1000); minutes, seconds = divmod(seconds, 60); hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def write_direct_subtitles(descriptor, path, *, fps, total_frames):
    rate = _rate(fps); cues = build_subtitle_cues(descriptor, fps=fps, total_frames=total_frames)
    body = '\n\n'.join(f"{i+1}\n{_srt_stamp(c['startFrame'],rate)} --> {_srt_stamp(c['endFrame'],rate)}\n" + c['text'] for i,c in enumerate(cues)) + '\n'
    path.write_text(body, encoding='utf-8')
    sidecar = {'schemaVersion': 'photo.video.subtitles.frames.v1', 'rate': [rate.numerator, rate.denominator],
               'totalFrames': total_frames, 'subtitleSha256': hashlib.sha256(body.encode()).hexdigest(),
               'source': 'narration' if (descriptor.get('narration') or {}).get('sentenceTimings') else 'storyboard', 'cues': cues}
    path.with_suffix('.frames.json').write_text(json.dumps(sidecar, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return cues


def subtitle_style(width, height):
    scale = width / 1080
    padding = max(1, round(16*scale)); spacing = max(1, round(12*scale))
    # Portrait 1080x1920 uses 64px. Small/landscape derivatives must also keep
    # both lines and the backplate inside their bottom fifth.
    size = max(1, min(round(64*scale), math.floor((height*.2-2*padding-spacing)/3)))
    return {'fontSize': size, 'boxOpacity': .75, 'padding': padding, 'lineSpacing': spacing,
            'maxLineChars': 14, 'maxLines': 2, 'sideMargin': math.ceil(72*scale), 'bottomRatio': .8}


def _render_cues(subtitles, rate, total_frames):
    sidecar = subtitles.with_suffix('.frames.json')
    if sidecar.exists():
        data = json.loads(sidecar.read_text(encoding='utf-8'))
        if (data.get('schemaVersion') != 'photo.video.subtitles.frames.v1' or data.get('rate') != [rate.numerator,rate.denominator]
            or data.get('totalFrames') != total_frames or data.get('subtitleSha256') != hashlib.sha256(subtitles.read_bytes()).hexdigest()):
            _reject()
        cues = data['cues']
    else:
        spans = review_module().read_srt_cues(subtitles)
        cues = _plan(spans, [], rate, total_frames)
    previous_end = 0
    for c in cues:
        if (type(c['startFrame']) is not int or type(c['endFrame']) is not int
            or not previous_end <= c['startFrame'] < c['endFrame'] <= total_frames-1 or c['lines'] != _lines(c['text'])):
            _reject()
        previous_end = c['endFrame']
    return cues


def _caption_font():
    # Fontconfig can silently resolve an unavailable CJK family to Latin-only
    # Verdana. Bind a real CJK font file so Chinese never becomes tofu boxes.
    candidates = ([Path('/System/Library/Fonts/STHeiti Medium.ttc')] if platform.system() == 'Darwin' else []) + [
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf'),
        Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')]
    for path in candidates:
        if path.is_file():
            return path
    _reject()


def burn_subtitles(video: Path, subtitles: Path, output: Path) -> float:
    stream = next(s for s in probe_media(video)['streams'] if s['codec_type']=='video')
    width, height = stream['width'], stream['height']; rate = _rate(stream['avg_frame_rate'])
    total_frames = int(stream.get('nb_frames') or round(Fraction(stream['duration']) * rate))
    cues = _render_cues(subtitles, rate, total_frames); style = subtitle_style(width,height)
    with tempfile.TemporaryDirectory(prefix='photo-subtitles-') as directory:
        root = Path(directory); filters = []
        (root/'caption-font.ttc').symlink_to(_caption_font())
        for index,cue in enumerate(cues):
            textfile = f'cue-{index:04}.txt'
            (root/textfile).write_text('\n'.join(cue['lines']),encoding='utf-8')
            filters.append(f"drawtext=fontfile=caption-font.ttc:textfile={textfile}:expansion=none:fontsize={style['fontSize']}:fontcolor=white:"
                           f"text_align=M+C:box=1:boxcolor=black@{style['boxOpacity']}:boxborderw={style['padding']}:line_spacing={style['lineSpacing']}:"
                           f"x=(w-text_w)/2:y=h*0.9-text_h/2:enable='gte(n,{cue['startFrame']})*lt(n,{cue['endFrame']})'")
        (root/'captions.filters').write_text('[0:v]'+','.join(filters)+'[captioned]', encoding='utf-8')
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-v','error','-xerror','-y','-i',str(video),
                        '-filter_complex_script','captions.filters','-map','[captioned]','-map','0:a:0',
                        '-c:v','libx264','-threads','1','-crf','18','-pix_fmt','yuv420p','-c:a','copy',
                        '-map_metadata','-1','-movflags','+faststart',str(output)],cwd=root,capture_output=True,timeout=1800,check=True)
    output.with_suffix('.subtitle-style.json').write_text(json.dumps(style,indent=2)+'\n')
    return .8
