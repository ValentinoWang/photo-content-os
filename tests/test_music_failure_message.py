"""Replay the recorded anonymous failure without touching the real library."""
import hashlib
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_music
from music_library.egress import SSHTunnel
from music_library.errors import DOUYIN_IMPORT_FAILURE_MESSAGE, MusicError, import_failure_message
from music_library.links import parse_link
from music_library.network import MusicOpener


def test_recorded_douyin_failure_cli_has_zero_requests_and_tunnels(tmp_path, monkeypatch, capsys):
    counts = {'requests': 0, 'tunnels': 0}

    def forbidden_request(*args, **kwargs):
        counts['requests'] += 1
        pytest.fail('Cached failure must not request a platform or read cookies')

    def forbidden_tunnel(*args, **kwargs):
        counts['tunnels'] += 1
        pytest.fail('Cached failure must not start a tunnel')

    monkeypatch.setattr(socket.socket, 'connect', forbidden_request)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden_request)
    monkeypatch.setattr(MusicOpener, 'open', forbidden_request)
    monkeypatch.setattr(SSHTunnel, 'start', forbidden_tunnel)
    import music_library.platforms
    monkeypatch.setattr(music_library.platforms, 'PlatformAdapter', forbidden_request)
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path))
    share = 'https://v.douyin.com/iSj4d8_TFGA/'
    link = parse_link(share)
    record = tmp_path / 'library/music/.attempts' / (hashlib.sha256(link.key.encode()).hexdigest() + '.json')
    record.parent.mkdir(parents=True)
    original = (Path(__file__).parent / 'fixtures/music-library/douyin-failed-attempt.json').read_bytes()
    record.write_bytes(original)

    assert import_music.main([share]) == 1
    assert capsys.readouterr().out == f'1. 失败：{DOUYIN_IMPORT_FAILURE_MESSAGE}\n'
    assert counts == {'requests': 0, 'tunnels': 0}
    assert record.read_bytes() == original
    assert not list((tmp_path / 'library/music').glob('*/track.json'))


def test_public_message_keeps_other_platform_errors_and_diagnostic():
    error = MusicError('HTTP 403 /aweme/detail 签名失败')
    assert import_failure_message('douyin', error) == DOUYIN_IMPORT_FAILURE_MESSAGE
    assert import_failure_message('netease', error) == str(error)
    assert str(error) == 'HTTP 403 /aweme/detail 签名失败'
