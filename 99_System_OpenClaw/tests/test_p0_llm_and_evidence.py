from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import llm_common  # noqa: E402


def load_script(name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


summary_module = load_script("05_write_content_summary.py", "content_summary_under_test")


class LLMAndEvidenceTests(unittest.TestCase):
    def test_codex_subprocess_is_utf8_and_receives_real_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "证据.png"
            image.write_bytes(b"png-evidence")

            def fake_run(args, **kwargs):
                self.assertEqual(kwargs["encoding"], "utf-8")
                self.assertEqual(kwargs["errors"], "replace")
                self.assertIn("--image", args)
                self.assertIn(str(image.resolve()), args)
                output = Path(args[args.index("-o") + 1])
                output.write_text("# 作品内容概述\n\n事实。\n", encoding="utf-8")
                class Completed:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return Completed()

            with patch.object(llm_common.shutil, "which", return_value="/fake/codex"), patch.object(llm_common.subprocess, "run", side_effect=fake_run):
                result = llm_common.generate_text_with_codex_cli(
                    system_prompt="系统",
                    user_prompt="中文输入",
                    image_paths=[image],
                    model="gpt-test",
                    reasoning_effort="high",
                )
            self.assertIn("作品内容概述", result)

    def test_image_paths_are_actual_project_files_and_evenly_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            paths = []
            for index in range(5):
                path = project / "_ai_analysis" / "keyframes" / f"{index}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"frame-{index}".encode())
                paths.append(path.relative_to(project).as_posix())
            outside = project.parent / "outside.jpg"
            outside.write_bytes(b"outside")
            item = {"media_id": "m1", "media_type": "video", "keyframes": [*paths, str(outside)]}
            selected = summary_module.item_image_paths(project, item, max_images=3)
            self.assertEqual(len(selected), 3)
            self.assertEqual(selected[0].name, "0.jpg")
            self.assertEqual(selected[-1].name, "4.jpg")
            self.assertNotIn(outside.resolve(), selected)

    def test_pending_transcript_is_not_reported_as_ok(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            transcript = project / "_ai_analysis" / "transcripts" / "m1.transcript.json"
            transcript.parent.mkdir(parents=True)
            transcript.write_text(json.dumps({"status": "pending", "segments": [], "text": "", "language": None}), encoding="utf-8")
            payload = summary_module.transcript_payload(project, {"media_id": "m1", "transcript_path": transcript.relative_to(project).as_posix(), "transcript_status": "pending"})
            self.assertEqual(payload["status"], "pending")

    def test_metadata_tier_never_calls_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.md"
            prompt.write_text("prompt", encoding="utf-8")
            output = root / "summary.md"
            with patch.object(summary_module, "generate_text", side_effect=AssertionError("model must not run")):
                source = summary_module.generate_item_summary(
                    root,
                    {"media_id": "m1", "media_type": "video", "duration_sec": 4, "has_audio": True},
                    prompt,
                    output,
                    model="gpt-test",
                    reasoning="high",
                    max_images=0,
                    tier="metadata",
                    cache_root=root / "cache",
                    ignore_cache=False,
                )
            self.assertEqual(source, "metadata")
            self.assertIn("没有调用语义模型", output.read_text(encoding="utf-8"))

    def test_multimodal_summary_cache_prevents_duplicate_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            image = project / "frame.jpg"
            image.write_bytes(b"frame-evidence")
            prompt = project / "prompt.md"
            prompt.write_text("prompt", encoding="utf-8")
            first = project / "first.md"
            second = project / "second.md"
            item = {"media_id": "m1", "media_type": "video", "keyframes": ["frame.jpg"], "analysis_cache_key": "sha256:asset"}
            seen = {}
            def fake_generate(**kwargs):
                seen["images"] = kwargs["image_paths"]
                return "# 作品内容概述\n\n基于实际附件。\n"
            with patch.object(summary_module, "generate_text", side_effect=fake_generate):
                source = summary_module.generate_item_summary(
                    project, item, prompt, first, model="gpt-test", reasoning="high",
                    max_images=3, tier="preview", cache_root=project / "cache", ignore_cache=False,
                )
            self.assertEqual(source, "model")
            self.assertEqual(seen["images"], [image.resolve()])
            with patch.object(summary_module, "generate_text", side_effect=AssertionError("cache should avoid model")):
                source = summary_module.generate_item_summary(
                    project, item, prompt, second, model="gpt-test", reasoning="high",
                    max_images=3, tier="preview", cache_root=project / "cache", ignore_cache=False,
                )
            self.assertEqual(source, "cache")
            self.assertEqual(first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
