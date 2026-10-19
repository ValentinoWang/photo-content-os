"""Private SSH egress; no remote commands, retries, or direct fallback."""
import atexit
import hashlib
import json
import re
import socket
import stat
import subprocess
import time

from .errors import MusicError, NetworkFailure
from .netease import config_dir
from .network import MusicOpener


def read_target(path=None):
    path = path or config_dir() / 'egress.json'
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MusicError('音乐出口配置无法读取；未退回直连') from exc
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise MusicError('音乐出口配置必须是权限 600 的普通文件；未退回直连')
    try:
        value = json.loads(path.read_text())
        target = value['ssh_target']
        if set(value) != {'ssh_target'} or not isinstance(target, str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*', target):
            raise ValueError('invalid target')
        return target
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise MusicError('音乐出口配置无法读取或格式无效；未退回直连') from exc


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.1):
            return True
    except OSError:
        return False


class SSHTunnel:
    def __init__(self, target, *, spawn=subprocess.Popen, port_factory=free_port, ready=listening):
        self.target, self.spawn, self.port_factory, self.ready = target, spawn, port_factory, ready
        self.process = None
        self.proxy = None
        self.starts = 0

    def ensure_alive(self):
        if self.process is None or self.process.poll() is not None:
            raise NetworkFailure('音乐出口隧道不可用或已断开；未退回直连', {'failure_class': 'egress_unavailable'})

    def start(self):
        if self.process is not None:
            self.ensure_alive()
            return
        port = self.port_factory()
        args = ['ssh', '-T', '-N', '-D', f'127.0.0.1:{port}', '-o', 'ExitOnForwardFailure=yes',
                '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', '-o', 'BatchMode=yes',
                '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', self.target]
        try:
            self.process = self.spawn(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.starts += 1
            atexit.register(self.close)
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                self.ensure_alive()
                if self.ready(port):
                    self.proxy = f'socks5h://127.0.0.1:{port}'
                    return
                time.sleep(.05)
            raise MusicError('音乐出口隧道启动超时；未退回直连')
        except OSError as exc:
            self.close()
            raise NetworkFailure('音乐出口隧道无法启动；未退回直连', {'failure_class': 'egress_start_failed'}) from exc
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        atexit.unregister(self.close)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()


class TunnelOpener:
    def __init__(self, tunnel):
        self.tunnel = tunnel
        self.transport = None
        self.proxy = 'socks5h://pending'

    def open(self, request, timeout):
        self.tunnel.start()
        self.tunnel.ensure_alive()
        if self.transport is None:
            self.proxy = self.tunnel.proxy
            self.transport = MusicOpener(proxy=self.proxy)
        return self.transport.open(request, timeout)

    def close(self):
        try:
            if self.transport is not None:
                self.transport.session.close()
        finally:
            self.tunnel.close()


def cache_partition(target):
    return 'egress-' + hashlib.sha256(target.encode()).hexdigest()[:16]
