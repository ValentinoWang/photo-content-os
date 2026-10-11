"""In-memory consumer for the safe upstream pairing projection."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Protocol


# Keep this boundary identical to upstream_identity.RESULT_FIELDS.  The desktop
# consumer intentionally does not import the upstream transport/compatibility
# module, so it remains usable when the optional upstream package is absent.
E4_RESULT_FIELDS = frozenset(
    {
        "upstream_principal_id",
        "roles",
        "revoked",
        "pairing_status",
        "session_ref",
    }
)
_PAIRING_STATUSES = frozenset({"rejected", "unavailable", "unsupported", "paired"})
_SECRET_FIELD_MARKERS = (
    "api_key",
    "access_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class UpstreamSessionStatus(str, Enum):
    """Local state names that never enable upstream capabilities by themselves."""

    DEFAULT = "default"
    UNPAIRED = "unpaired"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    PAIRED = "paired"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SIGNED_OUT = "signed_out"
    INVALID = "invalid"


class UpstreamSessionContractError(ValueError):
    """Raised without echoing untrusted upstream fields or values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class UpstreamReadback(Protocol):
    """Injectable readback boundary; it has no default transport implementation."""

    def __call__(self, session_ref: str) -> Mapping[str, object]:
        """Read the current safe pairing projection for a session reference."""


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    """Immutable, serializable local state with local capability always enabled."""

    session_state: str
    local_features_available: bool
    upstream_features_available: bool
    upstream_principal_id: str | None
    roles: tuple[str, ...]
    revoked: bool | None
    pairing_status: str | None
    session_ref: str | None

    def to_dict(self) -> dict[str, object]:
        """Return only the public projection; the internal tuple stays immutable."""

        return {
            "session_state": self.session_state,
            "local_features_available": self.local_features_available,
            "upstream_features_available": self.upstream_features_available,
            "upstream_principal_id": self.upstream_principal_id,
            "roles": list(self.roles),
            "revoked": self.revoked,
            "pairing_status": self.pairing_status,
            "session_ref": self.session_ref,
        }


@dataclass(frozen=True, slots=True)
class _ValidatedPairing:
    pairing_status: str
    upstream_principal_id: str | None
    roles: tuple[str, ...]
    revoked: bool | None
    session_ref: str | None


def _reject(code: str) -> None:
    raise UpstreamSessionContractError(code)


def _is_secret_field(name: str) -> bool:
    normalized = name.casefold().replace("-", "_")
    return any(marker in normalized for marker in _SECRET_FIELD_MARKERS)


def _validate_result(result: object) -> _ValidatedPairing:
    """Validate the exact E4 projection before any value can enter state."""

    if not isinstance(result, Mapping):
        _reject("result_not_mapping")

    try:
        keys = tuple(result.keys())
        field_set = frozenset(keys)
    except (AttributeError, TypeError):
        _reject("result_fields_invalid")

    if any(not isinstance(key, str) for key in keys):
        _reject("result_fields_invalid")
    if field_set != E4_RESULT_FIELDS:
        unknown_fields = field_set - E4_RESULT_FIELDS
        if any(_is_secret_field(field) for field in unknown_fields):
            _reject("secret_field_rejected")
        _reject("unknown_field_rejected")

    pairing_status = result["pairing_status"]
    if not isinstance(pairing_status, str) or pairing_status not in _PAIRING_STATUSES:
        _reject("pairing_status_invalid")

    roles = result["roles"]
    if not isinstance(roles, list):
        _reject("roles_invalid")
    normalized_roles: list[str] = []
    for role in roles:
        if not isinstance(role, str) or not role or role != role.strip() or role in normalized_roles:
            _reject("roles_invalid")
        normalized_roles.append(role)

    principal_id = result["upstream_principal_id"]
    revoked = result["revoked"]
    session_ref = result["session_ref"]
    if pairing_status != "paired":
        if principal_id is not None or normalized_roles or revoked is not None or session_ref is not None:
            _reject("inactive_result_invalid")
        return _ValidatedPairing(pairing_status, None, (), None, None)

    if not isinstance(principal_id, str) or not principal_id or principal_id != principal_id.strip():
        _reject("principal_id_invalid")
    if type(revoked) is not bool:
        _reject("revoked_invalid")
    if not isinstance(session_ref, str) or not session_ref or session_ref != session_ref.strip() or any(
        character.isspace() for character in session_ref
    ):
        _reject("session_ref_invalid")
    return _ValidatedPairing(pairing_status, principal_id, tuple(normalized_roles), revoked, session_ref)


def _empty_snapshot(status: UpstreamSessionStatus, *, pairing_status: str | None = None, revoked: bool | None = None) -> SessionSnapshot:
    return SessionSnapshot(
        session_state=status.value,
        local_features_available=True,
        upstream_features_available=False,
        upstream_principal_id=None,
        roles=(),
        revoked=revoked,
        pairing_status=pairing_status,
        session_ref=None,
    )


class UpstreamSessionConsumer:
    """Consume E4 results while keeping the local workbench fully usable."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._generation = 0
        self._state = _empty_snapshot(UpstreamSessionStatus.DEFAULT)

    @property
    def state(self) -> SessionSnapshot:
        """Return the immutable state object without exposing mutable internals."""

        with self._lock:
            return self._state

    def snapshot(self) -> dict[str, object]:
        """Return a fresh JSON-safe copy of the current state."""

        return self.state.to_dict()

    def consume(self, pairing_result: Mapping[str, object]) -> dict[str, object]:
        """Accept one E4 projection and replace all prior upstream state."""

        with self._lock:
            try:
                projection = _validate_result(pairing_result)
            except UpstreamSessionContractError:
                self._clear(UpstreamSessionStatus.INVALID)
                raise
            self._apply(projection)
            return self._state.to_dict()

    def refresh(self, reader: UpstreamReadback) -> dict[str, object]:
        """Refresh through the injected reader and fail closed on invalid readback."""

        with self._lock:
            session_ref = self._state.session_ref
            generation = self._generation
        if session_ref is None:
            return self.snapshot()

        try:
            result = reader(session_ref)
        except Exception:
            return self._invalidate_refresh(generation, session_ref)

        with self._lock:
            if generation != self._generation or self._state.session_ref != session_ref:
                return self._state.to_dict()
            try:
                projection = _validate_result(result)
            except UpstreamSessionContractError:
                self._clear(UpstreamSessionStatus.INVALID)
                return self._state.to_dict()
            self._apply(projection)
            return self._state.to_dict()

    def expire(self) -> dict[str, object]:
        """Remove the session reference when its lifetime has ended."""

        with self._lock:
            self._clear(UpstreamSessionStatus.EXPIRED)
            return self._state.to_dict()

    def logout(self) -> dict[str, object]:
        """Clear every upstream projection while retaining local availability."""

        with self._lock:
            self._clear(UpstreamSessionStatus.SIGNED_OUT)
            return self._state.to_dict()

    def _invalidate_refresh(self, generation: int, session_ref: str) -> dict[str, object]:
        with self._lock:
            if generation == self._generation and self._state.session_ref == session_ref:
                self._clear(UpstreamSessionStatus.INVALID)
            return self._state.to_dict()

    def _apply(self, projection: _ValidatedPairing) -> None:
        if projection.pairing_status == "rejected":
            self._clear(UpstreamSessionStatus.UNPAIRED, pairing_status="rejected")
            return
        if projection.pairing_status == "unavailable":
            self._clear(UpstreamSessionStatus.UNAVAILABLE, pairing_status="unavailable")
            return
        if projection.pairing_status == "unsupported":
            self._clear(UpstreamSessionStatus.UNSUPPORTED, pairing_status="unsupported")
            return
        if projection.revoked:
            self._clear(UpstreamSessionStatus.REVOKED, pairing_status="paired", revoked=True)
            return
        self._generation += 1
        self._state = SessionSnapshot(
            session_state=UpstreamSessionStatus.PAIRED.value,
            local_features_available=True,
            upstream_features_available=True,
            upstream_principal_id=projection.upstream_principal_id,
            roles=projection.roles,
            revoked=False,
            pairing_status="paired",
            session_ref=projection.session_ref,
        )

    def _clear(
        self,
        status: UpstreamSessionStatus,
        *,
        pairing_status: str | None = None,
        revoked: bool | None = None,
    ) -> None:
        self._generation += 1
        self._state = _empty_snapshot(status, pairing_status=pairing_status, revoked=revoked)


__all__ = [
    "E4_RESULT_FIELDS",
    "SessionSnapshot",
    "UpstreamReadback",
    "UpstreamSessionConsumer",
    "UpstreamSessionContractError",
    "UpstreamSessionStatus",
]
