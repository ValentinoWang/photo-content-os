#!/usr/bin/env python3
"""Regression coverage for the shared queue_identity module (L-06 dedup).

Before 32_process_openclaw_queue.py, 33_enqueue_openclaw_queue_job.py and
mac_openclaw_runner.py were switched to import VOLATILE_TASK_FIELDS,
request_fingerprint and TASK_INBOX/RESULT_OUTBOX from queue_identity, each
of them defined an identical, hand-rolled copy. This test asserts the three
call sites (and the new shared module) still agree, which is exactly the
guarantee the dedup relies on -- if a future change makes any one of them
diverge again, this test is the tripwire.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


queue_identity = load("queue_identity")
openclaw_queue = load("32_process_openclaw_queue")
enqueue_queue = load("33_enqueue_openclaw_queue_job")
runner = load("mac_openclaw_runner")


SAMPLE_PAYLOAD = {
    "task_id": "task_20260828_001",
    "task_type": "local_material_match",
    "project_id": "project_demo",
    "project_revision": 3,
    "editor_backend": "handoff_pack",
    "idempotency_key": "task_20260828_001",
    "nested": {"b": 2, "a": 1},
    "created_at": "2026-08-28T00:00:00Z",
    "updated_at": "2026-08-29T00:00:00Z",
    "generated_at": "2026-08-29T00:00:01Z",
    "request_fingerprint": "sha256:stale-value-from-a-previous-write",
}


class QueueIdentityRegressionTests(unittest.TestCase):
    def test_request_fingerprint_agrees_across_all_three_call_sites(self) -> None:
        fingerprints = {
            "queue_identity": queue_identity.request_fingerprint(SAMPLE_PAYLOAD),
            "32_process_openclaw_queue": openclaw_queue.request_fingerprint(SAMPLE_PAYLOAD),
            "33_enqueue_openclaw_queue_job": enqueue_queue.request_fingerprint(SAMPLE_PAYLOAD),
            "mac_openclaw_runner": runner.request_fingerprint(SAMPLE_PAYLOAD),
        }
        distinct = set(fingerprints.values())
        self.assertEqual(
            len(distinct),
            1,
            f"request_fingerprint diverged across call sites: {fingerprints}",
        )
        self.assertTrue(next(iter(distinct)).startswith("sha256:"))

    def test_request_fingerprint_ignores_volatile_fields_everywhere(self) -> None:
        stable_only = {
            key: value for key, value in SAMPLE_PAYLOAD.items() if key not in queue_identity.VOLATILE_TASK_FIELDS
        }
        expected = queue_identity.request_fingerprint(stable_only)
        for module in (openclaw_queue, enqueue_queue, runner):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.request_fingerprint(SAMPLE_PAYLOAD), expected)

    def test_volatile_task_fields_are_identical_across_call_sites(self) -> None:
        self.assertEqual(openclaw_queue.VOLATILE_TASK_FIELDS, queue_identity.VOLATILE_TASK_FIELDS)
        self.assertEqual(enqueue_queue.VOLATILE_TASK_FIELDS, queue_identity.VOLATILE_TASK_FIELDS)
        self.assertEqual(runner.VOLATILE_TASK_FIELDS, queue_identity.VOLATILE_TASK_FIELDS)

    def test_task_inbox_and_result_outbox_paths_are_identical(self) -> None:
        self.assertEqual(enqueue_queue.TASK_INBOX, queue_identity.TASK_INBOX)
        self.assertEqual(enqueue_queue.RESULT_OUTBOX, queue_identity.RESULT_OUTBOX)
        self.assertEqual(runner.TASK_INBOX, queue_identity.TASK_INBOX)
        self.assertEqual(runner.RESULT_OUTBOX, queue_identity.RESULT_OUTBOX)


if __name__ == "__main__":
    unittest.main()
