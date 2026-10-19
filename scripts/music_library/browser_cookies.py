"""Read only matching macOS Chrome/Edge cookies; secrets stay in memory."""
import hashlib
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from .errors import MusicError


BROWSERS = {
    'chrome': ('Google/Chrome', 'Chrome Safe Storage', 'Chrome'),
    'edge': ('Microsoft Edge', 'Microsoft Edge Safe Storage', 'Microsoft Edge'),
}


def decrypt_cookie(encrypted: bytes, password: bytes, host: str, version: int) -> str:
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    if not encrypted.startswith(b'v10'):
        raise MusicError('浏览器 Cookie 加密格式暂不支持；请交由维护者检查')
    try:
        key = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=b'saltysalt', iterations=1003).derive(password)
        decryptor = Cipher(algorithms.AES(key), modes.CBC(b' ' * 16)).decryptor()
        padded = decryptor.update(encrypted[3:]) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plain = unpadder.update(padded) + unpadder.finalize()
        if version >= 24:
            if plain[:32] != hashlib.sha256(host.encode()).digest():
                raise ValueError('host mismatch')
            plain = plain[32:]
        return plain.decode('utf-8')
    except (ValueError, UnicodeError) as exc:
        raise MusicError('浏览器 Cookie 无法解密；这不代表尚未登录') from exc


def build_cookie_header(url: str, browser='chrome', profile='Default') -> str:
    if sys.platform != 'darwin':
        raise MusicError('读取浏览器登录态目前只支持 Mac')
    if browser not in BROWSERS or not profile or Path(profile).name != profile or profile in ('.', '..'):
        raise MusicError('浏览器或个人资料名称无效')
    subdir, service, account = BROWSERS[browser]
    base = Path.home() / 'Library/Application Support' / subdir / profile
    db = next((p for p in (base / 'Cookies', base / 'Network/Cookies') if p.is_file()), None)
    if db is None:
        raise MusicError('没有找到所选浏览器的 Cookie 文件，请确认浏览器和个人资料')
    host = urlsplit(url).hostname or ''
    path = urlsplit(url).path or '/'
    password = None
    cookies = []
    try:
        with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=3) as connection:
            version_row = connection.execute("SELECT value FROM meta WHERE key='version'").fetchone()
            if not version_row:
                raise MusicError('浏览器 Cookie 数据版本无法读取')
            version = int(version_row[0])
            rows = connection.execute('SELECT host_key,name,value,encrypted_value,path,expires_utc,is_secure FROM cookies').fetchall()
        for domain, name, value, encrypted, cookie_path, expires, secure in rows:
            domain_name = domain.lstrip('.').lower()
            matches = host == domain_name or (domain.startswith('.') and host.endswith('.' + domain_name))
            if not matches or not (path == cookie_path or path.startswith(cookie_path.rstrip('/') + '/')):
                continue
            if secure and urlsplit(url).scheme != 'https':
                continue
            if expires and expires / 1e6 - 11644473600 <= time.time():
                continue
            if not value and encrypted:
                if password is None:
                    result = subprocess.run(['security', 'find-generic-password', '-w', '-s', service, '-a', account],
                                            capture_output=True, timeout=15, check=False)
                    if result.returncode or not result.stdout.strip():
                        raise MusicError('无法读取钥匙串中的浏览器密钥；这不代表尚未登录')
                    password = result.stdout.rstrip(b'\n')
                value = decrypt_cookie(bytes(encrypted), password, domain, version)
            if any(c in name + value for c in '\r\n'):
                raise MusicError('浏览器 Cookie 格式无法读取')
            cookies.append(f'{name}={value}')
    except (sqlite3.Error, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise MusicError('浏览器 Cookie 文件或密钥无法读取；这不代表尚未登录') from exc
    return '; '.join(cookies)
