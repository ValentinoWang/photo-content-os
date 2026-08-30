#!/usr/bin/env python3
"""Cross-platform orchestration for tiered, evidence-backed project analysis."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from llm_common import DEFAULT_CREATIVE_MODEL, DEFAULT_REASONING_EFFORT
from media_common import analysis_dir, analysis_plan_path, manifest_path as _manifest_path, project_path
from runtime_paths import repository_root as _repository_root

SCRIPT_DIR = Path(__file__).resolve().parent
SYSTEM_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = _repository_root(Path(__file__))
PROMPT_VERSION = "content_summary_evidence_v1"


class AnalysisRunError(RuntimeError):
    pass


def run(command: list[str]) -> None:
    print("+ " + shlex.join(command))
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.rstrip())
    if completed.stderr.strip():
        print(completed.stderr.rstrip(), file=sys.stderr)
    if completed.returncode != 0:
        raise AnalysisRunError(f"command failed ({completed.returncode}): {shlex.join(command)}")


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def is_inbox(project: Path) -> bool:
    return "00_Inbox_Mac_Intake" in project.parts


def apply_requested_tier(plan_path: Path, requested_tier: str) -> None:
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    rank = {"metadata": 0, "preview": 1, "deep": 2}
    ceiling = rank[requested_tier]
    for plan in data.get("plans", []):
        if rank.get(str(plan.get("tier")), 0) > ceiling:
            plan["tier"] = requested_tier
            plan["image_budget"] = 0 if requested_tier == "metadata" else min(int(plan.get("image_budget") or 0), 3)
            plan["audio_seconds_budget"] = 0 if requested_tier == "metadata" else plan.get("audio_seconds_budget", 0)
            plan.setdefault("reason_codes", []).append("requested_tier_ceiling")
    data["requested_tier"] = requested_tier
    plan_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--tier", choices=("metadata", "preview", "deep"), default="preview")
    parser.add_argument("--audio", action="store_true", help="提取音频并运行转写步骤")
    parser.add_argument("--transcript-provider", choices=("pending", "sidecar", "openai_api"), default=os.getenv("OPENCLAW_TRANSCRIPTION_PROVIDER", "openai_api"))
    parser.add_argument("--transcript-model", default="gpt-4o-mini-transcribe")
    parser.add_argument("--model", default=DEFAULT_CREATIVE_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--include-derived", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-llm", action="store_true", help="只生成清单、层级计划和本地证据，不调用创作模型")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    outline = SYSTEM_ROOT / "docs" / "00_本地素材与剪映HyperFrames流转总纲.md"
    if outline.is_file():
        run([sys.executable, script("06_check_outline_contract.py"), str(REPOSITORY_ROOT)])
    if not is_inbox(project):
        run([sys.executable, script("13_ensure_project_structure.py"), str(project)])
    run([sys.executable, script("01_scan_media_manifest.py"), str(project)])
    run([sys.executable, script("07_validate_media_decisions.py"), str(project)])

    analysis_root = analysis_dir(project)
    plan_path = analysis_plan_path(project)
    manifest_path = _manifest_path(project)
    run(
        [
            sys.executable,
            script("analysis_tiering.py"),
            str(manifest_path),
            "--model",
            args.model,
            "--prompt-version",
            PROMPT_VERSION,
            "--output",
            str(plan_path),
        ]
    )
    apply_requested_tier(plan_path, args.tier)

    keyframe_args = [sys.executable, script("02_extract_keyframes.py"), str(project), "--analysis-plan", str(plan_path)]
    if args.include_derived:
        keyframe_args.append("--include-derived")
    if args.overwrite:
        keyframe_args.append("--overwrite")
    run(keyframe_args)

    if args.audio:
        audio_args = [sys.executable, script("03_extract_audio_helper.py"), str(project)]
        if args.include_derived:
            audio_args.append("--include-derived")
        run(audio_args)
        transcript_args = [
            sys.executable,
            script("03_transcribe_audio.py"),
            str(project),
            "--provider",
            args.transcript_provider,
            "--model",
            args.transcript_model,
        ]
        if args.overwrite:
            transcript_args.append("--overwrite")
        run(transcript_args)

    run([sys.executable, script("04_generate_ai_prompt.py"), str(project)])
    if not args.skip_llm and args.tier != "metadata":
        summary_args = [
            sys.executable,
            script("05_write_content_summary.py"),
            str(project),
            "--analysis-plan",
            str(plan_path),
            "--model",
            args.model,
            "--reasoning",
            args.reasoning,
        ]
        if args.include_derived:
            summary_args.append("--include-derived")
        if args.overwrite:
            summary_args.append("--overwrite")
        run(summary_args)
    else:
        print("跳过创作模型调用；本地清单、层级计划、关键帧和可选转写已完成。")

    print("分析流程完成。")
    print(f"manifest={manifest_path}")
    print(f"analysis_plan={plan_path}")
    print(f"keyframes={analysis_root / 'keyframes'}")
    print(f"transcripts={analysis_root / 'transcripts'}")
    print(f"summaries={analysis_root / 'summaries'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
