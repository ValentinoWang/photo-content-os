"""Focused tests for the optional ChatCut Desktop local MCP state machine."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.chatcut_mcp import (
    DEFAULT_PROBE_TIMEOUT_SECONDS,
    MAX_PROBE_TIMEOUT_SECONDS,
    PROBE_COMMAND,
    ChatCutMcp,
    ProbeCommandResult,
    default_state,
)


class FakeResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeExecutor:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[list[str], float]] = []

    def __call__(self, command: list[str], timeout_seconds: float) -> object:
        self.calls.append((command, timeout_seconds))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class ChatCutMcpTests(unittest.TestCase):
    def test_default_state_is_hidden_without_probe(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0))
        client = ChatCutMcp(executor=executor)

        self.assertEqual(client.state, default_state())
        self.assertEqual(client.state["status"], "hidden")
        self.assertFalse(client.state["visible"])
        self.assertEqual(executor.calls, [])

    def test_probe_uses_the_exact_public_command_and_short_timeout(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0))
        client = ChatCutMcp(executor=executor)

        state = client.probe()

        self.assertEqual(executor.calls, [(list(PROBE_COMMAND), DEFAULT_PROBE_TIMEOUT_SECONDS)])
        self.assertEqual(state["status"], "awaiting_confirmation")
        self.assertTrue(state["visible"])
        self.assertFalse(state["available"])
        self.assertTrue(state["can_connect"])
        self.assertIsNone(state["reason_code"])
        self.assertLessEqual(executor.calls[0][1], MAX_PROBE_TIMEOUT_SECONDS)

    def test_successful_probe_waits_for_explicit_confirmation(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0))
        client = ChatCutMcp(executor=executor)

        client.probe()

        self.assertNotEqual(client.state["status"], "connected")
        self.assertFalse(client.state["available"])
        self.assertEqual(len(executor.calls), 1)

    def test_confirmation_reprobes_before_connected_state(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0), ProbeCommandResult(0))
        client = ChatCutMcp(executor=executor)

        client.probe()
        state = client.confirm_connection()

        self.assertEqual(len(executor.calls), 2)
        self.assertEqual(executor.calls[0][0], list(PROBE_COMMAND))
        self.assertEqual(executor.calls[1][0], list(PROBE_COMMAND))
        self.assertEqual(state["status"], "connected")
        self.assertTrue(state["available"])
        self.assertFalse(state["can_connect"])

    def test_confirmation_without_probe_is_fail_closed_and_does_not_probe(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0))
        client = ChatCutMcp(executor=executor)

        state = client.confirm_connection()

        self.assertEqual(state["status"], "hidden")
        self.assertFalse(state["available"])
        self.assertEqual(executor.calls, [])

    def test_timeout_missing_failure_and_exception_are_unavailable(self) -> None:
        cases = (
            (
                subprocess.TimeoutExpired(list(PROBE_COMMAND), DEFAULT_PROBE_TIMEOUT_SECONDS),
                "probe_timeout",
            ),
            (FileNotFoundError(), "command_missing"),
            (ProbeCommandResult(23), "probe_failed"),
            (RuntimeError("private executor detail"), "probe_error"),
        )
        for outcome, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                executor = FakeExecutor(outcome)
                client = ChatCutMcp(executor=executor)

                state = client.probe()

                self.assertEqual(state["status"], "unavailable")
                self.assertTrue(state["visible"])
                self.assertFalse(state["available"])
                self.assertEqual(state["reason_code"], reason_code)

    def test_failed_connection_reprobe_never_becomes_available(self) -> None:
        executor = FakeExecutor(ProbeCommandResult(0), ProbeCommandResult(9))
        client = ChatCutMcp(executor=executor)

        client.probe()
        state = client.confirm_connection()

        self.assertEqual(state["status"], "unavailable")
        self.assertFalse(state["available"])
        self.assertEqual(state["reason_code"], "probe_failed")

    def test_command_output_is_not_exposed_in_state(self) -> None:
        executor = FakeExecutor(
            FakeResult(0, stdout="account-token media-path", stderr="secret diagnostic")
        )
        client = ChatCutMcp(executor=executor)

        state_text = json.dumps(client.probe(), sort_keys=True)

        self.assertNotIn("account-token", state_text)
        self.assertNotIn("media-path", state_text)
        self.assertNotIn("secret diagnostic", state_text)
        self.assertNotIn("codex", state_text)

    @mock.patch("desktop.chatcut_mcp.subprocess.run")
    def test_default_executor_discards_output_and_uses_short_timeout(
        self, run: mock.Mock
    ) -> None:
        run.return_value = mock.Mock(returncode=0)
        client = ChatCutMcp()

        state = client.probe()

        self.assertEqual(state["status"], "awaiting_confirmation")
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(args[0], list(PROBE_COMMAND))
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertLessEqual(kwargs["timeout"], MAX_PROBE_TIMEOUT_SECONDS)

    def test_implementation_imports_only_local_process_support(self) -> None:
        source = (SYSTEM_ROOT / "desktop" / "chatcut_mcp.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [node])
        }

        self.assertLessEqual(imported_modules, {"__future__", "dataclasses", "subprocess", "typing"})


if __name__ == "__main__":
    unittest.main()
