"""Tests for converting audio_transcript_v1 JSON into source-clock SRT."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import review_output_video as review
import transcript_to_srt as tts


def _word_transcript(words: list[dict], *, text: str | None = None) -> dict:
    start = words[0]["start"] if words else 0.0
    end = words[-1]["end"] if words else 0.0
    joined = text if text is not None else " ".join(w["text"] for w in words)
    return {
        "schema_version": "audio_transcript_v1",
        "media_id": "m1",
        "audio_ref": "ai-analysis/audio/m1.wav",
        "provider": "funasr",
        "model": "paraformer-zh",
        "language": "zh",
        "status": "ok",
        "segments": [
            {
                "start_sec": start,
                "end_sec": end,
                "speaker": None,
                "text": joined,
                "confidence": None,
                "words": words,
                "precision": "word",
            }
        ],
        "text": joined,
        "words": words,
        "precision": "word",
        "auto_cut_allowed": True,
    }


def test_word_transcript_splits_on_pauses_and_max_chars_and_roundtrips_srt(tmp_path):
    doc = _word_transcript([
        {"start": 2.97, "end": 3.21, "text": "上"},
        {"start": 3.55, "end": 3.75, "text": "高"},
        {"start": 3.75, "end": 3.99, "text": "铁"},
        {"start": 3.99, "end": 4.23, "text": "啊"},
        # 1.2s pause -> new cue
        {"start": 5.43, "end": 5.59, "text": "打"},
        {"start": 5.59, "end": 5.83, "text": "算"},
        {"start": 6.03, "end": 6.13, "text": "马"},
        {"start": 6.13, "end": 6.37, "text": "上"},
        {"start": 6.37, "end": 6.49, "text": "去"},
        {"start": 6.49, "end": 6.59, "text": "酒"},
        {"start": 6.59, "end": 6.83, "text": "店"},
    ])
    transcript_path = tmp_path / "m1.transcript.json"
    transcript_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "source.srt"

    receipt = tts.convert_transcript_to_srt(transcript_path, output_path, max_chars=5, pause_seconds=0.4)
    assert receipt == {"status": "ok", "cue_count": 3, "output": str(output_path.resolve())}

    cues = [(round(a, 3), round(b, 3), text) for a, b, text in review.read_srt_cues(output_path)]
    assert cues == [
        (2.97, 4.23, "上高铁啊"),
        (5.43, 6.49, "打算马上去"),
        (6.49, 6.83, "酒店"),
    ]


def test_word_transcript_keeps_ascii_word_spaces_and_splits_clause_punctuation():
    doc = _word_transcript([
        {"start": 0.1, "end": 0.3, "text": "Concat"},
        {"start": 0.3, "end": 0.6, "text": "CLI"},
        {"start": 0.6, "end": 0.9, "text": "很稳。"},
        {"start": 0.9, "end": 1.2, "text": "继续"},
    ])
    cues = tts.transcript_to_cues(doc, max_chars=20, pause_seconds=0.4)
    assert cues == [
        (0.1, 0.9, "Concat CLI很稳。"),
        (0.9, 1.2, "继续"),
    ]


def test_sentence_transcript_without_words_falls_back_to_segments():
    doc = {
        "schema_version": "audio_transcript_v1",
        "media_id": "m2",
        "audio_ref": "ai-analysis/audio/m2.wav",
        "provider": "sidecar",
        "model": "sidecar-v1",
        "language": "zh",
        "status": "ok",
        "segments": [
            {"start_sec": 0.5, "end_sec": 2.0, "speaker": None, "text": "今 天 拍 了 一 条", "confidence": None, "words": [], "precision": "sentence"},
            {"start_sec": 2.5, "end_sec": 4.0, "speaker": None, "text": "Hello world", "confidence": None, "words": [], "precision": "sentence"},
        ],
        "text": "今 天 拍 了 一 条\nHello world",
        "words": [],
        "precision": "sentence",
        "auto_cut_allowed": False,
    }
    cues = tts.transcript_to_cues(doc)
    assert cues == [
        (0.5, 2.0, "今天拍了一条"),
        (2.5, 4.0, "Hello world"),
    ]


@pytest.mark.parametrize("bad_doc,match", [
    ({"schema_version": "other", "status": "ok", "segments": []}, "transcript_schema_invalid"),
    ({"schema_version": "audio_transcript_v1", "status": "pending", "segments": []}, "transcript_not_ready"),
    ({"schema_version": "audio_transcript_v1", "status": "ok", "segments": []}, "transcript_segments_missing"),
])
def test_invalid_transcripts_are_rejected(bad_doc, match):
    with pytest.raises(tts.TranscriptSrtError, match=match):
        tts.transcript_to_cues(bad_doc)


def test_cli_runs_and_refuses_to_overwrite_input(tmp_path):
    doc = _word_transcript([
        {"start": 0.2, "end": 0.5, "text": "你"},
        {"start": 0.5, "end": 0.8, "text": "好"},
    ])
    src = tmp_path / "in.transcript.json"
    out = tmp_path / "out.srt"
    src.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    ok = subprocess.run(
        [sys.executable, str(SCRIPTS / "transcript_to_srt.py"), str(src), "--output", str(out)],
        capture_output=True, text=True, check=False,
    )
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["cue_count"] == 1
    assert review.read_srt_cues(out) == [(0.2, 0.8, "你好")]

    rejected = subprocess.run(
        [sys.executable, str(SCRIPTS / "transcript_to_srt.py"), str(src), "--output", str(src)],
        capture_output=True, text=True, check=False,
    )
    assert rejected.returncode != 0
    assert "output_must_not_overwrite_input" in rejected.stderr
