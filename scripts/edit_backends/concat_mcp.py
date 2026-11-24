"""Own one Concat headless stdio session and log its JSON-RPC traffic."""
from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import subprocess
import time

from .interface import BackendError


def _started_at(pid: int) -> str | None:
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "lstart="],
                            capture_output=True, text=True, timeout=2, check=False)
    return result.stdout.strip() or None if result.returncode == 0 else None


class ConcatMCP:
    """Single caller; the context manager initializes and reaps its own child."""

    def __init__(self, app: Path, root: Path, log_path: Path, *,
                 timeout: float = 15, close_timeout: float = 2):
        self._app = app
        self._root = root.resolve()
        self._log_path = log_path
        self._timeout = timeout
        self._close_timeout = close_timeout
        self._process = None
        self._started_at = None
        self._log = None
        self._next_id = 0
        self._pending = bytearray()

    @property
    def pid(self) -> int:
        return self._process.pid

    def __enter__(self):
        try:
            self._log = self._log_path.open("a", encoding="utf-8")
            stderr_path = self._log_path.with_suffix(".stderr.log")
            with stderr_path.open("ab") as stderr:
                self._process = subprocess.Popen(
                    [str(self._app / "Contents/MacOS/concat"), "--mcp", "headless"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                    bufsize=0, env={**os.environ, "CONCAT_MCP_ROOTS": str(self._root)},
                )
            self._started_at = _started_at(self.pid)
            self._record("process", {"pid": self.pid, "started_at": self._started_at,
                                     "stderr": str(stderr_path)})
            os.set_blocking(self._process.stdin.fileno(), False)
            os.set_blocking(self._process.stdout.fileno(), False)
            result = self._request("initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "content-os", "version": "1"},
            }, deadline=time.monotonic() + self._timeout, label="initialize")
            if result.get("protocolVersion") != "2025-06-18" or "tools" not in result.get("capabilities", {}):
                raise BackendError(f"unexpected_initialize_result:{result}")
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"},
                       time.monotonic() + self._timeout, "notifications/initialized")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            failure = BackendError(f"concat_handshake_failed:{exc}")
            self.__exit__(type(failure), failure, None)
            raise failure from exc
        except BaseException as exc:
            self.__exit__(type(exc), exc, None)
            raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except (OSError, BackendError, subprocess.SubprocessError) as close_error:
            if exc is None:
                raise
            exc.add_note(str(close_error))

    def _record(self, direction: str, message):
        self._log.write(json.dumps({"direction": direction, "message": message},
                                   ensure_ascii=False) + "\n")
        self._log.flush()

    def _ready(self, fd: int, event: int, deadline: float, label: str):
        remaining = deadline - time.monotonic()
        if remaining > 0:
            with selectors.DefaultSelector() as selector:
                selector.register(fd, event)
                if selector.select(remaining):
                    return
        raise BackendError(f"concat_timeout:{label}")

    def _send(self, message: dict, deadline: float, label: str):
        self._record("out", message)
        data = memoryview((json.dumps(message, ensure_ascii=False) + "\n").encode())
        fd = self._process.stdin.fileno()
        while data:
            self._ready(fd, selectors.EVENT_WRITE, deadline, label)
            try:
                data = data[os.write(fd, data):]
            except BlockingIOError:
                continue

    def _receive(self, request_id: int, deadline: float, label: str) -> dict:
        fd = self._process.stdout.fileno()
        while time.monotonic() < deadline:
            end = self._pending.find(b"\n")
            if end == -1:
                self._ready(fd, selectors.EVENT_READ, deadline, label)
                try:
                    block = os.read(fd, 65536)
                except BlockingIOError:
                    continue
                if not block:
                    raise BackendError(f"concat_stdout_closed:{label}:exit={self._process.poll()}")
                self._pending.extend(block)
                continue
            line = bytes(self._pending[:end])
            del self._pending[:end + 1]
            try:
                message = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                self._record("in-raw", line.decode(errors="replace"))
                raise BackendError(f"concat_invalid_response:{label}:{exc}") from exc
            self._record("in", message)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise BackendError(f"concat_invalid_response:{label}:{message}")
            if message.get("id") == request_id:
                return message
        raise BackendError(f"concat_timeout:{label}")

    def _request(self, method: str, params: dict, *, deadline: float, label: str) -> dict:
        self._next_id += 1
        request_id = self._next_id
        try:
            self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                       deadline, label)
            response = self._receive(request_id, deadline, label)
        except OSError as exc:
            raise BackendError(f"concat_io_error:{label}:{exc}") from exc
        if "error" in response:
            error = response["error"]
            original = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            self._tool_error(label, original)
        result = response.get("result")
        if not isinstance(result, dict):
            raise BackendError(f"concat_invalid_result:{label}:{result}")
        return result

    @staticmethod
    def _tool_error(tool: str, original: str):
        raise BackendError(f"concat_tool_error:{tool}:{original.splitlines()[0] if original else ''}")

    def call(self, tool: str, args: dict, *, timeout: float | None = None) -> dict:
        deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
        result = self._request("tools/call", {"name": tool, "arguments": args},
                               deadline=deadline, label=tool)
        original = "\n".join(block["text"] for block in result.get("content", [])
                             if block.get("type") == "text")
        if result.get("isError"):
            self._tool_error(tool, original)
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        try:
            data = json.loads(original)
        except ValueError as exc:
            raise BackendError(f"concat_invalid_result:{tool}:{original}") from exc
        if not isinstance(data, dict):
            raise BackendError(f"concat_invalid_result:{tool}:{original}")
        return data

    def close(self):
        process = self._process
        try:
            if process is not None and not process.stdin.closed:
                process.stdin.close()
            if process is not None and process.stdout and not process.stdout.closed:
                stopped = False
                try:
                    for stop in (None, process.terminate, process.kill):
                        if stop is not None and process.poll() is None:
                            if self._started_at is None or _started_at(self.pid) != self._started_at:
                                if process.poll() is None:
                                    raise BackendError(f"concat_process_identity_unverified:{self.pid}")
                            else:
                                stop()
                                stopped = True
                        try:
                            process.wait(timeout=self._close_timeout)
                            break
                        except subprocess.TimeoutExpired:
                            if stop == process.kill:
                                raise
                    self._record("process_exit", {"pid": self.pid, "returncode": process.returncode})
                    if process.returncode and not stopped:
                        raise BackendError(f"concat_process_failed:{process.returncode}")
                finally:
                    process.stdout.close()
        finally:
            if self._log is not None and not self._log.closed:
                self._log.close()
