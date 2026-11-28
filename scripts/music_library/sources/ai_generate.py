"""AI music generation via paid per-second APIs with persistent no-retry caching.

Official API references verified before implementation:
- WaveSpeed AI (ACE-Step 1.5):
  - Model page: https://wavespeed.ai/models/wavespeed-ai/ace-step-1.5
  - Machine-readable spec: https://wavespeed.ai/models/wavespeed-ai/ace-step-1.5/llms.txt
  - API docs: https://wavespeed.ai/docs/docs-api/wavespeed-ai/ace-step-1.5
- Alibaba Cloud Bailian / Model Studio (Fun-Music):
  - API reference: https://help.aliyun.com/zh/model-studio/fun-music-api
  - Model overview: https://help.aliyun.com/zh/model-studio/fun-music-v1
  - DashScope async tasks (fallback polling if server returns task_id):
    https://help.aliyun.com/zh/model-studio/manage-asynchronous-tasks
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from media import utc_now_iso as _now_iso
from ..cache import read_json, write_json
from ..errors import MusicError


# Official WaveSpeed ACE-Step 1.5 REST schema (llms.txt):
#   POST https://api.wavespeed.ai/api/v3/wavespeed-ai/ace-step-1.5
#   Body: {"tags": str, "lyrics": str, "duration": 5..240, "seed"?: int}
#   Poll: GET https://api.wavespeed.ai/api/v3/predictions/{id}/result
# Note: WaveSpeed REST input schema does not expose a standalone `bpm` field;
# BPM hints are appended to `tags` (e.g. "<prompt>, 100 bpm"). Instrumental mode
# uses `lyrics: "[inst]"` as specified in official llms.txt.
if __package__:
    from ..constants import (
        WAVESPEED_MODEL,
        WAVESPEED_SUBMIT_URL,
        WAVESPEED_POLL_URL,
        WAVESPEED_DOC_URL,
        BAILIAN_MODEL,
        BAILIAN_DEFAULT_SUBMIT_URL,
        BAILIAN_WORKSPACE_URL,
        BAILIAN_DOC_URL,
        DEFAULT_STT_ENV_PATH,
        AUDIO_EXTENSIONS,
        PROVIDERS,
    )
else:
    try:
        from scripts.music_library.constants import (
            WAVESPEED_MODEL,
            WAVESPEED_SUBMIT_URL,
            WAVESPEED_POLL_URL,
            WAVESPEED_DOC_URL,
            BAILIAN_MODEL,
            BAILIAN_DEFAULT_SUBMIT_URL,
            BAILIAN_WORKSPACE_URL,
            BAILIAN_DOC_URL,
            DEFAULT_STT_ENV_PATH,
            AUDIO_EXTENSIONS,
            PROVIDERS,
        )
    except ImportError:
        from constants import (
            WAVESPEED_MODEL,
            WAVESPEED_SUBMIT_URL,
            WAVESPEED_POLL_URL,
            WAVESPEED_DOC_URL,
            BAILIAN_MODEL,
            BAILIAN_DEFAULT_SUBMIT_URL,
            BAILIAN_WORKSPACE_URL,
            BAILIAN_DOC_URL,
            DEFAULT_STT_ENV_PATH,
            AUDIO_EXTENSIONS,
            PROVIDERS,
        )

# Official Alibaba Bailian Fun-Music API (fun-music-api):
#   POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/music/generation
#   Body: {"model": "fun-music-v1", "input": {"prompt": str, "is_instrumental": bool, "format": "wav"|"mp3"}}
# Note:
# 1. Official doc shows `{WorkspaceId}.cn-beijing.maas.aliyuncs.com`; if BAILIAN_WORKSPACE_ID
#    is not set, we fall back to the public DashScope Beijing host `dashscope.aliyuncs.com`.
# 2. `fun-music-v1` has no input duration parameter; output is trimmed during post-processing.
# 3. Official doc describes non-streaming sync and SSE streaming responses. If a server/gateway
#    returns a standard DashScope async `output.task_id`, we also poll `/api/v1/tasks/{task_id}`.





@dataclass(frozen=True)
class HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class GenerationResult:
    provider: str
    model: str
    prompt: str
    seconds: float
    bpm: int | None
    instrumental: bool
    request_digest: str
    request_id: str
    generated_at: str
    raw_path: Path
    processed_path: Path
    billed_seconds: float | None = None
    from_cache: bool = False


def _file_sha256(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    try:
        with temporary.open('wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_request(
    provider: str,
    prompt: str,
    seconds: float,
    *,
    bpm: int | None = None,
    instrumental: bool = True,
) -> tuple[str, str, float, int | None, bool]:
    if provider not in PROVIDERS:
        supported = '、'.join(PROVIDERS)
        raise MusicError(f'不支持的 AI 配乐服务商「{provider}」，请选用：{supported}')
    if not isinstance(prompt, str) or not prompt.strip():
        raise MusicError('提示词不能为空，请描述风格、情绪或乐器')
    clean_prompt = prompt.strip()
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
        raise MusicError('目标时长必须是有效数字（秒）')
    spec = PROVIDERS[provider]
    target_seconds = round(float(seconds), 3)
    if target_seconds < spec['min_seconds'] or target_seconds > spec['max_seconds']:
        raise MusicError(
            f"{spec['label']}目标时长须在 {int(spec['min_seconds'])} 到 {int(spec['max_seconds'])} 秒之间"
        )
    clean_bpm: int | None = None
    if bpm is not None:
        if isinstance(bpm, bool) or not isinstance(bpm, int) or bpm < 30 or bpm > 300:
            raise MusicError('BPM 须为 30 到 300 之间的整数')
        clean_bpm = bpm
    return provider, clean_prompt, target_seconds, clean_bpm, bool(instrumental)


def request_digest(
    provider: str,
    prompt: str,
    seconds: float,
    *,
    bpm: int | None = None,
    instrumental: bool = True,
    model: str | None = None,
) -> str:
    provider, clean_prompt, target_seconds, clean_bpm, clean_instrumental = validate_request(
        provider, prompt, seconds, bpm=bpm, instrumental=instrumental
    )
    resolved_model = model or PROVIDERS[provider]['model']
    canonical = {
        'provider': provider,
        'model': resolved_model,
        'prompt': clean_prompt,
        'seconds': target_seconds,
        'bpm': clean_bpm,
        'instrumental': clean_instrumental,
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def estimate_cost(provider: str, seconds: float, *, billed_seconds: float | None = None) -> dict[str, object]:
    if provider not in PROVIDERS:
        raise MusicError(f'不支持的 AI 配乐服务商「{provider}」')
    spec = PROVIDERS[provider]
    unit_price = spec['unit_price']
    currency = spec['currency']
    effective_seconds = float(billed_seconds) if billed_seconds is not None else float(seconds)
    amount = round(effective_seconds * unit_price, 6)
    if currency == 'USD':
        text = f'约 ${amount:.4f}（$0.0003/秒 × {effective_seconds:g} 秒）'
    else:
        if billed_seconds is not None:
            text = (
                f'约 ¥{amount:.3f}（¥0.002/秒 × 实际生成 {effective_seconds:g} 秒；'
                f'已裁至 {float(seconds):g} 秒）'
            )
        else:
            text = f'按目标 {effective_seconds:g} 秒估算约 ¥{amount:.3f}（¥0.002/秒，百炼实际按生成原长计费）'
    return {
        'currency': currency,
        'unit_price': unit_price,
        'seconds': effective_seconds,
        'amount': amount,
        'text': text,
    }


def _read_keychain_secret(service: str, *, runner=subprocess.run, platform: str | None = None) -> str | None:
    current_platform = platform or sys.platform
    try:
        completed = runner(
            ['security', 'find-generic-password', '-s', service, '-w'],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError as exc:
        if current_platform == 'darwin':
            raise MusicError(f'找不到系统 security 命令，无法读取钥匙串里的 {service}') from exc
        return None
    except subprocess.TimeoutExpired as exc:
        raise MusicError(f'读取 macOS 钥匙串里的 {service} 超时：请解锁钥匙串或允许访问后重试') from exc
    except OSError as exc:
        raise MusicError(f'无法执行钥匙串读取命令以获取 {service}，请检查系统权限') from exc

    if completed.returncode == 0:
        secret = (completed.stdout or '').strip()
        return secret or None
    # macOS Security framework errSecItemNotFound == 44.
    if completed.returncode == 44:
        return None
    raise MusicError(
        f'无法读取 macOS 钥匙串里的 {service}（退出码 {completed.returncode}）：'
        '请解锁钥匙串或允许访问后重试，未将其视为未配置'
    )


def _read_env_file_key(path: Path, key_name: str) -> str | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MusicError(f'无法读取备用密钥文件 {path.name}，请检查文件权限') from exc

    if not stat.S_ISREG(info.st_mode):
        raise MusicError(f'备用密钥路径 {path.name} 不是普通文件，无法读取')

    try:
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise MusicError(f'无法读取备用密钥文件 {path.name}，请检查文件权限和 UTF-8 编码') from exc

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].strip()
        if '=' not in line:
            continue
        name, value = line.split('=', 1)
        if name.strip() != key_name:
            continue
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ('"', "'"):
            cleaned = cleaned[1:-1].strip()
        return cleaned or None
    return None


def read_api_key(
    provider: str,
    *,
    keychain_runner=subprocess.run,
    stt_env_path: Path | None = None,
    platform: str | None = None,
) -> str:
    if provider not in PROVIDERS:
        raise MusicError(f'不支持的 AI 配乐服务商「{provider}」')
    service = PROVIDERS[provider]['keychain_service']
    secret = _read_keychain_secret(service, runner=keychain_runner, platform=platform)
    if secret:
        return secret

    if provider == 'bailian':
        fallback_path = Path(stt_env_path) if stt_env_path is not None else DEFAULT_STT_ENV_PATH
        fallback_secret = _read_env_file_key(fallback_path, 'SPEECH_TO_TEXT_API_KEY')
        if fallback_secret:
            return fallback_secret
        raise MusicError(
            '还没有百炼密钥：请将百炼 API Key 放进钥匙串 bailian-api-key，'
            '或配置 ~/.config/harness/speech-to-text.env 里的 SPEECH_TO_TEXT_API_KEY'
        )

    raise MusicError(
        '还没有 WaveSpeed 密钥：注册后放进钥匙串 wavespeed-api-key'
        '（security add-generic-password -a "$USER" -s wavespeed-api-key -w）'
    )


def default_http_call(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 120,
) -> HTTPResponse:
    import requests
    from requests.adapters import HTTPAdapter

    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname:
        raise MusicError('服务商请求地址不合法，已停止联网')

    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=0))
    session.mount('http://', HTTPAdapter(max_retries=0))
    try:
        response = session.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            data=body,
            timeout=timeout,
            allow_redirects=(method.upper() == 'GET'),
        )
        return HTTPResponse(
            status=response.status_code,
            headers={k.lower(): v for k, v in response.headers.items()},
            body=response.content,
        )
    except requests.Timeout as exc:
        raise MusicError('AI 配乐接口请求超时，已停止自动重试') from exc
    except requests.RequestException as exc:
        raise MusicError('AI 配乐接口网络请求失败，请检查网络连接后再决定是否重试') from exc
    finally:
        session.close()


def _parse_json_response(response: HTTPResponse, provider_label: str) -> dict:
    try:
        parsed = json.loads(response.body.decode('utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise MusicError(f'{provider_label}返回了无法解析的响应（HTTP {response.status}），未自动重试') from exc
    if not isinstance(parsed, dict):
        raise MusicError(f'{provider_label}返回了未识别的数据结构，未自动重试')
    return parsed


def _extract_error_detail(payload: dict | None, fallback_text: str) -> str:
    if isinstance(payload, dict):
        parts = []
        for container in (payload, payload.get('data'), payload.get('output')):
            if not isinstance(container, dict):
                continue
            for key in ('code', 'error', 'message'):
                value = container.get(key)
                if isinstance(value, str) and value.strip() and value.strip() not in parts:
                    parts.append(value.strip())
        if parts:
            return ' / '.join(parts)[:200]
    snippet = fallback_text.strip().splitlines()[0] if fallback_text.strip() else ''
    return snippet[:200] or '服务未返回具体原因'


def _contains_access_denied(status: int, payload: dict | None, raw_text: str) -> bool:
    if status == 403:
        return True
    haystacks = [raw_text]
    if isinstance(payload, dict):
        for container in (payload, payload.get('data'), payload.get('output')):
            if isinstance(container, dict):
                for key in ('code', 'error', 'message'):
                    value = container.get(key)
                    if isinstance(value, str):
                        haystacks.append(value)
    return any('accessdenied' in text.lower() or 'access_denied' in text.lower() for text in haystacks)


def _audio_extension_from_url(url: str, content_type: str = '', default: str = '.wav') -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return suffix
    ctype = content_type.lower()
    if 'mpeg' in ctype or 'mp3' in ctype:
        return '.mp3'
    if 'wav' in ctype:
        return '.wav'
    if 'flac' in ctype:
        return '.flac'
    if 'mp4' in ctype or 'm4a' in ctype or 'aac' in ctype:
        return '.m4a'
    if 'ogg' in ctype:
        return '.ogg'
    return default


def _download_audio(url: str, http_call, provider_label: str) -> tuple[bytes, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise MusicError(f'{provider_label}返回了不安全的音频下载地址，已停止下载')
    response = http_call('GET', url, headers={}, body=None, timeout=180)
    if response.status >= 400:
        raise MusicError(f'{provider_label}生成的音频下载失败（HTTP {response.status}），未自动重试')
    if not response.body:
        raise MusicError(f'{provider_label}返回的音频文件内容为空，未入库')
    ext = _audio_extension_from_url(url, response.headers.get('content-type', ''))
    return response.body, ext


def _wavespeed_tags(prompt: str, bpm: int | None) -> str:
    if bpm is None:
        return prompt
    if re.search(r'\bbpm\b', prompt, flags=re.IGNORECASE):
        return prompt
    return f'{prompt}, {bpm} bpm'


def _call_wavespeed(
    *,
    api_key: str,
    prompt: str,
    seconds: float,
    bpm: int | None,
    instrumental: bool,
    http_call,
    sleep,
    poll_interval: float,
    max_polls: int,
    base_url: str | None = None,
    on_accepted=None,
) -> tuple[str, bytes, str, float | None]:
    # Official doc: https://wavespeed.ai/models/wavespeed-ai/ace-step-1.5/llms.txt
    submit_url = base_url or WAVESPEED_SUBMIT_URL
    payload = {
        'tags': _wavespeed_tags(prompt, bpm),
        'lyrics': '[inst]' if instrumental else '',
        'duration': seconds,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    response = http_call(
        'POST',
        submit_url,
        headers=headers,
        body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        timeout=120,
    )
    raw_text = response.body.decode('utf-8', errors='replace')
    parsed = None
    try:
        parsed = json.loads(raw_text) if raw_text.strip() else None
    except ValueError:
        parsed = None

    if response.status in (401, 403) or _contains_access_denied(response.status, parsed, raw_text):
        raise MusicError('WaveSpeed 拒绝访问：请检查钥匙串 wavespeed-api-key 是否有效或账号余额是否充足')
    if response.status >= 400:
        detail = _extract_error_detail(parsed, raw_text)
        raise MusicError(f'WaveSpeed 生成请求失败（HTTP {response.status}）：{detail}')

    body = _parse_json_response(response, 'WaveSpeed')
    data = body.get('data') if isinstance(body.get('data'), dict) else body
    prediction_id = data.get('id')
    if not isinstance(prediction_id, str) or not prediction_id.strip():
        raise MusicError('WaveSpeed 响应缺少任务编号 data.id，未自动重试')
    prediction_id = prediction_id.strip()
    if on_accepted is not None:
        on_accepted(prediction_id)

    poll_url = None
    urls_obj = data.get('urls')
    if isinstance(urls_obj, dict) and isinstance(urls_obj.get('get'), str) and urls_obj['get'].strip():
        poll_url = urls_obj['get'].strip()
    if not poll_url:
        poll_url = WAVESPEED_POLL_URL.format(prediction_id=prediction_id)

    polls = 0
    while True:
        status = str(data.get('status') or '').strip().lower()
        outputs = data.get('outputs')
        if status == 'completed':
            audio_url = _extract_wavespeed_output_url(outputs)
            if not audio_url:
                raise MusicError('WaveSpeed 任务已完成但未返回音频地址，未入库')
            raw_bytes, ext = _download_audio(audio_url, http_call, 'WaveSpeed')
            return prediction_id, raw_bytes, ext, float(seconds)
        if status in ('failed', 'cancelled', 'canceled', 'timeout', 'deleted'):
            detail = _extract_error_detail(data, '')
            raise MusicError(f'WaveSpeed 生成失败（状态 {status}）：{detail}')
        if status not in ('created', 'processing', 'queued', 'pending', 'running'):
            raise MusicError(f'WaveSpeed 返回了未识别的任务状态「{status or "空"}」，已停止等待')
        if polls >= max_polls:
            raise MusicError(f'WaveSpeed 任务 {prediction_id} 等待超时，已停止轮询')
        polls += 1
        sleep(poll_interval)
        poll_resp = http_call(
            'GET',
            poll_url,
            headers={'Authorization': f'Bearer {api_key}'},
            body=None,
            timeout=60,
        )
        poll_text = poll_resp.body.decode('utf-8', errors='replace')
        poll_parsed = None
        try:
            poll_parsed = json.loads(poll_text) if poll_text.strip() else None
        except ValueError:
            poll_parsed = None
        if poll_resp.status in (401, 403) or _contains_access_denied(poll_resp.status, poll_parsed, poll_text):
            raise MusicError('WaveSpeed 查询结果被拒绝：请检查钥匙串 wavespeed-api-key 是否有效')
        if poll_resp.status >= 400:
            detail = _extract_error_detail(poll_parsed, poll_text)
            raise MusicError(f'WaveSpeed 查询结果失败（HTTP {poll_resp.status}）：{detail}')
        poll_body = _parse_json_response(poll_resp, 'WaveSpeed')
        data = poll_body.get('data') if isinstance(poll_body.get('data'), dict) else poll_body


def _extract_wavespeed_output_url(outputs) -> str | None:
    if not isinstance(outputs, list) or not outputs:
        return None
    first = outputs[0]
    if isinstance(first, str) and first.strip():
        return first.strip()
    if isinstance(first, dict):
        for key in ('url', 'audio_url', 'file_url'):
            value = first.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _bailian_prompt(prompt: str, bpm: int | None) -> str:
    if bpm is None:
        return prompt
    if re.search(r'\bbpm\b', prompt, flags=re.IGNORECASE):
        return prompt
    return f'{prompt}，约 {bpm} BPM'


def _bailian_submit_url(workspace_id: str | None = None, base_url: str | None = None) -> str:
    if base_url:
        return base_url
    ws = (workspace_id if workspace_id is not None else os.environ.get('BAILIAN_WORKSPACE_ID', '')).strip()
    if ws:
        return BAILIAN_WORKSPACE_URL.format(workspace_id=ws)
    return BAILIAN_DEFAULT_SUBMIT_URL


def _extract_bailian_audio_url(output: dict) -> str | None:
    audio = output.get('audio')
    if isinstance(audio, dict):
        url = audio.get('url')
        if isinstance(url, str) and url.strip():
            return url.strip()
    url = output.get('audio_url') or output.get('url')
    if isinstance(url, str) and url.strip():
        return url.strip()
    results = output.get('results')
    if isinstance(results, list) and results and isinstance(results[0], dict):
        first_url = results[0].get('url') or results[0].get('audio_url')
        if isinstance(first_url, str) and first_url.strip():
            return first_url.strip()
    return None


def _extract_bailian_billed_seconds(payload: dict) -> float | None:
    usage = payload.get('usage')
    if isinstance(usage, dict):
        duration = usage.get('duration')
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration > 0:
            return float(duration)
    return None


def _call_bailian(
    *,
    api_key: str,
    prompt: str,
    seconds: float,
    bpm: int | None,
    instrumental: bool,
    http_call,
    sleep,
    poll_interval: float,
    max_polls: int,
    workspace_id: str | None = None,
    base_url: str | None = None,
    on_accepted=None,
) -> tuple[str, bytes, str, float | None]:
    # Official doc: https://help.aliyun.com/zh/model-studio/fun-music-api
    submit_url = _bailian_submit_url(workspace_id=workspace_id, base_url=base_url)
    payload = {
        'model': BAILIAN_MODEL,
        'input': {
            'prompt': _bailian_prompt(prompt, bpm),
            'is_instrumental': bool(instrumental),
            'format': 'wav',
        },
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    response = http_call(
        'POST',
        submit_url,
        headers=headers,
        body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        timeout=300,
    )
    raw_text = response.body.decode('utf-8', errors='replace')
    parsed = None
    try:
        parsed = json.loads(raw_text) if raw_text.strip() else None
    except ValueError:
        parsed = None

    if _contains_access_denied(response.status, parsed, raw_text):
        raise MusicError('百炼账号还没开通 Fun-Music 邀测，请先在阿里云百炼控制台申请开通 fun-music-v1 权限')
    if response.status == 401:
        raise MusicError('百炼密钥无效或已过期，请检查钥匙串 bailian-api-key 或 ~/.config/harness/speech-to-text.env')
    if response.status >= 400:
        detail = _extract_error_detail(parsed, raw_text)
        raise MusicError(f'百炼 Fun-Music 生成请求失败（HTTP {response.status}）：{detail}')

    body = _parse_json_response(response, '百炼 Fun-Music')
    if _contains_access_denied(200, body, raw_text):
        raise MusicError('百炼账号还没开通 Fun-Music 邀测，请先在阿里云百炼控制台申请开通 fun-music-v1 权限')

    request_id = str(body.get('request_id') or '').strip()
    output = body.get('output') if isinstance(body.get('output'), dict) else {}
    billed_seconds = _extract_bailian_billed_seconds(body)

    # Case 1: Direct synchronous response (official fun-music-api non-streaming mode).
    direct_url = _extract_bailian_audio_url(output)
    if direct_url:
        req_id = request_id or str((output.get('audio') or {}).get('id') or 'bailian-sync')
        if on_accepted is not None:
            on_accepted(req_id)
        raw_bytes, ext = _download_audio(direct_url, http_call, '百炼 Fun-Music')
        return req_id, raw_bytes, ext, billed_seconds

    # Case 2: Standard DashScope async task response (output.task_id + /api/v1/tasks/{task_id}).
    task_id = output.get('task_id')
    if not isinstance(task_id, str) or not task_id.strip():
        detail = _extract_error_detail(body, raw_text)
        raise MusicError(f'百炼 Fun-Music 未返回音频地址或任务编号：{detail}')
    task_id = task_id.strip()
    if on_accepted is not None:
        on_accepted(task_id)

    parsed_submit = urlsplit(submit_url)
    task_url = f'{parsed_submit.scheme}://{parsed_submit.netloc}/api/v1/tasks/{task_id}'
    polls = 0
    while True:
        task_status = str(output.get('task_status') or '').strip().upper()
        if task_status == 'SUCCEEDED':
            audio_url = _extract_bailian_audio_url(output)
            if not audio_url:
                raise MusicError('百炼 Fun-Music 任务已完成但未返回音频地址，未入库')
            req_id = request_id or task_id.strip()
            raw_bytes, ext = _download_audio(audio_url, http_call, '百炼 Fun-Music')
            return req_id, raw_bytes, ext, billed_seconds
        if task_status in ('FAILED', 'CANCELED', 'CANCELLED', 'UNKNOWN'):
            if _contains_access_denied(200, body, json.dumps(body, ensure_ascii=False)):
                raise MusicError('百炼账号还没开通 Fun-Music 邀测，请先在阿里云百炼控制台申请开通 fun-music-v1 权限')
            detail = _extract_error_detail(body, '')
            raise MusicError(f'百炼 Fun-Music 生成失败（状态 {task_status}）：{detail}')
        if task_status not in ('PENDING', 'RUNNING', 'QUEUED', ''):
            raise MusicError(f'百炼 Fun-Music 返回了未识别的任务状态「{task_status}」，已停止等待')
        if polls >= max_polls:
            raise MusicError(f'百炼 Fun-Music 任务 {task_id} 等待超时，已停止轮询')
        polls += 1
        sleep(poll_interval)
        poll_resp = http_call(
            'GET',
            task_url,
            headers={'Authorization': f'Bearer {api_key}'},
            body=None,
            timeout=60,
        )
        poll_text = poll_resp.body.decode('utf-8', errors='replace')
        poll_parsed = None
        try:
            poll_parsed = json.loads(poll_text) if poll_text.strip() else None
        except ValueError:
            poll_parsed = None
        if _contains_access_denied(poll_resp.status, poll_parsed, poll_text):
            raise MusicError('百炼账号还没开通 Fun-Music 邀测，请先在阿里云百炼控制台申请开通 fun-music-v1 权限')
        if poll_resp.status >= 400:
            detail = _extract_error_detail(poll_parsed, poll_text)
            raise MusicError(f'百炼 Fun-Music 查询任务失败（HTTP {poll_resp.status}）：{detail}')
        body = _parse_json_response(poll_resp, '百炼 Fun-Music')
        if isinstance(body.get('request_id'), str) and body['request_id'].strip():
            request_id = body['request_id'].strip()
        output = body.get('output') if isinstance(body.get('output'), dict) else {}
        billed_seconds = _extract_bailian_billed_seconds(body) or billed_seconds
        audio_url = _extract_bailian_audio_url(output)
        if audio_url and str(output.get('task_status') or '').strip().upper() in ('', 'SUCCEEDED'):
            req_id = request_id or task_id.strip()
            raw_bytes, ext = _download_audio(audio_url, http_call, '百炼 Fun-Music')
            return req_id, raw_bytes, ext, billed_seconds


def _probe_audio(path: Path) -> tuple[float, int]:
    probe = subprocess.run(
        [
            'ffprobe', '-v', 'error', '-select_streams', 'a:0',
            '-show_streams', '-show_format', '-of', 'json', str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    data = json.loads(probe.stdout)
    streams = data.get('streams') or []
    if not streams:
        raise ValueError('no audio stream')
    stream = streams[0]
    duration = float(stream.get('duration') or data['format']['duration'])
    sample_rate = int(stream['sample_rate'])
    if not math.isfinite(duration) or duration <= 0 or sample_rate <= 0:
        raise ValueError('invalid audio probe')
    return duration, sample_rate


def postprocess_audio(raw_path: Path, output_path: Path, target_seconds: float) -> Path:
    """Strip leading/trailing silence (-45 dB), trim to target_seconds, fade in/out, and loudnorm to -16 LUFS."""
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise MusicError('需要安装 ffmpeg 和 ffprobe 才能处理生成的音频')
    raw_path = Path(raw_path)
    output_path = Path(output_path)
    if not raw_path.is_file():
        raise MusicError('原始生成音频不存在，无法后处理')
    if not isinstance(target_seconds, (int, float)) or not math.isfinite(target_seconds) or target_seconds <= 0:
        raise MusicError('目标时长必须是大于 0 的数字')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.postproc-', dir=output_path.parent) as staging:
        stage = Path(staging)
        stripped = stage / 'stripped.wav'
        faded = stage / 'faded.wav'
        normalized = stage / 'normalized.wav'
        try:
            # 1. Remove leading and trailing silence at -45 dB without touching mid-track pauses.
            silence_filter = (
                'silenceremove=start_periods=1:start_duration=0:start_threshold=-45dB,'
                'areverse,'
                'silenceremove=start_periods=1:start_duration=0:start_threshold=-45dB,'
                'areverse'
            )
            subprocess.run(
                [
                    'ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(raw_path),
                    '-map', '0:a:0', '-af', silence_filter, '-c:a', 'pcm_s16le', str(stripped),
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            try:
                stripped_duration, sample_rate = _probe_audio(stripped)
            except (ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
                raise MusicError('生成的音频去除首尾静音后没有有效声音，未入库') from exc
            if stripped_duration < 0.1:
                raise MusicError('生成的音频去除首尾静音后没有有效声音，未入库')

            # 2. Trim to target_seconds + 3. Fade in 0.2s, fade out 2.0s.
            actual_duration = min(float(target_seconds), stripped_duration)
            fade_in = min(0.2, actual_duration * 0.2)
            fade_out = min(2.0, actual_duration * 0.5)
            fade_out_start = max(0.0, actual_duration - fade_out)
            trim_fade_filter = (
                f'atrim=0:{actual_duration:.6f},asetpts=PTS-STARTPTS,'
                f'afade=t=in:st=0:d={fade_in:.6f},'
                f'afade=t=out:st={fade_out_start:.6f}:d={fade_out:.6f}'
            )
            subprocess.run(
                [
                    'ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(stripped),
                    '-af', trim_fade_filter, '-c:a', 'pcm_s16le', str(faded),
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            # 4. Two-pass loudnorm to -16 LUFS (ducking to -24..-28 LUFS happens during voiceover mixing).
            pass1 = subprocess.run(
                [
                    'ffmpeg', '-nostdin', '-v', 'info', '-i', str(faded),
                    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
                    '-f', 'null', '-',
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            blocks = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', pass1.stderr, re.S)
            if not blocks:
                raise ValueError('missing loudnorm measurement')
            measured = json.loads(blocks[-1])
            measured_i = float(measured['input_i'])
            if not math.isfinite(measured_i):
                raise MusicError('生成的音频响度异常（近乎静音），无法完成响度归一')

            pass2_filter = (
                'loudnorm=I=-16:TP=-1.5:LRA=11:'
                f"measured_I={measured['input_i']}:"
                f"measured_TP={measured['input_tp']}:"
                f"measured_LRA={measured['input_lra']}:"
                f"measured_thresh={measured['input_thresh']}:"
                f"offset={measured['target_offset']}:"
                'linear=true:print_format=summary'
            )
            subprocess.run(
                [
                    'ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(faded),
                    '-af', pass2_filter, '-ar', str(sample_rate), '-c:a', 'pcm_s16le', str(normalized),
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            os.replace(normalized, output_path)
            return output_path
        except MusicError:
            raise
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
            raise MusicError('生成的音频后处理失败，未入库') from exc


def _build_retry_command(provider: str, prompt: str, seconds: float, bpm: int | None, instrumental: bool) -> str:
    parts = [
        '.venv/bin/python',
        'scripts/video_tools/generate_music.py',
        '--provider',
        provider,
        '--prompt',
        json.dumps(prompt, ensure_ascii=False),
        '--seconds',
        f'{seconds:g}',
    ]
    if bpm is not None:
        parts.extend(['--bpm', str(bpm)])
    if not instrumental:
        parts.append('--with-vocals')
    parts.append('--retry-failed')
    return ' '.join(parts)


def _archive_failed_record(entry_dir: Path, record_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    candidate = entry_dir / f'record.failed-{stamp}.json'
    suffix = 1
    while candidate.exists():
        candidate = entry_dir / f'record.failed-{stamp}-{suffix}.json'
        suffix += 1
    record_path.replace(candidate)
    return candidate


def generate_music(
    provider: str,
    prompt: str,
    seconds: float,
    *,
    cache_root: Path,
    bpm: int | None = None,
    instrumental: bool = True,
    retry_failed: bool = False,
    api_key: str | None = None,
    workspace_id: str | None = None,
    base_url: str | None = None,
    http_call=default_http_call,
    sleep=time.sleep,
    poll_interval: float = 2.0,
    max_polls: int = 150,
    keychain_runner=subprocess.run,
    stt_env_path: Path | None = None,
    platform: str | None = None,
) -> GenerationResult:
    """Generate and post-process an AI track, reusing cached results by request digest."""
    provider, clean_prompt, target_seconds, clean_bpm, clean_instrumental = validate_request(
        provider, prompt, seconds, bpm=bpm, instrumental=instrumental
    )
    model = PROVIDERS[provider]['model']
    digest = request_digest(
        provider, clean_prompt, target_seconds, bpm=clean_bpm, instrumental=clean_instrumental, model=model
    )

    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    entry_dir = cache_root / digest
    record_path = entry_dir / 'record.json'
    archive_failed = False

    if record_path.exists():
        record = read_json(record_path, 'AI 生成缓存')
        state = record.get('state')
        if state == 'complete':
            raw_name = record.get('raw_file')
            proc_name = record.get('processed_file')
            if not isinstance(raw_name, str) or not isinstance(proc_name, str):
                raise MusicError('AI 生成缓存记录损坏，已停止重复请求以避免重复扣费')
            raw_path = entry_dir / raw_name
            proc_path = entry_dir / proc_name
            if not raw_path.is_file() or not proc_path.is_file():
                raise MusicError('AI 生成缓存音频文件缺失，已停止重复请求以避免重复扣费')
            if (
                record.get('raw_sha256') and _file_sha256(raw_path) != record['raw_sha256']
            ) or (
                record.get('processed_sha256') and _file_sha256(proc_path) != record['processed_sha256']
            ):
                raise MusicError('AI 生成缓存音频校验失败，已停止重复请求以避免重复扣费')
            return GenerationResult(
                provider=record['provider'],
                model=record['model'],
                prompt=record['prompt'],
                seconds=float(record['params']['seconds']),
                bpm=record['params']['bpm'],
                instrumental=bool(record['params']['instrumental']),
                request_digest=digest,
                request_id=record['request_id'],
                generated_at=record['generated_at'],
                raw_path=raw_path,
                processed_path=proc_path,
                billed_seconds=record.get('billed_seconds'),
                from_cache=True,
            )
        if state == 'failed':
            if not retry_failed:
                reason = record.get('reason') if isinstance(record.get('reason'), str) else '上次已受理任务失败'
                retry_cmd = _build_retry_command(provider, clean_prompt, target_seconds, clean_bpm, clean_instrumental)
                raise MusicError(
                    f'{reason}（已受理任务失败缓存，未自动重试；如确认需要重新发起请求，请运行：{retry_cmd}）'
                )
            archive_failed = True
        else:
            task_ref = record.get('request_id') or record.get('task_id') or '未记录'
            raise MusicError(
                f'这组参数已有已受理但未完成的任务（任务号：{task_ref}，缓存目录：{entry_dir}），'
                '已拦截以避免重复扣费；请先到服务商后台查询该任务状态'
            )

    resolved_key = (
        api_key.strip()
        if isinstance(api_key, str) and api_key.strip()
        else read_api_key(
            provider,
            keychain_runner=keychain_runner,
            stt_env_path=stt_env_path,
            platform=platform,
        )
    )

    if archive_failed and record_path.exists():
        _archive_failed_record(entry_dir, record_path)

    params = {'seconds': target_seconds, 'bpm': clean_bpm, 'instrumental': clean_instrumental}
    accepted = {'id': None}

    def mark_accepted(task_ref: str) -> None:
        accepted['id'] = task_ref
        entry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_json(
            record_path,
            {
                'state': 'pending',
                'provider': provider,
                'model': model,
                'prompt': clean_prompt,
                'params': params,
                'request_id': task_ref,
                'accepted_at': _now_iso(),
            },
        )

    try:
        if provider == 'wavespeed':
            request_id, raw_bytes, raw_ext, billed_seconds = _call_wavespeed(
                api_key=resolved_key,
                prompt=clean_prompt,
                seconds=target_seconds,
                bpm=clean_bpm,
                instrumental=clean_instrumental,
                http_call=http_call,
                sleep=sleep,
                poll_interval=poll_interval,
                max_polls=max_polls,
                base_url=base_url,
                on_accepted=mark_accepted,
            )
        else:
            request_id, raw_bytes, raw_ext, billed_seconds = _call_bailian(
                api_key=resolved_key,
                prompt=clean_prompt,
                seconds=target_seconds,
                bpm=clean_bpm,
                instrumental=clean_instrumental,
                http_call=http_call,
                sleep=sleep,
                poll_interval=poll_interval,
                max_polls=max_polls,
                workspace_id=workspace_id,
                base_url=base_url,
                on_accepted=mark_accepted,
            )

        entry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw_name = 'raw' + raw_ext
        raw_path = entry_dir / raw_name
        _write_bytes_atomic(raw_path, raw_bytes)

        processed_name = 'processed.wav'
        processed_path = entry_dir / processed_name
        postprocess_audio(raw_path, processed_path, target_seconds)

        generated_at = _now_iso()
        write_json(
            record_path,
            {
                'state': 'complete',
                'provider': provider,
                'model': model,
                'prompt': clean_prompt,
                'params': params,
                'request_id': request_id,
                'generated_at': generated_at,
                'billed_seconds': billed_seconds,
                'raw_file': raw_name,
                'raw_sha256': _file_sha256(raw_path),
                'processed_file': processed_name,
                'processed_sha256': _file_sha256(processed_path),
            },
        )
        return GenerationResult(
            provider=provider,
            model=model,
            prompt=clean_prompt,
            seconds=target_seconds,
            bpm=clean_bpm,
            instrumental=clean_instrumental,
            request_digest=digest,
            request_id=request_id,
            generated_at=generated_at,
            raw_path=raw_path,
            processed_path=processed_path,
            billed_seconds=billed_seconds,
            from_cache=False,
        )
    except MusicError as exc:
        if accepted['id'] is not None:
            entry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            write_json(
                record_path,
                {
                    'state': 'failed',
                    'provider': provider,
                    'model': model,
                    'prompt': clean_prompt,
                    'params': params,
                    'request_id': accepted['id'],
                    'reason': str(exc),
                    'failed_at': _now_iso(),
                },
            )
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reason = 'AI 生成结果处理或本地写入失败，未完成入库'
        if accepted['id'] is not None:
            entry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            write_json(
                record_path,
                {
                    'state': 'failed',
                    'provider': provider,
                    'model': model,
                    'prompt': clean_prompt,
                    'params': params,
                    'request_id': accepted['id'],
                    'reason': reason,
                    'failed_at': _now_iso(),
                },
            )
        raise MusicError(reason) from exc
