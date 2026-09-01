# C1 Structured EDL Bridge

Implement SSOT node `C1` against plan version 4, DAG version 3, interface freeze version 4, and node contract version 1.

Goal: make the loopback Studio service expose a read-only structured editing-decision-list bridge sourced only from a workspace's `06_edit_decision_list.json`. The bridge must return source identity, structured content, and validation state. It must use the existing EDL contract validator; it must not derive fields from the Studio text document. A missing file, schema/validation failure, or source identity problem must result in a stable, non-guessing error/status while the existing editable Studio EDL text document remains usable.

Allowed reads:

- `99_System_OpenClaw/desktop/server.py`
- `99_System_OpenClaw/desktop/project_store.py`
- `99_System_OpenClaw/scripts/edl_contract.py`
- `99_System_OpenClaw/schemas/edit_decision_list.schema.json`
- relevant existing Studio tests

Allowed writes only:

- `99_System_OpenClaw/desktop/server.py`
- `99_System_OpenClaw/desktop/project_store.py`
- a new focused module below `99_System_OpenClaw/desktop/` only when necessary
- `99_System_OpenClaw/tests/test_ssot_edl_bridge.py`

Forbidden writes:

- `desktop/static/`, raw media, real projects, real Inbox, archive, Jianying drafts, scripts other than no scripts, existing SSOT machine files, and tests other than the one allowed test file.

Acceptance:

1. Valid fixture workspace returns a structured bridge object validated through the existing EDL contract.
2. The response identifies the authority file and a content digest or equally strong source identity.
3. Missing, malformed, and schema-invalid source data have stable non-guessing results.
4. Existing Studio editable EDL text behavior remains intact.
5. Run the frozen command supplied in `VALIDATION_COMMAND_FILE` and report it accurately.

No git commit, remote operation, new worker, broad refactor, production configuration, or frontend changes. Before exit write the required JSON record to `STRUCTURED_RETURN_PATH`, listing actual changed paths, commands, evidence level, and any unverified items.
