"""Local Paraformer acoustic units must align before authorizing automatic cuts."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from _support import load_script


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
transcribe = load_script("pipeline/transcribe_audio.py", "r226_transcribe")


def local_document(payload):
    client = Mock()
    client.generate.return_value = [payload]
    factory = Mock(return_value=client)
    with patch.dict(sys.modules, {"funasr": SimpleNamespace(AutoModel=factory)}):
        provider = transcribe.FunASRProvider("paraformer-zh")
        result = provider.transcribe(Path("synthetic.wav"), language="zh")
    document = transcribe.transcript_document(
        media_id="synthetic", audio_ref="synthetic.wav", provider=result["provider"],
        model=result["model"], language=result["language"], segments=result["segments"],
    )
    return document, client, factory


def test_local_model_surface_units_keep_acoustic_gaps_and_seconds():
    payload = {"text": "今 天 出 发", "timestamp": [[350, 500], [500, 800], [1150, 1300], [1300, 1550]]}
    document, client, factory = local_document(payload)
    assert document["words"] == [
        {"start": .35, "end": .5, "text": "今"},
        {"start": .5, "end": .8, "text": "天"},
        {"start": 1.15, "end": 1.3, "text": "出"},
        {"start": 1.3, "end": 1.55, "text": "发"},
    ]
    assert document["precision"] == "word"
    assert document["auto_cut_allowed"] is True
    assert document["text"] == payload["text"]
    assert document["segments"][0]["start_sec"] == .35
    assert document["segments"][0]["end_sec"] == 1.55
    assert document["words"][2]["start"] - document["words"][1]["end"] == pytest.approx(.35)
    assert "raw_text" not in payload  # Do not mutate the provider response.
    factory.assert_called_once_with(model="paraformer-zh", disable_update=True)
    assert client.generate.call_args.kwargs["output_timestamp"] is True


@pytest.mark.parametrize("text,timestamps,expected", [
    ("去 OpenAI 上 班", [[0, 100], [100, 400], [700, 800], [800, 900]], ["去", "OpenAI", "上", "班"]),
    ("hello world", [[0, 400], [700, 900]], ["hello", "world"]),
    ("好", [[100, 300]], ["好"]),
])
def test_units_are_not_split_into_display_characters(text, timestamps, expected):
    document, _, _ = local_document({"text": text, "timestamp": timestamps})
    assert [word["text"] for word in document["words"]] == expected
    assert document["precision"] == "word"
    assert document["auto_cut_allowed"] is True


@pytest.mark.parametrize("payload", [
    {"text": "今天", "timestamp": [[0, 200], [200, 400]]},
    {"text": "今 天", "timestamp": [[0, 400]]},
    {"text": "今天", "raw_text": "今 错", "timestamp": [[0, 200], [200, 400]]},
    {"text": "今天", "raw_text": "今 天 天", "timestamp": [[0, 200], [200, 400]]},
    {"text": "今 天", "raw_text": "", "timestamp": [[0, 200], [200, 400]]},
    {"text": "今 天"},
    {"text": "今 天", "timestamp": []},
    {"sentence_info": [{"text": "今天", "start": 0, "end": 400,
                        "raw_text": "今 错", "timestamp": [[0, 200], [200, 400]]}]},
])
def test_unaligned_or_missing_units_stay_chunk(payload):
    document, _, _ = local_document(payload)
    assert document["words"] == []
    assert document["precision"] == "chunk"
    assert document["auto_cut_allowed"] is False


def test_explicit_raw_tokens_still_take_precedence():
    document, _, _ = local_document({"text": "今天，出发。", "raw_text": "今 天 出 发",
                                   "timestamp": [[0, 100], [100, 200], [500, 600], [600, 900]]})
    assert document["text"] == "今天，出发。"
    assert [word["text"] for word in document["words"]] == ["今", "天", "出", "发"]
    assert document["auto_cut_allowed"] is True


@pytest.mark.parametrize("intervals", [
    [[0, 200], [100, 400]], [[0, 200], [400, 300]],
    [[-100, 200], [200, 400]], [[0, 200], [200, float("nan")]],
    [[0, 200], [True, 400]], [[0, 200], [200]],
])
def test_invalid_acoustic_intervals_are_rejected(intervals):
    with pytest.raises(transcribe.TranscriptionError):
        local_document({"text": "今 天", "timestamp": intervals})


def test_untrusted_normalization_does_not_infer_raw_tokens():
    result = transcribe.normalize_asr_payload({"text": "今 天", "timestamp": [[0, 100], [100, 200]]}, local=True)
    assert result["segments"][0]["words"] == []
