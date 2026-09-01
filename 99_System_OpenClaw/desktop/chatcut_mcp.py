"""Optional ChatCut Desktop local MCP capability probing.

The integration is deliberately capability-only. It probes the public local
Codex command and keeps the command result out of the exposed state.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable, Literal, Sequence


PROBE_COMMAND = ("codex", "mcp", "get", "chatcut")
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
        timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    ) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError("timeout_seconds must be a number")
        if not 0 < float(timeout_seconds) <= MAX_PROBE_TIMEOUT_SECONDS:
            raise ValueError("timeout_seconds must be short and positive")
        if executor is not None and not callable(executor):
            raise TypeError("executor must be callable")

        self._executor = executor if executor is not None else _subprocess_executor
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

    # These names keep the user actions explicit while offering concise callers.
    trigger_probe = probe
    confirm = confirm_connection
    connect = confirm_connection


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
