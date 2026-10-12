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
    "chatcut": "edit_backends.chatcut_adapter",
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


def local_editor_choice(store_dir, project_id):
    """Read Studio's explicit preference from the canonical project's store."""
    import hashlib
    import json
    from pathlib import Path
    path = Path(store_dir) / 'settings/video-editors' / (hashlib.sha256(project_id.encode()).hexdigest()+'.json')
    if not path.is_file():
        return None
    if path.stat().st_size > 4096:
        raise BackendError('editor_choice_invalid')
    value = json.loads(path.read_text())
    if value.get('editor')=='kdenlive': value={**value,'editor':'otio_kdenlive'}
    if value.get('editor') not in BACKENDS or value.get('method','external') not in ('external','guide','self') or type(value.get('revision')) is not int or value['revision'] < 1:
        raise BackendError('editor_choice_invalid')
    return value
