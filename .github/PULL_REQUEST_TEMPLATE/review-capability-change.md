# Review Capability Change

## Change type

- [ ] New review capability
- [ ] Existing capability extension
- [ ] Remote orchestration change
- [ ] Documentation-only clarification

## Single source of truth checklist

- [ ] `99_System_OpenClaw/review_capabilities.registry.json` is updated first.
- [ ] The capability has exactly one `canonical_owner`.
- [ ] Mac-owned media analysis remains in `19_review_output_video.py`.
- [ ] Remote-server changes only create tasks, advance state, or consume Mac results.
- [ ] No second implementation of video probing, rhythm scoring, VLM review, or publish decision was introduced.

## Required local checks

```bash
python3 99_System_OpenClaw/scripts/36_validate_review_capability_registry.py
python3 -m unittest 99_System_OpenClaw/tests/test_review_capability_registry.py
python3 -m unittest 99_System_OpenClaw/tests/test_mac_openclaw_runner.py
```
