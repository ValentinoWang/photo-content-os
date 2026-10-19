"""Offline NCM conversion and client metadata, adapted from MIT ncmdump's format.

See THIRD_PARTY_NOTICES.md for the upstream copyright and permission notice.
"""
import base64
import json
import struct
import subprocess
from pathlib import Path

from .errors import MusicError

CORE_KEY = b'hzHRAmso5kInbaxW'
META_KEY = b"#14ljk_!\\]&0U<'("


def aes_decrypt(data, key):
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    padded = decryptor.update(data) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def decode_ncm(path: Path, output_dir: Path):
    try:
        with path.open('rb') as handle:
            def take(length):
                if not 0 <= length <= 64 * 1024 * 1024:
                    raise ValueError('invalid length')
                value = handle.read(length)
                if len(value) != length:
                    raise ValueError('truncated')
                return value
            def integer():
                return struct.unpack('<I', take(4))[0]
            if take(8) != b'CTENFDAM':
                raise ValueError('header')
            take(2)
            secret = aes_decrypt(bytes(c ^ 0x64 for c in take(integer())), CORE_KEY)
            if not secret.startswith(b'neteasecloudmusic') or len(secret) <= 17:
                raise ValueError('key prefix')
            key = secret[17:]
            box = list(range(256))
            last = 0
            for index in range(256):
                last = (box[index] + last + key[index % len(key)]) & 255
                box[index], box[last] = box[last], box[index]
            encoded = bytes(c ^ 0x63 for c in take(integer()))
            metadata = {}
            if encoded:
                if not encoded.startswith(b"163 key(Don't modify):"):
                    raise ValueError('metadata prefix')
                plain = aes_decrypt(base64.b64decode(encoded[22:], validate=True), META_KEY)
                if not plain.startswith(b'music:'):
                    raise ValueError('metadata format')
                metadata = json.loads(plain[6:])
                if not isinstance(metadata, dict):
                    raise ValueError('metadata object')
            take(5)
            cover_capacity, cover_length = integer(), integer()
            if cover_length > cover_capacity:
                raise ValueError('cover length')
            take(cover_capacity)
            # NCM repeats this 256-byte mask for the whole audio payload.
            mask = bytes(box[(box[j] + box[(box[j] + j) & 255]) & 255] for j in list(range(1, 256)) + [0])
            first = handle.read(32768)
            if not first:
                raise ValueError('no audio')
            first = bytes(c ^ mask[i % 256] for i, c in enumerate(first))
            if first.startswith(b'fLaC'):
                extension = '.flac'
            elif first.startswith(b'ID3') or (first[0] == 255 and first[1] & 224 == 224):
                extension = '.mp3'
            else:
                raise ValueError('unknown audio')
            output = output_dir / ('decoded' + extension)
            with output.open('wb') as target:
                target.write(first)
                while block := handle.read(32768):
                    target.write(bytes(c ^ mask[i % 256] for i, c in enumerate(block)))
            return output, normalize_metadata(metadata, path.stem)
    except (OSError, ValueError, IndexError, TypeError, struct.error) as exc:
        raise MusicError('网易云加密文件损坏或格式暂不支持，未入库，原文件未改动') from exc


def normalize_metadata(value, fallback):
    identity = value.get('musicId') or value.get('id')
    if identity is not None and not str(identity).isdigit():
        raise MusicError('客户端下载文件中的歌曲编号格式无法读取')
    artists = value.get('artist') or []
    artist = ' / '.join(a[0] for a in artists if isinstance(a, list) and a and isinstance(a[0], str))
    return {'platform_id': str(identity) if identity else None,
            'title': value.get('musicName') or value.get('title') or fallback,
            'artist': artist or value.get('artist_text') or '未知歌手',
            'album': value.get('album'), 'license_status': 'platform_copyrighted'}


def read_client_metadata(path: Path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format_tags', '-of', 'json', str(path)],
                                capture_output=True, text=True, check=True, timeout=60)
        tags = {k.lower(): v for k, v in json.loads(result.stdout).get('format', {}).get('tags', {}).items()}
        # NetEase stores its encrypted metadata in the 163-key comment on MP3/FLAC.
        comment = tags.get('comment') or tags.get('description') or ''
        if comment.startswith("163 key(Don't modify):"):
            raw = aes_decrypt(base64.b64decode(comment[22:], validate=True), META_KEY)
            if not raw.startswith(b'music:'):
                raise ValueError('comment prefix')
            return normalize_metadata(json.loads(raw[6:]), path.stem)
        return normalize_metadata({'musicId': tags.get('musicid') or tags.get('netease_music_id'),
                                   'title': tags.get('title'), 'artist_text': tags.get('artist'), 'album': tags.get('album')}, path.stem)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        raise MusicError('客户端下载文件的音频标签无法读取，尚未入库') from exc
