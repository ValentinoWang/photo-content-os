#!/usr/bin/env python3
"""Compatibility guard for the current OpenClaw Media local-agent contract."""

from __future__ import annotations

import json
import hashlib
import copy
import re
import sys
from dataclasses import dataclass
from importlib import metadata, resources
from pathlib import Path, PurePosixPath
from typing import Any

from runtime_paths import platform_contract_name

if __package__:
    from .constants import (
        SNAPSHOT_PATH,
        P1A_OPERATIONS,
        P1A_EXAMPLES,
        VIDEO_IDENTITY_FIELDS,
        VIDEO_STORYBOARD_COLUMNS,
    )
else:
    from constants import (
        SNAPSHOT_PATH,
        P1A_OPERATIONS,
        P1A_EXAMPLES,
        VIDEO_IDENTITY_FIELDS,
        VIDEO_STORYBOARD_COLUMNS,
    )


class ProductContractError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class Compatibility:
    available: bool
    compatible: bool
    platform: str
    package_version: str | None
    expected_digest: str
    actual_digest: str | None
    upstream_commit: str
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "photo_content_os_openclaw_compatibility_v1",
            "available": self.available,
            "compatible": self.compatible,
            "platform": self.platform,
            "package_version": self.package_version,
            "expected_digest": self.expected_digest,
            "actual_digest": self.actual_digest,
            "upstream_commit": self.upstream_commit,
            "reason": self.reason,
        }


def load_snapshot() -> dict[str, Any]:
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProductContractError("snapshot_invalid")
    validate_snapshot(data)
    return data


def validate_snapshot(data: dict[str, Any]) -> None:
    """Validate the local upstream pin without pretending it is live HEAD."""

    if data.get("schema_version") != "photo_content_os_openclaw_bridge_v1":
        raise ProductContractError("snapshot_invalid", "unsupported schema_version")
    if data.get("upstream_repository") != "ValentinoWang/openclaw-media":
        raise ProductContractError("snapshot_invalid", "unexpected upstream repository")
    if not re.fullmatch(r"[0-9a-f]{40}", str(data.get("upstream_commit", "")), re.IGNORECASE):
        raise ProductContractError("snapshot_invalid", "upstream_commit must be a git SHA")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(data.get("catalog_digest", "")), re.IGNORECASE):
        raise ProductContractError("snapshot_invalid", "catalog_digest must be sha256")
    if data.get("upstream_contract_id") != "openclaw_media_product_v1":
        raise ProductContractError("snapshot_invalid", "unexpected upstream contract id")
    if not isinstance(data.get("upstream_contract_version"), int) or data["upstream_contract_version"] < 1:
        raise ProductContractError("snapshot_invalid", "upstream_contract_version must be positive")
    pipelines = data.get("pipelines")
    if not isinstance(pipelines, dict) or len(pipelines) != 9:
        raise ProductContractError("snapshot_invalid", "snapshot must pin exactly nine pipeline aliases")
    if any(
        not isinstance(alias, str)
        or not alias.strip()
        or not isinstance(pipeline, str)
        or not pipeline.startswith("media.")
        for alias, pipeline in pipelines.items()
    ):
        raise ProductContractError("snapshot_invalid", "pipeline aliases must map to media pipeline ids")
    if "p1a_first_project" in data:
        require_p1a_snapshot(data)
    platforms = data.get("supported_device_platforms")
    if not isinstance(platforms, list) or "macos" not in platforms:
        raise ProductContractError("snapshot_invalid", "macos must be a supported device platform")




def p1a_content_digest(section: dict[str, Any], api_schemas: dict[str, Any]) -> str:
    content = {"contract": section, "api_schemas": api_schemas}
    try:
        raw = json.dumps(
            content, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ProductContractError("snapshot_invalid", "invalid P1a JSON content") from exc
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def require_p1a_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen first-project contract section after checking the pin."""
    if "p1a_first_project" not in data:
        raise ProductContractError("p1a_snapshot_missing")
    pin = data["p1a_first_project"]
    if not isinstance(pin, dict) or set(pin) != {"source_sha256", "content_sha256", "contract", "api_schemas"}:
        raise ProductContractError("snapshot_invalid", "invalid P1a pin fields")
    for name in ("source_sha256", "content_sha256"):
        if not isinstance(pin[name], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", pin[name]):
            raise ProductContractError("snapshot_invalid", f"invalid P1a {name}")
    section, api_schemas = pin["contract"], pin["api_schemas"]
    if not isinstance(section, dict) or not isinstance(api_schemas, dict):
        raise ProductContractError("snapshot_invalid", "invalid P1a contract or api_schemas")
    if pin["content_sha256"] != p1a_content_digest(section, api_schemas):
        raise ProductContractError("snapshot_invalid", "P1a content digest mismatch")

    schema = section.get("schema")
    definitions = schema.get("$defs") if isinstance(schema, dict) else None
    if not isinstance(definitions, dict) or not definitions:
        raise ProductContractError("snapshot_invalid", "missing P1a schema definitions")
    if any(not isinstance(item, dict) for item in (*definitions.values(), *api_schemas.values())):
        raise ProductContractError("snapshot_invalid", "invalid P1a schema definition")

    operations = section.get("operations")
    if not isinstance(operations, list) or len(operations) != len(P1A_OPERATIONS):
        raise ProductContractError("snapshot_invalid", "missing P1a operations")
    for op in operations:
        if (
            not isinstance(op, dict)
            or not all(isinstance(op.get(key), str) and op[key] for key in ("operation_id", "auth", "relative_path"))
            or op.get("method") not in ("GET", "POST")
            or not op["relative_path"].startswith("/")
            or type(op.get("success_status")) is not int
            or not isinstance(op.get("errors"), dict)
            or "request_schema_ref" not in op
            or (op["method"] == "GET" and op["request_schema_ref"] is not None)
            or (op["method"] == "POST" and not isinstance(op["request_schema_ref"], str))
            or not isinstance(op.get("response_schema_ref"), str)
        ):
            raise ProductContractError("snapshot_invalid", "invalid P1a operation fields")
    if {op["operation_id"] for op in operations} != P1A_OPERATIONS:
        raise ProductContractError("snapshot_invalid", "missing or duplicate P1a operation IDs")

    ports = section.get("studio_ports")
    if not isinstance(ports, dict) or set(ports) != {"select_project", "stage_handoff"}:
        raise ProductContractError("snapshot_invalid", "missing P1a Studio ports")
    for port in ports.values():
        if not isinstance(port, dict) or not all(
            isinstance(port.get(key), str) for key in ("request_schema_ref", "response_schema_ref")
        ):
            raise ProductContractError("snapshot_invalid", "invalid P1a Studio port fields")

    examples = section.get("examples")
    if not isinstance(examples, dict) or not all(
        isinstance(examples.get(name), kind) and examples[name] for name, kind in P1A_EXAMPLES.items()
    ):
        raise ProductContractError("snapshot_invalid", "missing or invalid P1a examples")

    def check_refs(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key != "$ref" and not key.endswith("_schema_ref"):
                    check_refs(child)
                    continue
                if child is None and key != "$ref":
                    continue
                if not isinstance(child, str):
                    raise ProductContractError("snapshot_invalid", "invalid P1a schema reference")
                if child.startswith("#/$defs/"):
                    name, target = child.removeprefix("#/$defs/"), definitions
                elif child.startswith("#/api_schemas/"):
                    name, target = child.removeprefix("#/api_schemas/"), api_schemas
                else:
                    raise ProductContractError("snapshot_invalid", f"invalid P1a schema reference: {child}")
                if name not in target:
                    raise ProductContractError("snapshot_invalid", f"unresolved P1a schema reference: {child}")
        elif isinstance(value, list):
            for child in value:
                check_refs(child)

    check_refs(section)
    check_refs(api_schemas)
    return section


def safe_workspace_ref(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ProductContractError("invalid_workspace_ref", str(value))
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductContractError("invalid_workspace_ref", value)
    return path.as_posix()




def video_digest(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def validate_video_handoff(payload: dict[str, Any], current_identity: dict[str, Any], *, expected_handoff_digest: str) -> dict[str, Any]:
    """Check a locally delivered descriptor against an explicit, current binding.

    This does not authorize cloud execution or define a second job protocol.
    The binding belongs to the local CreativeProject, never to its title.
    """
    import uuid

    fields = {"identity", "script", "storyboard", "animations", "tts_ref", "handoff_digest"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ProductContractError("video_handoff_rejected")
    identity = payload["identity"]
    if not isinstance(identity, dict) or set(identity) != VIDEO_IDENTITY_FIELDS or set(current_identity) != VIDEO_IDENTITY_FIELDS:
        raise ProductContractError("video_identity_rejected")
    for key, value in identity.items():
        if key in {"work_revision", "project_revision"}:
            valid = type(value) is int and value > 0
        elif key == "tenant_id":
            try:
                valid = str(uuid.UUID(value)) == value
            except (ValueError, TypeError, AttributeError):
                valid = False
        elif key == "catalog_digest":
            valid = isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
        else:
            valid = isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is not None
        if not valid or type(value) is not type(current_identity[key]) or value != current_identity[key]:
            raise ProductContractError("video_identity_rejected")
    if identity["catalog_digest"] != load_snapshot()["catalog_digest"]:
        raise ProductContractError("catalog_digest_mismatch")
    raw = {k: v for k, v in payload.items() if k != "handoff_digest"}
    if video_digest(raw) != payload["handoff_digest"] or payload["handoff_digest"] != expected_handoff_digest:
        raise ProductContractError("handoff_digest_mismatch")
    if not isinstance(payload["script"], str) or not payload["script"].strip():
        raise ProductContractError("video_handoff_rejected")
    rows = payload["storyboard"]
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) or set(row) != VIDEO_STORYBOARD_COLUMNS or any(not isinstance(v, str) for v in row.values()) for row in rows):
        raise ProductContractError("video_handoff_rejected")
    shots = [row["shot"] for row in rows]
    if any(not shot for shot in shots) or len(set(shots)) != len(shots):
        raise ProductContractError("video_handoff_rejected")
    animations = payload["animations"]
    if not isinstance(animations, list) or any(not isinstance(row, dict) or set(row) != {"shot", "narration", "requirement"} or any(not isinstance(v, str) for v in row.values()) or row["shot"] not in shots for row in animations):
        raise ProductContractError("video_handoff_rejected")
    if payload["tts_ref"] is not None:
        safe_workspace_ref(payload["tts_ref"])
    # The wire descriptor contains text and controlled refs only, no local paths.
    def check_text(value: Any) -> None:
        if isinstance(value, str):
            if re.search(r"(?:^|[\s\"'=(:：])(?:/(?:[\w.-]+/)+[^\s\"']*|[A-Za-z]:[\\/][^\s\"']*)", value) or "\x00" in value:
                raise ProductContractError("video_privacy_rejected")
        elif isinstance(value, dict):
            for child in value.values():
                check_text(child)
        elif isinstance(value, list):
            for child in value:
                check_text(child)
    check_text(payload)
    return copy.deepcopy(payload)


def _installed_catalog() -> tuple[str | None, dict[str, Any] | None]:
    try:
        version = metadata.version("openclaw-media")
    except metadata.PackageNotFoundError:
        return None, None
    try:
        resource = resources.files("openclaw_media").joinpath("data/pipelines.json")
        data = json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError, TypeError):
        return version, None
    return version, data if isinstance(data, dict) else None


def compatibility(*, require_cloud_platform: bool = False) -> Compatibility:
    snapshot = load_snapshot()
    version, catalog = _installed_catalog()
    platform = platform_contract_name()
    expected = str(snapshot["catalog_digest"])
    actual = str(catalog.get("catalog_digest")) if catalog else None
    reason = None
    compatible = bool(catalog and actual == expected)
    if compatible:
        try:
            definitions = [copy.deepcopy(item) for item in catalog["pipelines"]]
            for item in definitions:
                item.pop("catalog_digest", None)
            definitions.sort(key=lambda item: (item["pipeline_id"], item["version"]))
            raw = json.dumps(definitions, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            compatible = actual == "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
        except (KeyError, TypeError, AttributeError):
            compatible = False
    if version is None:
        reason = "openclaw_media_not_installed"
    elif catalog is None:
        reason = "openclaw_media_catalog_unavailable"
    elif actual != expected:
        reason = "catalog_digest_mismatch"
    elif not compatible:
        reason = "catalog_definitions_mismatch"
    elif require_cloud_platform and platform not in set(snapshot.get("supported_device_platforms") or []):
        compatible = False
        reason = "upstream_platform_unsupported"
    return Compatibility(
        available=version is not None,
        compatible=compatible,
        platform=platform,
        package_version=version,
        expected_digest=expected,
        actual_digest=actual,
        upstream_commit=str(snapshot["upstream_commit"]),
        reason=reason,
    )


def pipeline_id(alias_or_id: str) -> str:
    snapshot = load_snapshot()
    aliases = snapshot.get("pipelines") or {}
    value = str(alias_or_id).strip()
    resolved = str(aliases.get(value, value))
    if resolved not in set(aliases.values()):
        raise ProductContractError("pipeline_not_allowed", value)
    return resolved


def assert_compatible(*, require_cloud_platform: bool = False) -> Compatibility:
    result = compatibility(require_cloud_platform=require_cloud_platform)
    if not result.compatible:
        raise ProductContractError(result.reason or "incompatible", json.dumps(result.to_dict(), ensure_ascii=False))
    return result


def main() -> int:
    result = compatibility(require_cloud_platform="--cloud" in sys.argv)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.compatible else 2


if __name__ == "__main__":
    raise SystemExit(main())
