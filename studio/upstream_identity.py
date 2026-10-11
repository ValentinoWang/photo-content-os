"""Transport-free diagnosis for optional upstream identity pairing."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum


LOCAL_DEVICE_PLATFORMS = frozenset({"macos", "windows", "linux"})
UPSTREAM_DEVICE_PLATFORMS = frozenset({"macos"})


class UpstreamIdentityDiagnosisState(str, Enum):
    """Capability states that keep unsupported distinct from failures."""

    READY = "ready"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class UpstreamIdentityDiagnosis:
    """Secret-free capability projection for a local device platform."""

    state: UpstreamIdentityDiagnosisState
    platform: str
    reason_code: str | None

    @property
    def local_features_available(self) -> bool:
        return True

    @property
    def pairing_available(self) -> bool:
        return self.state is UpstreamIdentityDiagnosisState.READY

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "platform": self.platform,
            "reason_code": self.reason_code,
            "local_features_available": True,
            "pairing_available": self.pairing_available,
        }


def _diagnosis(
    state: UpstreamIdentityDiagnosisState,
    platform: str,
    reason_code: str | None,
) -> UpstreamIdentityDiagnosis:
    return UpstreamIdentityDiagnosis(state=state, platform=platform, reason_code=reason_code)


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def diagnose_upstream_identity(
    platform: str,
    compatibility_checker: Callable[..., object] | None = None,
) -> UpstreamIdentityDiagnosis:
    """Diagnose pairing without transport, persistence, or login side effects."""

    if not isinstance(platform, str) or not platform.strip():
        return _diagnosis(UpstreamIdentityDiagnosisState.ERROR, "unknown", "platform_invalid")
    normalized_platform = platform.strip().lower()
    if normalized_platform not in LOCAL_DEVICE_PLATFORMS:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.ERROR,
            "unknown",
            "local_platform_unknown",
        )
    if normalized_platform not in UPSTREAM_DEVICE_PLATFORMS:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.UNSUPPORTED,
            normalized_platform,
            "upstream_platform_unsupported",
        )
    if compatibility_checker is None:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.UNAVAILABLE,
            normalized_platform,
            "upstream_probe_unavailable",
        )

    try:
        compatibility = compatibility_checker(require_cloud_platform=True)
    except Exception:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.ERROR,
            normalized_platform,
            "upstream_probe_error",
        )

    available = _field(compatibility, "available")
    compatible = _field(compatibility, "compatible")
    diagnosed_platform = _field(compatibility, "platform")
    reason = _field(compatibility, "reason")
    if type(available) is not bool or type(compatible) is not bool or not isinstance(diagnosed_platform, str):
        return _diagnosis(
            UpstreamIdentityDiagnosisState.ERROR,
            normalized_platform,
            "upstream_probe_invalid",
        )
    if diagnosed_platform.strip().lower() != normalized_platform:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.ERROR,
            normalized_platform,
            "upstream_platform_mismatch",
        )
    if reason == "upstream_platform_unsupported":
        return _diagnosis(
            UpstreamIdentityDiagnosisState.UNSUPPORTED,
            normalized_platform,
            "upstream_platform_unsupported",
        )
    if not available:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.UNAVAILABLE,
            normalized_platform,
            "upstream_dependency_unavailable",
        )
    if not compatible or reason is not None:
        return _diagnosis(
            UpstreamIdentityDiagnosisState.ERROR,
            normalized_platform,
            "upstream_contract_incompatible",
        )
    return _diagnosis(UpstreamIdentityDiagnosisState.READY, normalized_platform, None)


__all__ = [
    "LOCAL_DEVICE_PLATFORMS",
    "UPSTREAM_DEVICE_PLATFORMS",
    "UpstreamIdentityDiagnosis",
    "UpstreamIdentityDiagnosisState",
    "diagnose_upstream_identity",
]
