"""Build an openly inspectable NCM container around a synthetic sine wave."""
import base64
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt(data, key):
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return cipher.update(padded) + cipher.finalize()


def build(payload, metadata):
    raw_key = b'synthetic-key-for-tests'
    encrypted_key = bytes(v ^ 0x64 for v in encrypt(b'neteasecloudmusic' + raw_key, b'hzHRAmso5kInbaxW'))
    encrypted_metadata = b"163 key(Don't modify):" + base64.b64encode(encrypt(b'music:' + json.dumps(metadata).encode(), b"#14ljk_!\\]&0U<'("))
    encoded_metadata = bytes(v ^ 0x63 for v in encrypted_metadata)
    state = list(range(256))
    cursor = 0
    for i in range(256):
        cursor = (cursor + state[i] + raw_key[i % len(raw_key)]) % 256
        state[i], state[cursor] = state[cursor], state[i]
    stream = bytearray()
    for offset, value in enumerate(payload):
        j = (offset + 1) % 256
        stream.append(value ^ state[(state[j] + state[(state[j] + j) % 256]) % 256])
    length = lambda value: struct.pack('<I', len(value)) + value
    return b'CTENFDAM\0\0' + length(encrypted_key) + length(encoded_metadata) + b'\0' * 13 + stream


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as folder:
        mp3 = Path(folder) / 'sine.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                        '-c:a', 'libmp3lame', str(mp3)], check=True)
        payload = mp3.read_bytes()
        metadata = {'musicId': 90001, 'musicName': '合成测试曲', 'artist': [['合成歌手', 1]], 'album': '合成专辑', 'format': 'mp3'}
        (root / 'synthetic.ncm').write_bytes(build(payload, metadata))
        import hashlib
        (root / 'synthetic-audio.sha256').write_text(hashlib.sha256(payload).hexdigest() + '\n')
