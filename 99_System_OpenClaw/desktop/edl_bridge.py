"""Read-only bridge for the authoritative workspace EDL file."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from edl_contract import EDLContractError, normalise_edl  # type: ignore  # noqa: E402

AUTHORITY_FILE = "06_edit_decision_list.json"
BRIDGE_SCHEMA_VERSION = "studio_edl_bridge_v1"
VALIDATOR = "edl_contract.normalise_edl"
EDL_SCHEMA_VERSIONS = frozenset({"edit_decision_list_v1", "edit_decision_list_v2"})


@dataclass(frozen=True)
class EDLBridgeError(ValueError):
    code: str
    message: str
    http_status: int
    state: dict[str, Any]

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class _DeclaredSchemaError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _source_identity(digest: str | None, size_bytes: int | None = None) -> dict[str, Any]:
    source: dict[str, Any] = {
        "authority_file": AUTHORITY_FILE,
        "content_digest": digest,
    }
    if size_bytes is not None:
        source["size_bytes"] = size_bytes
    return source


def bridge_state(
    status: str,
    *,
    digest: str | None = None,
    size_bytes: int | None = None,
    content: dict[str, Any] | None = None,
    validation_code: str | None = None,
) -> dict[str, Any]:
    validation: dict[str, Any] = {"status": status, "validator": VALIDATOR}
    if validation_code:
        validation["code"] = validation_code
    return {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": status,
        "source": _source_identity(digest, size_bytes),
        "content": content,
        "validation": validation,
    }


def _raise_identity(message: str = "The authoritative EDL source identity cannot be verified.") -> None:
    raise EDLBridgeError(
        code="edl_source_identity_invalid",
        message=message,
        http_status=409,
        state=bridge_state("unavailable", validation_code="source_identity_invalid"),
    )


def _raise_missing() -> None:
    raise EDLBridgeError(
        code="edl_source_missing",
        message="The authoritative EDL source is missing.",
        http_status=404,
        state=bridge_state("missing", validation_code="source_missing"),
    )


def _raise_invalid_json(digest: str, size_bytes: int) -> None:
    raise EDLBridgeError(
        code="edl_source_invalid",
        message="The authoritative EDL source is not valid JSON.",
        http_status=422,
        state=bridge_state(
            "invalid",
            digest=digest,
            size_bytes=size_bytes,
            validation_code="invalid_json",
        ),
    )


def _raise_contract_invalid(
    digest: str,
    size_bytes: int,
    validation_code: str,
) -> None:
    raise EDLBridgeError(
        code="edl_contract_invalid",
        message="The authoritative EDL source failed the EDL contract.",
        http_status=422,
        state=bridge_state(
            "invalid",
            digest=digest,
            size_bytes=size_bytes,
            validation_code=validation_code,
        ),
    )


def _declared_schema_error(raw: dict[str, Any]) -> str | None:
    schema_version = raw.get("schema_version")
    if "schema_version" in raw and schema_version not in EDL_SCHEMA_VERSIONS:
        return "schema_version_invalid"
    if "doc_type" in raw and raw["doc_type"] != "edit_decision_list":
        return "doc_type_invalid"
    if "missing_materials" in raw and not isinstance(raw["missing_materials"], list):
        return "missing_materials_invalid"
    return None


def read_edl_bridge(workspace: Path) -> dict[str, Any]:
    """Read one workspace file, hash its exact bytes, and validate its content."""
    try:
        root = Path(workspace).expanduser().resolve()
        source_path = root / AUTHORITY_FILE
        if source_path.is_symlink():
            _raise_identity()
        if not source_path.exists():
            _raise_missing()
        if not source_path.is_file():
            _raise_identity()
        raw_bytes = source_path.read_bytes()
    except EDLBridgeError:
        raise
    except FileNotFoundError:
        _raise_missing()
    except (OSError, RuntimeError, ValueError):
        _raise_identity()

    digest = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    size_bytes = len(raw_bytes)
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _raise_invalid_json(digest, size_bytes)

    try:
        if not isinstance(raw, dict):
            raise _DeclaredSchemaError("invalid_json_root")
        declared_error = _declared_schema_error(raw)
        if declared_error:
            raise _DeclaredSchemaError(declared_error)
        content = normalise_edl(raw)
    except _DeclaredSchemaError as exc:
        _raise_contract_invalid(digest, size_bytes, exc.code)
    except EDLContractError as exc:
        _raise_contract_invalid(digest, size_bytes, exc.code)

    return bridge_state(
        "valid",
        digest=digest,
        size_bytes=size_bytes,
        content=content,
        validation_code="valid",
    )
