"""Photo-owned execution adapter for the canonical Media PipelineRuntime.

Bindings are local operator configuration. Cloud descriptors cannot select a
script, Python function, command, filesystem root, or CreativeProject by title.
No scheduler, result queue, or alternate receipt store lives in this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from importlib import import_module

from runtime_paths import local_media_root
from openclaw_product_contract import ProductContractError, safe_workspace_ref, validate_video_handoff


SCRIPTS = Path(__file__).resolve().parent
PHOTO_PYTHON = SCRIPTS.parent / ".venv/bin/python"
ENTRYPOINTS = {
    "transcribe": "transcribe_audio.py",
    "suggest": "spoken_edit.py",
    "chatcut": "edit_backends/chatcut_handoff.py",
    "kdenlive": "edit_backends/execution.py",
    "editor": "edit_backends/execution.py",
    "review": "review_output_video.py",
    "compose": "video_render/compose.py",
    "multi_shot": "video_render/multi_shot.py",
    "teaching_clips": "video_render/teaching_clips.py",
    "shot_image": "video_derivatives.py",
}

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
result = callback(**kwargs)
Path(request["result_path"]).write_text(json.dumps(result, ensure_ascii=False, allow_nan=False))
"""


# Candidate projection burns captions and measures fonts, so it shares Photo's
# interpreter boundary with composition rather than importing into Agent.
_CANDIDATE_DRIVER = """import json, sys
from pathlib import Path
request = json.load(sys.stdin)
sys.path.insert(0, str(Path(request['scripts_root']).parent))
sys.path.insert(0, request['scripts_root'])
from video_candidate import project_candidate
result = project_candidate(native=request['native'], descriptor=request['descriptor'],
    source=Path(request['source']),
    original_hashes={Path(path): digest for path, digest in request['original_hashes'].items()},
    output_dir=Path(request['output_dir']), workspace=Path(request['workspace']))
Path(request['result_path']).write_text(json.dumps(result, ensure_ascii=False, allow_nan=False))
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
        self.retry_shot_id = None
        self.descriptor = None
        self.workspace_root = None
        self.image_source = None
        self.image_manifest = None

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
        if not root.is_relative_to(local_media_root()) or not root.is_dir() or not isinstance(data["steps"], list) or not data["steps"] or not isinstance(data["source_refs"], list):
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
        if value == "$live":
            raise ProductContractError("photo_binding_rejected")
        if isinstance(value, dict) and set(value) == {"json_ref"}:
            return json.loads(local_path(root, value["json_ref"]).read_text(encoding="utf-8"))
        if isinstance(value, dict) and set(value) in ({"runtime_ref"}, {"runtime_path"}):
            key = next(iter(value))
            ref = value[key]
            if ref not in {"native-" + action + ".json" for action in ENTRYPOINTS}:
                raise ProductContractError("photo_binding_rejected")
            path = local_path(output_root.parent, ref)
            return path if key == "runtime_path" else json.loads(path.read_text(encoding="utf-8"))
        if value == "$tts_path":
            if tts_path is None:
                raise ProductContractError("photo_binding_rejected")
            return tts_path
        if isinstance(value, dict) and set(value) == {"local_ref"}:
            return local_path(root, value["local_ref"])
        if isinstance(value, (dict, list)):
            raise ProductContractError("photo_binding_rejected")
        return value

    def _invoke(self, step: dict[str, Any], *, root: Path, handoff: dict[str, Any], output_root: Path, tts_path: Path | None = None) -> Any:
        if not isinstance(step, dict) or set(step) != {"action", "function", "kwargs"} or not isinstance(step["action"], str) or step["action"] not in ENTRYPOINTS:
            raise ProductContractError("photo_binding_rejected")
        script = (SCRIPTS / ENTRYPOINTS[step["action"]]).resolve()
        if not script.is_relative_to(SCRIPTS.resolve()) or not script.is_file():
            raise ProductContractError("photo_entrypoint_unavailable")
        function = step["function"]
        if not isinstance(function, str) or not function.isidentifier() or function.startswith("_") or not isinstance(step["kwargs"], dict):
            raise ProductContractError("photo_binding_rejected")
        if not PHOTO_PYTHON.is_file():
            raise ProductContractError("photo_entrypoint_unavailable")
        kwargs = {k: self._argument(v, root=root, handoff=handoff, output_root=output_root / step["action"], tts_path=tts_path) for k, v in step["kwargs"].items()}
        if step['action'] == 'suggest' and self.descriptor is not None:
            if function != 'generate_suggestions':
                raise ProductContractError('photo_binding_rejected')
            # The descriptor has already passed confirmation/digest validation.
            # Local binding text must not substitute for the confirmed script.
            kwargs['handoff'] = self.descriptor
        if step['action'] == 'shot_image':
            if function != 'create_shot_image' or self.descriptor is None or 'shotImageTask' not in self.descriptor:
                raise ProductContractError('photo_image_action_rejected')
            kwargs = {'task': self.descriptor['shotImageTask'], 'source': self.image_source,
                      'manifest_path': self.image_manifest, 'output': output_root / 'shot_image'}
        if self.descriptor is not None and step['action'] in {'compose', 'teaching_clips'}:
            from video_derivatives import confirmed_manifest
            if function != step['action'] or not isinstance(kwargs.get('manifest_path'), Path):
                raise ProductContractError('photo_binding_rejected')
            previous_manifest = None
            if self.descriptor.get('previousJobId'):
                previous_ref = 'runs/' + hashlib.sha256(self.descriptor['previousJobId'].encode()).hexdigest()[:32]
                previous_manifest = local_path(self.workspace_root, previous_ref + '/confirmed-' + step['action'] + '.json')
            kwargs['manifest_path'] = confirmed_manifest(kwargs['manifest_path'], self.descriptor,
                self.workspace_root, output_root / ('confirmed-' + step['action'] + '.json'), teaching=step['action'] == 'teaching_clips',
                narration_path=tts_path if self.descriptor['narration'] is not None else None, previous_manifest=previous_manifest)
            if self.descriptor.get('renderShotIds'):
                kwargs['render_shot_ids'] = self.descriptor['renderShotIds']
        if self.retry_shot_id is not None and step["action"] in {"compose", 'teaching_clips'}:
            if function != step['action']:
                raise ProductContractError("photo_shot_retry_unavailable")
            kwargs["retry_shot_id"] = self.retry_shot_id
        if self.descriptor is not None and step['action'] in {'kdenlive', 'editor'} and (self.descriptor.get('renderShotIds') or (output_root / 'native-teaching_clips.json').is_file()):
            from video_derivatives import teaching_overlays
            if function != 'render' or not (output_root / 'native-teaching_clips.json').is_file():
                raise ProductContractError('photo_plan_revision_unavailable')
            clips = json.loads((output_root / 'native-teaching_clips.json').read_text())
            kwargs['animations'] = teaching_overlays(clips, self.descriptor, kwargs['source'])
        if step['action'] in {'kdenlive', 'editor'}:
            from edit_backends.registry import BACKENDS, local_editor_choice
            if function != 'render':
                raise ProductContractError('photo_binding_rejected')
            selected = kwargs.get('backend_id', 'otio_kdenlive' if step['action'] == 'kdenlive' else None)
            if self.binding_path.is_file():
                frozen = self._binding()
                choice = local_editor_choice(Path(frozen['creative_store']).parent, frozen['identity']['project_id'])
                if choice:
                    if choice.get('method','external') != 'external':
                        raise ProductContractError('photo_manual_workflow_required')
                    selected = choice['editor']
            if selected not in BACKENDS:
                raise ProductContractError('photo_editor_selection_required')
            kwargs['backend_id'] = selected
            kwargs['editing_method'] = 'open_source'
        if step["action"] == "transcribe":
            if function != "transcribe_project":
                raise ProductContractError("photo_entrypoint_unavailable")
            kwargs["live"] = self.live
            if kwargs.get("provider_name") in {"openai_api", "dashscope", "fun_asr"} and not self.live:
                raise ProductContractError("photo_live_required")
        result_path = output_root / ("native-" + step["action"] + ".json")
        result_path.unlink(missing_ok=True)
        encoded = {k: {"__photo_local_path__": str(v)} if isinstance(v, Path) else v for k, v in kwargs.items()}
        module_name = ".".join(script.relative_to(SCRIPTS.resolve()).with_suffix("").parts)
        request = {"scripts_root": str(SCRIPTS.resolve()), "script": str(script), "module": module_name, "function": function, "kwargs": encoded, "result_path": str(result_path)}
        # Agent and router packages can use another Python ABI. The fixed Photo
        # interpreter resolves its own packages; the driver pins script paths.
        environment = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
        completed = subprocess.run([str(PHOTO_PYTHON), "-c", _LOCAL_DRIVER], input=json.dumps(request, ensure_ascii=False), cwd=root, env=environment, capture_output=True, text=True, timeout=1800, check=False)
        # Diagnostics can contain local paths and remain exclusively local.
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / (step["action"] + ".log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise ProductContractError("photo_execution_failed")
        native = json.loads(result_path.read_text())
        if step["action"] in {"kdenlive", "editor", "compose", "teaching_clips"} and (not isinstance(native, dict) or native.get("status") not in {"candidate", "completed"}):
            raise ProductContractError("photo_execution_failed")
        return native

    def _descriptor(self, workspace: Path, input_ref: str, handoff: dict) -> dict:
        from openclaw_product_contract import video_digest
        path = local_path(workspace, input_ref).with_name("video.json")
        descriptor = json.loads(path.read_text(encoding="utf-8"))
        if descriptor.get("mxHandoff") != handoff or descriptor.get("scope") != "video_handoff_v1":
            raise ProductContractError("video_identity_rejected")
        identity = descriptor["identity"]
        pairs = {"jobId": "job_id", "publicVariantId": "work_id", "workRevision": "work_revision",
                 "photoProjectId": "project_id", "photoProjectRevision": "project_revision",
                 "catalogDigest": "catalog_digest", "confirmationRef": "confirmation_ref"}
        if any(identity[key] != handoff["identity"][value] for key, value in pairs.items()):
            raise ProductContractError("video_identity_rejected")
        frozen = {"script": descriptor["script"], "shots": descriptor["shots"], "animations": descriptor["animations"],
                  "documentRef": descriptor["documentRef"],
                  "narrationCacheKey": descriptor["narration"]["cacheKey"] if descriptor["narration"] else None}
        if descriptor.get('shotImageInputs'):
            frozen['shotImageInputs'] = descriptor['shotImageInputs']
        if descriptor.get('shotImageTask'):
            frozen['shotImageTask'] = descriptor['shotImageTask']
        elif descriptor.get('renderShotIds'):
            frozen['renderShotIds'] = descriptor['renderShotIds']
            if descriptor.get('previousJobId'):
                frozen['previousJobId'] = descriptor['previousJobId']
        if video_digest(frozen) != identity["confirmedContentDigest"] or descriptor["script"] != handoff["script"]:
            raise ProductContractError("video_identity_rejected")
        from video_derivatives import code_bytes
        ids = [r['shot']['shotId'] for r in descriptor['shots']]
        if len(ids) != len(set(ids)) or any(not isinstance(s, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', s) for s in ids):
            raise ProductContractError('photo_shot_identity_rejected')
        for row in descriptor['shots']:
            if row.get('renderCode'):
                code_bytes(row['renderCode'])
        selected = descriptor.get('renderShotIds')
        if selected is not None and (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected) or not set(selected) <= set(ids)):
            raise ProductContractError('photo_shot_revision_rejected')
        return descriptor

    def _candidate(self, binding, descriptor, root, workspace, before, native, output_root):
        if not isinstance(native, dict):
            raise ProductContractError("photo_candidate_projection_missing")
        if native.get("manifest"):
            plan = json.loads(Path(native["manifest"]).read_text())
            source = next((Path(i["path"]) for i in plan["inputs"] if i["role"] == "original_video"), None)
            if source not in before:
                raise ProductContractError("photo_candidate_projection_missing")
        else:
            source = local_path(workspace, descriptor['mxHandoff']['tts_ref']) if descriptor['narration'] is not None else next((p for p in before if p.suffix.lower() == '.wav'), None)
        if source is None:
            raise ProductContractError("photo_candidate_projection_missing")
        output_root.mkdir(parents=True, exist_ok=True)
        result_path = output_root / 'native-candidate.json'
        result_path.unlink(missing_ok=True)
        request = {'scripts_root': str(SCRIPTS.resolve()), 'native': native, 'descriptor': descriptor,
                   'source': str(source), 'original_hashes': {str(path): digest for path, digest in before.items()},
                   'output_dir': str(output_root / 'return'), 'workspace': str(workspace),
                   'result_path': str(result_path)}
        environment = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
        completed = subprocess.run([str(PHOTO_PYTHON), '-c', _CANDIDATE_DRIVER],
            input=json.dumps(request, ensure_ascii=False), cwd=root, env=environment,
            capture_output=True, text=True, timeout=1800, check=False)
        (output_root / 'candidate.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
        if completed.returncode != 0 or not result_path.is_file():
            raise ProductContractError('photo_execution_failed')
        payload = json.loads(result_path.read_text())
        destination = local_path(root, binding["candidate_ref"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=True, allow_nan=False) + "\n")
        return payload

    def execute(self, node: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        NodeExecutionError = import_module("openclaw_media.node_registry").NodeExecutionError

        if node.get("type") != "edit.handoff" or node.get("version") != "1.0.0" or node.get("outputs") != ["handoff_manifest"]:
            raise NodeExecutionError("unknown_node")
        try:
            binding = self._binding()
            workspace = Path(context["workspace_root"]).resolve()
            self.workspace_root = workspace
            inputs = context["inputs"]
            descriptor = local_path(workspace, inputs.get("workspace_ref", inputs.get("run_ref")))
            handoff = validate_video_handoff(json.loads(descriptor.read_text(encoding="utf-8")), binding["identity"], expected_handoff_digest=binding["handoff_digest"])
            full_descriptor = self._descriptor(workspace, str(descriptor.relative_to(workspace)), handoff)
            self.descriptor = full_descriptor
            tts_path = local_path(workspace, handoff["tts_ref"]) if handoff["tts_ref"] is not None else None
            if tts_path is not None and not tts_path.is_file():
                raise ProductContractError("photo_binding_rejected")
            root = Path(binding["project_root"]).resolve()
            sources = [local_path(root, ref) for ref in binding["source_refs"]]
            if full_descriptor['narration'] is not None:
                sources.append(tts_path)
            before = {p: file_sha256(p) for p in sources}
            output_root = local_path(workspace, context["run_ref"])
            output_root.mkdir(parents=True, exist_ok=True)
            try:
                native = None
                for step in binding["steps"]:
                    if (self.retry_shot_id is not None or full_descriptor.get('renderShotIds')) and step["action"] not in {'compose', 'teaching_clips', 'kdenlive', 'editor'}:
                        continue
                    returned = self._invoke(step, root=root, handoff=handoff, output_root=output_root, tts_path=tts_path)
                    if step["action"] in {"kdenlive", "editor", "compose"}:
                        native = returned
                if native is not None and native.get('manifest') and (output_root / 'native-teaching_clips.json').is_file():
                    teaching = json.loads((output_root / 'native-teaching_clips.json').read_text())
                    native['shots'] = teaching['shots']
                    native['shot_fps'] = teaching['clips'][0]['fps']
                # Re-read the authority after execution, before projecting a result.
                current = self._binding()
                validate_video_handoff(handoff, current["identity"], expected_handoff_digest=current["handoff_digest"])
                if before != {p: file_sha256(p) for p in sources} or self._descriptor(workspace, str(descriptor.relative_to(workspace)), handoff) != full_descriptor:
                    raise ProductContractError("photo_execution_failed")
                candidate = self._candidate(binding, full_descriptor, root, workspace, before, native, output_root)
            except Exception as exc:
                code = getattr(exc, "code", "photo_execution_failed")
                if code not in {"photo_entrypoint_unavailable", "photo_binding_rejected", "photo_live_required", "photo_candidate_projection_missing"}:
                    code = "photo_execution_failed"
                candidate = {"identity": handoff["identity"], "handoff_digest": handoff["handoff_digest"], "status": "failed", "description": None, "checks": [], "subtitles": "", "preview": None, "failure_code": code}
                from video_candidate import failed_shot_progress
                for action in ('compose', 'teaching_clips'):
                    native_path = output_root / ('native-' + action + '.json')
                    manifest_path = output_root / ('confirmed-' + action + '.json')
                    if native_path.is_file() and manifest_path.is_file():
                        failed = json.loads(native_path.read_text())
                        if failed.get('status') == 'failed':
                            facts = failed_shot_progress(failed, full_descriptor, json.loads(manifest_path.read_text())['fps'],
                                **({'output_dir': output_root, 'workspace': workspace} if action == 'compose' else {}))
                            candidate.update(progress={'shotProgress': facts['shotProgress']}, failedShotId=facts['failedShotId'])
            # This is a local artifact in the existing durable runtime. A failure
            # receipt is not a succeeded render and never enters the media library.
            artifact = output_root / "handoff_manifest.json"
            artifact.write_text(json.dumps(candidate, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            if candidate.get("status") == "failed":
                raise NodeExecutionError(candidate["failure_code"])
            return {"handoff_manifest": {"local_path": str(artifact), "artifact_ref": str(artifact.relative_to(workspace)), "mime_type": "application/json", "size_bytes": artifact.stat().st_size, "cloud_bytes": 0}}
        except ProductContractError as exc:
            raise NodeExecutionError(exc.code) from exc
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NodeExecutionError("photo_binding_rejected") from exc
        finally:
            self.descriptor = None


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
            full = self.node_registry._descriptor(self.root, str(descriptor.relative_to(self.root)), handoff)
            from openclaw_product_contract import video_digest
            result["photo_descriptor_digest"] = video_digest({k: v for k, v in full.items() if k != "retryShotId"})
            result["photo_tts_digest"] = file_sha256(local_path(self.root, handoff["tts_ref"])) if handoff["tts_ref"] is not None else None
            if full['narration'] is not None:
                audio = local_path(self.root, handoff['tts_ref'])
                meta = full['narration']['artifact']
                if meta['sha256'] != 'sha256:' + result['photo_tts_digest'] or meta['sizeBytes'] != audio.stat().st_size or meta['mimeType'] != 'audio/wav':
                    raise ProductContractError('photo_narration_digest_rejected')
            images = []
            for item in full.get('shotImageInputs', []):
                if item['shotId'] not in {r['shot']['shotId'] for r in full['shots']}:
                    raise ProductContractError('photo_image_identity_rejected')
                image = local_path(self.root, 'video-inputs/' + full['identity']['jobId'] + '/shot-images/' + item['shotId'] + '.jpg')
                from video_derivatives import inspect_jpeg
                inspect_jpeg(image)
                digest = file_sha256(image)
                if item['artifact']['sha256'] != 'sha256:' + digest or image.stat().st_size != item['artifact']['sizeBytes'] or item['artifact']['mimeType'] != 'image/jpeg':
                    raise ProductContractError('photo_image_digest_rejected')
                images.append(digest)
            result['photo_image_digests'] = images
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

        def create_video_shot_image(self, run_ref, *, task, inputs):
            registry = self.node_registry
            try:
                normalized = self._inputs(inputs)
                binding = registry._binding()
                handoff = json.loads(local_path(self.root, normalized['workspace_ref']).read_text())
                descriptor = registry._descriptor(self.root, normalized['workspace_ref'], handoff)
                expected = 'runs/' + hashlib.sha256(binding['identity']['job_id'].encode()).hexdigest()[:32]
                if run_ref != expected or descriptor.get('shotImageTask') != task or task.get('shotId') not in {r['shot']['shotId'] for r in descriptor['shots']}:
                    raise ProductContractError('photo_image_identity_rejected')
                output = local_path(self.root, run_ref)
                output.mkdir(parents=True, exist_ok=True)
                root = Path(binding['project_root']).resolve()
                sources = [local_path(root, ref) for ref in binding['source_refs']]
                before = {p: file_sha256(p) for p in sources}
                registry.descriptor = descriptor; registry.workspace_root = self.root
                if task['action'] == 'source_frame':
                    videos = [p for p in sources if p.suffix.lower() in {'.mp4', '.mov', '.mkv', '.webm', '.m4v'}]
                    if len(videos) != 1:
                        raise ProductContractError('photo_source_frame_rejected')
                    registry.image_source = videos[0]
                elif task['action'] == 'code_render':
                    from video_derivatives import confirmed_manifest
                    row = next(r for r in descriptor['shots'] if r['shot']['shotId'] == task['shotId'])
                    if not row.get('renderCode'):
                        raise ProductContractError('photo_render_code_rejected')
                    steps = [s for s in binding['steps'] if s['action'] in {'compose', 'teaching_clips'} and s['function'] == s['action']]
                    if len(steps) != 1:
                        raise ProductContractError('photo_image_action_unavailable')
                    step = steps[0]
                    manifest = registry._argument(step['kwargs']['manifest_path'], root=root, handoff=handoff, output_root=output)
                    registry.image_manifest = confirmed_manifest(manifest, descriptor, self.root,
                        output / 'confirmed-image.json', teaching=step['action'] == 'teaching_clips')
                else:
                    raise ProductContractError('photo_image_action_rejected')
                native = registry._invoke({'action': 'shot_image', 'function': 'create_shot_image', 'kwargs': {}},
                    root=root, handoff=handoff, output_root=output)
                if normalized != self._inputs(inputs) or before != {p: file_sha256(p) for p in sources}:
                    raise ProductContractError('video_identity_rejected')
                image = Path(native['image_path']).resolve()
                from video_derivatives import inspect_jpeg
                inspect_jpeg(image)
                return {'image_ref': str(image.relative_to(self.root)), 'shotId': task['shotId']}
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                RemoteError = import_module('openclaw_media.remote_client').RemoteError
                raise RemoteError(getattr(exc, 'code', 'photo_image_action_rejected')) from exc
            finally:
                registry.descriptor = None; registry.image_source = None; registry.image_manifest = None

        def render_video_revision(self, run_ref, *, shot_ids, previous_job_id, inputs):
            Outcome = import_module('openclaw_media.pipeline_runtime').RuntimeOutcome
            try:
                normalized = self._inputs(inputs)
                handoff = json.loads(local_path(self.root, normalized['workspace_ref']).read_text())
                descriptor = self.node_registry._descriptor(self.root, normalized['workspace_ref'], handoff)
                if descriptor.get('renderShotIds') != shot_ids or descriptor.get('previousJobId') != previous_job_id or not isinstance(previous_job_id, str) or not previous_job_id or previous_job_id == descriptor['identity']['jobId']:
                    raise ProductContractError('photo_shot_revision_rejected')
                previous_ref = 'runs/' + hashlib.sha256(previous_job_id.encode()).hexdigest()[:32]
                previous, _ = self._load(previous_ref)
                if previous is None or previous['status'] not in {'succeeded', 'pending_manual'}:
                    raise ProductContractError('photo_previous_run_unavailable')
                prior_inputs = json.loads(previous['inputs_json'])
                prior = json.loads(local_path(self.root, prior_inputs['workspace_ref']).with_name('video.json').read_text())
                from openclaw_product_contract import video_digest
                if prior_inputs['photo_descriptor_digest'] != video_digest({k: v for k, v in prior.items() if k != 'retryShotId'}):
                    raise ProductContractError('photo_previous_run_changed')
                keys = ('publicTenantId', 'publicContentId', 'publicVariantId', 'workRevision', 'photoProjectId', 'photoProjectRevision', 'catalogDigest')
                if prior['identity']['jobId'] != previous_job_id or any(prior['identity'][k] != descriptor['identity'][k] for k in keys) or prior['documentRef'] != descriptor['documentRef'] or prior['script'] != descriptor['script']:
                    raise ProductContractError('photo_previous_run_rejected')
                if any(prior_inputs[k] != normalized[k] for k in ('photo_tts_digest', 'photo_source_digests')):
                    raise ProductContractError('photo_previous_run_changed')
                prior_rows = {r['shot']['shotId']: r for r in prior['shots']}
                for row in descriptor['shots']:
                    if row['shot']['shotId'] not in shot_ids and prior_rows.get(row['shot']['shotId']) != row:
                        raise ProductContractError('photo_unselected_shot_changed')
                prior_animations = {a['animationId']: a for a in prior['animations'] if a['shotId'] not in shot_ids}
                current_animations = {a['animationId']: a for a in descriptor['animations'] if a['shotId'] not in shot_ids}
                if prior_animations != current_animations:
                    raise ProductContractError('photo_unselected_shot_changed')
                binding = self.node_registry._binding()
                actions = [s['action'] for s in binding['steps'] if s['action'] in {'compose', 'teaching_clips'} and s['function'] == s['action']]
                if len(actions) != 1:
                    raise ProductContractError('photo_plan_revision_unavailable')
                created = self.create_run(previous['pipeline_id'], previous['version'], previous['catalog_digest'], run_ref=run_ref, inputs=inputs)
                if created.status in {'pending_manual', 'cancelled'}:
                    return created
                run, _ = self._load(run_ref)
                if run['status'] == 'succeeded':
                    return self.execute(run_ref, inputs=inputs)
                action = actions[0]
                destination = local_path(self.root, run_ref + '/' + action)
                marker = local_path(self.root, run_ref + '/revision-origin.json')
                origin = {'previousJobId': previous_job_id, 'descriptorDigest': normalized['photo_descriptor_digest']}
                if destination.exists():
                    if not marker.is_file() or json.loads(marker.read_text()) != origin:
                        raise ProductContractError('photo_previous_run_rejected')
                else:
                    from video_derivatives import clone_render_cache
                    clone_render_cache(local_path(self.root, previous_ref + '/' + action), destination)
                    marker.write_text(json.dumps(origin))
                return self.execute(run_ref, inputs=inputs)
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                return Outcome(status='pending_manual', code=getattr(exc, 'code', 'photo_shot_revision_rejected'))

        def retry_video_shot(self, run_ref, *, shot_id, inputs):
            Outcome = import_module("openclaw_media.pipeline_runtime").RuntimeOutcome
            try:
                normalized = self._inputs(inputs)
                binding = self.node_registry._binding()
                path = local_path(self.root, normalized["workspace_ref"])
                handoff = json.loads(path.read_text())
                descriptor = self.node_registry._descriptor(self.root, normalized["workspace_ref"], handoff)
                if descriptor.get("retryShotId") != shot_id or shot_id not in {r["shot"]["shotId"] for r in descriptor["shots"]}:
                    raise ProductContractError("photo_shot_retry_rejected")
                render_steps = [s for s in binding["steps"] if s['action'] in {'compose', 'teaching_clips'} and s['function'] == s['action']]
                if len(render_steps) != 1:
                    raise ProductContractError("photo_shot_retry_unavailable")
                run, nodes = self._load(run_ref)
                if run is None or run["status"] != "pending_manual" or json.loads(run["inputs_json"]) != normalized:
                    raise ProductContractError("photo_shot_retry_rejected")
                native = json.loads(local_path(self.root, run_ref + '/native-' + render_steps[0]['action'] + '.json').read_text())
                if native.get("status") != "failed" or {s["id"] for s in native.get("shots", []) if s.get("status") == "failed"} != {shot_id}:
                    raise ProductContractError("photo_shot_retry_rejected")
                pipeline = self.catalog.resolve(run["pipeline_id"], run["version"], run["catalog_digest"])
                if len(pipeline["nodes"]) != 1 or pipeline["nodes"][0]["type"] != "edit.handoff":
                    raise ProductContractError("photo_shot_retry_unavailable")
                # Reuse the canonical run/receipt store; only this single handoff node is invalidated.
                with self._db() as db:
                    changed = db.execute("UPDATE analysis_runs SET status='created' WHERE run_ref=? AND status=?", (run_ref, run["status"]))
                    if changed.rowcount != 1:
                        raise ProductContractError("photo_shot_retry_rejected")
                    db.execute("DELETE FROM node_receipts WHERE run_ref=?", (run_ref,))
                self.node_registry.retry_shot_id = shot_id
                try:
                    return super().execute(run_ref, inputs=normalized)
                finally:
                    self.node_registry.retry_shot_id = None
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                return Outcome(status="pending_manual", code=getattr(exc, "code", "photo_shot_retry_rejected"))

        def execute(self, run_ref, *, inputs):
            # Replay still checks today's binding and descriptor. The canonical
            # runtime stores refs, which alone do not freeze referenced content.
            try:
                normalized = self._inputs(inputs)
                binding = self.node_registry._binding()
                descriptor = local_path(self.root, normalized.get("workspace_ref", normalized.get("run_ref")))
                validate_video_handoff(json.loads(descriptor.read_text(encoding="utf-8")), binding["identity"], expected_handoff_digest=binding["handoff_digest"])
                run, _ = self._load(run_ref)
                if run is not None and json.loads(run["inputs_json"]) != normalized:
                    raise ProductContractError("video_identity_rejected")
            except (ProductContractError, OSError, ValueError, TypeError, KeyError) as exc:
                Outcome = import_module("openclaw_media.pipeline_runtime").RuntimeOutcome
                return Outcome(status="pending_manual", code=getattr(exc, "code", "photo_binding_rejected"))
            return super().execute(run_ref, inputs=normalized)

    def create(workspace, catalog):
        return PhotoRuntime(workspace, catalog=catalog, node_registry=PhotoNodeRegistry(catalog, binding_path, live=live))
    return create
