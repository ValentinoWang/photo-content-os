"""Offline MCP fixtures and real lavfi -> OTIO -> melt -> integrity checks."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SYSTEM = Path(__file__).resolve().parents[1]
for path in (SYSTEM, SYSTEM / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from studio.chatcut_mcp import ChatCutMcp, LocalMcpSession, McpError
from edit_backends import chatcut_handoff as handoff, kdenlive_render as renderer
from media_common import file_sha256


class FakeSession:
    def __init__(self, tools):
        self.tools = tools
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def list_tools(self):
        self.calls.append(("tools/list", {}))
        return self.tools
    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"structuredContent": {"project": "fixture-project"}}


class LocalMcpTests(unittest.TestCase):
    def test_registration_without_handshake_never_connects(self):
        client = ChatCutMcp(executor=lambda *_: 0, handshake=lambda: False)
        client.probe()
        self.assertEqual(client.confirm_connection()["reason_code"], "handshake_failed")
        self.assertFalse(client.state["available"])

    def test_real_stdio_jsonrpc_initialize_list_call(self):
        server = '''import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 method=r['method']
 if method=='initialize': result={'protocolVersion':'2024-11-05','serverInfo':{'name':'fixture','version':'1'}}
 elif method=='tools/list': result={'tools':[{'name':'fixture_import','inputSchema':{'type':'object'}}]}
 else: result={'structuredContent':r['params']}
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':result}),flush=True)
'''
        config = {"transport": {"type": "stdio", "command": sys.executable, "args": ["-u", "-c", server]}}
        with LocalMcpSession(config) as session:
            process = session.process
            self.assertEqual(session.list_tools()[0]["name"], "fixture_import")
            self.assertEqual(session.call_tool("fixture_import", {"asset": "local"})["structuredContent"]["arguments"], {"asset": "local"})
        self.assertIsNotNone(process.poll())

    def test_nonlocal_transport_rejected_before_request(self):
        with self.assertRaisesRegex(McpError, "nonlocal"):
            with LocalMcpSession({"transport": {"type": "streamable_http", "url": "https://example.com/mcp"}}):
                self.fail("remote transport must not initialize")

    def test_initialize_failure_cleans_owned_process(self):
        session = LocalMcpSession({"transport": {"type": "stdio", "command": sys.executable,
                     "args": ["-u", "-c", "import sys;sys.exit(1)"]}}, timeout_seconds=0.5)
        with self.assertRaises(McpError):
            session.__enter__()
        self.assertIsNone(session.process)


class SuggestionTests(unittest.TestCase):
    def test_overlapping_cuts_union_and_frame_timing(self):
        ranges, _ = renderer.plan_ranges({"precision": "word", "suggestions": [
            {"type": "silence", "start": 1, "end": 2, "auto_cut_allowed": True},
            {"type": "repetition", "start": 1.5, "end": 2.5, "auto_cut_allowed": True}]}, 4)
        self.assertEqual(ranges, [{"source_start": 0, "source_end": 1, "output_start": 0},
                                  {"source_start": 2.5, "source_end": 4, "output_start": 1}])

    def test_sentence_repetition_is_review_only(self):
        raw = {"precision": "sentence", "suggestions": [{"type": "repetition", "start": 1, "end": 2, "auto_cut_allowed": False}]}
        ranges, ignored = renderer.plan_ranges(raw, 4)
        self.assertEqual(ranges[0]["source_end"], 4)
        self.assertEqual(len(ignored), 1)
        raw["suggestions"][0]["auto_cut_allowed"] = True
        with self.assertRaisesRegex(ValueError, "word_timing"):
            renderer.plan_ranges(raw, 4)

    def test_out_of_bounds_and_entire_source_cut_rejected(self):
        for end in (4, 5):
            with self.assertRaises(ValueError):
                renderer.plan_ranges({"suggestions": [{"type": "silence", "start": 0, "end": end, "auto_cut_allowed": True}]}, 4)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "original.mp4"
        self.source.write_bytes(b"original-fixture")
        self.subtitles = self.root / "source.srt"
        self.subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nfixture\n")
        self.suggestions = self.root / "edit.json"
        self.suggestions.write_text(json.dumps({"suggestions": []}))
        self.media_patch = patch.object(handoff, "probe_media", return_value={"format": {"duration": "4"}, "streams": [{"codec_type": "video", "duration": "4"}]})
        self.media_patch.start()
        self.package = self.root / "package"
        handoff.prepare_package(source=self.source, subtitles=self.subtitles, suggestions=self.suggestions,
                                animations=[], output_dir=self.package, project_id="fixture", project_revision=1)
    def tearDown(self):
        self.media_patch.stop()
        self.temp.cleanup()
    def test_offline_package_no_mcp_calls(self):
        self.assertEqual(handoff.execute_handoff(self.package, session_factory=lambda: self.fail("offline called MCP"))["message"], "等 ChatCut 登录")
        self.assertEqual(file_sha256(self.source), file_sha256(self.package / "original.mp4"))
    def bindings(self):
        schema1 = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}
        schema2 = {"type": "object", "properties": {"project": {"type": "string"}, "suggestions": {"type": "string"}}, "required": ["project", "suggestions"], "additionalProperties": False}
        tools = [{"name": "fixture_import", "inputSchema": schema1}, {"name": "fixture_precut", "inputSchema": schema2}]
        adapter = {
            "import": {"name": "fixture_import", "schema_sha256": handoff.schema_digest(schema1), "arguments": {"path": {"$input": "manifest_path"}}},
            "precut": {"name": "fixture_precut", "schema_sha256": handoff.schema_digest(schema2), "arguments": {"project": {"$result": "import.structuredContent.project"}, "suggestions": {"$input": "suggestions_path"}}}}
        return tools, adapter
    def test_connected_schema_bound_import_then_precut(self):
        tools, adapter = self.bindings()
        session = FakeSession(tools)
        result = handoff.execute_handoff(self.package, adapter=adapter, live=True, session_factory=lambda: session)
        self.assertEqual(result["status"], "candidate")
        self.assertEqual([name for name, _ in session.calls], ["tools/list", "fixture_import", "fixture_precut"])
        self.assertEqual(session.calls[-1][1]["project"], "fixture-project")
    def test_schema_drift_or_missing_tool_never_mutates(self):
        for missing in (False, True):
            tools, adapter = self.bindings()
            if missing:
                tools.pop()
            else:
                tools[0]["inputSchema"]["required"].append("new_required")
            session = FakeSession(tools)
            self.assertEqual(handoff.execute_handoff(self.package, adapter=adapter, live=True, session_factory=lambda: session)["status"], "failed")
            self.assertEqual(len(session.calls), 1)
    def test_registered_but_handshake_fails_keeps_login_path(self):
        def fail():
            raise McpError("mcp_timeout")
        result = handoff.execute_handoff(self.package, live=True, session_factory=fail)
        self.assertEqual(result["status"], "awaiting_chatcut_login")
        self.assertFalse(result["connection_verified"])
    def test_package_hash_tampering_blocks(self):
        (self.package / "original.mp4").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "integrity"):
            handoff.execute_handoff(self.package)
    def test_schema_required_and_type_checks(self):
        with self.assertRaises(Exception):
            handoff.validate_arguments({"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, {"path": 2})
        with self.assertRaisesRegex(ValueError, "external"):
            handoff.validate_arguments({"$ref": "https://example.com/schema"}, {})


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe") and renderer.melt_executable(), "real ffmpeg and melt required")
class MeltPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evidence_root = os.environ.get("PB_PIPELINE_EVIDENCE_ROOT")
        cls.temp = None if evidence_root else tempfile.TemporaryDirectory()
        cls.root = Path(evidence_root).resolve() if evidence_root else Path(cls.temp.name)
        if evidence_root:
            cls.root.mkdir(parents=True, exist_ok=False)
        cls.source = cls.root / "source.mp4"
        cls.animation = cls.root / "animation.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=30:d=4",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
                        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest", str(cls.source)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=320x180:r=30:d=0.5",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.animation)], check=True)
        cls.original_hash = file_sha256(cls.source)
        cls.suggestions = cls.root / "suggestions.json"
        cls.suggestions.write_text(json.dumps({"precision": "word", "suggestions": [
            {"type": "silence", "start": 0.8, "end": 1.3, "auto_cut_allowed": True},
            {"type": "repetition", "start": 2.5, "end": 3, "auto_cut_allowed": True},
            {"type": "animation", "start": 1.5, "end": 2, "animation_id": "lesson-1", "precision": "word", "ambiguous": False}]}))
        cls.subtitles = cls.root / "source.srt"
        cls.subtitles.write_text("1\n00:00:00,100 --> 00:00:00,700\nFixture caption\n\n2\n00:00:01,500 --> 00:00:02,300\nSecond caption\n\n3\n00:00:03,000 --> 00:00:03,800\nThird caption\n")
        cls.result = renderer.render(source=cls.source, suggestions_path=cls.suggestions,
                                     subtitles=cls.subtitles, animations=[{"path": str(cls.animation), "animation_id": "lesson-1"}],
                                     output_dir=cls.root / "render")
        cls.review = renderer.review_module()
    @classmethod
    def tearDownClass(cls):
        if cls.temp is not None:
            cls.temp.cleanup()
    def test_melt_candidate_passes_all_checks_with_sound_and_90_frames(self):
        self.assertEqual(self.result["status"], "candidate", self.result)
        self.assertEqual(self.result["frames"], 90)
        self.assertEqual(self.result["duration"], 3)
        self.assertEqual(self.result["removed_seconds"], 1)
        self.assertEqual(file_sha256(self.source), self.original_hash)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", self.result["output"], "-vn", "-f", "f32le", "-"], capture_output=True, check=True).stdout
        import array
        samples = array.array("f", pcm)
        self.assertGreater(math.sqrt(sum(v*v for v in samples)/len(samples)), 0.02)
    def test_overlay_and_subtitle_pixels_are_rendered(self):
        def frame(t):
            return subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", self.result["output"], "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        blue, red = frame(0), frame(1.2)
        self.assertGreater(blue[2], blue[0] + 100)
        self.assertGreater(red[0], red[2] + 100)
        caption = frame(0.3)
        self.assertGreater(sum(1 for i in range(0, len(caption), 3) if min(caption[i:i+3]) > 180), 10)
    def test_hash_mismatch_and_subtitle_nonmonotonic_reject(self):
        bad_srt = self.root / "bad.srt"
        bad_srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOne\n\n2\n00:00:00,500 --> 00:00:01,000\nTwo\n")
        result = self.review.check_output_video(Path(self.result["output"]), original_hashes={self.source: "0"*64}, subtitles=bad_srt)
        self.assertIn("input_hash_mismatch", result["error_codes"])
        self.assertIn("subtitle_nonmonotonic", result["error_codes"])
    def test_manifest_is_bound_to_actual_candidate_and_time_map(self):
        manifest = Path(self.result["manifest"])
        self.assertEqual(self.review.check_pipeline_manifest(manifest, expected_output=self.animation)["status"], "failed")
        raw = json.loads(manifest.read_text())
        raw["time_map"][0]["source_end"] = -1
        changed = self.root / "bad-manifest.json"
        changed.write_text(json.dumps(raw))
        self.assertEqual(self.review.check_pipeline_manifest(changed)["status"], "failed")

    def test_av_difference_at_boundary_passes_and_over_boundary_fails(self):
        base = renderer.probe_media(Path(self.result["output"]))
        for stream in base["streams"]:
            if stream["codec_type"] == "video":
                stream["duration"] = "3"
                stream["nb_read_frames"] = "90"
        real_run = subprocess.run
        def mocked_run(command, **kwargs):
            if command[0] == "ffprobe":
                return subprocess.CompletedProcess(command, 0, json.dumps(base), "")
            return real_run(command, **kwargs)
        for difference, expected in (("3.1", "passed"), ("3.100001", "failed")):
            for stream in base["streams"]:
                if stream["codec_type"] == "audio":
                    stream["duration"] = difference
            with patch.object(self.review.subprocess, "run", side_effect=mocked_run):
                result = self.review.check_output_video(Path(self.result["output"]), original_hashes={self.source: self.original_hash})
            av = next(item for item in result["checks"] if item["check"] == "av_duration")
            self.assertEqual(av["status"], expected)

    def test_frame_expectations_mismatch_reject(self):
        result = self.review.check_output_video(Path(self.result["output"]), original_hashes={self.source: self.original_hash}, expected_frames=100, expected_duration=4)
        self.assertIn("frame_count_mismatch", result["error_codes"])
        self.assertIn("duration_mismatch", result["error_codes"])
    def test_missing_audio_and_corrupt_file_reject(self):
        result = self.review.check_output_video(self.animation, original_hashes={self.source: self.original_hash})
        self.assertIn("audio_track_missing", result["error_codes"])
        bad = self.root / "corrupt.mp4"
        bad.write_bytes(b"bad video")
        result = self.review.check_output_video(bad, original_hashes={self.source: self.original_hash})
        self.assertIn("output_decode_failed", result["error_codes"])
    def test_output_directory_reuse_rejected(self):
        with self.assertRaisesRegex(ValueError, "already_exists"):
            renderer.render(source=self.source, suggestions_path=self.suggestions, output_dir=self.root / "render")


if __name__ == "__main__":
    unittest.main()
