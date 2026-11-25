"""Generate a resumable, labelled avatar clip with DashScope videoretalk."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

BASE = 'https://dashscope.aliyuncs.com/api/v1'
TIMEOUT = (10, 60)


class AvatarError(Exception):
    pass


def fail(code):
    raise AvatarError(code)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        name = f.name
        try:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            os.unlink(name)
            raise
    os.replace(name, path)


def command(args):
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        fail('avatar_input_invalid')


def duration(path):
    try:
        value = float(command(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]).stdout.strip())
        if not 0 < value < float('inf'):
            raise ValueError()
        return value
    except ValueError:
        fail('avatar_input_invalid')


def plan_audio(audio, maximum):
    total = duration(audio)
    if total <= maximum:
        return total, [{'start': 0.0, 'end': total, 'cut': 'end'}]
    output = command(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(audio), '-af', 'silencedetect=noise=-35dB:d=0.25', '-f', 'null', '-']).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', output)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', output)]
    intervals = list(zip(starts, ends))
    if len(starts) > len(ends):
        intervals.append((starts[-1], total))
    segments = []
    start = 0.0
    while total - start > maximum:
        lower = start + min(90, maximum * 0.8)
        upper = start + maximum
        choices = [(min(b, upper) - max(a, lower), (max(a, lower) + min(b, upper)) / 2) for a, b in intervals if min(b, upper) > max(a, lower)]
        end = max(choices)[1] if choices else upper
        segments.append({'start': start, 'end': end, 'cut': 'silence' if choices else 'hard'})
        start = end
    segments.append({'start': start, 'end': total, 'cut': 'end'})
    return total, segments


class Client:
    def __init__(self, key, transport=None):
        self.key = key
        self.http = transport or requests.Session()

    def upload(self, path):
        try:
            r = self.http.get(BASE + '/uploads', params={'action': 'getPolicy', 'model': 'videoretalk'}, headers={'Authorization': 'Bearer ' + self.key}, timeout=TIMEOUT)
            r.raise_for_status()
            p = r.json()['data']
            key = p['upload_dir'] + '/' + path.name
            fields = {'OSSAccessKeyId': p['oss_access_key_id'], 'Signature': p['signature'], 'policy': p['policy'], 'x-oss-object-acl': p['x_oss_object_acl'], 'x-oss-forbid-overwrite': p['x_oss_forbid_overwrite'], 'key': key, 'success_action_status': '200'}
            with path.open('rb') as f:
                r = self.http.post(p['upload_host'], data=fields, files={'file': (path.name, f)}, timeout=TIMEOUT)
                r.raise_for_status()
            return 'oss://' + key
        except Exception:
            fail('avatar_upload_failed')

    def submit(self, video, audio):
        try:
            r = self.http.post(BASE + '/services/aigc/image2video/video-synthesis', headers={'Authorization': 'Bearer ' + self.key, 'X-DashScope-Async': 'enable', 'X-DashScope-OssResourceResolve': 'enable'}, json={'model': 'videoretalk', 'input': {'video_url': video, 'audio_url': audio, 'ref_image_url': ''}, 'parameters': {'video_extension': True}}, timeout=TIMEOUT)
        except requests.RequestException:
            fail('avatar_submit_unknown')
        if not r.ok:
            fail('avatar_submit_failed')
        try:
            return r.json()['output']['task_id'] or fail('avatar_submit_unknown')
        except (ValueError, KeyError, TypeError):
            fail('avatar_submit_unknown')

    def poll(self, task_id, deadline):
        while time.monotonic() < deadline:
            try:
                r = self.http.get(BASE + '/tasks/' + task_id, headers={'Authorization': 'Bearer ' + self.key}, timeout=TIMEOUT)
                r.raise_for_status()
                output = r.json()['output']
                status = output['task_status']
            except Exception:
                fail('avatar_task_failed')
            if status == 'SUCCEEDED':
                return output.get('video_url', '')
            if status not in ('PENDING', 'RUNNING'):
                fail('avatar_task_failed')
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        fail('avatar_timeout')

    def download(self, url, target):
        try:
            u = urlsplit(url)
            host = u.hostname or ''
            if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or not host.startswith('dashscope-') or '.oss-' not in host or not host.endswith('.aliyuncs.com'):
                fail('avatar_result_url_invalid')
        except ValueError:
            fail('avatar_result_url_invalid')
        try:
            r = self.http.get(url, timeout=TIMEOUT, stream=True, allow_redirects=False)
            r.raise_for_status()
            if not 200 <= r.status_code < 300:
                fail('avatar_download_failed')
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
                name = f.name
                try:
                    for chunk in r.iter_content(1024 * 1024):
                        f.write(chunk)
                except BaseException:
                    os.unlink(name)
                    raise
            os.replace(name, target)
        except AvatarError:
            raise
        except Exception:
            fail('avatar_download_failed')


def generate_avatar_clip(video: Path, audio: Path, out_dir: Path, *, material: str, owner_consent: str | None, api_key: str, live: bool, max_seconds: float = 110, wait_seconds: float = 900, transport=None) -> dict:
    video, audio, out_dir = Path(video), Path(audio), Path(out_dir)
    if not video.is_file() or not audio.is_file() or material not in ('self', 'public-sample') or (material == 'self' and not (owner_consent or '').strip()) or not 0 < max_seconds < 120 or not 0 < wait_seconds:
        fail('avatar_input_invalid')
    duration(video)
    total, segments = plan_audio(audio, max_seconds)
    result = {'segments': segments, 'total_seconds': total, 'estimated_yuan': round(total * 0.08, 2)}
    if not live:
        return result
    if not api_key:
        fail('avatar_api_key_missing')
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / 'avatar-ledger.json'
    if ledger_path.exists():
        try:
            ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
            old = ledger['segments']
            if not isinstance(old, list):
                raise ValueError()
        except (ValueError, KeyError, OSError, TypeError):
            fail('avatar_input_invalid')
    else:
        old = []
    ledger = {'model': 'videoretalk', 'material': material, 'owner_consent': owner_consent if material == 'self' else None, 'updated_at': utc(), 'segments': []}
    client = Client(api_key, transport)
    video_hash = digest(video)
    params_hash = hashlib.sha256(json.dumps({'model': 'videoretalk', 'video_extension': True, 'max_seconds': max_seconds}, sort_keys=True).encode()).hexdigest()
    deadline = time.monotonic() + wait_seconds
    with tempfile.TemporaryDirectory(prefix='avatar-audio-') as tmp:
        for index, seg in enumerate(segments):
            part = Path(tmp) / f'audio-{index:04d}.wav'
            command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(seg['start']), '-i', str(audio), '-t', str(seg['end'] - seg['start']), '-c:a', 'pcm_s16le', str(part)])
            identity = {'audio_sha256': digest(part), 'video_sha256': video_hash, 'parameters_sha256': params_hash}
            previous = old[index] if index < len(old) else {}
            row = dict(previous) if all(previous.get(k) == v for k, v in identity.items()) else {}
            row.update(identity, **seg)
            ledger['segments'].append(row)
            # Preserve untouched later rows until they are processed; a crash must not erase their task IDs.
            def save():
                ledger['updated_at'] = utc()
                snapshot = dict(ledger, segments=ledger['segments'] + old[len(ledger['segments']):])
                write_json(ledger_path, snapshot)
            target = out_dir / f'segment-{index:04d}.mp4'
            if row.get('status') == 'completed' and target.is_file() and row.get('result_sha256') == digest(target):
                save()
                continue
            if row.get('status') == 'submitting' and not row.get('task_id'):
                fail('avatar_submit_unknown')
            if not row.get('task_id'):
                v = client.upload(video)
                a = client.upload(part)
                row.update(status='submitting', task_id=None)
                save()
                task_id = client.submit(v, a)
                row.update(task_id=task_id, status='submitted')
                save()
            url = client.poll(row['task_id'], deadline)
            client.download(url, target)
            row.update(status='completed', result_sha256=digest(target))
            save()
    # Remove obsolete rows once every current segment is accounted for.
    ledger['updated_at'] = utc()
    write_json(ledger_path, ledger)
    concat = out_dir / 'avatar.concat.txt'
    concat.write_text(''.join("file '" + str((out_dir / f'segment-{i:04d}.mp4').resolve()).replace("'", "'\\''") + "'\n" for i in range(len(segments))), encoding='utf-8')
    try:
        command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', '-metadata', 'comment=AI生成', str(out_dir / 'avatar.mp4')])
    finally:
        concat.unlink(missing_ok=True)
    write_json(out_dir / 'avatar.ai-label.json', {'model': 'videoretalk', 'segments': len(segments), 'total_seconds': total, 'generated_at': utc()})
    return result | {'output': str(out_dir / 'avatar.mp4')}
