"""Offline tunnel ownership and per-platform routing regressions."""
import json
import sys
from pathlib import Path
from contextlib import contextmanager

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.errors import MusicError


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket
    def forbidden(*a, **k): raise AssertionError('offline tests cannot open sockets')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def test_bad_config_never_means_direct(tmp_path):
    from music_library.egress import read_target
    path = tmp_path / 'egress.json'
    assert read_target(path) is None
    path.write_text('{bad')
    path.chmod(0o600)
    with pytest.raises(MusicError, match='出口配置'):
        read_target(path)
    path.write_text(json.dumps({'ssh_target': 'user@host.example'}))
    path.chmod(0o644)
    with pytest.raises(MusicError, match='600'):
        read_target(path)
    path.chmod(0o600)
    assert read_target(path) == 'user@host.example'
    for value in ['-oProxyCommand=bad', 'user@host command', 'user@host\ncommand']:
        path.write_text(json.dumps({'ssh_target': value}))
        with pytest.raises(MusicError): read_target(path)


@pytest.mark.parametrize('failure', [None, RuntimeError, KeyboardInterrupt])
def test_tunnel_always_closed_on_exit(failure):
    from music_library.egress import SSHTunnel
    class Process:
        stopped = False
        def poll(self): return 0 if self.stopped else None
        def terminate(self): self.stopped = True
        def wait(self, timeout): return 0
    process = Process()
    calls = []
    tunnel = SSHTunnel('user@host.example', spawn=lambda args, **kw: (calls.append(args) or process),
                       port_factory=lambda: 19000, ready=lambda port: True)
    try:
        with tunnel:
            assert tunnel.proxy == 'socks5h://127.0.0.1:19000'
            if failure: raise failure()
    except (RuntimeError, KeyboardInterrupt): pass
    assert process.stopped
    assert calls[0][-1] == 'user@host.example'
    assert '-N' in calls[0] and '-D' in calls[0]
    assert not any('ProxyCommand' in arg for arg in calls[0])


def test_tunnel_death_never_restarts_or_falls_back():
    from music_library.egress import SSHTunnel
    class Process:
        code = None
        def poll(self): return self.code
        def terminate(self): self.code = 0
        def wait(self, timeout): pass
    process = Process()
    tunnel = SSHTunnel('user@host.example', spawn=lambda *a, **k: process,
                       port_factory=lambda: 19000, ready=lambda p: True)
    with tunnel:
        process.code = 255
        with pytest.raises(MusicError, match='隧道.*直连'): tunnel.ensure_alive()


def test_duplicate_does_not_construct_adapter_or_start_tunnel(tmp_path, monkeypatch):
    from music_library.library import MusicLibrary
    from music_library.cache import write_json
    from music_library.links import parse_link
    import hashlib
    lib = MusicLibrary(tmp_path)
    link = parse_link('https://music.163.com/song?id=90001')
    lib.root.mkdir(parents=True)
    (lib.root / '.attempts').mkdir()
    write_json(lib.root / '.attempts' / (hashlib.sha256(link.key.encode()).hexdigest()+'.json'),
               {'state': 'complete', 'file_sha256': 'synthetic'})
    monkeypatch.setattr(lib, '_tracks', lambda: [{'file_sha256': 'synthetic', 'sources': []}])
    monkeypatch.setattr('music_library.platforms.PlatformAdapter', lambda *a, **k: pytest.fail('must not create adapter'))
    assert lib.import_link(link.url)[0] == '已在库里'


def test_only_netease_qishui_route_through_lazy_tunnel(tmp_path, monkeypatch):
    from music_library.platforms import PlatformAdapter
    from music_library.egress import TunnelOpener
    monkeypatch.setattr('music_library.egress.read_target', lambda: 'user@host.example')
    adapter = PlatformAdapter(tmp_path)
    for platform in ('netease', 'qishui'):
        with adapter.import_context(platform):
            assert isinstance(adapter.http.opener, TunnelOpener)
            assert adapter.http.opener.tunnel.process is None
    with adapter.import_context('douyin'):
        assert adapter.http.opener.proxy == ''
        assert not isinstance(adapter.http.opener, TunnelOpener)


def test_start_failure_is_explicit_without_retry():
    from music_library.egress import SSHTunnel
    calls = []
    def spawn(*a, **k):
        calls.append(1)
        raise OSError('private target must never appear')
    tunnel = SSHTunnel('user@host.example', spawn=spawn, port_factory=lambda: 19000)
    with pytest.raises(MusicError, match='隧道无法启动.*未.*直连') as error:
        tunnel.start()
    assert len(calls) == 1 and 'private target' not in str(error.value)


def test_starting_ssh_exit_is_reported_and_not_restarted():
    from music_library.egress import SSHTunnel
    class Process:
        def poll(self): return 255
    calls = []
    tunnel = SSHTunnel('user@host.example', spawn=lambda *a, **k: (calls.append(1) or Process()),
                       port_factory=lambda: 19000, ready=lambda p: pytest.fail('process already exited'))
    with pytest.raises(MusicError, match='隧道不可用.*未.*直连'):
        tunnel.start()
    assert len(calls) == 1
