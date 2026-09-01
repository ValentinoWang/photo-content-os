#!/usr/bin/env python3
"""Fail-closed, auditable movement to a recoverable system trash backend."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol

from media_delete_recommendations import (
    CANDIDATE_STATE,
    CONFIRMED_STATE,
    DeleteRecommendationError,
    candidate_number_for_evidence,
)


_MEDIA_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_REQUIRED_BACKEND_METHODS = (
    "move_to_trash",
    "verify_in_trash",
    "restore_from_trash",
    "verify_restored",
)
_MACOS_TRASH_TIMEOUT_SECONDS = 10.0
_MACOS_TRASH_SCRIPT = r'''
ObjC.import('Foundation');
const source = $.NSURL.fileURLWithPath($(arguments[0]));
const resulting = Ref();
const error = Ref();
const ok = $.NSFileManager.defaultManager.trashItemAtURLResultingItemURLError(
  source,
  resulting,
  error
);
if (!ok || resulting[0] === undefined || resulting[0] === null) {
  throw new Error('system_trash_failed');
}
$.puts(JSON.stringify({trash_path: ObjC.unwrap(resulting[0].path)}));
'''


class MediaTrashFlowError(ValueError):
    """A validation failure with a stable machine-readable error code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.error_code = code
        super().__init__(f"{code}: {message}")


class TrashBackend(Protocol):
    """The platform-neutral capability required by :class:`MediaTrashFlow`.

    ``trash_location_id`` must be an opaque, non-empty identifier.  The
    backend owns the platform-specific location and must never require the
    flow to inspect that location directly.
    """

    def move_to_trash(self, source: Path, *, candidate_number: str) -> str:
        """Move ``source`` into the system trash and return its opaque id."""

    def verify_in_trash(self, trash_location_id: str, expected_sha256: str) -> bool:
        """Prove that the moved item has the expected content."""

    def restore_from_trash(
        self,
        trash_location_id: str,
        destination: Path,
        *,
        candidate_number: str,
    ) -> object:
        """Restore the item to ``destination`` without replacing an item."""

    def verify_restored(self, restored_path: Path, expected_sha256: str) -> bool:
        """Prove that the restored item has the expected content."""


class UnavailableSystemTrashBackend:
    """Explicit unavailable backend used when recoverability is unproven."""

    available = False
    recovery_proven = False

    def __init__(self, platform_name: str, reason: str = "recovery_not_proven") -> None:
        self.platform_name = platform_name
        self.reason = reason

    def _unavailable(self) -> None:
        raise MediaTrashFlowError("unsupported_backend", "system trash recovery is unavailable")

    def move_to_trash(self, source: Path, *, candidate_number: str) -> str:
        self._unavailable()
        raise AssertionError("unreachable")

    def verify_in_trash(self, trash_location_id: str, expected_sha256: str) -> bool:
        self._unavailable()
        raise AssertionError("unreachable")

    def restore_from_trash(
        self,
        trash_location_id: str,
        destination: Path,
        *,
        candidate_number: str,
    ) -> object:
        self._unavailable()
        raise AssertionError("unreachable")

    def verify_restored(self, restored_path: Path, expected_sha256: str) -> bool:
        self._unavailable()
        raise AssertionError("unreachable")


class MacOSSystemTrashBackend:
    """Use Foundation's macOS system Trash operation with opaque receipts.

    The Foundation call selects the right system Trash for the source volume
    and returns the resulting file URL.  That URL is retained only in the
    private receipt registry; callers receive an opaque location identifier.
    Each move and restore is independently content-hash verified by
    :class:`MediaTrashFlow`.
    """

    available = True
    recovery_proven = True

    def __init__(
        self,
        *,
        registry_path: str | Path | None = None,
        runner: Callable[[Sequence[str], float], object] | None = None,
        identifier_factory: Callable[[], object] = uuid.uuid4,
    ) -> None:
        self.registry_path = Path(registry_path).expanduser().resolve() if registry_path else None
        self._runner = runner or self._run_foundation_trash
        self._identifier_factory = identifier_factory
        self._locations: dict[str, Path] = self._load_registry()

    @staticmethod
    def _run_foundation_trash(command: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
        )

    @staticmethod
    def _returncode(result: object) -> int:
        value = getattr(result, "returncode", None)
        if isinstance(value, bool) or not isinstance(value, int):
            raise MediaTrashFlowError("system_trash_failed", "system trash returned an invalid result")
        return value

    @staticmethod
    def _stdout(result: object) -> str:
        value = getattr(result, "stdout", None)
        if not isinstance(value, str):
            raise MediaTrashFlowError("system_trash_failed", "system trash returned no receipt")
        return value

    def _load_registry(self) -> dict[str, Path]:
        if self.registry_path is None or not self.registry_path.exists():
            return {}
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "locations"}:
            return {}
        locations = payload.get("locations")
        if payload.get("schema_version") != 1 or not isinstance(locations, dict):
            return {}
        result: dict[str, Path] = {}
        for location_id, raw_path in locations.items():
            if not isinstance(location_id, str) or not location_id.startswith("macos-"):
                continue
            if not isinstance(raw_path, str) or not raw_path:
                continue
            try:
                result[location_id] = Path(raw_path).expanduser().resolve()
            except (OSError, RuntimeError):
                continue
        return result

    def _save_registry(self) -> None:
        if self.registry_path is None:
            return
        parent = self.registry_path.parent
        temporary_path: Path | None = None
        descriptor: int | None = None
        try:
            parent.mkdir(parents=True, exist_ok=True)
            descriptor, raw_temporary_path = tempfile.mkstemp(
                prefix=f".{self.registry_path.name}.", suffix=".tmp", dir=parent
            )
            temporary_path = Path(raw_temporary_path)
            payload = {
                "schema_version": 1,
                "locations": {key: str(path) for key, path in sorted(self._locations.items())},
            }
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = None
                handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.registry_path)
        except OSError as exc:
            raise MediaTrashFlowError("receipt_registry_failed", "system trash receipt could not be retained") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _trash_path_from_result(result: object) -> Path:
        try:
            payload = json.loads(MacOSSystemTrashBackend._stdout(result))
        except json.JSONDecodeError as exc:
            raise MediaTrashFlowError("system_trash_failed", "system trash returned an invalid receipt") from exc
        raw_path = payload.get("trash_path") if isinstance(payload, dict) else None
        if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
            raise MediaTrashFlowError("system_trash_failed", "system trash returned an invalid receipt")
        try:
            return Path(raw_path).resolve()
        except (OSError, RuntimeError) as exc:
            raise MediaTrashFlowError("system_trash_failed", "system trash receipt could not be resolved") from exc

    def move_to_trash(self, source: Path, *, candidate_number: str) -> str:
        if sys.platform != "darwin":
            raise MediaTrashFlowError("unsupported_backend", "macOS system trash is unavailable")
        try:
            result = self._runner(
                ("/usr/bin/osascript", "-l", "JavaScript", "-e", _MACOS_TRASH_SCRIPT, str(source)),
                _MACOS_TRASH_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            raise MediaTrashFlowError("system_trash_failed", "system trash move failed") from exc
        if self._returncode(result) != 0:
            raise MediaTrashFlowError("system_trash_failed", "system trash move failed")
        trash_path = self._trash_path_from_result(result)
        location_id = f"macos-{self._identifier_factory()}"
        if location_id in self._locations:
            raise MediaTrashFlowError("system_trash_failed", "system trash receipt id collision")
        self._locations[location_id] = trash_path
        self._save_registry()
        return location_id

    def verify_in_trash(self, trash_location_id: str, expected_sha256: str) -> bool:
        path = self._locations.get(trash_location_id)
        return bool(path and path.is_file() and _sha256_file(path) == expected_sha256)

    def restore_from_trash(
        self,
        trash_location_id: str,
        destination: Path,
        *,
        candidate_number: str,
    ) -> object:
        path = self._locations.get(trash_location_id)
        if path is None or not path.is_file():
            raise MediaTrashFlowError("trash_item_missing", "system trash receipt cannot be restored")
        if destination.exists():
            raise MediaTrashFlowError("restore_target_not_empty", "restore destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(path, destination)
        except OSError as exc:
            raise MediaTrashFlowError("restore_failed", "system trash item could not be restored") from exc
        self._locations.pop(trash_location_id, None)
        self._save_registry()
        return destination

    def verify_restored(self, restored_path: Path, expected_sha256: str) -> bool:
        return restored_path.is_file() and _sha256_file(restored_path) == expected_sha256


def get_system_trash_backend(
    platform_name: str | None = None,
    *,
    registry_path: str | Path | None = None,
) -> TrashBackend | UnavailableSystemTrashBackend:
    """Return the native backend only where recoverability is implemented."""

    normalized = (platform_name or sys.platform).strip().lower() or "unspecified"
    aliases = {
        "darwin": "macos",
        "mac": "macos",
        "macos": "macos",
        "win32": "windows",
        "windows": "windows",
        "linux": "linux",
    }
    platform = aliases.get(normalized, normalized)
    if platform == "macos" and sys.platform == "darwin":
        return MacOSSystemTrashBackend(registry_path=registry_path)
    return UnavailableSystemTrashBackend(platform)


def _fail(code: str, message: str) -> None:
    raise MediaTrashFlowError(code, message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp(value: str | datetime | None, clock: Callable[[], datetime]) -> str:
    if value is None:
        current = clock()
        if not isinstance(current, datetime):
            _fail("invalid_clock", "clock must return a datetime")
        return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.strip():
        _fail("invalid_operation_time", "operation time must be non-blank")
    return value


def _validate_operator(operator: object) -> str:
    if not isinstance(operator, str) or not operator.strip():
        _fail("invalid_operator", "operator must be non-blank")
    return operator.strip()


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        _fail("missing_relative_path", "candidate relative path is required")
    if not value.strip() or "\x00" in value:
        _fail("invalid_relative_path", "candidate relative path is invalid")
    if value.startswith(("/", "\\")) or _WINDOWS_ABSOLUTE_RE.match(value):
        _fail("invalid_relative_path", "candidate relative path must be relative")
    try:
        windows_path = PureWindowsPath(value)
    except (TypeError, ValueError):
        _fail("invalid_relative_path", "candidate relative path is invalid")
    if windows_path.is_absolute() or windows_path.drive:
        _fail("invalid_relative_path", "candidate relative path must be relative")
    if any(part in {"", ".", ".."} for part in re.split(r"[/\\]", value)):
        _fail("invalid_relative_path", "candidate relative path contains an unsafe component")
    return value


def _candidate_number(candidate: Mapping[str, Any]) -> str:
    number = candidate.get("candidate_number")
    alias = candidate.get("candidate_id")
    if number is None:
        number = alias
    if not isinstance(number, str) or not number.strip():
        _fail("missing_candidate_number", "candidate number is required")
    if alias is not None and alias != number:
        _fail("candidate_number_mismatch", "candidate number aliases do not match")
    return number


def _candidate_evidence(candidate: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(candidate, Mapping):
        _fail("invalid_candidate", "candidate must be an object")
    required = ("media_id", "relative_path", "sha256", "image_health", "image_readable")
    if any(field not in candidate or candidate.get(field) is None for field in required):
        _fail("missing_candidate_evidence", "candidate evidence is incomplete")
    media_id = candidate.get("media_id")
    relative_path = _validate_relative_path(candidate.get("relative_path"))
    sha256 = candidate.get("sha256")
    if not isinstance(media_id, str) or not _MEDIA_ID_RE.fullmatch(media_id):
        _fail("invalid_candidate_evidence", "candidate media identity is invalid")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        _fail("invalid_candidate_evidence", "candidate content hash is invalid")
    if candidate.get("image_health") != "healthy" or candidate.get("image_readable") is not True:
        _fail("invalid_candidate_evidence", "candidate image evidence is not eligible")
    evidence = {
        "media_id": media_id,
        "relative_path": relative_path,
        "sha256": sha256,
        "image_health": "healthy",
        "image_readable": True,
    }
    number = _candidate_number(candidate)
    try:
        expected_number = candidate_number_for_evidence(evidence)
    except DeleteRecommendationError as exc:
        _fail("invalid_candidate_evidence", "candidate evidence is invalid")
        raise AssertionError("unreachable") from exc
    if number != expected_number:
        _fail("stale_candidate_number", "candidate number does not match evidence")
    if candidate.get("state") != CANDIDATE_STATE:
        _fail("candidate_state_invalid", "candidate is not a B2 suggested candidate")
    return number, evidence


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _validate_confirmation(confirmation: object) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(confirmation, Mapping):
        _fail("invalid_confirmation", "confirmation must be an object")
    if confirmation.get("state") != CONFIRMED_STATE or confirmation.get("status") != CONFIRMED_STATE:
        _fail("confirmation_not_confirmed", "confirmation must be in the B2 confirmed state")
    if not isinstance(confirmation.get("operation_time"), str) or not confirmation.get("operation_time", "").strip():
        _fail("missing_confirmation_time", "confirmation time is required")
    numbers_value = confirmation.get("selected_candidate_numbers")
    candidates_value = confirmation.get("selected_candidates")
    if not _is_sequence(numbers_value) or not _is_sequence(candidates_value):
        _fail("missing_candidate_selection", "confirmed candidate selection is incomplete")
    numbers = list(numbers_value)
    candidates = list(candidates_value)
    if not numbers or not candidates:
        _fail("empty_candidate_selection", "at least one candidate must be confirmed")
    if len(numbers) != len(candidates):
        _fail("selection_mismatch", "selected numbers and candidates must have equal length")
    if any(not isinstance(number, str) or not number.strip() for number in numbers):
        _fail("invalid_candidate_number", "selected candidate numbers must be non-blank strings")
    if len(numbers) != len(set(numbers)):
        _fail("duplicate_candidate_number", "selected candidate numbers must be unique")

    normalized: list[tuple[str, dict[str, Any]]] = []
    for expected_number, candidate in zip(numbers, candidates, strict=True):
        actual_number, evidence = _candidate_evidence(candidate)
        if actual_number != expected_number:
            _fail("selection_mismatch", "selected number does not match candidate evidence")
        normalized.append((actual_number, evidence))
    return normalized


def _validate_backend(backend: object) -> None:
    if backend is None:
        _fail("unsupported_backend", "a recoverable trash backend is required")
    if getattr(backend, "available", True) is False:
        _fail("unsupported_backend", "system trash backend is unavailable")
    if getattr(backend, "recovery_proven", True) is False:
        _fail("unsupported_backend", "backend recoverability is unproven")
    if any(not callable(getattr(backend, method, None)) for method in _REQUIRED_BACKEND_METHODS):
        _fail("unsupported_backend", "backend lacks required recovery capabilities")


def _validate_location(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("invalid_trash_location", "backend returned no opaque trash location")
    if "\x00" in value or "/" in value or "\\" in value or PureWindowsPath(value).drive:
        _fail("invalid_trash_location", "trash location must be an opaque identifier")
    return value


def _resolve_inside_root(work_root: Path, relative_path: str) -> Path:
    root = work_root.resolve()
    candidate = (root / Path(*re.split(r"[/\\]", relative_path))).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        _fail("path_outside_work_root", "candidate path is outside the explicit work root")
    return candidate


def _pending_record(
    *,
    candidate_number: str,
    relative_path: str,
    expected_sha256: str,
    operator: str,
    operation_time: str,
    code: str,
    location_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": "pending",
        "failure_code": code,
        "candidate_number": candidate_number,
        "original_relative_path": relative_path,
        "sha256": expected_sha256,
        "content_sha256": expected_sha256,
        "operator": operator,
        "operation_time": operation_time,
        "trash_location_id": location_id,
    }


class MediaTrashFlow:
    """Execute confirmed candidate movement and explicit receipt restoration."""

    def __init__(
        self,
        work_root: str | Path,
        backend: TrashBackend | object | None = None,
        *,
        content_hasher: Callable[[Path], str] = _sha256_file,
        clock: Callable[[], datetime] | None = None,
        platform_name: str | None = None,
        system_trash_registry_path: str | Path | None = None,
    ) -> None:
        if not isinstance(work_root, (str, Path)) or not str(work_root).strip():
            _fail("invalid_work_root", "an explicit work root is required")
        self.work_root = Path(work_root).expanduser().resolve()
        if not self.work_root.is_dir():
            _fail("invalid_work_root", "explicit work root must be a directory")
        if not callable(content_hasher):
            _fail("invalid_hasher", "content_hasher must be callable")
        self.backend = backend if backend is not None else get_system_trash_backend(
            platform_name,
            registry_path=system_trash_registry_path,
        )
        self.content_hasher = content_hasher
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._receipts: dict[str, dict[str, Any]] = {}

    def trash_confirmed_candidates(
        self,
        confirmation: Mapping[str, Any],
        *,
        operator: str,
        second_confirmation: bool,
        operation_time: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Move only a complete B2 confirmation through a recoverable backend."""

        _validate_backend(self.backend)
        normalized = _validate_confirmation(confirmation)
        audit_operator = _validate_operator(operator)
        if second_confirmation is not True:
            _fail("second_confirmation_required", "explicit second confirmation is required")
        timestamp = _timestamp(operation_time, self.clock)

        prepared: list[tuple[str, dict[str, Any], Path]] = []
        for number, evidence in normalized:
            source = _resolve_inside_root(self.work_root, evidence["relative_path"])
            if not source.exists():
                _fail("source_missing", "candidate source is unavailable")
            if not source.is_file():
                _fail("source_not_file", "candidate source is not a regular file")
            try:
                actual_sha256 = self.content_hasher(source)
            except Exception as exc:
                _fail("source_unreadable", "candidate source could not be read")
                raise AssertionError("unreachable") from exc
            if actual_sha256 != evidence["sha256"]:
                _fail("source_hash_mismatch", "candidate source content differs from B2 evidence")
            prepared.append((number, evidence, source))

        receipts: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        for number, evidence, source in prepared:
            try:
                current_sha256 = self.content_hasher(source)
            except Exception:
                pending.append(
                    _pending_record(
                        candidate_number=number,
                        relative_path=evidence["relative_path"],
                        expected_sha256=evidence["sha256"],
                        operator=audit_operator,
                        operation_time=timestamp,
                        code="source_unreadable",
                    )
                )
                continue
            if current_sha256 != evidence["sha256"]:
                pending.append(
                    _pending_record(
                        candidate_number=number,
                        relative_path=evidence["relative_path"],
                        expected_sha256=evidence["sha256"],
                        operator=audit_operator,
                        operation_time=timestamp,
                        code="source_hash_mismatch",
                    )
                )
                continue

            try:
                location_id = _validate_location(
                    self.backend.move_to_trash(source, candidate_number=number)
                )
            except MediaTrashFlowError as exc:
                pending.append(
                    _pending_record(
                        candidate_number=number,
                        relative_path=evidence["relative_path"],
                        expected_sha256=evidence["sha256"],
                        operator=audit_operator,
                        operation_time=timestamp,
                        code=exc.code,
                    )
                )
                continue
            except Exception:
                pending.append(
                    _pending_record(
                        candidate_number=number,
                        relative_path=evidence["relative_path"],
                        expected_sha256=evidence["sha256"],
                        operator=audit_operator,
                        operation_time=timestamp,
                        code="move_failed",
                        location_id=None,
                    )
                )
                continue

            try:
                verified = self.backend.verify_in_trash(location_id, evidence["sha256"])
            except Exception:
                verified = False
            if verified is not True:
                pending.append(
                    _pending_record(
                        candidate_number=number,
                        relative_path=evidence["relative_path"],
                        expected_sha256=evidence["sha256"],
                        operator=audit_operator,
                        operation_time=timestamp,
                        code="post_move_verification_failed",
                        location_id=location_id,
                    )
                )
                continue

            receipt = {
                "status": "trashed",
                "candidate_number": number,
                "media_id": evidence["media_id"],
                "original_relative_path": evidence["relative_path"],
                "sha256": evidence["sha256"],
                "content_sha256": evidence["sha256"],
                "operator": audit_operator,
                "operation_time": timestamp,
                "trash_location_id": location_id,
                "post_move_verification": {"status": "verified", "verified": True},
                "restore_result": {"status": "not_requested", "verified": None},
            }
            self._receipts[number] = dict(receipt)
            receipts.append(receipt)

        status = "completed" if not pending else "partial"
        return {
            "status": status,
            "state": status,
            "operator": audit_operator,
            "operation_time": timestamp,
            "receipts": receipts,
            "pending": pending,
        }

    def restore_receipt(
        self,
        receipt: Mapping[str, Any],
        *,
        operator: str | None = None,
        operation_time: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Restore one successful receipt and prove the restored content."""

        _validate_backend(self.backend)
        if not isinstance(receipt, Mapping):
            _fail("invalid_receipt", "receipt must be an object")
        if receipt.get("status") != "trashed":
            _fail("receipt_not_restorable", "only a verified trash receipt can be restored")
        number = receipt.get("candidate_number")
        media_id = receipt.get("media_id")
        relative_path = receipt.get("original_relative_path")
        expected_sha256 = receipt.get("sha256")
        location_id = receipt.get("trash_location_id")
        if (
            not isinstance(number, str)
            or not number.strip()
            or not isinstance(media_id, str)
            or not _MEDIA_ID_RE.fullmatch(media_id)
            or not isinstance(relative_path, str)
            or not isinstance(expected_sha256, str)
            or not _SHA256_RE.fullmatch(expected_sha256)
        ):
            _fail("invalid_receipt", "receipt evidence is incomplete")
        _validate_relative_path(relative_path)
        try:
            expected_number = candidate_number_for_evidence(
                {
                    "media_id": media_id,
                    "relative_path": relative_path,
                    "sha256": expected_sha256,
                    "image_health": "healthy",
                    "image_readable": True,
                }
            )
        except DeleteRecommendationError as exc:
            _fail("invalid_receipt", "receipt evidence is invalid")
            raise AssertionError("unreachable") from exc
        if number != expected_number:
            _fail("invalid_receipt", "receipt candidate number does not match evidence")
        location_id = _validate_location(location_id)
        post_move = receipt.get("post_move_verification")
        if not isinstance(post_move, Mapping) or post_move.get("verified") is not True:
            _fail("receipt_not_restorable", "receipt lacks verified post-move content")
        audit_operator = _validate_operator(operator if operator is not None else receipt.get("operator"))
        timestamp = _timestamp(operation_time, self.clock)
        destination = _resolve_inside_root(self.work_root, relative_path)
        if destination.exists():
            return self._restore_pending(
                receipt,
                number=number,
                operator=audit_operator,
                operation_time=timestamp,
                code="restore_target_not_empty",
            )

        try:
            self.backend.restore_from_trash(
                location_id,
                destination,
                candidate_number=number,
            )
        except Exception:
            return self._restore_pending(
                receipt,
                number=number,
                operator=audit_operator,
                operation_time=timestamp,
                code="restore_failed",
            )

        try:
            backend_verified = self.backend.verify_restored(destination, expected_sha256)
        except Exception:
            backend_verified = False
        if backend_verified is not True:
            return self._restore_pending(
                receipt,
                number=number,
                operator=audit_operator,
                operation_time=timestamp,
                code="restore_verification_failed",
            )
        try:
            actual_sha256 = self.content_hasher(destination)
        except Exception:
            actual_sha256 = None
        if actual_sha256 != expected_sha256:
            return self._restore_pending(
                receipt,
                number=number,
                operator=audit_operator,
                operation_time=timestamp,
                code="restore_hash_mismatch",
            )

        restored = dict(receipt)
        restored["status"] = "restored"
        restored["restore_result"] = {
            "status": "verified",
            "verified": True,
            "operator": audit_operator,
            "operation_time": timestamp,
        }
        self._receipts[number] = dict(restored)
        return restored

    def _restore_pending(
        self,
        receipt: Mapping[str, Any],
        *,
        number: str,
        operator: str,
        operation_time: str,
        code: str,
    ) -> dict[str, Any]:
        pending = dict(receipt)
        pending["status"] = "pending"
        pending["restore_result"] = {
            "status": "pending",
            "verified": False,
            "failure_code": code,
            "operator": operator,
            "operation_time": operation_time,
        }
        self._receipts[number] = dict(pending)
        return pending


def trash_confirmed_candidates(
    confirmation: Mapping[str, Any],
    *,
    work_root: str | Path,
    backend: TrashBackend | object | None = None,
    operator: str,
    second_confirmation: bool,
    operation_time: str | datetime | None = None,
    content_hasher: Callable[[Path], str] = _sha256_file,
    clock: Callable[[], datetime] | None = None,
    platform_name: str | None = None,
    system_trash_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convenience entry point for one isolated trash-flow operation."""

    flow = MediaTrashFlow(
        work_root,
        backend,
        content_hasher=content_hasher,
        clock=clock,
        platform_name=platform_name,
        system_trash_registry_path=system_trash_registry_path,
    )
    return flow.trash_confirmed_candidates(
        confirmation,
        operator=operator,
        second_confirmation=second_confirmation,
        operation_time=operation_time,
    )


__all__ = [
    "MediaTrashFlow",
    "MediaTrashFlowError",
    "MacOSSystemTrashBackend",
    "TrashBackend",
    "UnavailableSystemTrashBackend",
    "get_system_trash_backend",
    "trash_confirmed_candidates",
]
