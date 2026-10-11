"""Photo-owned execution adapter for the canonical Media PipelineRuntime.

Bindings are local operator configuration. Cloud descriptors cannot select a
script, Python function, command, filesystem root, or CreativeProject by title.
No scheduler, result queue, or alternate receipt store lives in this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import shutil
from pathlib import Path
from typing import Any
from importlib import import_module

from openclaw_product_contract import ProductContractError, safe_workspace_ref, validate_video_handoff


SCRIPTS = Path(__file__).resolve().parent
PHOTO_PYTHON = SCRIPTS.parent / ".venv/bin/python"
ENTRYPOINTS = {
    "transcribe": "transcribe_audio.py",
    "suggest": "spoken_edit.py",
    "chatcut": "edit_backends/chatcut_handoff.py",
    "kdenlive": "edit_backends/kdenlive_render.py",
    "review": "review_output_video.py",
    "compose": "video_render/compose.py",
    "multi_shot": "video_render/multi_shot.py",
    "teaching_clips": "video_render/teaching_clips.py",
}
CHECKS = {"decode", "audio_video_tracks", "av_duration", "frame_count", "source_unchanged", "subtitle_monotonic"}

# This fixed driver receives local arguments on stdin. It is never a cloud
# command surface; the parent selects the allowlisted file before spawning it.
_LOCAL_DRIVER = """import importlib.util, inspect, json, sys
from pathlib import Path
request = json.load(sys.stdin)
sys.path.insert(0, str(Path(request['scripts_root']).parent))
sys.path.insert(0, request['scripts_root'])
sys.path.insert(0, str(Path(request['script']).parent))
spec = importlib.util.spec_from_file_location(request['module'], request['script'])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
callback = getattr(module, request['function'])
kwargs = {key: Path(value['__photo_local_path__']) if isinstance(value, dict) and set(value) == {'__photo_local_path__'} else value for key, value in request['kwargs'].items()}
inspect.signature(callback).bind(**kwargs)
callback(**kwargs)
"""


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_path(root: Path, ref: str) -> Path:
    value = (root / safe_workspace_ref(ref)).resolve()
    if not value.is_relative_to(root.resolve()):
        raise ProductContractError("photo_binding_rejected")
    return value


class PhotoNodeRegistry:
    """Execute fixed Photo scripts inside a caller's explicit project binding.

    Function names and kwargs come from trusted local configuration, allowing
    PA/PB/PC to publish their real Python signatures without inventing CLI flags.
    Missing scripts/functions block; there is no substitute backend.
    """

    def __init__(self, catalog: Any, binding_path: Path, *, live: bool = False) -> None:
        self.catalog = catalog
        self.binding_path = binding_path.resolve()
        self.live = live

    def _binding(self) -> dict[str, Any]:
        data = json.loads(self.binding_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"identity", "handoff_digest", "creative_store", "project_root", "steps", "candidate_ref", "source_refs"}:
            raise ProductContractError("photo_binding_rejected")
        store = json.loads(Path(data["creative_store"]).read_text(encoding="utf-8"))
        if store.get("schema_version") != "creative_project_store_v1":
            raise ProductContractError("photo_binding_rejected")
        projects = [p for p in store["projects"] if p.get("id") == data["identity"]["project_id"]]
        if len(projects) != 1 or type(projects[0].get("revision")) is not int or projects[0]["revision"] != data["identity"]["project_revision"]:
            raise ProductContractError("photo_binding_rejected")
        if data["identity"]["catalog_digest"] != self.catalog.manifest["catalog_digest"]:
            raise ProductContractError("catalog_digest_mismatch")
        root = Path(data["project_root"]).resolve()
        if not root.is_dir() or not isinstance(data["steps"], list) or not data["steps"] or not isinstance(data["source_refs"], list):
            raise ProductContractError("photo_binding_rejected")
        return data

    @staticmethod
    def _argument(value: Any, *, root: Path, handoff: dict[str, Any], output_root: Path, tts_path: Path | None = None) -> Any:
        if value == "$handoff":
            return copy.deepcopy(handoff)
        if value == "$project_root":
            return root
        if value == "$output_root":
            return output_root
        if value == "$tts_path":
            if tts_path is None:
                raise ProductContractError("photo_binding_rejected")
            return tts_path
        if isinstance(value, dict) and set(value) == {"local_ref"}:
            return local_path(root, value["local_ref"])
        if isinstance(value, (dict, list)):
            raise ProductContractError("photo_binding_rejected")
        return value

    def _invoke(self, step: dict[str, Any], *, root: Path, handoff: dict[str, Any], output_root: Path, tts_path: Path | None = None) -> None:
        if not isinstance(step, dict) or set(step) != {"action", "function", "kwargs"} or not isinstance(step["action"], str) or step["action"] not in ENTRYPOINTS:
            raise ProductContractError("photo_binding_rejected")
        if step["action"] == "transcribe" and not self.live:
            raise ProductContractError("photo_entrypoint_unavailable")
        script = (SCRIPTS / ENTRYPOINTS[step["action"]]).resolve()
        if not script.is_relative_to(SCRIPTS.resolve()) or not script.is_file():
            raise ProductContractError("photo_entrypoint_unavailable")
        function = step["function"]
        if not isinstance(function, str) or not function.isidentifier() or function.startswith("_") or not isinstance(step["kwargs"], dict):
            raise ProductContractError("photo_binding_rejected")
        if not PHOTO_PYTHON.is_file():
            raise ProductContractError("photo_entrypoint_unavailable")
        kwargs = {k: self._argument(v, root=root, handoff=handoff, output_root=output_root, tts_path=tts_path) for k, v in step["kwargs"].items()}
        encoded = {k: {"__photo_local_path__": str(v)} if isinstance(v, Path) else v for k, v in kwargs.items()}
        module_name = ".".join(script.relative_to(SCRIPTS.resolve()).with_suffix("").parts)
        request = {"scripts_root": str(SCRIPTS.resolve()), "script": str(script), "module": module_name, "function": function, "kwargs": encoded}
        completed = subprocess.run([str(PHOTO_PYTHON), "-c", _LOCAL_DRIVER], input=json.dumps(request, ensure_ascii=False), cwd=root, capture_output=True, text=True, timeout=1800, check=False)
        # Diagnostics can contain local paths and remain exclusively local.
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / (step["action"] + ".log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise ProductContractError("photo_execution_failed")

    def _candidate(self, binding: dict[str, Any], handoff: dict[str, Any], root: Path, workspace: Path, source_digests: set[str]) -> dict[str, Any]:
        data = json.loads(local_path(root, binding["candidate_ref"]).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"description", "checks", "subtitles", "preview_ref"}:
            raise ProductContractError("photo_execution_failed")
        description = data["description"]
        if not isinstance(description, dict) or set(description) != {"duration_seconds", "frames", "cut_seconds"} or type(description["frames"]) is not int or description["frames"] < 1:
            raise ProductContractError("photo_execution_failed")
        for key in ("duration_seconds", "cut_seconds"):
            value = description[key]
            if type(value) not in {int, float} or not math.isfinite(value) or value < 0 or (key == "duration_seconds" and value == 0):
                raise ProductContractError("photo_execution_failed")
        checks = data["checks"]
        if not isinstance(checks, list) or len(checks) != len(CHECKS) or any(not isinstance(c, dict) or set(c) != {"name", "status"} or not isinstance(c["name"], str) or c["name"] not in CHECKS or not isinstance(c["status"], str) or c["status"] not in {"pass", "fail", "unknown"} for c in checks) or {c["name"] for c in checks} != CHECKS:
            raise ProductContractError("photo_execution_failed")
        if not isinstance(data["subtitles"], str) or len(data["subtitles"].encode()) > 1_048_576 or _local_text(data["subtitles"]):
            raise ProductContractError("photo_execution_failed")
        preview = local_path(root, data["preview_ref"])
        if preview.suffix.lower() != ".mp4" or not preview.is_file() or not 0 < preview.stat().st_size <= 20_000_000:
            raise ProductContractError("photo_execution_failed")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(preview)], capture_output=True, text=True, check=True, timeout=30)
        streams = json.loads(probe.stdout)["streams"]
        videos = [s for s in streams if s.get("codec_type") == "video"]
        if len(videos) != 1 or not any(s.get("codec_type") == "audio" for s in streams):
            raise ProductContractError("photo_execution_failed")
        width, height = videos[0]["width"], videos[0]["height"]
        if type(width) is not int or type(height) is not int or min(width, height) <= 0 or min(width, height) > 480 or max(width, height) > 854:
            raise ProductContractError("photo_execution_failed")
        digest = hashlib.sha256(preview.read_bytes()).hexdigest()
        if digest in source_digests:
            raise ProductContractError("photo_execution_failed")
        preview_ref = f"previews/{digest}.mp4"
        destination = local_path(workspace, preview_ref)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if preview != destination:
            shutil.copyfile(preview, destination)
        return {"identity": handoff["identity"], "handoff_digest": handoff["handoff_digest"], "status": "candidate" if all(c["status"] == "pass" for c in checks) else "check_failed", "description": description, "checks": checks, "subtitles": data["subtitles"], "preview": {"artifact_ref": preview_ref, "sha256": "sha256:" + digest, "size_bytes": destination.stat().st_size, "width": width, "height": height}, "failure_code": None}

    def execute(self, node: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        NodeExecutionError = import_module("openclaw_media.node_registry").NodeExecutionError

        if node.get("type") != "edit.handoff" or node.get("version") != "1.0.0" or node.get("outputs") != ["handoff_manifest"]:
            raise NodeExecutionError("unknown_node")
        try:
            binding = self._binding()
            workspace = Path(context["workspace_root"]).resolve()
            inputs = context["inputs"]
            descriptor = local_path(workspace, inputs.get("workspace_ref", inputs.get("run_ref")))
            handoff = validate_video_handoff(json.loads(descriptor.read_text(encoding="utf-8")), binding["identity"], expected_handoff_digest=binding["handoff_digest"])
            tts_path = local_path(workspace, handoff["tts_ref"]) if handoff["tts_ref"] is not None else None
            if tts_path is not None and not tts_path.is_file():
                raise ProductContractError("photo_binding_rejected")
            root = Path(binding["project_root"]).resolve()
            sources = [local_path(root, ref) for ref in binding["source_refs"]]
            before = {p: file_sha256(p) for p in sources}
            output_root = local_path(workspace, context["run_ref"])
            output_root.mkdir(parents=True, exist_ok=True)
            try:
                for step in binding["steps"]:
                    self._invoke(step, root=root, handoff=handoff, output_root=output_root, tts_path=tts_path)
                # Re-read the authority after execution, before projecting a result.
                current = self._binding()
                validate_video_handoff(handoff, current["identity"], expected_handoff_digest=current["handoff_digest"])
                if before != {p: file_sha256(p) for p in sources}:
                    raise ProductContractError("photo_execution_failed")
                candidate = self._candidate(binding, handoff, root, workspace, set(before.values()))
            except Exception as exc:
                code = getattr(exc, "code", "photo_execution_failed")
                if code not in {"photo_entrypoint_unavailable", "photo_binding_rejected"}:
                    code = "photo_execution_failed"
                candidate = {"identity": handoff["identity"], "handoff_digest": handoff["handoff_digest"], "status": "failed", "description": None, "checks": [], "subtitles": "", "preview": None, "failure_code": code}
            # This is a local artifact in the existing durable runtime. A failure
            # receipt is not a succeeded render and never enters the media library.
            artifact = output_root / "handoff_manifest.json"
            artifact.write_text(json.dumps(candidate, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            if candidate["status"] == "failed":
                raise NodeExecutionError(candidate["failure_code"])
            return {"handoff_manifest": {"local_path": str(artifact), "artifact_ref": str(artifact.relative_to(workspace)), "mime_type": "application/json", "size_bytes": artifact.stat().st_size, "cloud_bytes": 0}}
        except ProductContractError as exc:
            raise NodeExecutionError(exc.code) from exc
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NodeExecutionError("photo_binding_rejected") from exc


def _local_text(value: str) -> bool:
    import re
    return bool(re.search(r"(?:^|[\s\"'=(:：])(?:/(?:[\w.-]+/)+[^\s\"']*|[A-Za-z]:[\\/][^\s\"']*)", value) or "\x00" in value)


def runtime_factory(binding_path: Path, *, live: bool = False, for_agent: bool = False):
    """Use the installed runtime's database, DAG and receipts unchanged."""
    PipelineRuntime = import_module("openclaw_media.pipeline_runtime").PipelineRuntime

    class PhotoRuntime(PipelineRuntime):
        def _inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
            # Agent hands the input_refs[0] descriptor in workspace_ref; the
            # existing handoff pipeline requires run_ref. Keep both identities.
            result = dict(inputs)
            if "workspace_ref" in result and "run_ref" not in result:
                result["run_ref"] = result["workspace_ref"]
            binding = self.node_registry._binding()
            result["photo_handoff_digest"] = binding["handoff_digest"]
            descriptor = local_path(self.root, result.get("workspace_ref", result.get("run_ref")))
            handoff = validate_video_handoff(json.loads(descriptor.read_text(encoding="utf-8")), binding["identity"], expected_handoff_digest=binding["handoff_digest"])
            result["photo_tts_digest"] = file_sha256(local_path(self.root, handoff["tts_ref"])) if handoff["tts_ref"] is not None else None
            project_root = Path(binding["project_root"]).resolve()
            result["photo_source_digests"] = [file_sha256(local_path(project_root, ref)) for ref in binding["source_refs"]]
            return result

        def create_run(self, pipeline_id, version, digest, *, run_ref, inputs):
            try:
                normalized = self._inputs(inputs)
                if for_agent:
                    job_id = self.node_registry._binding()["identity"]["job_id"]
                    expected_ref = "runs/" + hashlib.sha256(job_id.encode()).hexdigest()[:32]
                    if run_ref != expected_ref:
                        raise ProductContractError("video_identity_rejected")
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                Outcome = import_module("openclaw_media.pipeline_runtime").RuntimeOutcome
                return Outcome(status="pending_manual", code=getattr(exc, "code", "photo_binding_rejected"))
            return super().create_run(pipeline_id, version, digest, run_ref=run_ref, inputs=normalized)

        def execute(self, run_ref, *, inputs):
            # Replay still checks today's binding and descriptor. The canonical
            # runtime stores refs, which alone do not freeze referenced content.
            try:
                normalized = self._inputs(inputs)
                binding = self.node_registry._binding()
                descriptor = local_path(self.root, normalized.get("workspace_ref", normalized.get("run_ref")))
                validate_video_handoff(json.loads(descriptor.read_text(encoding="utf-8")), binding["identity"], expected_handoff_digest=binding["handoff_digest"])
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                Outcome = import_module("openclaw_media.pipeline_runtime").RuntimeOutcome
                return Outcome(status="pending_manual", code=getattr(exc, "code", "photo_binding_rejected"))
            return super().execute(run_ref, inputs=normalized)

    def create(workspace, catalog):
        return PhotoRuntime(workspace, catalog=catalog, node_registry=PhotoNodeRegistry(catalog, binding_path, live=live))
    return create
