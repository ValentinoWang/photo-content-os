"""Fast adapter identity, delegation and fail-closed contract tests."""
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_backends import kdenlive_adapter, kdenlive_render, registry
from edit_backends.interface import BackendError, EditBackend


def test_single_table_and_descriptions():
    assert set(registry.BACKENDS) == {"otio_kdenlive", "openfilm", "openchatcut", "chatcut"}
    backend = registry.get_backend("otio_kdenlive")
    assert isinstance(backend, EditBackend)
    assert backend.describe()["capabilities"]["transparent_overlay"]
    rows = registry.describe_backends()
    assert rows[0]["implemented"] is True
    assert [r["id"] for r in rows] == list(registry.BACKENDS)
    with pytest.raises(TypeError):
        registry.BACKENDS["unexpected"] = "unexpected"


@pytest.mark.parametrize("backend_id", ["not-an-editor", "openfilm", "openchatcut"])
def test_missing_or_unknown_backend_never_loads_another(backend_id):
    module = registry.BACKENDS.get(backend_id)
    with patch.object(kdenlive_render, "render") as render, patch.object(
        registry, "import_module", side_effect=ModuleNotFoundError(name=module)):
        with pytest.raises(BackendError):
            registry.get_backend(backend_id)
        render.assert_not_called()


def test_signature_matches_producer_and_delegates_unchanged(tmp_path):
    signature = inspect.signature(kdenlive_adapter.Backend.render)
    assert list(signature.parameters)[1:] == list(inspect.signature(kdenlive_render.render).parameters)
    arguments = {"source": tmp_path / "source", "suggestions_path": tmp_path / "suggestions",
                 "output_dir": tmp_path / "output", "subtitles": None, "animations": [],
                 "project_id": "ei-fixture", "project_revision": 7, "timeout_seconds": 3}
    with patch.object(kdenlive_render, "render", return_value={"status": "candidate"}) as render:
        assert kdenlive_adapter.Backend().render(**arguments) == {"status": "candidate"}
        render.assert_called_once_with(**arguments)


def test_preflight_unavailable_writes_receipt(tmp_path):
    output = tmp_path / "failed"
    with patch.object(kdenlive_render, "melt_executable", return_value=None):
        with pytest.raises(BackendError, match="melt_unavailable"):
            kdenlive_adapter.Backend().render(source=tmp_path / "source",
                                              suggestions_path=tmp_path / "suggestions", output_dir=output)
    receipt = json.loads((output / "render-result.json").read_text())
    assert receipt["status"] == "failed"
    assert receipt["editor_backend"] == "otio_kdenlive"
    assert not (output / "candidate.mp4").exists()


def test_existing_run_never_overwritten(tmp_path):
    receipt = tmp_path / "render-result.json"
    receipt.write_text("human-owned-receipt")
    with pytest.raises(BackendError, match="already_exists"):
        kdenlive_adapter.Backend().render(source=tmp_path / "source",
                                         suggestions_path=tmp_path / "suggestions", output_dir=tmp_path)
    assert receipt.read_text() == "human-owned-receipt"


def test_probe_does_not_claim_unavailable_runtime_online():
    with patch.object(kdenlive_render, "melt_executable", return_value=None):
        probe = kdenlive_adapter.Backend().probe()
    assert probe["installed"] is False
    assert probe["runnable"] is False
    assert probe["status"] == "unavailable"


def test_missing_adapter_dependency_is_not_a_missing_slot():
    with patch.object(registry, "import_module", side_effect=ModuleNotFoundError(name="adapter_dependency")):
        with pytest.raises(BackendError, match="dependency_missing:openfilm:adapter_dependency"):
            registry.get_backend("openfilm")


def test_no_refine_claim_and_idempotent_close(tmp_path):
    backend = kdenlive_adapter.Backend()
    assert backend.describe()['capabilities']['read_back'] is True
    with pytest.raises(BackendError,match='unsupported'):
        backend.open_for_refine(project_dir=tmp_path)
    with pytest.raises(BackendError,match='owned_project_missing'):
        backend.read_back(project_dir=tmp_path)
    assert backend.close() == backend.close()
    assert backend.close()["remaining_pids"] == []
