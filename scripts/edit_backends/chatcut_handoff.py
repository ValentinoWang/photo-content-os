#!/usr/bin/env python3
"""Local immutable ChatCut package and explicitly schema-bound MCP pre-cut."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

SYSTEM = Path(__file__).resolve().parents[2]
for directory in (SYSTEM, SYSTEM / "scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from studio.chatcut_mcp import LocalMcpSession
from media_common import file_sha256
from edit_backends.kdenlive_render import plan_ranges, probe_media


def schema_digest(schema: dict) -> str:
    return hashlib.sha256(json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prepare_package(*, source: Path, subtitles: Path, animations: list[Path], suggestions: Path,
                    output_dir: Path, project_id: str, project_revision: int) -> dict:
    if not isinstance(project_id, str) or not project_id.strip() or type(project_revision) is not int or project_revision < 1:
        raise ValueError("handoff_project_identity_invalid")
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists():
        raise ValueError("handoff_directory_already_exists")
    sources = [("original", source), ("subtitles", subtitles), ("suggestions", suggestions)]
    sources.extend((f"animation-{i}", p) for i, p in enumerate(animations))
    sources = [(role, path.expanduser().resolve()) for role, path in sources]
    if not all(path.is_file() for _, path in sources):
        raise ValueError("handoff_input_missing")
    # Validate input JSON before creating a package that could appear usable.
    raw = json.loads(suggestions.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("suggestions"), list) or not all(isinstance(v, dict) for v in raw["suggestions"]):
        raise ValueError("suggestions_list_required")
    output_dir.mkdir(parents=True)
    # The editor receives an execution-only subset as well as the review package.
    # Sentence/chunk candidates may be displayed, but never become pre-cut calls.
    executable = [item for item in raw["suggestions"] if item.get("type") in {"silence", "repetition"}
                  and item.get("auto_cut_allowed") is True and raw.get("auto_cut_allowed") is not False]
    for item in executable:
        if item["type"] == "repetition" and (raw.get("precision") != "word" or item.get("precision", "word") != "word"):
            raise ValueError("repetition_requires_word_timing")
    precut = {**raw, "suggestions": executable}
    precut_path = output_dir / "precut_suggestions.json"
    precut_path.write_text(json.dumps(precut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entries = []
    for role, original in sources:
        digest = file_sha256(original)
        name = "edit_suggestions.json" if role == "suggestions" else f"{role}{original.suffix}"
        copied = output_dir / name
        shutil.copyfile(original, copied)
        if file_sha256(copied) != digest or file_sha256(original) != digest:
            raise ValueError("handoff_input_changed")
        entries.append({"role": role, "path": name, "sha256": digest})
    entries.append({"role": "executable_suggestions", "path": precut_path.name, "sha256": file_sha256(precut_path)})
    manifest = {"contract": "chatcut_local_handoff.v1", "project_id": project_id,
                "project_revision": project_revision, "status": "awaiting_chatcut_login",
                "message": "等 ChatCut 登录", "files": entries}
    (output_dir / "handoff.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def resolve_arguments(template, inputs: dict, results: dict):
    if isinstance(template, dict):
        if set(template) == {"$input"}:
            return inputs[template["$input"]]
        if set(template) == {"$result"}:
            value = results
            for component in template["$result"].split("."):
                value = value[component]
            return value
        return {key: resolve_arguments(value, inputs, results) for key, value in template.items()}
    if isinstance(template, list):
        return [resolve_arguments(item, inputs, results) for item in template]
    return template


def validate_arguments(schema: dict, arguments: dict):
    # Use the full JSON Schema validator; do not invent a subset of MCP schemas.
    from jsonschema.validators import validator_for
    def reject_external_refs(value):
        if isinstance(value, dict):
            for reference in ("$ref", "$dynamicRef", "$recursiveRef"):
                if reference in value and (not isinstance(value[reference], str) or not value[reference].startswith("#")):
                    raise ValueError("external_schema_reference_rejected")
            for item in value.values():
                reject_external_refs(item)
        elif isinstance(value, list):
            for item in value:
                reject_external_refs(item)
    reject_external_refs(schema)
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(arguments)


def execute_handoff(package: Path, *, adapter: dict | None = None, live: bool = False,
                    session_factory=LocalMcpSession) -> dict:
    package = package.resolve()
    manifest_path = package / "handoff.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = {"status": "awaiting_chatcut_login", "message": "等 ChatCut 登录", "connection_verified": False}
    for item in manifest["files"]:
        path = (package / item["path"]).resolve()
        if path.parent != package or file_sha256(path) != item["sha256"]:
            raise ValueError("handoff_integrity_failed")
    if live:
        try:
            with session_factory() as session:
                tools = session.list_tools()
                result["connection_verified"] = True
                (package / "tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                by_name = {tool["name"]: tool for tool in tools}
                if not adapter:
                    result.update(status="schema_adapter_required", reason="no_verified_tool_bindings")
                else:
                    video_entry = next(item for item in manifest["files"] if item["role"] == "original")
                    media = probe_media(package / video_entry["path"])
                    video = next(item for item in media["streams"] if item.get("codec_type") == "video")
                    plan_ranges(json.loads((package / "precut_suggestions.json").read_text()),
                                float(video.get("duration") or media["format"]["duration"]))
                    # Both selected tools must be present with the exact reviewed schema.
                    for phase in ("import", "precut"):
                        binding = adapter[phase]
                        if binding["name"] not in by_name or schema_digest(by_name[binding["name"]]["inputSchema"]) != binding["schema_sha256"]:
                            raise ValueError("tool_schema_mismatch")
                    inputs = {"manifest_path": str(manifest_path), "package_dir": str(package),
                              "suggestions_path": str(package / "precut_suggestions.json"),
                              "review_suggestions_path": str(package / "edit_suggestions.json"),
                              "files": [dict(item, path=str(package / item["path"])) for item in manifest["files"]]}
                    results = {}
                    for phase in ("import", "precut"):
                        binding = adapter[phase]
                        arguments = resolve_arguments(binding["arguments"], inputs, results)
                        validate_arguments(by_name[binding["name"]]["inputSchema"], arguments)
                        results[phase] = session.call_tool(binding["name"], arguments)
                    # Editor outputs remain local candidates; no cloud or adoption here.
                    (package / "mcp-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    result.update(status="candidate", message=None)
        except Exception as exc:
            result.update(status="failed" if result["connection_verified"] else "awaiting_chatcut_login",
                          reason=str(exc) if str(exc) in {"tool_schema_mismatch", "mcp_tool_failed"} else type(exc).__name__)
    for item in manifest["files"]:
        if file_sha256(package / item["path"]) != item["sha256"]:
            result.update(status="failed", reason="handoff_input_changed")
    (package / "handoff-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--subtitles", type=Path)
    parser.add_argument("--suggestions", type=Path)
    parser.add_argument("--animation", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--resume-package", type=Path, help="Execute an existing immutable handoff package")
    parser.add_argument("--project-id")
    parser.add_argument("--project-revision", type=int)
    parser.add_argument("--live", action="store_true", help="Connect only to registered local ChatCut MCP")
    parser.add_argument("--adapter", type=Path, help="Bindings with probed tool names, schema hashes and argument templates")
    args = parser.parse_args()
    try:
        if args.resume_package:
            package = args.resume_package
        else:
            if any(value is None for value in (args.source, args.subtitles, args.suggestions, args.output_dir, args.project_id, args.project_revision)):
                parser.error("provide all package inputs or --resume-package")
            package = args.output_dir
            prepare_package(source=args.source, subtitles=args.subtitles, animations=args.animation,
                        suggestions=args.suggestions, output_dir=args.output_dir,
                        project_id=args.project_id, project_revision=args.project_revision)
        result = execute_handoff(package, live=args.live,
                                 adapter=json.loads(args.adapter.read_text()) if args.adapter else None)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
