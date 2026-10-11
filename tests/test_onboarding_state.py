from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.onboarding_state import (  # noqa: E402
    OnboardingState,
    OnboardingStateError,
    OnboardingStateStore,
    OnboardingStep,
    StepStatus,
)


class OnboardingStateTests(unittest.TestCase):
    def test_partial_progress_survives_restart_and_resumes_at_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory) / "state"
            store = OnboardingStateStore(work_dir)
            initial = store.resume()
            self.assertEqual(initial.current_step, OnboardingStep.STORAGE_LOCATION)

            store.transition(OnboardingStep.STORAGE_LOCATION, StepStatus.READY)
            reloaded = OnboardingStateStore(work_dir).resume()

            self.assertEqual(reloaded.current_step, OnboardingStep.RUNTIME_ENVIRONMENT)
            self.assertFalse(reloaded.completed)
            self.assertFalse(reloaded.local_features_available)

    def test_skipped_account_completes_local_onboarding_without_upstream_login(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory) / "state"
            store = OnboardingStateStore(work_dir)
            store.resume()
            for step in (
                OnboardingStep.STORAGE_LOCATION,
                OnboardingStep.RUNTIME_ENVIRONMENT,
                OnboardingStep.EDITOR,
            ):
                store.transition(step, StepStatus.READY)

            completed = store.transition(OnboardingStep.ACCOUNT_DEVICE, StepStatus.SKIPPED)
            restarted = OnboardingStateStore(work_dir).load()

            self.assertEqual(restarted, completed)
            self.assertTrue(restarted.completed)
            self.assertTrue(restarted.local_features_available)
            self.assertFalse(restarted.upstream_features_available)
            self.assertEqual(
                restarted.step(OnboardingStep.ACCOUNT_DEVICE).reason_code,
                "user_skipped",
            )
            serialized = store.path.read_text(encoding="utf-8")
            for forbidden in ("access_token", "refresh_token", "credential", "session_ref"):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(list(work_dir.glob("*.tmp")), [])

    def test_unsupported_account_is_terminal_but_does_not_disable_local_features(self) -> None:
        state = OnboardingState.initial()
        for step in (
            OnboardingStep.STORAGE_LOCATION,
            OnboardingStep.RUNTIME_ENVIRONMENT,
            OnboardingStep.EDITOR,
        ):
            state = state.transition(step, StepStatus.READY)

        state = state.transition(OnboardingStep.ACCOUNT_DEVICE, StepStatus.UNSUPPORTED)

        self.assertTrue(state.completed)
        self.assertTrue(state.local_features_available)
        self.assertFalse(state.upstream_features_available)
        self.assertEqual(
            state.step(OnboardingStep.ACCOUNT_DEVICE).reason_code,
            "upstream_platform_unsupported",
        )

    def test_required_steps_cannot_be_skipped_or_completed_out_of_order(self) -> None:
        state = OnboardingState.initial()

        with self.assertRaises(OnboardingStateError) as skipped:
            state.transition(OnboardingStep.STORAGE_LOCATION, StepStatus.SKIPPED)
        self.assertEqual(skipped.exception.code, "required_step_optional_outcome")

        with self.assertRaises(OnboardingStateError) as out_of_order:
            state.transition(OnboardingStep.EDITOR, StepStatus.READY)
        self.assertEqual(out_of_order.exception.code, "step_out_of_order")

    def test_corrupt_unknown_and_forged_state_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = OnboardingStateStore(Path(directory) / "state")
            store.resume()
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            payload["steps"]["account_device"]["access_token"] = "must-not-escape"
            store.path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(OnboardingStateError) as unknown:
                store.load()
            self.assertEqual(unknown.exception.code, "step_state_schema_invalid")
            self.assertNotIn("must-not-escape", str(unknown.exception))

            payload["steps"]["account_device"].pop("access_token")
            payload["completed"] = True
            store.path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(OnboardingStateError) as forged:
                store.load()
            self.assertEqual(forged.exception.code, "derived_state_invalid")

            store.path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(OnboardingStateError) as corrupt:
                store.load()
            self.assertEqual(corrupt.exception.code, "state_json_invalid")


if __name__ == "__main__":
    unittest.main()
