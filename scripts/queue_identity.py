#!/usr/bin/env python3
"""Shared identity/fingerprint primitives for the cloud <-> Mac OpenClaw queue.

32_process_openclaw_queue.py (the local _OpenClawQueue execution layer),
33_enqueue_openclaw_queue_job.py (the bridge from the upper Content OS task
layer into that queue) and mac_openclaw_runner.py (the Mac-side task runner)
each used to define an identical VOLATILE_TASK_FIELDS set, an identical
request_fingerprint() implementation, and identical TASK_INBOX/RESULT_OUTBOX
path constants. This module is their single source of truth for those.

VOLATILE_TASK_FIELDS and request_fingerprint() are re-exported from
validate_content_os_task, which already carried the canonical implementation
(mac_openclaw_runner.py had switched to importing from there independently,
in a change that landed on main concurrently with this module's own,
duplicate hand-rolled copy). Re-exporting here -- instead of keeping a
second parallel implementation that merely produced byte-identical output --
means 32/33's existing `from queue_identity import ...` call sites keep
working unchanged while there is truly one source of truth.

source_identity() and idempotency_key() are deliberately NOT unified here:
32 and 33 read them from different shapes (an already-enqueued local queue
task JSON vs. an upper-layer cloud task YAML) with different fallback
chains, and mac_openclaw_runner.task_identity() is a distinct concept again
(the immutable identity every Mac result must echo back to cloud, not a
source/idempotency lookup). Only the set of keys those three functions read
is shared here, as SOURCE_IDENTITY_KEYS, so the three call sites stay
visibly in sync on *what* they key off of; each keeps its own independent
value-resolution and fallback logic.
"""

from __future__ import annotations

from pathlib import Path

from validate_content_os_task import VOLATILE_TASK_FIELDS, request_fingerprint

__all__ = [
    "VOLATILE_TASK_FIELDS",
    "request_fingerprint",
    "SOURCE_IDENTITY_KEYS",
    "TASK_INBOX",
    "RESULT_OUTBOX",
]

# Keys that 32_process_openclaw_queue.source_identity,
# 33_enqueue_openclaw_queue_job.source_identity and
# mac_openclaw_runner.task_identity all read from, kept here only so the
# three call sites can be cross-referenced. This is not a contract that
# their resolved values must match -- each function's value-resolution and
# fallback chain stays independent (see module docstring).
SOURCE_IDENTITY_KEYS = (
    "task_id",
    "task_type",
    "project_id",
    "idea_id",
    "project_revision",
    "change_request_id",
    "editor_backend",
    "tenant_id",
)

# 98_Agent任务队列 is the document/task layer; both the cloud->Mac bridge
# (33_enqueue_openclaw_queue_job.py) and the Mac-side runner
# (mac_openclaw_runner.py) read/write it at these vault-relative paths.
TASK_INBOX = Path("98_Agent任务队列/01_cloud_to_mac_ready")
RESULT_OUTBOX = Path("98_Agent任务队列/02_mac_to_cloud_results")
