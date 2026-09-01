# B1 Media Manifest Contract

Implement SSOT node `B1` against plan version 4, DAG version 3, interface freeze version 4, and node contract version 1.

Goal: define a fail-closed media-manifest contract for still images. Each scanned image must report a content SHA-256, readable/health state, and bounded EXIF location facts. Missing EXIF data is an explicit unknown state, not a guessed coordinate. Unreadable or malformed images must stay in the manifest with a stable health result and must not crash the scan. Do not alter any raw media outside temporary test fixtures.

Allowed reads:

- `99_System_OpenClaw/scripts/01_scan_media_manifest.py`
- `99_System_OpenClaw/scripts/media_common.py`
- `99_System_OpenClaw/schemas/`
- existing media-manifest tests

Allowed writes only:

- `99_System_OpenClaw/scripts/01_scan_media_manifest.py`
- `99_System_OpenClaw/scripts/media_common.py` when a reusable helper is needed
- `99_System_OpenClaw/schemas/media_manifest.schema.json` if needed
- `99_System_OpenClaw/tests/test_media_manifest_contract.py`

Forbidden writes:

- any raw media, project directory, real Inbox, archive, Jianying draft, desktop service, HTML/UI, existing SSOT machine files, or tests outside the one allowed test file.

Acceptance:

1. Valid image fixtures demonstrate SHA-256 and an explicit image health state.
2. EXIF location absence is represented as an explicit unknown/absent value, never fabricated.
3. Corrupt image fixtures remain reportable with a stable non-healthy state.
4. The manifest schema/contract makes the fields and their semantics deterministic.
5. Run the frozen command supplied in `VALIDATION_COMMAND_FILE` and report it accurately.

No git commit, remote operation, new worker, broad refactor, or production configuration. Before exit write the required JSON record to `STRUCTURED_RETURN_PATH`, listing actual changed paths, commands, evidence level, and any unverified items.
