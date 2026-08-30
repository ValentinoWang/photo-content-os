from __future__ import annotations

import json
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
