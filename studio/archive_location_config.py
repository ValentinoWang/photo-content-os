#!/usr/bin/env python3
"""Persisted lifecycle and physical-location configuration for archive fixtures.

The module stores logical location references and injected readback facts only.
It never resolves a location reference to a filesystem path and never copies,
scans, uploads, or deletes media.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias


SCHEMA_VERSION = 1
CONFIG_FILE_NAME = "archive_location_config.json"


class LifecycleState(str, Enum):
    """Lifecycle values are deliberately independent from physical locations."""

    ACTIVE = "active"
    ARCHIVING = "archiving"
    ARCHIVED = "archived"
    RETIRED = "retired"


Lifecycle = LifecycleState


class ReadbackState(str, Enum):
    """The result of the most recent injected readback attempt."""

    UNKNOWN = "unknown"
    VERIFIED = "verified"
    FAILED = "failed"


LIFECYCLE_VALUES = frozenset(state.value for state in LifecycleState)
READBACK_VALUES = frozenset(state.value for state in ReadbackState)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_LOCATION_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")
_ABSOLUTE_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|Volumes|private|tmp|var|home)(?:/|$)"
)


class ArchiveLocationConfigError(ValueError):
    """Fail-closed validation or storage error with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.error_code = code
        super().__init__(f"{code}: {message}")


ConfigError = ArchiveLocationConfigError


def _reject(code: str, message: str) -> None:
    raise ArchiveLocationConfigError(code, message)


def _contains_forbidden_reference(value: str) -> bool:
    """Detect path/URL fragments before user text is persisted."""

    return bool(
        _URL_RE.search(value)
        or _WINDOWS_ABSOLUTE_RE.search(value)
        or value.startswith(("/", "\\", "~/"))
        or _ABSOLUTE_FRAGMENT_RE.search(value)
    )


def _safe_label(value: object, *, code: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject(code, "text is required")
    text = value.strip()
    if len(text) > max_length:
        _reject(code, "text is too long")
    if "\x00" in text or _contains_forbidden_reference(text):
        _reject(code, "text contains a forbidden path or URL")
    return text


def _safe_id(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value.strip()):
        _reject(code, "identifier is invalid")
    return value.strip()


def _safe_location_ref(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject("invalid_location_ref", "location reference is required")
    reference = value.strip()
    if (
        len(reference) > 128
        or "\x00" in reference
        or _URL_RE.search(reference)
        or _WINDOWS_ABSOLUTE_RE.match(reference)
        or reference.startswith(("/", "\\", "~/"))
        or not _LOCATION_REF_RE.fullmatch(reference)
    ):
        _reject("invalid_location_ref", "location reference must be controlled and relative")
    parts = re.split(r"[/\\:]", reference)
    if any(part in {"", ".", ".."} for part in parts):
        _reject("invalid_location_ref", "location reference must not escape its root")
    return reference


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject("invalid_relative_path", "relative path is required")
    relative_path = value
    if (
        len(relative_path) > 1024
        or "\x00" in relative_path
        or relative_path.startswith(("/", "\\", "~/"))
        or _WINDOWS_ABSOLUTE_RE.match(relative_path)
        or _URL_RE.search(relative_path)
        or "\\" in relative_path
    ):
        _reject("invalid_relative_path", "relative path must stay inside the location")
    parts = relative_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _reject("invalid_relative_path", "relative path must stay inside the location")
    return relative_path


def _safe_sha256(value: object) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        _reject("invalid_sha256", "sha256 must be 64 lowercase hexadecimal characters")
    return value


def _timestamp(value: str | datetime, *, code: str = "invalid_timestamp") -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArchiveLocationConfigError(code, "timestamp is invalid") from exc
    else:
        _reject(code, "timestamp is required")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _reject(code, "timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_lifecycle(value: object) -> LifecycleState:
    if isinstance(value, LifecycleState):
        return value
    if not isinstance(value, str):
        _reject("invalid_lifecycle", "lifecycle must be an explicit enum value")
    try:
        return LifecycleState(value)
    except ValueError as exc:
        raise ArchiveLocationConfigError("invalid_lifecycle", "lifecycle must be an explicit enum value") from exc


def _coerce_readback_state(value: object) -> ReadbackState:
    if isinstance(value, ReadbackState):
        return value
    if not isinstance(value, str):
        _reject("invalid_readback_state", "readback state is invalid")
    try:
        return ReadbackState(value)
    except ValueError as exc:
        raise ArchiveLocationConfigError("invalid_readback_state", "readback state is invalid") from exc


def _strict_keys(data: Mapping[str, Any], expected: set[str], *, code: str) -> None:
    unknown = set(data) - expected
    if unknown:
        _reject(code, "record contains unknown fields")


def _coerce_manifest(value: object) -> tuple["MediaManifestEntry", ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        _reject("invalid_media_manifest", "media_manifest must be a list")
    entries: list[MediaManifestEntry] = []
    seen: set[str] = set()
    for item in value:
        entry = item if isinstance(item, MediaManifestEntry) else MediaManifestEntry.from_dict(item)
        if entry.relative_path in seen:
            _reject("duplicate_media_entry", "media manifest contains a duplicate path")
        seen.add(entry.relative_path)
        entries.append(entry)
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class MediaManifestEntry:
    """An immutable location-relative media identity and content digest."""

    relative_path: str
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "relative_path", _safe_relative_path(self.relative_path))
        object.__setattr__(self, "sha256", _safe_sha256(self.sha256))

    @property
    def content_sha256(self) -> str:
        return self.sha256

    @classmethod
    def from_dict(cls, data: object) -> "MediaManifestEntry":
        if not isinstance(data, Mapping):
            _reject("invalid_media_entry", "media manifest entry must be an object")
        _strict_keys(data, {"relative_path", "sha256"}, code="invalid_media_entry")
        if set(data) != {"relative_path", "sha256"}:
            _reject("invalid_media_entry", "media manifest entry is incomplete")
        return cls(relative_path=data["relative_path"], sha256=data["sha256"])

    def to_dict(self) -> dict[str, str]:
        return {"relative_path": self.relative_path, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class ReadbackResult:
    """A small result returned by an injected readback reader."""

    success: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.success) is not bool:
            _reject("invalid_readback_result", "success must be boolean")
        if self.success:
            if self.reason is not None:
                _reject("invalid_readback_result", "successful readback cannot have a failure reason")
            return
        if self.reason is None:
            return
        _safe_label(self.reason, code="invalid_readback_result", max_length=500)

    @classmethod
    def verified(cls) -> "ReadbackResult":
        return cls(success=True)

    @classmethod
    def failed(cls, reason: str | None = None) -> "ReadbackResult":
        return cls(success=False, reason=reason)


ReadbackReader: TypeAlias = Callable[["LocationRecord"], bool | ReadbackResult]


@dataclass(frozen=True, slots=True)
class LocationRecord:
    """One independently tracked physical location with immutable inventory."""

    location_id: str
    display_name: str
    location_ref: str
    media_manifest: tuple[MediaManifestEntry, ...]
    observed_at: str
    readback_state: ReadbackState = ReadbackState.UNKNOWN
    readback_at: str | None = None
    readback_error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "location_id", _safe_id(self.location_id, code="invalid_location_id"))
        object.__setattr__(
            self,
            "display_name",
            _safe_label(self.display_name, code="invalid_display_name", max_length=120),
        )
        object.__setattr__(self, "location_ref", _safe_location_ref(self.location_ref))
        object.__setattr__(self, "media_manifest", _coerce_manifest(self.media_manifest))
        object.__setattr__(self, "observed_at", _timestamp(self.observed_at))
        state = _coerce_readback_state(self.readback_state)
        object.__setattr__(self, "readback_state", state)
        if self.readback_at is not None:
            object.__setattr__(self, "readback_at", _timestamp(self.readback_at, code="invalid_readback_at"))
        if self.readback_error is not None:
            object.__setattr__(
                self,
                "readback_error",
                _safe_label(self.readback_error, code="invalid_readback_error", max_length=500),
            )
        if state is ReadbackState.UNKNOWN and (self.readback_at is not None or self.readback_error is not None):
            _reject("invalid_readback_record", "unknown readback cannot have a result")
        if state is ReadbackState.VERIFIED and (self.readback_at is None or self.readback_error is not None):
            _reject("invalid_readback_record", "verified readback requires a timestamp and no error")
        if state is ReadbackState.FAILED and self.readback_at is None:
            _reject("invalid_readback_record", "failed readback requires a timestamp")

    @classmethod
    def from_dict(cls, data: object) -> "LocationRecord":
        fields = {
            "location_id",
            "display_name",
            "location_ref",
            "media_manifest",
            "observed_at",
            "readback_state",
            "readback_at",
            "readback_error",
        }
        if not isinstance(data, Mapping):
            _reject("invalid_location_record", "location record must be an object")
        _strict_keys(data, fields, code="invalid_location_record")
        if set(data) != fields:
            _reject("invalid_location_record", "location record is incomplete")
        return cls(
            location_id=data["location_id"],
            display_name=data["display_name"],
            location_ref=data["location_ref"],
            media_manifest=data["media_manifest"],
            observed_at=data["observed_at"],
            readback_state=data["readback_state"],
            readback_at=data["readback_at"],
            readback_error=data["readback_error"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "display_name": self.display_name,
            "location_ref": self.location_ref,
            "media_manifest": [entry.to_dict() for entry in self.media_manifest],
            "observed_at": self.observed_at,
            "readback_state": self.readback_state.value,
            "readback_at": self.readback_at,
            "readback_error": self.readback_error,
        }


def _validate_locations(locations: Sequence[LocationRecord]) -> tuple[LocationRecord, ...]:
    result: list[LocationRecord] = []
    ids: set[str] = set()
    references: set[str] = set()
    for location in locations:
        if not isinstance(location, LocationRecord):
            _reject("invalid_location_record", "locations must contain location records")
        if location.location_id in ids or location.location_ref in references:
            _reject("duplicate_location", "locations must have unique ids and references")
        ids.add(location.location_id)
        references.add(location.location_ref)
        result.append(location)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ArchiveLocationConfig:
    """Immutable in-memory representation of the persisted configuration."""

    lifecycle: LifecycleState = LifecycleState.ACTIVE
    locations: tuple[LocationRecord, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            _reject("invalid_schema_version", "schema version is unsupported")
        object.__setattr__(self, "lifecycle", _coerce_lifecycle(self.lifecycle))
        if isinstance(self.locations, (str, bytes, bytearray)) or not isinstance(self.locations, Sequence):
            _reject("invalid_locations", "locations must be a list")
        object.__setattr__(self, "locations", _validate_locations(tuple(self.locations)))

    @classmethod
    def from_dict(cls, data: object) -> "ArchiveLocationConfig":
        fields = {"schema_version", "lifecycle", "locations"}
        if not isinstance(data, Mapping):
            _reject("invalid_config", "configuration root must be an object")
        _strict_keys(data, fields, code="invalid_config")
        if set(data) != fields:
            _reject("invalid_config", "configuration is incomplete")
        raw_locations = data["locations"]
        if not isinstance(raw_locations, list):
            _reject("invalid_locations", "locations must be a list")
        return cls(
            schema_version=data["schema_version"],
            lifecycle=data["lifecycle"],
            locations=tuple(LocationRecord.from_dict(item) for item in raw_locations),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lifecycle": self.lifecycle.value,
            "locations": [location.to_dict() for location in self.locations],
        }

    def location(self, location_id: str) -> LocationRecord:
        safe_id = _safe_id(location_id, code="invalid_location_id")
        for location in self.locations:
            if location.location_id == safe_id:
                return location
        _reject("location_not_found", "location does not exist")

    def add_location(
        self,
        *,
        location_id: str,
        display_name: str,
        location_ref: str,
        media_manifest: Sequence[MediaManifestEntry | Mapping[str, Any]],
        observed_at: str | datetime | None = None,
    ) -> "ArchiveLocationConfig":
        safe_id = _safe_id(location_id, code="invalid_location_id")
        safe_ref = _safe_location_ref(location_ref)
        if any(location.location_id == safe_id for location in self.locations):
            _reject("duplicate_location", "location id is already configured")
        if any(location.location_ref == safe_ref for location in self.locations):
            _reject("duplicate_location", "location reference is already configured")
        timestamp = _now() if observed_at is None else _timestamp(observed_at)
        record = LocationRecord(
            location_id=safe_id,
            display_name=display_name,
            location_ref=safe_ref,
            media_manifest=_coerce_manifest(media_manifest),
            observed_at=timestamp,
        )
        return replace(self, locations=self.locations + (record,))

    def register_location(self, **kwargs: Any) -> "ArchiveLocationConfig":
        return self.add_location(**kwargs)

    def with_lifecycle(self, lifecycle: LifecycleState | str) -> "ArchiveLocationConfig":
        """Change only the top-level lifecycle enum."""

        return replace(self, lifecycle=_coerce_lifecycle(lifecycle))

    def update_lifecycle(self, lifecycle: LifecycleState | str) -> "ArchiveLocationConfig":
        return self.with_lifecycle(lifecycle)

    def with_readback(
        self,
        location_id: str,
        reader: ReadbackReader | Any,
        *,
        checked_at: str | datetime | None = None,
    ) -> "ArchiveLocationConfig":
        """Apply only an injected reader's result to one location."""

        timestamp = _now() if checked_at is None else _timestamp(checked_at, code="invalid_readback_at")
        current = self.location(location_id)
        result = _readback_result(reader, current)
        if result.success:
            updated = replace(
                current,
                readback_state=ReadbackState.VERIFIED,
                readback_at=timestamp,
                readback_error=None,
            )
        else:
            updated = replace(
                current,
                readback_state=ReadbackState.FAILED,
                readback_at=timestamp,
                readback_error=result.reason or "reader_reported_failure",
            )
        locations = tuple(updated if item.location_id == current.location_id else item for item in self.locations)
        return replace(self, locations=locations)

    def readback_location(
        self,
        location_id: str,
        reader: ReadbackReader | Any,
        *,
        checked_at: str | datetime | None = None,
    ) -> "ArchiveLocationConfig":
        return self.with_readback(location_id, reader, checked_at=checked_at)


def _readback_result(reader: ReadbackReader | Any, location: LocationRecord) -> ReadbackResult:
    callback = reader if callable(reader) else getattr(reader, "readback", None)
    if not callable(callback):
        _reject("invalid_readback_reader", "readback reader must be callable")
    value = callback(location)
    if type(value) is bool:
        return ReadbackResult(success=value)
    if isinstance(value, ReadbackResult):
        return value
    _reject("invalid_readback_result", "reader must return bool or ReadbackResult")


class ArchiveLocationConfigStore:
    """Atomic JSON storage rooted at an explicit runtime work directory."""

    def __init__(self, work_dir: str | os.PathLike[str]) -> None:
        if isinstance(work_dir, (bytes, bytearray)) or not str(work_dir).strip():
            _reject("invalid_work_dir", "an explicit work directory is required")
        try:
            resolved = Path(work_dir).expanduser().resolve()
        except (OSError, RuntimeError, TypeError) as exc:
            raise ArchiveLocationConfigError("invalid_work_dir", "work directory is invalid") from exc
        if resolved.exists() and not resolved.is_dir():
            _reject("invalid_work_dir", "work directory must be a directory")
        self.work_dir = resolved
        self.config_path = resolved / CONFIG_FILE_NAME

    def _ensure_work_dir(self) -> None:
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArchiveLocationConfigError("storage_unavailable", "work directory is unavailable") from exc
        if not self.work_dir.is_dir():
            _reject("storage_unavailable", "work directory is unavailable")

    def load(self) -> ArchiveLocationConfig:
        try:
            raw = self.config_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ArchiveLocationConfigError("config_not_found", "configuration file does not exist") from exc
        except OSError as exc:
            raise ArchiveLocationConfigError("storage_unavailable", "configuration file cannot be read") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArchiveLocationConfigError("invalid_json", "configuration JSON is invalid") from exc
        return ArchiveLocationConfig.from_dict(data)

    def save(self, config: ArchiveLocationConfig | Mapping[str, Any]) -> None:
        if isinstance(config, Mapping):
            config = ArchiveLocationConfig.from_dict(config)
        if not isinstance(config, ArchiveLocationConfig):
            _reject("invalid_config", "save requires an archive location configuration")
        payload = config.to_dict()
        self._ensure_work_dir()
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                dir=self.work_dir,
                prefix=f".{CONFIG_FILE_NAME}.",
                suffix=".tmp",
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.config_path)
            temporary_path = None
        except OSError as exc:
            raise ArchiveLocationConfigError("storage_write_failed", "configuration file cannot be written") from exc
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

    def initialize(self, lifecycle: LifecycleState | str = LifecycleState.ACTIVE) -> ArchiveLocationConfig:
        config = ArchiveLocationConfig(lifecycle=_coerce_lifecycle(lifecycle))
        self.save(config)
        return config

    def create(self, lifecycle: LifecycleState | str = LifecycleState.ACTIVE) -> ArchiveLocationConfig:
        return self.initialize(lifecycle)

    def add_location(self, **kwargs: Any) -> ArchiveLocationConfig:
        updated = self.load().add_location(**kwargs)
        self.save(updated)
        return updated

    def register_location(self, **kwargs: Any) -> ArchiveLocationConfig:
        return self.add_location(**kwargs)

    def update_lifecycle(self, lifecycle: LifecycleState | str) -> ArchiveLocationConfig:
        updated = self.load().with_lifecycle(lifecycle)
        self.save(updated)
        return updated

    def set_lifecycle(self, lifecycle: LifecycleState | str) -> ArchiveLocationConfig:
        return self.update_lifecycle(lifecycle)

    def readback_location(
        self,
        location_id: str,
        reader: ReadbackReader | Any,
        *,
        checked_at: str | datetime | None = None,
    ) -> ArchiveLocationConfig:
        updated = self.load().with_readback(location_id, reader, checked_at=checked_at)
        self.save(updated)
        return updated

    def readback(
        self,
        location_id: str,
        reader: ReadbackReader | Any,
        *,
        checked_at: str | datetime | None = None,
    ) -> ArchiveLocationConfig:
        return self.readback_location(location_id, reader, checked_at=checked_at)


def create_config(lifecycle: LifecycleState | str = LifecycleState.ACTIVE) -> ArchiveLocationConfig:
    return ArchiveLocationConfig(lifecycle=_coerce_lifecycle(lifecycle))


def load_config(work_dir: str | os.PathLike[str]) -> ArchiveLocationConfig:
    return ArchiveLocationConfigStore(work_dir).load()


def save_config(
    work_dir: str | os.PathLike[str],
    config: ArchiveLocationConfig | Mapping[str, Any],
) -> None:
    ArchiveLocationConfigStore(work_dir).save(config)


__all__ = [
    "ArchiveLocationConfig",
    "ArchiveLocationConfigError",
    "ArchiveLocationConfigStore",
    "ConfigError",
    "CONFIG_FILE_NAME",
    "Lifecycle",
    "LifecycleState",
    "LIFECYCLE_VALUES",
    "LocationRecord",
    "MediaManifestEntry",
    "ReadbackReader",
    "ReadbackResult",
    "ReadbackState",
    "READBACK_VALUES",
    "SCHEMA_VERSION",
    "create_config",
    "load_config",
    "save_config",
]
