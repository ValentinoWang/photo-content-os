#!/usr/bin/env python3
"""Compatibility guard for the current OpenClaw Media local-agent contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from importlib import metadata, resources
from pathlib import Path, PurePosixPath
from typing import Any

from runtime_paths import platform_contract_name

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "schemas" / "openclaw_media_contract_snapshot.json"


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
    return data


def safe_workspace_ref(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "://" in value:
        raise ProductContractError("invalid_workspace_ref", str(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductContractError("invalid_workspace_ref", value)
    return path.as_posix()


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
    if version is None:
        reason = "openclaw_media_not_installed"
    elif catalog is None:
        reason = "openclaw_media_catalog_unavailable"
    elif actual != expected:
        reason = "catalog_digest_mismatch"
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
