## harness Engineering

This project uses harness Engineering SSOT. Before non-trivial work, read:

- `develop/harness/fullstack-ai-harness.md`
- `.harness/overlays/project-harness-adapter.yaml`

Rules:

- `develop/harness/*`, `.agents/skills/*`, and project-declared `.codex/skills/*` may point to harness Engineering SSOT.
- Before editing linked files, confirm the real path with `readlink`.
- When the real path is inside harness Engineering, report it as a harness SSOT change.
- Project-specific paths, commands, design-system mapping, and test matrices belong in `.harness/overlays/project-harness-adapter.yaml`.
- Reusable workflows belong in the linked Skill or harness namespace.
- New blocking guards need a stable failure class, a guard card, red/green or negative proof, calibrated scope, and a repair path.
- For a user-visible Surface, field, action, navigation, role, or permission change, resolve project-owned Product Context and Role Context before Screen Contract or visual work; bind only a generated resolved Surface Contract, not a human Surface Definition.
- Non-human evidence belongs in `evidence/YYYY-MM-DD/<task>/`. Human acceptance belongs independently in project-level `acceptance/human/<YYYY-Www>/{未-}<YYYY-MM-DD>-<task-id>/` with a hash-bound contract/SSOT binding; `未-` means no current valid human pass.
- At task start, read `acceptance/human-acceptance-log.json` and identify intersecting `PENDING`, `REJECTED`, or `INVALIDATED` entries. Do not parse the Markdown log as machine authority.
- After approved bindings and required machine evidence are green, write or refresh that task's `handoff.json` immediately. Continue machine-only development without waiting; execute queued human checklists together in a separate terminal acceptance phase.
- Keep non-blocking sampling entries in their own log partition. They never block release. A release with an unresolved blocking entry in scope cannot be reported `READY`.
- Reuse a `PASSED` human result until a bounded invalidation condition or newer handoff makes it `INVALIDATED`. Repair a rejected loop from its signed run, rerun machine evidence, then create a newer handoff.
- Creating or materially updating a declared project SSOT requires the `ssot-obsidian-snapshot` Skill before completion. Require `ssot-archive.json`, preserve its stable artifact date and identity across updates, include every declared `openproblem` file, verify hashes, and pass global `--audit-archive`; ordinary reports and evidence-only bundles stay out.
- When the project requires a phone reminder, schedule it only through the dedicated list in the unique iCloud Reminders account after snapshot hash verification succeeds. Its only purpose is to tell the user to open Obsidian; it may include one percent-encoded `obsidian://open` link to the verified snapshot's declared main document, but no source text, absolute local path, project-source link, review decision, or second reminder transport. It must not represent review, approval, synchronization, archival, or completion evidence.
- Final output includes both business project git status and harness SSOT git status.

# AGENTS.md

## Scope

Codex may edit:

- `scripts/`
- `tests/`
- `schemas/`
- automation documentation
- Content OS protocol documents under `$OBSIDIAN_ROOT/00_入口与总览/`
- Content OS automation protocol documents under `$OBSIDIAN_ROOT/06_技术栈与自动化/`

Codex must not edit:

- raw media files
- Final output videos
- real Jianying drafts unless the user explicitly asks to repair that draft
- Obsidian creative content unless explicitly asked

## Required checks

Software root and local media root are independent. Read material paths only
through `runtime_paths.local_media_root()` (`LOCAL_MEDIA_ROOT`, default
`~/Desktop/照片筛选`). Never derive material paths from the software root.
Tests use temporary media directories.

Run from the software root:

```bash
bash scripts/check_runtime_contract.sh
.venv/bin/python scripts/check_obsidian_doc_sync.py
.venv/bin/python scripts/check_outline_contract.py .
.venv/bin/python -m pytest -q tests
.venv/bin/python scripts/validate_content_os_task.py --help
.venv/bin/python scripts/validate_jianying_draft.py --help
```

Set `OBSIDIAN_ROOT` explicitly for document synchronization. Use the fixed
`.venv` for OTIO/Kdenlive execution.

## Document synchronization

The local execution rules and Obsidian protocol pages are kept aligned by:

```text
$SOFTWARE_ROOT/doc-sync-contract.json
```

After changing a covered local execution document, script README, or matching
Obsidian protocol page, run `check_obsidian_doc_sync.py`. Update the paired
document; do not weaken a marker merely to make the check pass.

## Content OS project and task rules

- `08_内容项目/{project_id}/00_项目总览.md` is the only source for a project's
  stage, current version, selected editing method, block state and next step.
- A Mac task and its result must carry the same project version
  (`project_revision`) and editing method (`editor_backend`). Mac does not
  advance the project stage.
- A confirmed local change must also carry `change_request_id`. The Runner
  reads the canonical change request, checks that it belongs to the project,
  is assigned to Mac, is confirmed for execution and targets the current
  version. A noted idea never creates an execution task.
- Unknown actions, a stale version, a mismatched editing method, a missing
  confirmation or an unavailable runtime write a blocked result. They never
  trigger a substitute script, editor or model.
- Cloud-created task YAML is read-only to Mac. Mac writes only its own local
  evidence and the Mac-to-cloud result.
- Obsidian paths in tasks are vault-relative. Local media and local editing
  outputs are absolute Mac paths only where the result needs to identify them.

## Formal editing route

The current production route has two explicit choices. The project overview
records one choice per version; it is never selected automatically.

1. **标准剪辑交接（`handoff_pack`，默认）**
   - Mac generates an immutable package at
     `draft-project/edit-handoff/{project_revision}/`.
   - It contains the manifest, ordered clips list, editable subtitles and a
     human-readable handoff note. A person then chooses their editing tool and
     performs the fine edit.
2. **自动生成可编辑时间线（`otio_kdenlive`，可选）**
   - Mac uses only
     `.venv/bin/python` to generate and validate
     the OTIO/Kdenlive timeline for the same revision.
   - If that runtime or Kdenlive evidence is unavailable, the task is blocked;
     it does not fall back to the standard package or another editor.

The detailed protocol is
`00_入口与总览/剪辑交接与可编辑时间线.md`. A person may still use Jianying for
manual fine editing, but the system does not create or patch a production
Jianying draft. Real Jianying drafts remain local human workspaces and are not
synced, moved or rewritten by automation.

## Historical Jianying material

`Jianying_Roughcut_Draft_Pipeline.md`, native-import packages and old
`06b`/`06d` outputs are retained as historical evidence for older projects.
They are not a supported route for a new Content OS v0.2 task. Do not delete,
rewrite or treat a real historical draft as current project evidence.

## Media Bot change entry

The only formal entry for a collaborator to change a Content OS project is the
Media Bot conversation. The collaborator states the requested change in plain
Chinese; the Bot records:

- what to change;
- what it should become;
- why;
- whether it is urgent; and
- optional reference image or explanation.

The Bot restates the request and offers three human choices: **先记下**,
**只改一小处**, or **现在修改**. “先记下” records an idea only. The latter two
first show an impact explanation, then require an explicit human confirmation
before cloud or Mac work is created. Operator-facing text must be Chinese and
must not show internal paths, task IDs, error stacks or backend names.

## AI edit log rules

`07_edit_log.md` is an AI-assisted edit log, not a raw human memory dump. It
uses `04_script.md`, `05_storyboard.md`, `06_edit_decision_list.json`, the
selected editing-method result, optional human notes and output-review evidence.

- Call `generate_ai_edit_log.py` only through the Mac Runner action
  `generate_ai_edit_log`.
- Keep the distinction between `已确认人工修改`, `AI 建议修改`, and `AI 推断修改`.
- Do not claim BGM, effects, timing, cuts or grading as facts without human
  notes, verified editor evidence or output-review evidence.
- Do not overwrite a human-edited log unless the explicit replacement flag is
  provided.
