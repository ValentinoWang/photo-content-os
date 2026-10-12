"""ChatCut registration, local MCP handshake and secret-free studio state."""

from __future__ import annotations

import subprocess
import json
import os
import selectors
import time
import urllib.request
from urllib.parse import urlsplit
from dataclasses import dataclass
from typing import Callable, Literal, Sequence


PROBE_COMMAND = ("codex", "mcp", "get", "chatcut_desktop")
DEFAULT_PROBE_TIMEOUT_SECONDS = 3.0
MAX_PROBE_TIMEOUT_SECONDS = 5.0
SCHEMA_VERSION = "chatcut_desktop_local_mcp_v1"

ChatCutStatus = Literal[
    "hidden",
    "unavailable",
    "awaiting_confirmation",
    "connected",
]
CommandExecutor = Callable[[Sequence[str], float], object]


@dataclass(frozen=True)
class ProbeCommandResult:
    """The only command result detail needed by the state machine."""

    returncode: int


@dataclass(frozen=True)
class ChatCutMcpState:
    """Serializable, deliberately secret-free public state."""

    schema_version: str
    status: ChatCutStatus
    visible: bool
    available: bool
    can_connect: bool
    reason_code: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "visible": self.visible,
            "available": self.available,
            "can_connect": self.can_connect,
            "reason_code": self.reason_code,
        }


def _state(
    status: ChatCutStatus,
    *,
    visible: bool,
    available: bool,
    can_connect: bool,
    reason_code: str | None,
) -> ChatCutMcpState:
    return ChatCutMcpState(
        schema_version=SCHEMA_VERSION,
        status=status,
        visible=visible,
        available=available,
        can_connect=can_connect,
        reason_code=reason_code,
    )


def default_state() -> dict[str, object]:
    """Return the hidden state without executing a probe."""

    return _state(
        "hidden",
        visible=False,
        available=False,
        can_connect=False,
        reason_code=None,
    ).to_dict()


def _subprocess_executor(command: Sequence[str], timeout_seconds: float) -> ProbeCommandResult:
    """Run the one supported local probe without retaining its output."""

    completed = subprocess.run(
        list(command),
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout_seconds,
    )
    return ProbeCommandResult(returncode=completed.returncode)


def _returncode(result: object) -> int:
    if isinstance(result, int) and not isinstance(result, bool):
        return result
    value = getattr(result, "returncode", None)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("command result has no valid return code")
    return value


class ChatCutMcp:
    """Manage optional local MCP capability and explicit user confirmation."""

    def __init__(
        self,
        *,
        executor: CommandExecutor | None = None,
        handshake: Callable[[], object] | None = None,
        timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    ) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError("timeout_seconds must be a number")
        if not 0 < float(timeout_seconds) <= MAX_PROBE_TIMEOUT_SECONDS:
            raise ValueError("timeout_seconds must be short and positive")
        if executor is not None and not callable(executor):
            raise TypeError("executor must be callable")

        self._executor = executor if executor is not None else _subprocess_executor
        self._handshake = handshake
        self._timeout_seconds = float(timeout_seconds)
        self._state = ChatCutMcpState(
            schema_version=SCHEMA_VERSION,
            status="hidden",
            visible=False,
            available=False,
            can_connect=False,
            reason_code=None,
        )

    @property
    def state(self) -> dict[str, object]:
        """Return a fresh state mapping with no command details."""

        return self._state.to_dict()

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def _probe_once(self) -> tuple[bool, str | None]:
        try:
            result = self._executor(list(PROBE_COMMAND), self._timeout_seconds)
        except (subprocess.TimeoutExpired, TimeoutError):
            return False, "probe_timeout"
        except FileNotFoundError:
            return False, "command_missing"
        except OSError:
            return False, "probe_error"
        except Exception:
            return False, "probe_error"

        try:
            returncode = _returncode(result)
        except (TypeError, ValueError, AttributeError):
            return False, "probe_error"
        if returncode == 0:
            return True, None
        return False, "probe_failed"

    def probe(self) -> dict[str, object]:
        """Run a user-triggered capability probe."""

        success, reason_code = self._probe_once()
        if success:
            self._state = _state(
                "awaiting_confirmation",
                visible=True,
                available=False,
                can_connect=True,
                reason_code=None,
            )
        else:
            self._state = _state(
                "unavailable",
                visible=True,
                available=False,
                can_connect=False,
                reason_code=reason_code or "probe_error",
            )
        return self.state

    def confirm_connection(self) -> dict[str, object]:
        """Re-probe after explicit confirmation before becoming connected."""

        if self._state.status != "awaiting_confirmation":
            return self.state

        success, reason_code = self._probe_once()
        if success:
            try:
                if self._handshake is not None:
                    if self._handshake() is not True:
                        raise McpError("handshake_failed")
                else:
                    with LocalMcpSession(timeout_seconds=self._timeout_seconds) as session:
                        session.list_tools()
            except Exception:
                self._state = _state(
                    "unavailable", visible=True, available=False,
                    can_connect=False, reason_code="handshake_failed",
                )
                return self.state
            self._state = _state(
                "connected",
                visible=True,
                available=True,
                can_connect=False,
                reason_code=None,
            )
        else:
            self._state = _state(
                "unavailable",
                visible=True,
                available=False,
                can_connect=False,
                reason_code=reason_code or "probe_error",
            )
        return self.state

    def reset(self) -> dict[str, object]:
        """Hide the optional integration and clear its transient state."""

        self._state = ChatCutMcpState(
            schema_version=SCHEMA_VERSION,
            status="hidden",
            visible=False,
            available=False,
            can_connect=False,
            reason_code=None,
        )
        return self.state

__all__ = [
    "ChatCutMcp",
    "ChatCutMcpState",
    "CommandExecutor",
    "DEFAULT_PROBE_TIMEOUT_SECONDS",
    "MAX_PROBE_TIMEOUT_SECONDS",
    "PROBE_COMMAND",
    "ProbeCommandResult",
    "SCHEMA_VERSION",
    "default_state",
]


class McpError(RuntimeError):
    """A local transport or protocol failure with a secret-free reason."""


def read_registration(timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS) -> dict:
    result = subprocess.run(
        [*PROBE_COMMAND, "--json"], capture_output=True, text=True,
        timeout=timeout_seconds, check=False,
    )
    if result.returncode:
        raise McpError("mcp_not_registered")
    try:
        config = json.loads(result.stdout)
        if not isinstance(config, dict) or not isinstance(config.get("transport"), dict):
            raise ValueError()
    except ValueError as exc:
        raise McpError("mcp_registration_invalid") from exc
    if config.get("enabled") is False:
        raise McpError("mcp_disabled")
    return config


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise McpError("mcp_redirect_rejected")


class LocalMcpSession:
    """MCP JSON-RPC over registered stdio or loopback Streamable HTTP only.

    A session owns only its launched stdio child. No application process or
    other MCP client is stopped. Credentials never enter studio state.
    """

    def __init__(self, config: dict | None = None, *, timeout_seconds: float = 5):
        self.config = config
        self.timeout = timeout_seconds
        self.process = None
        self.selector = None
        self.buffer = b""
        self.sequence = 0
        self.session_id = None
        self.protocol = "2024-11-05"

    def __enter__(self):
        try:
            config = self.config if self.config is not None else read_registration(self.timeout)
            transport = config["transport"]
            self.transport = transport
            if transport["type"] == "stdio":
                command = transport.get("command")
                args = transport.get("args", [])
                if not isinstance(command, str) or not isinstance(args, list) or not all(isinstance(v, str) for v in args):
                    raise McpError("mcp_registration_invalid")
                self.process = subprocess.Popen(
                    [command, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env={**os.environ, **(transport.get("env") or {})},
                    cwd=transport.get("cwd") or None, bufsize=0,
                )
                self.selector = selectors.DefaultSelector()
                self.selector.register(self.process.stdout, selectors.EVENT_READ)
            elif transport["type"] == "streamable_http":
                url = urlsplit(transport["url"])
                if url.scheme not in {"http", "https"} or url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.username or url.password:
                    raise McpError("mcp_nonlocal_transport_rejected")
                self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            else:
                raise McpError("mcp_transport_unsupported")
            initialized = self.request("initialize", {
                "protocolVersion": self.protocol, "capabilities": {},
                "clientInfo": {"name": "photo-content-os", "version": "1"},
            })
            if not isinstance(initialized.get("serverInfo"), dict) or not isinstance(initialized.get("protocolVersion"), str):
                raise McpError("mcp_initialize_invalid")
            self.protocol = initialized["protocolVersion"]
            self.request("notifications/initialized", {}, notification=True)
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.selector is not None:
            self.selector.close()
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None

    def request(self, method: str, params: dict, *, notification: bool = False) -> dict:
        self.sequence += 1
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            message["id"] = self.sequence
        payload = json.dumps(message, ensure_ascii=False).encode()
        deadline = time.monotonic() + self.timeout
        if self.process is not None:
            try:
                self.process.stdin.write(payload + b"\n")
                self.process.stdin.flush()
            except OSError as exc:
                raise McpError("mcp_connection_closed") from exc
            if notification:
                return {}
            while time.monotonic() < deadline:
                while b"\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\n", 1)
                    reply = json.loads(line)
                    if reply.get("id") == self.sequence and ("result" in reply or "error" in reply):
                        return self._result(reply)
                    if "method" in reply and "id" in reply:
                        self.process.stdin.write(json.dumps({
                            "jsonrpc": "2.0", "id": reply["id"],
                            "error": {"code": -32601, "message": "unsupported client request"},
                        }).encode() + b"\n")
                if not self.selector.select(max(0, deadline - time.monotonic())):
                    break
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise McpError("mcp_connection_closed")
                self.buffer += chunk
            raise McpError("mcp_timeout")
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": self.protocol, **(self.transport.get("http_headers") or {})}
        for name, variable in (self.transport.get("env_http_headers") or {}).items():
            if variable not in os.environ:
                raise McpError("mcp_auth_unavailable")
            headers[name] = os.environ[variable]
        token_var = self.transport.get("bearer_token_env_var")
        if token_var:
            if token_var not in os.environ:
                raise McpError("mcp_auth_unavailable")
            headers["Authorization"] = "Bearer " + os.environ[token_var]
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(self.transport["url"], data=payload, headers=headers, method="POST")
        with self.opener.open(req, timeout=self.timeout) as response:
            self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
            if notification:
                return {}
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                for line in response:
                    if time.monotonic() > deadline:
                        raise McpError("mcp_timeout")
                    if line.startswith(b"data:"):
                        reply = json.loads(line[5:])
                        if reply.get("id") == self.sequence:
                            return self._result(reply)
                raise McpError("mcp_response_missing")
            reply = json.loads(response.read())
            if reply.get("id") != self.sequence:
                raise McpError("mcp_response_id_mismatch")
            return self._result(reply)

    @staticmethod
    def _result(reply):
        if "error" in reply or not isinstance(reply.get("result"), dict):
            raise McpError("mcp_request_failed")
        return reply["result"]

    def list_tools(self) -> list[dict]:
        tools, cursors = [], set()
        params = {}
        while True:
            result = self.request("tools/list", params)
            batch = result.get("tools")
            if not isinstance(batch, list) or not all(isinstance(t, dict) and isinstance(t.get("name"), str) and isinstance(t.get("inputSchema"), dict) for t in batch):
                raise McpError("mcp_tool_schema_invalid")
            tools.extend(batch)
            cursor = result.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or cursor in cursors:
                raise McpError("mcp_cursor_invalid")
            cursors.add(cursor)
            params = {"cursor": cursor}
        if len({tool["name"] for tool in tools}) != len(tools):
            raise McpError("mcp_duplicate_tools")
        return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise McpError("mcp_tool_failed")
        return result
