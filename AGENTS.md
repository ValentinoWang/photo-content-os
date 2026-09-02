## Harness Engineering

This project uses Harness Engineering SSOT. Before non-trivial work, read:

- `develop/Harness/fullstack-ai-harness.md`
- `.harness/overlays/project-harness-adapter.yaml`

Rules:

- `develop/Harness/*`, `.agents/skills/*`, and project-declared `.codex/skills/*` may point to Harness Engineering SSOT.
- Before editing linked files, confirm the real path with `readlink`.
- When the real path is inside Harness Engineering, report it as a Harness SSOT change.
- Project-specific paths, commands, design-system mapping, and test matrices belong in `.harness/overlays/project-harness-adapter.yaml`.
- Reusable workflows belong in the linked Skill or Harness namespace.
- New blocking guards need a stable failure class, a guard card, red/green or negative proof, calibrated scope, and a repair path.
- For a user-visible Surface, field, action, navigation, role, or permission change, resolve project-owned Product Context and Role Context before Screen Contract or visual work; bind only a generated resolved Surface Contract, not a human Surface Definition.
- Non-human evidence belongs in `agents-results/YYYY-MM-DD/<task>/`. Human acceptance belongs independently in project-level `acceptance/human/<YYYY-Www>/{未-}<YYYY-MM-DD>-<task-id>/` with a hash-bound contract/SSOT binding; `未-` means no current valid human pass.
- At task start, read `acceptance/human-acceptance-log.json` and identify intersecting `PENDING`, `REJECTED`, or `INVALIDATED` entries. Do not parse the Markdown log as machine authority.
- After approved bindings and required machine evidence are green, write or refresh that task's `handoff.json` immediately. Continue machine-only development without waiting; execute queued human checklists together in a separate terminal acceptance phase.
- Keep non-blocking sampling entries in their own log partition. They never block release. A release with an unresolved blocking entry in scope cannot be reported `READY`.
- Reuse a `PASSED` human result until a bounded invalidation condition or newer handoff makes it `INVALIDATED`. Repair a rejected loop from its signed run, rerun machine evidence, then create a newer handoff.
- Creating or materially updating a declared project SSOT requires the `ssot-obsidian-snapshot` Skill before completion. Require `ssot-archive.json`, preserve its stable artifact date and identity across updates, include every declared `openproblem` file, verify hashes, and pass global `--audit-archive`; ordinary reports and evidence-only bundles stay out.
- When the project requires a phone reminder, schedule it only through the dedicated list in the unique iCloud Reminders account after snapshot hash verification succeeds. Its only purpose is to tell the user to open Obsidian; it may include one percent-encoded `obsidian://open` link to the verified snapshot's declared main document, but no source text, absolute local path, project-source link, review decision, or second reminder transport. It must not represent review, approval, synchronization, archival, or completion evidence.
- Final output includes both business project git status and Harness SSOT git status.
