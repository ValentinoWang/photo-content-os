"""Wrap native refinement with live authorization and provenance observations."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from edit_backends.openchatcut_adapter import delete_segment as native_delete, undo as native_undo


def request_status(backend, path, headers, payload=None):
    req = urllib.request.Request(backend._session["origin"] + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def record(name, data):
    (Path(os.environ["EI_TEST_EVIDENCE"]) / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def delete_segment(backend, project_dir, index):
    origin = backend._session["origin"]
    message = {"jsonrpc": "2.0", "id": 999, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "negative-proof", "version": "1"}}}
    common = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    proof = {
        "invalid_token": request_status(backend, "/api/external-mcp/mcp", {**common, "Origin": origin, "Authorization": "Bearer invalid-token"}, message),
        "foreign_origin": request_status(backend, "/api/external-mcp/mcp", {**common, "Origin": "https://example.invalid", "Authorization": "Bearer " + backend._token}, message),
        "codex_status_disabled": request_status(backend, "/api/codex/status", {"Origin": origin}),
    }
    record("authorization-proof.json", proof)
    assert proof == {"invalid_token": 401, "foreign_origin": 403, "codex_status_disabled": 403}
    native_delete(backend, project_dir, index)
    record("refine-deleted.json", {"time_map": backend.read_back(project_dir=project_dir)["time_map"]})


def undo(backend, project_dir):
    native_undo(backend, project_dir)
    record("refine-restored.json", {"time_map": backend.read_back(project_dir=project_dir)["time_map"]})
