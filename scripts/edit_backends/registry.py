"""Single adapter table. Loading never substitutes another editing backend."""
from __future__ import annotations

from importlib import import_module
from types import MappingProxyType

from .interface import BackendError, EditBackend


# OA/OCC own their modules, so they need not edit this shared table concurrently.
BACKENDS = MappingProxyType({
    "otio_kdenlive": "edit_backends.kdenlive_adapter",
    "openfilm": "edit_backends.openfilm_adapter",
    "openchatcut": "edit_backends.openchatcut_adapter",
})


def get_backend(backend_id: str) -> EditBackend:
    try:
        module_name = BACKENDS[backend_id]
    except KeyError as exc:
        raise BackendError(f"unknown_editor_backend:{backend_id}") from exc
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise BackendError(f"editor_backend_dependency_missing:{backend_id}:{exc.name}") from exc
        raise BackendError(f"editor_backend_not_implemented:{backend_id}") from exc
    backend = module.Backend()
    if not isinstance(backend, EditBackend) or backend.describe()["id"] != backend_id:
        raise BackendError(f"editor_backend_contract_invalid:{backend_id}")
    return backend


def describe_backends() -> list[dict]:
    """Describe implemented adapters; reserved slots declare no capabilities."""
    rows = []
    for backend_id in BACKENDS:
        try:
            backend = get_backend(backend_id)
        except BackendError as exc:
            rows.append({"id": backend_id, "implemented": False, "reason": str(exc)})
        else:
            try:
                rows.append({**backend.describe(), "implemented": True})
            finally:
                backend.close()
    return rows
