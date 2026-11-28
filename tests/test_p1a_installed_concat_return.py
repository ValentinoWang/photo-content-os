"""Exercise the installed U19 watch and Studio against local, synthetic media."""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from unittest.mock import patch

import pytest

from test_concat_backend import _make_fake_concat_mcp
from test_p1a_installed_watch import DEVICE, World, build_package, installed
from studio.project_store import ProjectStoreError


WAITING = "waiting_manual_refine"
LEASE = "lease_" + "1" * 32


class Media:
    """Offline Media boundary with the device requests and work projection used by watch."""

    def __init__(self, path):
        self.path = path
        self.state = json.loads(path.read_bytes())
        self.job = self.state["job"]

    def save(self):
        self.path.write_text(json.dumps(self.state), encoding="utf-8")

    def advance(self, state, **fields):
        self.job.update(state=state, revision=self.job["revision"] + 1, **fields)
        self.save()
        return {"job": copy.deepcopy(self.job)}

    def close(self):
        pass

    def request(self, method, path, *, headers, content, credential):
        from urllib.parse import parse_qsl, urlsplit
        import httpx
        from openclaw_media.generated_product_contract import OPERATIONS
        from openclaw_media.remote_client import RemoteError

        assert credential == "fixture-secret"
        url = urlsplit(path)
        assert url.path.startswith("/media/api/")
        target = url.path.removeprefix("/media/api")
        for operation, spec in OPERATIONS.items():
            callback = getattr(self, operation, None)
            if callback is None or method != spec["method"]:
                continue
            match = re.fullmatch(re.sub(r"\{[^}]+\}", r"([^/]+)", spec["relative_path"]), target)
            if match is None:
                continue
            body = json.loads(content) if content else dict(parse_qsl(url.query))
            if "limit" in body:
                body["limit"] = int(body["limit"])
            if spec["idempotency"] == "required":
                key = headers["Idempotency-Key"]
                assert self.state.setdefault("requests", {}).setdefault(key, [target, body]) == [target, body]
            try:
                return httpx.Response(200, json=callback(*match.groups(), **body))
            except RemoteError as exc:
                if exc.retryable:
                    raise httpx.ReadError("simulated connection loss") from exc
                return httpx.Response(exc.status, json={"error": {"code": exc.code}})
        raise AssertionError((method, target))

    def device_heartbeat(self, device, **request):
        assert device == DEVICE
        self.state["device_revision"] += 1
        claim = self.job if self.job and self.job["state"] == "queued" else None
        self.save()
        return dict(state="online", revision=self.state["device_revision"], api_compatible=True,
                    catalog_compatible=True, device_id=DEVICE, claimable_job=claim)

    def video_project_selection_list(self, device_id):
        assert device_id == DEVICE
        return {"requests": [] if self.state["consumed"] else [self.state["request"]]}

    def video_project_selection_confirm(self, device_id, request_id, **body):
        assert (device_id, request_id) == (DEVICE, self.state["request"]["request_id"])
        descriptor, data, meta, self.job = build_package(body["project_id"], body["project_revision"])
        self.state.update(consumed=True, job=self.job, descriptor=descriptor, meta=meta,
                          data=base64.b64encode(data).decode())
        self.save()
        return {"binding": {"bindingId": "binding_fixture", "bindingGeneration": 3, "deviceId": DEVICE,
                            "publicAccountId": self.job["public_account_id"], "photoProjectId": body["project_id"],
                            "photoProjectRevision": body["project_revision"]}, "selectionRevision": 2}

    def job_list(self, *, limit, state=None):
        include = {state} if state else {"queued", "leased", "acknowledged", "running"}
        return {"jobs": [copy.deepcopy(self.job)] if self.job and self.job["state"] in include else []}

    def job_lease(self, job, **body):
        return self.advance("leased", lease_id=LEASE, lease_expires_at="2099-01-01T00:00:00Z")

    def job_ack(self, job, **body):
        return self.advance("acknowledged")

    def job_start(self, job, **body):
        return self.advance("running")

    def video_artifact_download(self, job, artifact):
        assert (job, artifact) == (self.job["job_id"], self.state["meta"]["artifactId"])
        return {"ok": True, "artifact": self.state["meta"], "contentBase64": self.state["data"]}

    def video_progress(self, job, **body):
        return {"ok": True, "job": copy.deepcopy(self.job)}

    def video_refine_wait(self, job, **body):
        self.check(job, body)
        assert body["confirmed_content_digest"] == self.job["video_identity"]["confirmedContentDigest"]
        evidence = body["evidence"]
        assert evidence == dict(editor_backend="concat", project_built=True, opened_for_refine=True,
                                evidence_digest=evidence["evidence_digest"])
        self.state["wait"] = body
        return self.advance(WAITING, lease_id=None, lease_expires_at=None)

    def video_refine_resume(self, job, **body):
        from openclaw_media.remote_client import RemoteError
        assert body["evidence_digest"] == self.state["wait"]["evidence"]["evidence_digest"]
        assert body["confirmed_content_digest"] == self.state["wait"]["confirmed_content_digest"]
        assert self.state.get("pinned", body["candidate_digest"]) == body["candidate_digest"]
        self.state["pinned"] = body["candidate_digest"]
        key = str(body["expected_revision"])
        resumes = self.state.setdefault("resumes", {})
        if key in resumes:
            assert resumes[key]["body"] == body
            if resumes[key]["reply"]["job"]["lease_id"] != self.job["lease_id"]:
                raise RemoteError("invalid_state", status=409)
            return resumes[key]["reply"]
        assert self.job["state"] == WAITING and body["expected_revision"] == self.job["revision"]
        reply = self.advance("running", lease_id=f"lease_{self.job['revision']:032x}",
                             lease_expires_at="2099-01-01T00:00:00Z") | {"candidate_digest": self.state["pinned"]}
        resumes[key] = {"body": body, "reply": reply}
        self.save()
        return reply

    def check(self, job, body):
        assert job == self.job["job_id"] and self.job["state"] == "running"
        assert body["lease_id"] == self.job["lease_id"] and body["expected_revision"] == self.job["revision"]

    def video_artifact_upload(self, job, **body):
        from openclaw_media.remote_client import RemoteError
        self.check(job, body)
        raw = base64.b64decode(body["contentBase64"], validate=True)
        assert body["sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        assert body["sizeBytes"] == len(raw)
        meta = {key: body[key] for key in ("artifactId", "sha256", "mimeType", "sizeBytes")}
        meta["downloadPath"] = f"/media/api/jobs/{job}/video-artifacts/{meta['artifactId']}"
        entry = {"meta": meta, "content": body["contentBase64"]}
        assert self.state.setdefault("artifacts", {}).setdefault(body["kind"], entry) == entry
        lose_reply = self.state.pop("lose_preview", False)
        self.save()
        if lose_reply:
            raise RemoteError("request_failed", retryable=True)
        return {"artifact": meta}

    def job_result(self, job, **body):
        if body["result_status"] != "succeeded":
            self.state["blocked"] = body
            return self.advance("blocked")
        if "completed" in self.state:
            assert self.state["completed"] == body
            return {"job": copy.deepcopy(self.job)}
        self.check(job, body)
        artifacts = self.state["artifacts"]
        candidate = json.loads(base64.b64decode(artifacts["candidate_json"]["content"]))
        result = body["video_result"]
        assert candidate["candidateDigest"] == self.state["pinned"]
        assert result["candidateArtifact"] == artifacts["candidate_json"]["meta"]
        assert result["previewArtifact"]["artifact"] == artifacts["preview_mp4"]["meta"]
        assert result["subtitleArtifact"] == artifacts["subtitle_text"]["meta"]
        self.state["works"] = {job: [candidate]}
        self.state["completed"] = body
        return self.advance("succeeded")


def concat_double(source, recorded, mode):
    from edit_backends.editors import concat_adapter as adapter

    parent = _make_fake_concat_mcp(source, 1.0, recorded)

    class Concat(parent):
        def call(self, tool, args, **kwargs):
            project = Path(args["path"]) if "path" in args else None
            if tool == "project_save":
                project.mkdir()
                (project / "concat.json").write_text(json.dumps(self._state()))
            if tool == "project_open":
                state = json.loads((project / "concat.json").read_bytes())
                self.saved_state = state
                return state
            if tool == "timeline_read" and hasattr(self, "saved_state"):
                return self.saved_state
            return super().call(tool, args, **kwargs)

    def record_open(args, **kwargs):
        assert args[:3] == ["/usr/bin/open", "-n", "-a"]
        project = Path(args[-1])
        assert (project / "concat.json").is_file()
        recorded.setdefault("opens", []).append(project.name)
        if mode == "open-fails":
            raise subprocess.CalledProcessError(1, args, stderr="fixture refused to open")
        return subprocess.CompletedProcess(args, 0)

    return (patch.object(adapter, "ConcatMCP", Concat),
            patch.object(adapter, "_require_app"),
            patch.object(adapter, "subprocess", type("Open", (), {"run": staticmethod(record_open)})()))


def run_installed(config):
    from contextlib import ExitStack
    from openclaw_media import cli
    from openclaw_media.agent import Agent, AgentState, AgentStateStore
    from openclaw_media.catalog import InstalledCatalog
    from openclaw_media.device_credentials import DeviceCredentialStore
    from openclaw_media.remote_client import RemoteClient
    import openclaw_media.photo_refine_resume as installed_refine
    import bridge.openclaw_media_agent as wrapper
    import bridge.openclaw_video_execution as execution

    assert Path(installed_refine.__file__).is_relative_to(sys.prefix)
    state = AgentStateStore(Path(config["agent_dir"]) / "state.json")
    if not state.path.exists():
        state.save(AgentState(remote_base_url="https://fixture.invalid", device_id=DEVICE,
                              catalog_digest=InstalledCatalog().manifest["catalog_digest"], workspace=config["workspace"]))

    class Keyring:
        def __init__(self):
            self.values = {}

        def set_password(self, service, user, password):
            self.values[service, user] = password

        def get_password(self, service, user):
            return self.values.get((service, user))

    credentials = DeviceCredentialStore(backend=Keyring())
    credentials.put_device(DEVICE, "fixture-secret")
    media = Media(Path(config["remote"]))
    recorded = {}
    actual_run = subprocess.run
    real_forever = Agent.run_forever

    class Cycles(threading.Event):
        remaining = 1 if state.load().active_job or media.job is not None else 2

        def wait(self, timeout=None):
            self.remaining -= 1
            if self.remaining == 0:
                self.set()
            return self.is_set()

    def local_render(args, **kwargs):
        if args[:2] != [str(execution.PHOTO_PYTHON), "-c"] or args[2] != execution._LOCAL_DRIVER:
            return actual_run(args, **kwargs)
        request = json.loads(kwargs["input"])
        assert request["module"] == "edit_backends.execution"
        # Execute only the established local driver in-process so the MCP fixture can be injected.
        with patch("sys.stdin", io.StringIO(kwargs["input"])):
            exec(compile(execution._LOCAL_DRIVER, "<photo-local-driver>", "exec"), {})
        return subprocess.CompletedProcess(args, 0, "", "")

    with ExitStack() as stack:
        for substitute in concat_double(Path(config["source"]), recorded, config["mode"]):
            stack.enter_context(substitute)
        stack.enter_context(patch.object(execution, "subprocess", type("Render", (), {"run": staticmethod(local_render)})()))
        stack.enter_context(patch.object(cli, "RemoteClient",
                                         side_effect=lambda url, **_: RemoteClient(url, transport=media, retries=0)))
        stack.enter_context(patch.object(cli, "DeviceCredentialStore", return_value=credentials))
        stack.enter_context(patch.object(Agent, "run_forever", lambda self, **_: real_forever(self, stop_event=Cycles())))
        wrapper.main(["watch", "--agent-dir", config["agent_dir"], "--workspace", config["workspace"],
                      "--state-dir", config["state_dir"]], confirmation_provider=lambda _: config["decision"])
    print("CONCAT_COUNTS " + json.dumps({"build": sum(tool == "project_create" for tool, _ in recorded.get("calls", [])),
                                        "open": len(recorded.get("opens", []))}))


def stage_fixture(world, mode):
    project_root = world.store.local_workspace_path(world.project["id"])
    source = project_root / "source.mp4"
    source.unlink()
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=0x25516b:s=288x512:r=30:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=660:duration=1", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", "-shortest", str(source)], check=True)
    source.with_suffix(".srt").write_text("1\n00:00:00,100 --> 00:00:00,900\n合成口播\n")
    analysis = project_root / "ai-analysis"
    analysis.mkdir()
    (analysis / "edit_suggestions.json").write_text('{"suggestions":[],"duration":1}')
    from studio.server import StudioApplication
    StudioApplication(world.store).video_editor_choice(world.project["id"],
                                                      {"editor": "concat", "method": "external", "revision": 1})
    return {"agent_dir": str(world.agent_dir), "workspace": str(world.workspace), "state_dir": str(world.state_dir),
            "decision": world.decision(), "remote": str(world.remote_file), "source": str(source), "mode": mode}


def watch(installed, config, world):
    env = dict(os.environ, LOCAL_MEDIA_ROOT=str(world.media), HOME=str(world.home), PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    done = subprocess.run([str(installed.python), str(Path(__file__).resolve()), json.dumps(config)],
                          capture_output=True, text=True, timeout=45, env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    return json.loads(next(line.split(" ", 1)[1] for line in done.stdout.splitlines() if line.startswith("CONCAT_COUNTS ")))


@pytest.fixture
def world(tmp_path, monkeypatch):
    fixture = World(tmp_path)
    monkeypatch.setenv("LOCAL_MEDIA_ROOT", str(fixture.media))
    return fixture


def job_identity(job):
    return {key: job[key] for key in ("job_id", "device_id", "binding_id", "binding_generation", "public_account_id", "video_identity")}


def test_installed_watch_resumes_the_checked_concat_return_after_expiry(installed, world, monkeypatch):
    from media_ops.media_project_selection import StudioSelectionPort
    from openclaw_media.remote_client import RemoteError
    from studio.server import StudioApplication

    config = stage_fixture(world, "ok")
    assert watch(installed, config, world) == {"build": 1, "open": 1}
    remote = world.remote()
    assert remote["job"]["state"] == WAITING, remote.get("blocked")
    assert remote["job"]["lease_id"] is None and not remote.get("artifacts")
    identity = job_identity(remote["job"])
    port = StudioSelectionPort(world.store, device_id=DEVICE, workspace=world.workspace)
    assert port.refine_status(identity)["evidence_digest"] == remote["wait"]["evidence"]["evidence_digest"]
    assert port.read_refined_candidate(identity) is None

    app = StudioApplication(world.store)
    project_id = world.project["id"]
    request = {"identity": identity["video_identity"], "expectedRevision": world.project["revision"]}
    project = next(world.workspace.glob("runs/*/editor/concat-project"))
    raw = Path(config["source"]).read_bytes()
    with pytest.raises(ProjectStoreError, match="作品交接已变化"):
        app.video_workflow.receive(world.twin["id"], io.BytesIO(raw), len(raw), request)
    monkeypatch.setenv("PHOTO_STUDIO_VIDEO_BINDING", str(world.root / "invalid-legacy.json"))
    assert app.video_workflow.command(project_id, {"op": "refine", **request})["state"] == "refine-open"

    def receive(data):
        return app.video_workflow.receive(project_id, io.BytesIO(data), len(data), request)

    assert receive(b"not an mp4")["state"] == "check-failed"
    (project / "concat.lock").touch()
    occupied = receive(raw)
    assert occupied["candidate"]["reviewNotice"] == "请先关闭 Concat 里的这个工程再回传。"
    assert port.read_refined_candidate(identity) is None
    assert len(list(world.workspace.glob("runs/*/returned-*/returned.mp4"))) == 2
    (project / "concat.lock").unlink()
    recorded = {}
    render, installed_app, _ = concat_double(Path(config["source"]), recorded, "ok")
    with render, installed_app:
        first = receive(raw)
        assert first["state"] == "returned" and first["uploaded"] is False
        receipt = port.read_refined_candidate(identity)
        assert receive(raw)["state"] == "returned"
    assert StudioSelectionPort(world.store, device_id=DEVICE, workspace=world.workspace).read_refined_candidate(identity) == receipt
    assert len(app.video_handoff_projection(project_id)["candidates"]) == 1
    assert not (world.store.local_workspace_path(project_id) / "candidate.json").exists()
    preview = world.workspace / receipt["preview_ref"]
    initial = preview.read_bytes()
    preview.write_bytes(initial + b"changed")
    with pytest.raises(RemoteError, match="video_refine_candidate_changed"):
        port.read_refined_candidate(identity)
    with pytest.raises(ProjectStoreError, match="候选预览不可用"):
        app.video_workflow.preview(project_id, first["candidates"][0]["previewUrl"].rsplit("/", 1)[-1])
    preview.write_bytes(initial)
    with pytest.raises(RemoteError, match="video_identity_stale"):
        port.refine_status({**identity, "binding_generation": 4})
    with pytest.raises(RemoteError, match="video_identity_stale"):
        port.read_refined_candidate({**identity, "video_identity": {
            **identity["video_identity"], "confirmedContentDigest": "sha256:" + "0" * 64}})

    remote["lose_preview"] = True
    world.remote_file.write_text(json.dumps(remote))
    assert watch(installed, config, world) == {"build": 0, "open": 0}
    expired = Media(world.remote_file)
    assert expired.job["state"] == "running" and expired.state["artifacts"].keys() == {"preview_mp4"}
    assert not expired.state.get("works")
    expired.advance(WAITING, lease_id=None, lease_expires_at=None)
    assert watch(installed, config, world) == {"build": 0, "open": 0}
    assert watch(installed, config, world) == {"build": 0, "open": 0}
    final = world.remote()
    assert final["job"]["state"] == "succeeded" and len(final["resumes"]) == 2
    [candidate] = final["works"][identity["job_id"]]
    saved = json.loads((world.workspace / receipt["candidate_ref"]).read_bytes())["candidate"]
    assert candidate["publicCandidateId"] == saved["publicCandidateId"]
    assert candidate["preview"]["shortEdge"] == 480
    assert base64.b64decode(final["artifacts"]["preview_mp4"]["content"]) == initial
    assert app.video_workflow.preview(project_id, candidate["publicCandidateId"]).read_bytes() == initial
    world.store.update_project(project_id, {"title": "已换版本"}, expected_revision=world.project["revision"])
    with pytest.raises(RemoteError, match="video_identity_stale"):
        port.read_refined_candidate(identity)


def test_built_concat_is_not_open_evidence_when_open_fails(installed, world):
    from media_ops.media_project_selection import StudioSelectionPort

    config = stage_fixture(world, "open-fails")
    assert watch(installed, config, world) == {"build": 1, "open": 1}
    remote = world.remote()
    assert remote["job"]["state"] == "blocked"
    assert "wait" not in remote and not remote.get("artifacts")
    port = StudioSelectionPort(world.store, device_id=DEVICE, workspace=world.workspace)
    assert port.refine_status(job_identity(remote["job"])) is None
    assert port.read_refined_candidate(job_identity(remote["job"])) is None


if __name__ == "__main__":
    run_installed(json.loads(sys.argv[1]))
