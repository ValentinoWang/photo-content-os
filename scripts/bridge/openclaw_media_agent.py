#!/usr/bin/env python3
"""Thin bridge to the canonical OpenClaw Media outbound agent.

This module deliberately does not reimplement pairing, leasing, acknowledgement,
execution, result reporting, archive receipts or credential storage.  Those
state machines remain owned by the installed ``openclaw-media`` package.  The
bridge only validates the frozen catalog contract and forwards safe commands.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import json
from dataclasses import asdict
from importlib import import_module
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

from bridge.openclaw_product_contract import (
    ProductContractError,
    assert_compatible,
    compatibility,
    pipeline_id,
    safe_workspace_ref,
)


def _base_command() -> list[str]:
    return [sys.executable, "-m", "openclaw_media.cli"]


def run_cli(args: Sequence[str], *, stdin_text: str | None = None) -> int:
    completed = subprocess.run(
        [*_base_command(), *args],
        input=stdin_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    contract = commands.add_parser("contract", help="show compatibility with the frozen upstream catalog")
    contract.add_argument("--cloud", action="store_true", help="also require the current OS to be pairable upstream")

    pair = commands.add_parser("pair", help="pair through the canonical OpenClaw Media CLI")
    pair.add_argument("--base-url", required=True)
    pair.add_argument("--pair-code", required=True)
    pair.add_argument("--device-label", required=True)
    pair.add_argument("--workspace", required=True)
    pair.add_argument("--agent-dir")
    pair.add_argument("--local-endpoint", action="store_true")

    status = commands.add_parser("status", help="show redacted canonical agent state")
    status.add_argument("--agent-dir")

    once = commands.add_parser("once", help="run one canonical outbound agent cycle")
    once.add_argument("--workspace")
    once.add_argument("--agent-dir")
    once.add_argument("--local-endpoint", action="store_true")
    once.add_argument("--state-dir", type=Path, help="Studio state directory holding the CreativeProject store")
    once.add_argument("--live", action="store_true", help="Allow explicitly bound paid transcription")

    watch = commands.add_parser("watch", help="run the canonical outbound agent in the foreground")
    watch.add_argument("--workspace")
    watch.add_argument("--agent-dir")
    watch.add_argument("--interval", type=float, default=30.0)
    watch.add_argument("--local-endpoint", action="store_true")
    watch.add_argument("--state-dir", type=Path)
    watch.add_argument("--live", action="store_true")

    local_run = commands.add_parser("run", help="run one installed pipeline locally through the canonical runtime")
    local_run.add_argument("pipeline", help="allowed alias or canonical pipeline id")
    local_run.add_argument("--workspace", required=True)
    local_run.add_argument("--workspace-ref")
    local_run.add_argument("--descriptor-json")

    return parser


def _run_installed_agent(opts: argparse.Namespace, confirmation_provider: Callable[[Mapping], Mapping | None] | None) -> int:
    """Installed ``watch``/``once``: existing CLI state and credentials plus the Studio port.

    Pairing, polling, leases and server calls stay in the installed package. Only
    its two injection points are filled: the Studio selection/staging port and a
    runtime factory that reads each job's binding from the project it was staged to.
    """
    cli = import_module("openclaw_media.cli")
    from media_ops.media_project_selection import DEFAULT_STATE_DIR, StudioConfirmationStore, StudioSelectionPort
    from bridge.openclaw_video_execution import installed_runtime_factory
    from studio.project_store import ProjectStore

    agent_store = cli._agent_store(opts.agent_dir)
    state = agent_store.load()
    if not state.remote_base_url or not state.device_id:
        print("photo-content-os: error: agent_not_paired", file=sys.stderr)
        return 2
    workspace = cli._workspace(opts.workspace, state.workspace)
    store = ProjectStore(opts.state_dir or DEFAULT_STATE_DIR)
    port = StudioSelectionPort(store, device_id=state.device_id, workspace=workspace, confirm=confirmation_provider)
    if confirmation_provider is None:
        port.confirm = StudioConfirmationStore(port.root).provider
    factory = installed_runtime_factory(store, device_id=state.device_id, provider=cli._provider(), live=opts.live)
    agent, remote = cli._agent_from_state(agent_store, workspace=str(workspace), local_endpoint=opts.local_endpoint,
                                          studio_port=port, runtime_factory=factory)
    try:
        if opts.command == "watch":
            agent.run_forever(interval=max(1.0, opts.interval))
        else:
            agent.run_once()
        print(json.dumps(asdict(agent.state()), ensure_ascii=False))
        return 1 if agent.state().status == "blocked" else 0
    finally:
        remote.close()


def main(argv: Sequence[str] | None = None, *, confirmation_provider: Callable[[Mapping], Mapping | None] | None = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    try:
        if opts.command == "contract":
            result = compatibility(require_cloud_platform=opts.cloud)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0 if result.compatible else 2

        require_cloud = opts.command == "pair"
        assert_compatible(require_cloud_platform=require_cloud)

        if opts.command in {"once", "watch"}:
            return _run_installed_agent(opts, confirmation_provider)

        if opts.command == "pair":
            args = [
                "pair",
                "--base-url",
                opts.base_url,
                "--pair-code",
                opts.pair_code,
                "--device-label",
                opts.device_label,
                "--workspace",
                str(Path(opts.workspace).expanduser().resolve()),
            ]
            if opts.agent_dir:
                args.extend(["--agent-dir", opts.agent_dir])
            if opts.local_endpoint:
                args.append("--local-endpoint")
            return run_cli(args)
        if opts.command == "status":
            args = ["agent", "status"]
            if opts.agent_dir:
                args.extend(["--agent-dir", opts.agent_dir])
            return run_cli(args)
        if opts.command == "run":
            resolved = pipeline_id(opts.pipeline)
            if opts.descriptor_json:
                descriptor = json.loads(opts.descriptor_json)
                if not isinstance(descriptor, dict):
                    raise ProductContractError("descriptor_invalid")
            elif opts.workspace_ref:
                descriptor = {"workspace_ref": safe_workspace_ref(opts.workspace_ref)}
            else:
                parser.error("run requires --descriptor-json or --workspace-ref")
            return run_cli(
                [
                    "run",
                    resolved,
                    "--workspace",
                    str(Path(opts.workspace).expanduser().resolve()),
                    "--descriptor-json",
                    json.dumps(descriptor, ensure_ascii=False, separators=(",", ":")),
                ]
            )
    except (ProductContractError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "descriptor_invalid")
        print(f"photo-content-os: error: {code}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
