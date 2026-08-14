# AGENTS.md

## Scope

Codex may edit:

- `99_System_OpenClaw/scripts/`
- `99_System_OpenClaw/tests/`
- `99_System_OpenClaw/schemas/`
- automation documentation
- Content OS protocol documents under `/Users/vsiyo/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体/00_入口与总览/`
- Content OS automation protocol documents under `/Users/vsiyo/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体/06_技术栈与自动化/`

Codex must not edit:

- raw media files
- Final output videos
- real Jianying drafts unless the user explicitly asks to repair that draft
- Obsidian creative content unless explicitly asked

## Required checks

Run these from `/Users/vsiyo/Desktop/照片筛选` before handing off an automation or protocol change:

```bash
bash 99_System_OpenClaw/scripts/check_runtime_contract.sh
python3 99_System_OpenClaw/scripts/30_check_obsidian_doc_sync.py
python3 99_System_OpenClaw/scripts/06_check_outline_contract.py .
99_System_OpenClaw/.venv-content-os/bin/python -m unittest discover -s 99_System_OpenClaw/tests
99_System_OpenClaw/.venv-content-os/bin/python 99_System_OpenClaw/scripts/validate_content_os_task.py --help
python3 99_System_OpenClaw/scripts/25_validate_jianying_draft.py --help
```

`check_runtime_contract.sh` also verifies the fixed OTIO/Kdenlive runtime. Do
not replace that environment with the system Python ad hoc.

## Document synchronization

The local execution rules and Obsidian protocol pages are kept aligned by:

```text
/Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/doc_sync_contract.json
```

After changing a covered local execution document, script README, or matching
Obsidian protocol page, run `30_check_obsidian_doc_sync.py`. Update the paired
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
     `90_Draft_Project/edit_handoff/{project_revision}/`.
   - It contains the manifest, ordered clips list, editable subtitles and a
     human-readable handoff note. A person then chooses their editing tool and
     performs the fine edit.
2. **自动生成可编辑时间线（`otio_kdenlive`，可选）**
   - Mac uses only
     `99_System_OpenClaw/.venv-content-os/bin/python` to generate and validate
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

- Call `29_generate_ai_edit_log.py` only through the Mac Runner action
  `generate_ai_edit_log`.
- Keep the distinction between `已确认人工修改`, `AI 建议修改`, and `AI 推断修改`.
- Do not claim BGM, effects, timing, cuts or grading as facts without human
  notes, verified editor evidence or output-review evidence.
- Do not overwrite a human-edited log unless the explicit replacement flag is
  provided.
