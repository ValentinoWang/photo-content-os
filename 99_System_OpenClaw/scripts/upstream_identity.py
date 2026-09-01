#!/usr/bin/env python3
"""User-initiated, non-persistent pairing with the upstream identity system."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from openclaw_product_contract import Compatibility, compatibility


class PairingStatus(str, Enum):
    """Stable states exposed by the local pairing boundary."""

    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"
    PAIRED = "paired"


@dataclass(frozen=True)
class PairingRequest:
    """The two explicit signals required before an upstream lookup."""

    user_confirmed: bool
    local_pairing_intent: str


class UpstreamIdentityClient(Protocol):
    """Minimal upstream adapter; implementations own transport and idempotency."""

    def find_identity(self, local_pairing_intent: str) -> Mapping[str, object] | None:
        """Find the account associated with the explicit local intent."""

    def create_identity(self, local_pairing_intent: str) -> Mapping[str, object]:
        """Create or return the existing account for the intent, idempotently."""

    def read_identity(self, principal_id: str) -> Mapping[str, object]:
        """Read the authoritative identity, roles and revocation state."""


class UpstreamIdentityContractError(RuntimeError):
    """Raised when an injected adapter violates the identity readback shape."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


RESULT_FIELDS = frozenset(
    {
        "upstream_principal_id",
        "roles",
        "revoked",
        "pairing_status",
        "session_ref",
    }
)


def _empty_result(status: PairingStatus) -> dict[str, object]:
    return {
        "upstream_principal_id": None,
        "roles": [],
        "revoked": None,
        "pairing_status": status.value,
        "session_ref": None,
    }


def _request_intent(request: PairingRequest | Mapping[str, object]) -> str | None:
    if isinstance(request, PairingRequest):
        confirmed = request.user_confirmed
        intent = request.local_pairing_intent
    elif isinstance(request, Mapping):
        confirmed = request.get("user_confirmed")
        intent = request.get("local_pairing_intent")
    else:
        return None

    if confirmed is not True or not isinstance(intent, str):
        return None
    normalized_intent = intent.strip()
    return normalized_intent or None


def _principal_id(record: object) -> str:
    if not isinstance(record, Mapping):
        raise UpstreamIdentityContractError("identity_reference_invalid")

    candidates: list[str] = []
    for field in ("upstream_principal_id", "principal_id"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    if not candidates or len(set(candidates)) != 1:
        raise UpstreamIdentityContractError("principal_id_missing_or_ambiguous")
    return candidates[0]


def _roles(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise UpstreamIdentityContractError("roles_invalid")

    result: list[str] = []
    seen: set[str] = set()
    for role in value:
        if not isinstance(role, str):
            raise UpstreamIdentityContractError("role_invalid")
        normalized_role = role.strip()
        if normalized_role and normalized_role not in seen:
            seen.add(normalized_role)
            result.append(normalized_role)
    return result


def _session_ref(value: object) -> str:
    if not isinstance(value, str):
        raise UpstreamIdentityContractError("session_ref_invalid")
    normalized_ref = value.strip()
    if not normalized_ref or any(character.isspace() for character in normalized_ref):
        raise UpstreamIdentityContractError("session_ref_invalid")
    return normalized_ref


def _project_readback(record: object, expected_principal_id: str) -> dict[str, object]:
    if not isinstance(record, Mapping):
        raise UpstreamIdentityContractError("identity_readback_invalid")

    principal_id = _principal_id(record)
    if principal_id != expected_principal_id:
        raise UpstreamIdentityContractError("identity_readback_mismatch")

    revoked = record.get("revoked")
    if type(revoked) is not bool:
        raise UpstreamIdentityContractError("revoked_invalid")

    return {
        "upstream_principal_id": principal_id,
        "roles": _roles(record.get("roles")),
        "revoked": revoked,
        "pairing_status": PairingStatus.PAIRED.value,
        "session_ref": _session_ref(record.get("session_ref")),
    }


def _compatible(checker: Callable[..., Compatibility]) -> bool:
    result = checker(require_cloud_platform=True)
    return bool(result.available and result.compatible)


def pair_upstream_identity(
    request: PairingRequest | Mapping[str, object],
    client: UpstreamIdentityClient,
    *,
    compatibility_checker: Callable[..., Compatibility] | None = None,
) -> dict[str, object]:
    """Pair only after explicit confirmation and project the safe readback shape.

    The injected client is called at most once for each lookup, creation and
    readback step. It must treat ``local_pairing_intent`` as its idempotency key;
    this module deliberately has no persistence or transport implementation.
    """

    intent = _request_intent(request)
    if intent is None:
        return _empty_result(PairingStatus.REJECTED)

    checker = compatibility_checker or compatibility
    if not _compatible(checker):
        return _empty_result(PairingStatus.UNAVAILABLE)

    identity = client.find_identity(intent)
    if identity is None:
        identity = client.create_identity(intent)
    principal_id = _principal_id(identity)
    readback = client.read_identity(principal_id)
    result = _project_readback(readback, principal_id)
    if frozenset(result) != RESULT_FIELDS:
        raise UpstreamIdentityContractError("result_shape_invalid")
    return result


__all__ = [
    "PairingRequest",
    "PairingStatus",
    "RESULT_FIELDS",
    "UpstreamIdentityClient",
    "UpstreamIdentityContractError",
    "pair_upstream_identity",
]
