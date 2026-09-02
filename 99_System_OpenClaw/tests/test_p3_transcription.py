from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from _support import load_script


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
sys.path.insert(0, str(SCRIPTS))

module = load_script("03_transcribe_audio.py", "transcription_under_test")


class TranscriptionTests(unittest.TestCase):
    def test_srt_parsing_and_schema(self):
        segments = module.parse_srt("1\n00:00:00,000 --> 00:00:01,250\n你好\n\n2\n00:00:01,250 --> 00:00:03,000\n世界\n")
        document = module.transcript_document(
            media_id="m1",
            audio_ref="_ai_analysis/audio/m1.wav",
            provider="sidecar",
            model="sidecar-v1",
            language="zh",
            segments=segments,
        )
        self.assertEqual(document["status"], "ok")
        self.assertEqual(document["segments"][1]["start_sec"], 1.25)
        schema = json.loads((SCHEMAS / "audio_transcript.schema.json").read_text(encoding="utf-8"))
        self.assertIn(document["status"], schema["properties"]["status"]["enum"])
        self.assertTrue(set(schema["required"]).issubset(document))

    def test_pending_provider_is_explicit(self):
        document = module.transcript_document(
            media_id="m1",
            audio_ref="a.wav",
            provider="pending",
            model="none",
            language=None,
            segments=[],
        )
        self.assertEqual(document["status"], "pending")
        self.assertEqual(document["text"], "")

    def test_sidecar_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "a.wav"
            audio.write_bytes(b"wave")
            (root / "a.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\n真实对白\n", encoding="utf-8")
            result = module.SidecarProvider().transcribe(audio)
            self.assertEqual(result["segments"][0]["text"], "真实对白")

    def test_dashscope_request_contract_and_missing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "a.wav"
            audio.write_bytes(b"wave")
            body, boundary = module.DashscopeProvider._multipart(audio, model="paraformer-v2", language="zh")
            self.assertIn(b'name="model"', body)
            self.assertIn(b'filename="a.wav"', body)
            self.assertTrue(boundary.startswith("----OpenClawMedia"))
        previous = os.environ.pop("DASHSCOPE_API_KEY", None)
        try:
            with self.assertRaisesRegex(module.TranscriptionError, "DASHSCOPE_API_KEY"):
                module.DashscopeProvider("paraformer-v2")
            self.assertEqual(module.build_provider("dashscope", model="paraformer-v2", sidecar_dir=None).name, "dashscope")
        finally:
            if previous is not None:
                os.environ["DASHSCOPE_API_KEY"] = previous

    def test_dashscope_sentence_info_is_always_milliseconds(self):
        previous = os.environ.get("DASHSCOPE_API_KEY")
        os.environ["DASHSCOPE_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as directory:
                audio = Path(directory) / "a.wav"
                audio.write_bytes(b"wave")

                class Response:
                    def __enter__(self): return self
                    def __exit__(self, *_): return False
                    def read(self): return '{"sentence_info":[{"start":250,"end":900,"text":"短句"}]}'.encode("utf-8")

                with patch.object(module.urllib.request, "urlopen", return_value=Response()):
                    result = module.DashscopeProvider("paraformer-v2").transcribe(audio)
                self.assertEqual(result["segments"][0]["start_sec"], 0.25)
                self.assertEqual(result["segments"][0]["end_sec"], 0.9)
        finally:
            if previous is None:
                os.environ.pop("DASHSCOPE_API_KEY", None)
            else:
                os.environ["DASHSCOPE_API_KEY"] = previous

    def test_dashscope_uses_funasr_after_provider_failure(self):
        previous = os.environ.get("DASHSCOPE_API_KEY")
        os.environ["DASHSCOPE_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as directory:
                audio = Path(directory) / "a.wav"
                audio.write_bytes(b"wave")

                class LocalFunASR:
                    name = "funasr"
                    model = "paraformer-zh"
                    def __init__(self, *_): pass
                    def transcribe(self, *_args, **_kwargs):
                        return {"language": "zh", "segments": [{"start_sec": 0, "end_sec": 1, "text": "本机结果"}]}

                with patch.object(module.DashscopeProvider, "transcribe", side_effect=module.TranscriptionError("network")):
                    with patch.object(module, "FunASRProvider", LocalFunASR):
                        result = module.build_provider("dashscope", model="paraformer-v2", sidecar_dir=None).transcribe(audio)
                self.assertEqual(result["segments"][0]["text"], "本机结果")
        finally:
            if previous is None:
                os.environ.pop("DASHSCOPE_API_KEY", None)
            else:
                os.environ["DASHSCOPE_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
