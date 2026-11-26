"""Studio returns a Concat export by reading the saved Concat project (stand-in backend, no real Concat)."""
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_backends.interface import BackendError
from media_project_selection import RefineRun
from unittest.mock import patch
from test_ps4_kdenlive_readback import movie
import test_ps_studio_handoff as fixture_module


class FakeConcat:
    """Same surface as the Concat backend; the readback is whatever the test saved."""

    def __init__(self, readback=None, error=None):
        self.readback, self.error = readback, error

    def describe(self):
        return {"id": "concat", "display_name": "Concat"}

    def read_back(self, *, project_dir):
        if self.error:
            raise self.error
        return self.readback

    def close(self):
        return {"id": "concat", "started_pids": [], "remaining_pids": []}


class ConcatReturnTests(unittest.TestCase):
    setUp = fixture_module.StudioHandoffTests.setUp
    write = staticmethod(fixture_module.StudioHandoffTests.write)

    def prepare(self, backend, *, project_revision=1, project_id=None):
        source = self.media / "source.mp4"
        movie(source)
        self.identity = fixture_module.deliver_fixture(self.app, self.media, self.identity)
        directory = self.run / "editor"
        (directory / "concat-project").mkdir(parents=True)
        (directory / "concat-project" / "concat.json").write_text("{}", encoding="utf-8")
        self.app.video_editor_choice(self.project["id"], {"editor": "concat", "method": "external", "revision": 1})
        # The saved timeline keeps 0-1 s and 2-4 s of the 4 s source: 3 s, one cut.
        readback = {"time_map": [{"source_start": 0, "source_end": 1, "output_start": 0},
                                 {"source_start": 2, "source_end": 4, "output_start": 1}],
                    "captions": [{"start": 0, "end": 3, "text": "合成口播"}], "animations": [],
                    "duration": 3.0, "fps": 30.0, "engine_revision": "digest",
                    "render_kwargs": {"source": source, "project_id": project_id or self.project["id"],
                                      "project_revision": project_revision}}
        fake = backend(readback)
        ctx = self.app.video_workflow.context(self.project["id"], identity=self.identity, delivered_only=True)
        run = RefineRun(ctx)
        run.record_opened(directory / "concat-project", {"editor_backend": "concat", "opened": True},
                          run.digest_file(source))
        substitute = patch("studio.video_workflow.get_backend", return_value=fake)
        substitute.start()
        self.addCleanup(substitute.stop)
        return directory

    def upload(self, seconds=3):
        exported = self.media / "exported.mp4"
        movie(exported, seconds)
        raw = exported.read_bytes()
        return self.app.video_workflow.receive(self.project["id"], io.BytesIO(raw), len(raw),
                                               {"identity": self.identity, "expectedRevision": 1})

    def test_readback_success_records_a_native_candidate(self):
        self.prepare(lambda readback: FakeConcat(readback))
        data = self.upload()
        assert data["state"] == "returned"
        c = json.loads((self.run / "studio-candidate.json").read_text())["candidate"]
        assert c["provenance"] == "native_readback" and c["editor"]["toolId"] == "concat"
        assert c["cutCount"] == 1 and c["cuts"][0]["kind"] == "retake"
        assert c["checks"]["frameCount"] == "pass" and c["checks"]["expectedFrames"] == 90
        assert c["checks"]["subtitles"] == "pass" and "合成口播" in c["subtitles"]

    def test_project_identity_mismatch_is_check_failed(self):
        self.prepare(lambda readback: FakeConcat(readback), project_revision=2)
        data = self.upload()
        assert data["state"] == "check-failed"
        assert "关闭 Concat" not in data["candidate"].get("reviewNotice", "")
        assert not (self.run / "studio-candidate.json").exists()

    def test_refused_readback_asks_to_close_the_project(self):
        refused = BackendError("concat_tool_error:project_open:refused: project is open in a window")
        self.prepare(lambda readback: FakeConcat(error=refused))
        data = self.upload()
        assert data["state"] == "check-failed"
        assert data["candidate"]["status"] == "check_failed"
        assert data["candidate"]["reviewNotice"] == "请先关闭 Concat 里的这个工程再回传。"
        assert not (self.run / "studio-candidate.json").exists()

    def test_window_lock_is_refused_before_reading(self):
        directory = self.prepare(lambda readback: FakeConcat(readback))
        (directory / "concat-project" / "concat.lock").write_text("", encoding="utf-8")
        data = self.upload()
        assert data["state"] == "check-failed"
        assert data["candidate"]["reviewNotice"] == "请先关闭 Concat 里的这个工程再回传。"


if __name__ == "__main__":
    unittest.main()
