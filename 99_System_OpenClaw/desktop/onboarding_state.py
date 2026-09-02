"""Durable state for the four-step first-run onboarding wizard."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "photo_content_os_onboarding_v1"
STATE_FILE_NAME = "onboarding_state.json"


class OnboardingStep(str, Enum):
    """The fixed order presented by the desktop onboarding flow."""

    STORAGE_LOCATION = "storage_location"
    RUNTIME_ENVIRONMENT = "runtime_environment"
    EDITOR = "editor"
    ACCOUNT_DEVICE = "account_device"


class StepStatus(str, Enum):
    """Persisted outcomes; only the account step may be optional."""

    PENDING = "pending"
    READY = "ready"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


ONBOARDING_STEPS = tuple(OnboardingStep)
_LOCAL_STEPS = ONBOARDING_STEPS[:-1]
_REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "current_step",
        "completed",
        "local_features_available",
        "upstream_features_available",
        "steps",
    }
)
_STEP_FIELDS = frozenset({"status", "reason_code"})


class OnboardingStateError(ValueError):
    """Fail-closed state or storage error with a stable, non-secret code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _reject(code: str) -> None:
    raise OnboardingStateError(code)


def _coerce_step(value: OnboardingStep | str) -> OnboardingStep:
    try:
        return value if isinstance(value, OnboardingStep) else OnboardingStep(value)
    except (TypeError, ValueError) as exc:
        raise OnboardingStateError("step_invalid") from exc


def _coerce_status(value: StepStatus | str) -> StepStatus:
    try:
        return value if isinstance(value, StepStatus) else StepStatus(value)
    except (TypeError, ValueError) as exc:
        raise OnboardingStateError("step_status_invalid") from exc


def _reason_code(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _REASON_CODE_RE.fullmatch(value):
        _reject("reason_code_invalid")
    return value


@dataclass(frozen=True, slots=True)
class OnboardingStepState:
    """One allowlisted step outcome without user text or connection material."""

    step: OnboardingStep
    status: StepStatus = StepStatus.PENDING
    reason_code: str | None = None

    def __post_init__(self) -> None:
        step = _coerce_step(self.step)
        status = _coerce_status(self.status)
        reason_code = _reason_code(self.reason_code)
        if step in _LOCAL_STEPS and status in {StepStatus.SKIPPED, StepStatus.UNSUPPORTED}:
            _reject("required_step_optional_outcome")
        if status in {StepStatus.PENDING, StepStatus.READY} and reason_code is not None:
            _reject("reason_code_not_allowed")
        if status in {StepStatus.SKIPPED, StepStatus.UNSUPPORTED, StepStatus.ERROR} and reason_code is None:
            _reject("reason_code_required")
        object.__setattr__(self, "step", step)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason_code", reason_code)

    @classmethod
    def from_dict(cls, step: OnboardingStep, value: object) -> "OnboardingStepState":
        if not isinstance(value, Mapping) or set(value) != _STEP_FIELDS:
            _reject("step_state_schema_invalid")
        return cls(step=step, status=value["status"], reason_code=value["reason_code"])

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status.value, "reason_code": self.reason_code}


@dataclass(frozen=True, slots=True)
class OnboardingState:
    """Validated wizard snapshot whose derived readiness cannot be forged."""

    steps: tuple[OnboardingStepState, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.steps, tuple)
            or len(self.steps) != len(ONBOARDING_STEPS)
            or any(not isinstance(item, OnboardingStepState) for item in self.steps)
        ):
            _reject("steps_invalid")
        if tuple(item.step for item in self.steps) != ONBOARDING_STEPS:
            _reject("steps_invalid")

        open_step_seen = False
        for item in self.steps:
            terminal = item.status is StepStatus.READY or (
                item.step is OnboardingStep.ACCOUNT_DEVICE
                and item.status in {StepStatus.SKIPPED, StepStatus.UNSUPPORTED}
            )
            if open_step_seen and item.status is not StepStatus.PENDING:
                _reject("step_order_invalid")
            if not terminal:
                open_step_seen = True

    @classmethod
    def initial(cls) -> "OnboardingState":
        return cls(tuple(OnboardingStepState(step) for step in ONBOARDING_STEPS))

    @classmethod
    def from_dict(cls, value: object) -> "OnboardingState":
        if not isinstance(value, Mapping) or set(value) != _ROOT_FIELDS:
            _reject("state_schema_invalid")
        if value["schema_version"] != SCHEMA_VERSION:
            _reject("schema_version_invalid")
        raw_steps = value["steps"]
        expected_step_names = {step.value for step in ONBOARDING_STEPS}
        if not isinstance(raw_steps, Mapping) or set(raw_steps) != expected_step_names:
            _reject("steps_invalid")
        state = cls(tuple(OnboardingStepState.from_dict(step, raw_steps[step.value]) for step in ONBOARDING_STEPS))
        if value["current_step"] != (state.current_step.value if state.current_step else None):
            _reject("derived_state_invalid")
        if type(value["completed"]) is not bool or value["completed"] != state.completed:
            _reject("derived_state_invalid")
        if (
            type(value["local_features_available"]) is not bool
            or value["local_features_available"] != state.local_features_available
        ):
            _reject("derived_state_invalid")
        if (
            type(value["upstream_features_available"]) is not bool
            or value["upstream_features_available"] != state.upstream_features_available
        ):
            _reject("derived_state_invalid")
        return state

    @property
    def current_step(self) -> OnboardingStep | None:
        for item in self.steps:
            if item.status is StepStatus.READY:
                continue
            if item.step is OnboardingStep.ACCOUNT_DEVICE and item.status in {
                StepStatus.SKIPPED,
                StepStatus.UNSUPPORTED,
            }:
                continue
            return item.step
        return None

    @property
    def local_features_available(self) -> bool:
        return all(self.step(step).status is StepStatus.READY for step in _LOCAL_STEPS)

    @property
    def upstream_features_available(self) -> bool:
        return self.step(OnboardingStep.ACCOUNT_DEVICE).status is StepStatus.READY

    @property
    def completed(self) -> bool:
        return self.current_step is None

    def step(self, step: OnboardingStep | str) -> OnboardingStepState:
        resolved = _coerce_step(step)
        return self.steps[ONBOARDING_STEPS.index(resolved)]

    def transition(
        self,
        step: OnboardingStep | str,
        status: StepStatus | str,
        *,
        reason_code: str | None = None,
    ) -> "OnboardingState":
        resolved_step = _coerce_step(step)
        resolved_status = _coerce_status(status)
        if self.current_step is None:
            _reject("onboarding_complete")
        if resolved_step is not self.current_step:
            _reject("step_out_of_order")
        if resolved_status is StepStatus.PENDING:
            _reject("transition_invalid")
        if reason_code is None:
            reason_code = {
                StepStatus.SKIPPED: "user_skipped",
                StepStatus.UNSUPPORTED: "upstream_platform_unsupported",
                StepStatus.ERROR: "step_error",
            }.get(resolved_status)
        replacement = OnboardingStepState(resolved_step, resolved_status, reason_code)
        updated = list(self.steps)
        updated[ONBOARDING_STEPS.index(resolved_step)] = replacement
        return OnboardingState(tuple(updated))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "current_step": self.current_step.value if self.current_step else None,
            "completed": self.completed,
            "local_features_available": self.local_features_available,
            "upstream_features_available": self.upstream_features_available,
            "steps": {item.step.value: item.to_dict() for item in self.steps},
        }


class OnboardingStateStore:
    """Atomic JSON persistence rooted at one explicit runtime directory."""

    def __init__(self, work_dir: str | os.PathLike[str]) -> None:
        if work_dir is None or isinstance(work_dir, (bytes, bytearray)) or not str(work_dir).strip():
            _reject("work_dir_invalid")
        try:
            resolved = Path(work_dir).expanduser().resolve()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise OnboardingStateError("work_dir_invalid") from exc
        if resolved.exists() and not resolved.is_dir():
            _reject("work_dir_invalid")
        self.work_dir = resolved
        self.path = resolved / STATE_FILE_NAME

    def _ensure_work_dir(self) -> None:
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OnboardingStateError("storage_unavailable") from exc
        if not self.work_dir.is_dir():
            _reject("storage_unavailable")

    def load(self) -> OnboardingState:
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            _reject("storage_unavailable")
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise OnboardingStateError("state_not_found") from exc
        except (OSError, UnicodeError) as exc:
            raise OnboardingStateError("storage_unavailable") from exc
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OnboardingStateError("state_json_invalid") from exc
        return OnboardingState.from_dict(value)

    def save(self, state: OnboardingState | Mapping[str, object]) -> OnboardingState:
        if isinstance(state, Mapping):
            state = OnboardingState.from_dict(state)
        if not isinstance(state, OnboardingState):
            _reject("state_invalid")
        self._ensure_work_dir()
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            _reject("storage_unavailable")
        serialized = json.dumps(state.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        descriptor: int | None = None
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{STATE_FILE_NAME}.",
                suffix=".tmp",
                dir=self.work_dir,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = None
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
            self._sync_directory()
        except OSError as exc:
            raise OnboardingStateError("storage_write_failed") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
        return state

    def _sync_directory(self) -> None:
        try:
            descriptor = os.open(self.work_dir, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def initialize(self) -> OnboardingState:
        if self.path.exists() or self.path.is_symlink():
            _reject("state_exists")
        return self.save(OnboardingState.initial())

    def resume(self) -> OnboardingState:
        if self.path.exists() or self.path.is_symlink():
            return self.load()
        return self.save(OnboardingState.initial())

    def transition(
        self,
        step: OnboardingStep | str,
        status: StepStatus | str,
        *,
        reason_code: str | None = None,
    ) -> OnboardingState:
        updated = self.load().transition(step, status, reason_code=reason_code)
        return self.save(updated)


__all__ = [
    "ONBOARDING_STEPS",
    "OnboardingState",
    "OnboardingStateError",
    "OnboardingStateStore",
    "OnboardingStep",
    "OnboardingStepState",
    "SCHEMA_VERSION",
    "STATE_FILE_NAME",
    "StepStatus",
]
