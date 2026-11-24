import hashlib
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts/aigc/dreamverse_bridge.py"
PROVIDER = ROOT / "integrations/dreamverse/wanxiang-provider"
SECRET = "fake-provider-credential-must-never-escape"
VIDEO, STILL = b"sample video", b"sample last frame"


@pytest.fixture
def dreamverse(tmp_path):
    tasks, renders, events = {}, {}, []
    blocked = set()
    lose_submit_response = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, value, status=200):
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/dv/assets/"):
                self.reply(VIDEO if self.path.endswith(hashlib.sha256(VIDEO).hexdigest()) else STILL)
            elif self.path == "/api/dv/projects":
                self.reply([])
            else:
                self.reply({"error": SECRET}, 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            route = self.path
            if route == "/api/dv/projects":
                self.reply({"id": "project-1", "title": body["title"]})
            elif route == "/api/dv/operation/check":
                self.reply({"problems": []})
            elif route == "/api/dv/wanxiang/submit":
                key, shot = body["key"], body["shot_id"]
                assert key not in tasks
                events.append(("submit", shot, key))
                tasks[key] = shot
                if shot in lose_submit_response:
                    self.close_connection = True
                    self.send_response(200)
                    self.send_header("Content-Length", "200")
                    self.end_headers()
                    self.wfile.write(b'{"task_id":')
                    return
                self.reply({"task_id": f"task-{shot}", "status": "submitted"})
            elif route == "/api/dv/wanxiang/status":
                shot = tasks[body["key"]]
                assert ledger(tmp_path)["shots"][shot]["task_id"] == body["task_id"]
                events.append(("poll", shot, body["key"]))
                if shot in blocked:
                    self.reply({"status": "RUNNING", "task_id": f"task-{shot}", "debug": SECRET})
                else:
                    self.reply({"status": "SUCCEEDED", "task_id": f"task-{shot}", "billed_video_seconds": 5})
            elif route == "/api/dv/wanxiang/receipt":
                shot = tasks.get(body["key"])
                if shot in lose_submit_response:
                    self.reply({"error": SECRET}, 502)
                else:
                    self.reply({"status": "missing"})
            elif route == "/api/dv/operation":
                key = body["params"]["extra"]["bridge_confirmation"]
                events.append(("render", tasks[key], key))
                outputs = [hashlib.sha256(value).hexdigest() for value in (VIDEO, STILL)]
                record = {"id": f"render-{tasks[key]}", "intent": body["intent"], "status": "done", "outputs": outputs}
                renders[record["id"]] = record
                self.reply(record)
            elif route == "/api/dv/history":
                self.reply({"entries": [{"record": item} for item in renders.values()]})
            else:
                self.reply({"error": SECRET}, 404)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", events, blocked, lose_submit_response
        finally:
            server.shutdown()
            worker.join()


def run_bridge(tmp_path, dreamverse, shots, *options):
    manifest = tmp_path / "shots.json"
    manifest.write_text(json.dumps({"shots": shots}), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(BRIDGE), str(manifest), str(tmp_path / "output"),
         "--url", dreamverse[0], "--poll-interval", "0.01", "--wait-seconds", "0.25", *options],
        capture_output=True, text=True, timeout=10,
    )


def shot(name, **changes):
    return {"shot_id": name, "prompt": name, "seconds": 5, "aspect_ratio": "9:16", **changes}


def ledger(tmp_path):
    return json.loads((tmp_path / "output/ledger.json").read_text())


def test_provider_manifest_and_official_model_facts():
    manifest = json.loads((PROVIDER / "package.json").read_text())
    facts = json.loads((PROVIDER / "model-facts.json").read_text())
    assert manifest["name"] == "@dv/wanxiang-provider"
    assert (PROVIDER / manifest["exports"]).is_file()
    assert facts["modelId"] == "wan2.6-t2v"
    assert facts["durationsSec"] == list(range(2, 16))
    assert facts["aspectRatios"] == ["16:9", "9:16", "1:1", "4:3", "3:4"]
    assert facts["resolutions"] == ["1080p", "720p"]
    assert facts["frameSizes"] == {
        "16:9": {"720p": [1280, 720], "1080p": [1920, 1080]},
        "9:16": {"720p": [720, 1280], "1080p": [1080, 1920]},
        "1:1": {"720p": [960, 960], "1080p": [1440, 1440]},
        "4:3": {"720p": [1088, 832], "1080p": [1632, 1248]},
        "3:4": {"720p": [832, 1088], "1080p": [1248, 1632]},
    }


def test_install_links_provider_and_keeps_existing_profile(tmp_path):
    launch = tmp_path / "app/scripts/video-harness/launch.sh"
    launch.parent.mkdir(parents=True)
    launch.touch()
    profile = tmp_path / "state/profiles/video-harness"
    profile.mkdir(parents=True)
    (profile / "cordis.yml").write_text("[]\n")
    patch = profile / "cordis.patch.yml"
    original = "- id: existing-plugin\n  disabled: true\n"
    patch.write_text(original)
    command = ["bash", str(PROVIDER.parent / "install.sh"), str(tmp_path), "--max-submissions", "2"]
    subprocess.run(command, check=True, capture_output=True)
    installed = patch.read_text()
    subprocess.run(command, check=True, capture_output=True)
    assert patch.read_text() == installed
    assert installed.startswith(original)
    assert installed.count("id: dv-wanxiang-provider") == 1
    assert "maxSubmissions: 2" in installed
    assert (profile / "node_modules/@dv/wanxiang-provider").resolve() == PROVIDER


def test_restart_polls_existing_task_without_reconfirming(tmp_path, dreamverse):
    _, events, blocked, _ = dreamverse
    shots = [shot("first"), shot("second", seconds=14, aspect_ratio="4:3", resolution="1080p")]
    blocked.add("second")
    refused = run_bridge(tmp_path, dreamverse, shots)
    assert refused.returncode != 0
    assert not events
    interrupted = run_bridge(tmp_path, dreamverse, shots, "--confirm", "first", "--confirm", "second")
    assert interrupted.returncode != 0, interrupted.stderr
    before = ledger(tmp_path)["shots"]
    assert before["first"]["status"] == "completed"
    assert before["second"]["task_id"] == "task-second"
    assert before["second"]["status"] == "running"
    blocked.clear()

    resumed = run_bridge(tmp_path, dreamverse, shots)
    assert resumed.returncode == 0, resumed.stderr
    after = ledger(tmp_path)["shots"]
    assert after["first"] == before["first"]
    assert [name for event, name, _ in events if event == "submit"] == ["first", "second"]
    assert len([key for event, name, key in events if event == "poll" and name == "second"]) >= 2
    assert after["second"]["status"] == "completed"
    assert after["second"]["task_id"] == before["second"]["task_id"]
    assert after["second"]["billed_video_seconds"] == 5
    assert Path(after["second"]["mp4_path"]).read_bytes() == VIDEO
    assert Path(after["second"]["last_frame_path"]).read_bytes() == STILL
    assert after["second"]["dreamverse_video_asset_id"] == hashlib.sha256(VIDEO).hexdigest()
    assert after["second"]["timeline_clip_id"] is None
    assert SECRET not in json.dumps(after) + interrupted.stderr + resumed.stderr


def test_unknown_submission_never_repeats_and_does_not_log_body(tmp_path, dreamverse):
    _, events, _, lose_response = dreamverse
    lose_response.add("uncertain")
    shots = [shot("uncertain")]
    for _ in range(2):
        result = run_bridge(tmp_path, dreamverse, shots, "--confirm", "uncertain")
        assert result.returncode != 0
        assert SECRET not in result.stdout + result.stderr
        assert ledger(tmp_path)["shots"]["uncertain"]["status"] == "unknown"
    assert [event for event, _, _ in events] == ["submit"]
    assert SECRET not in (tmp_path / "output/ledger.json").read_text()


def test_changed_specification_requires_new_confirmation(tmp_path, dreamverse):
    original = run_bridge(tmp_path, dreamverse, [shot("first")], "--confirm", "first")
    assert original.returncode == 0, original.stderr
    first_key = ledger(tmp_path)["shots"]["first"]["confirmation_key"]
    changed = [shot("first", seconds=10)]
    assert run_bridge(tmp_path, dreamverse, changed).returncode != 0
    assert ledger(tmp_path)["shots"]["first"]["confirmation_key"] == first_key
    result = run_bridge(tmp_path, dreamverse, changed, "--confirm", "first")
    assert result.returncode == 0, result.stderr
    assert ledger(tmp_path)["shots"]["first"]["confirmation_key"] != first_key
    assert [event for event, _, _ in dreamverse[1]].count("submit") == 2


def test_invalid_later_specification_blocks_entire_batch(tmp_path, dreamverse):
    shots = [shot("first"), shot("second", seconds=16, resolution="4k")]
    result = run_bridge(tmp_path, dreamverse, shots, "--confirm", "first", "--confirm", "second")
    assert result.returncode != 0
    assert "second" in result.stderr
    assert not dreamverse[1]
