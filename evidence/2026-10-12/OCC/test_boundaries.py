"""OCC-specific negative proofs; the shared EI assertions remain untouched."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from edit_backends.openchatcut_adapter import Backend
from edit_backends.interface import BackendError


def test_existing_receipt_is_never_overwritten(tmp_path):
    receipt = tmp_path / "render-result.json"
    receipt.write_text("human-owned")
    with pytest.raises(BackendError, match="already_exists"):
        Backend().render(source=tmp_path / "missing", suggestions_path=tmp_path / "missing", output_dir=tmp_path)
    assert receipt.read_text() == "human-owned"


@pytest.mark.parametrize("revision", [True, 0, -1, "1"])
def test_invalid_identity_writes_failure_without_running_editor(tmp_path, revision):
    backend = Backend()
    with patch.object(backend, "probe", side_effect=AssertionError("must not run")):
        result = backend.render(source=tmp_path / "missing", suggestions_path=tmp_path / "missing", output_dir=tmp_path / "out", project_revision=revision)
    assert result["status"] == "failed"
    assert result["reason"] == "render_project_identity_invalid"
    assert result["editor_backend"] == "openchatcut"
    assert json.loads((tmp_path / "out/render-result.json").read_text()) == result


def test_credentials_are_not_inherited(monkeypatch):
    for key in ("OPENAI_API_KEY", "CODEX_ACCESS_TOKEN", "ASSEMBLYAI_API_KEY", "LLM_PROVIDER", "NODE_OPTIONS", "HTTPS_PROXY"):
        monkeypatch.setenv(key, "must-not-enter-occ")
    env = Backend()._environment()
    assert "must-not-enter-occ" not in env.values()
    assert env["HOME"] == os.environ["HOME"]
    assert env["CC_RENDER_VIDEO_DECODER"] == "offthread"


def test_missing_dependency_does_not_load_other_backend(monkeypatch):
    monkeypatch.setenv("CONTENT_OS_OPENCHATCUT_ROOT", "/nonexistent/occ-runtime")
    with patch("edit_backends.kdenlive_render.render", side_effect=AssertionError("fallback forbidden")):
        result = Backend().probe()
    assert result["installed"] is False and result["runnable"] is False


def test_native_codex_spawn_is_blocked_before_process_creation(tmp_path):
    backend = Backend()
    backend._prepare()
    (tmp_path / "tmp").mkdir()
    env = backend._environment(tmp_path / "library", tmp_path)
    result = subprocess.run([str(backend.node), "--import", str(backend.root / ".occ-guard.mjs"), "-e", "require('node:child_process').spawn('codex',['app-server'])"],
                            env=env, cwd=backend.root, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "occ_builtin_agent_process_disabled" in result.stderr
    trace = [json.loads(line) for line in (tmp_path / "process-trace.jsonl").read_text().splitlines()]
    assert trace == [{"pid": trace[0]["pid"], "method": "spawn", "executable": "codex", "blocked": True}]
    (Path(__file__).parent / "codex-negative-proof.json").write_text(json.dumps({"exit_code": result.returncode, "trace": trace}, indent=2))
