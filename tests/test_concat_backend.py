"""Concat contract tests with a real stdio child and synthetic tool responses."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_backends.concat_mcp import ConcatMCP
from edit_backends.interface import BackendError


SERVER = """\
import json
import os
import signal
import sys
import time

assert sys.argv[1:] == ["--mcp", "headless"]
signal.signal(signal.SIGTERM, signal.SIG_IGN)
initialized = False
for line in sys.stdin:
    msg = json.loads(line)
    method = msg["method"]
    if method == "notifications/initialized":
        initialized = True
        continue
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}}
    else:
        assert initialized
        name = msg["params"]["name"]
        if name == "stall":
            sys.stdout.write('{"jsonrpc":')
            sys.stdout.flush()
            time.sleep(60)
        if name == "rpc_error":
            print(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                              "error": {"code": -32602, "message": "参数错误"}}), flush=True)
            continue
        if name == "fail":
            result = {"isError": True, "content": [{"type": "text", "text": "原始错误\\n详情"}]}
        else:
            data = {"root": os.environ["CONCAT_MCP_ROOTS"], "args": msg["params"]["arguments"]}
            result = {"content": [{"type": "text", "text": json.dumps(data)}]}
    print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
"""


@pytest.fixture
def fake_app(tmp_path):
    app = tmp_path / "Concat.app"
    binary = app / "Contents/MacOS/concat"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!{sys.executable}\n" + SERVER, encoding="utf-8")
    binary.chmod(0o755)
    return app


def test_stdio_handshake_call_and_log(fake_app, tmp_path):
    log = tmp_path / "calls.jsonl"
    with ConcatMCP(fake_app, tmp_path, log) as mcp:
        assert mcp.call("echo", {"text": "字幕"}) == {
            "root": str(tmp_path.resolve()), "args": {"text": "字幕"},
        }
    sent = [row["message"] for line in log.read_text().splitlines()
            if (row := json.loads(line))["direction"] == "out"]
    assert [row["method"] for row in sent] == [
        "initialize", "notifications/initialized", "tools/call",
    ]


@pytest.mark.parametrize(("tool", "message"), [("fail", "原始错误"), ("rpc_error", "参数错误")])
def test_stdio_preserves_tool_error(fake_app, tmp_path, tool, message):
    with ConcatMCP(fake_app, tmp_path, tmp_path / "calls.jsonl") as mcp:
        with pytest.raises(BackendError) as exc:
            mcp.call(tool, {})
        assert str(exc.value) == f"concat_tool_error:{tool}:{message}"


def test_stdio_timeout_and_owned_process_cleanup(fake_app, tmp_path):
    binary = fake_app / "Contents/MacOS/concat"
    peer = subprocess.Popen([str(binary), "--mcp", "headless"], stdin=subprocess.PIPE)
    try:
        with ConcatMCP(fake_app, tmp_path, tmp_path / "calls.jsonl", close_timeout=0.2) as mcp:
            pid = mcp.pid
            started = time.monotonic()
            with pytest.raises(BackendError, match="concat_timeout:stall"):
                mcp.call("stall", {}, timeout=0.2)
            assert time.monotonic() - started < 3
        mcp.close()
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
        assert peer.poll() is None
    finally:
        peer.send_signal(signal.SIGKILL)
        peer.communicate(timeout=5)


def test_probe_reports_missing_app_separately(tmp_path, monkeypatch):
    from edit_backends.registry import get_backend

    monkeypatch.setenv("CONTENT_OS_CONCAT_APP", str(tmp_path / "missing.app"))
    probe = get_backend("concat").probe()
    assert probe == {"id": "concat", "installed": False, "runnable": False,
                     "version": None, "status": "unavailable", "reason": "concat_app_unavailable"}


def test_failed_save_keeps_original_mcp_reason_and_stops_export(tmp_path, monkeypatch):
    from edit_backends import concat_adapter

    monkeypatch.setenv("CONTENT_OS_CONCAT_APP", str(tmp_path / "Concat.app"))
    binary = tmp_path / "Concat.app/Contents/MacOS/concat"
    binary.parent.mkdir(parents=True)
    binary.touch(mode=0o755)
    source = tmp_path / "source.mp4"
    source.touch()
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": []}))
    monkeypatch.setattr(concat_adapter, "probe_media", lambda _: {
        "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
    })
    seen = []

    class RefusingSave:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call(self, tool, args, **kwargs):
            seen.append(tool)
            if tool == "project_create":
                return {"timeline": {"tracks": [{"id": "T1", "index": 0}]}}
            if tool == "media_import":
                return {"createdId": "m1", "media": [{"id": "m1", "duration": 20}]}
            if tool == "clip_add":
                return {"createdId": "c1"}
            if tool == "project_save":
                raise BackendError("concat_tool_error:project_save:原文")
            pytest.fail(f"unexpected call {tool}")

    monkeypatch.setattr(concat_adapter, "ConcatMCP", RefusingSave)
    output = tmp_path / "output"
    with pytest.raises(BackendError, match="^concat_tool_error:project_save:原文$"):
        concat_adapter.Backend().render(source=source, suggestions_path=suggestions, output_dir=output)
    assert seen == ["project_create", "media_import", "clip_add", "project_save"]
    receipt = json.loads((output / "render-result.json").read_text())
    assert (receipt["status"], receipt["reason"]) == ("failed", "concat_tool_error:project_save:原文")
