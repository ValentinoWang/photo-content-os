"""Optional QR-only NetEase authentication; credentials stay outside the repo."""
import json
import os
import secrets
import stat
import time
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode

from .cache import USER_AGENT
from .network import MusicOpener
from .errors import MusicError



def config_dir():
    root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')).expanduser().resolve() / 'photo-content-os/music'
    # The auth store cannot be redirected into a git checkout.
    if any((p / '.git').exists() for p in (root, *root.parents)):
        raise MusicError('登录状态目录必须位于仓库外，请调整用户配置目录')
    return root


def read_session(directory=None):
    path = (directory or config_dir()) / 'netease-session.json'
    if not path.exists() and not path.is_symlink():
        return ''
    try:
        if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise MusicError('网易云登录状态文件权限必须为 600，请维护者修复')
        value = json.loads(path.read_text())
        cookie = value['cookie']
        if not isinstance(cookie, str) or not cookie or '\r' in cookie or '\n' in cookie:
            raise ValueError('invalid cookie')
        return cookie
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise MusicError('网易云登录状态无法读取或已损坏；这不代表未登录') from exc


def save_session(cookie, directory=None):
    root = directory or config_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    path = root / 'netease-session.json'
    if path.is_symlink():
        raise MusicError('登录状态文件不能是软链接')
    temporary = root / ('.session-' + secrets.token_hex(8))
    try:
        with os.fdopen(os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
            json.dump({'cookie': cookie}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def aes_encrypt(value, key, iv=None):
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    padder = padding.PKCS7(128).padder()
    padded = padder.update(value) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv) if iv else modes.ECB()).encryptor()
    return cipher.update(padded) + cipher.finalize()


def linux_params(path, params):
    # Wire protocol documented by api-enhanced; the key is public, not a credential.
    payload = json.dumps({'method': 'POST', 'url': 'https://music.163.com' + path, 'params': params}, separators=(',', ':')).encode()
    return urlencode({'eparams': aes_encrypt(payload, b'rFgB&h#%2?^eDg:Q').hex().upper()}).encode()


def qr_request(path, params, opener=None):
    request = urllib.request.Request('https://music.163.com/api/linux/forward', data=linux_params(path, params),
                                     headers={'User-Agent': USER_AGENT, 'Referer': 'https://music.163.com/'})
    try:
        with (opener or MusicOpener()).open(request, timeout=30) as response:
            data = json.loads(response.read())
            jar = SimpleCookie()
            for header in response.headers.get_all('Set-Cookie', []):
                jar.load(header)
            return data, '; '.join(f'{key}={value.value}' for key, value in jar.items())
    except (OSError, ValueError) as exc:
        raise MusicError('网易云扫码服务读取失败，未自动重试') from exc


def login_qr(*, request=qr_request, display=None, sleep=time.sleep, directory=None):
    root = directory or config_dir()
    result, _ = request('/api/login/qrcode/unikey', {'type': 1})
    key = result.get('unikey')
    if result.get('code') != 200 or not isinstance(key, str) or not key:
        raise MusicError('网易云未返回登录二维码，未自动重试')
    url = 'https://music.163.com/login?' + urlencode({'codekey': key})
    if display:
        display(url)
    else:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        print('请用手机网易云音乐扫码，并在手机上确认登录：')
        qr.print_ascii(invert=True)
    for _ in range(60):
        sleep(3)
        result, cookie = request('/api/login/qrcode/client/login', {'key': key, 'type': 1})
        code = result.get('code')
        if code == 803:
            if not cookie or 'MUSIC_U=' not in cookie:
                raise MusicError('扫码确认后未收到登录凭据，请维护者检查')
            save_session(cookie, root)
            return
        if code == 800:
            raise MusicError('二维码已过期或已取消，请重新发起扫码登录')
        if code not in (801, 802):
            raise MusicError('网易云扫码返回未知状态，请维护者检查')
    raise MusicError('等待扫码超时，请重新发起扫码登录')
