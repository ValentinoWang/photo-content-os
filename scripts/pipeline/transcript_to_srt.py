#!/usr/bin/env python3
"""Convert an audio_transcript_v1 JSON file into a source-clock SRT subtitle file."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from edit_backends.editors.kdenlive_render import srt_timestamp

if __package__ and "." in __package__:
    from ..constants import (
        TRANSCRIPT_TO_SRT_SCHEMA_VERSION as SCHEMA_VERSION,
        DEFAULT_MAX_CHARS,
        DEFAULT_PAUSE_SECONDS,
    )
else:
    import sys as _sys
    from pathlib import Path as _Path
    _sdir = str(_Path(__file__).resolve().parents[1])
    if _sdir not in _sys.path:
        _sys.path.insert(0, _sdir)
    from constants import (
        TRANSCRIPT_TO_SRT_SCHEMA_VERSION as SCHEMA_VERSION,
        DEFAULT_MAX_CHARS,
        DEFAULT_PAUSE_SECONDS,
    )
_CLAUSE_END = re.compile(r"[。！？.!?;；，,]\s*$")
_CJK_SPACE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")


class TranscriptSrtError(ValueError):
    pass


def _finite_time(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise TranscriptSrtError(f"{label}_invalid")
    return float(value)


def _join_tokens(tokens: list[str]) -> str:
    parts: list[str] = []
    for raw in tokens:
        token = raw.strip()
        if not token:
            continue
        if parts and parts[-1][-1].isascii() and parts[-1][-1].isalnum() and token[0].isascii() and token[0].isalnum():
            parts.append(" " + token)
        else:
            parts.append(token)
    return _CJK_SPACE.sub("", "".join(parts)).strip()


def _cues_from_words(words: list[dict[str, Any]], *, max_chars: int, pause_seconds: float) -> list[tuple[float, float, str]]:
    cues: list[tuple[float, float, str]] = []
    group_tokens: list[str] = []
    group_start = 0.0
    group_end = 0.0
    previous_end = 0.0

    def flush() -> None:
        nonlocal group_tokens
        if not group_tokens:
            return
        text = _join_tokens(group_tokens)
        if text and round(group_end * 1000) > round(group_start * 1000):
            cues.append((group_start, group_end, text))
        group_tokens = []

    for word in words:
        if not isinstance(word, dict):
            raise TranscriptSrtError("transcript_word_invalid")
        start = _finite_time(word.get("start"), "word_start")
        end = _finite_time(word.get("end"), "word_end")
        text = word.get("text")
        if not isinstance(text, str) or not text.strip():
            raise TranscriptSrtError("transcript_word_text_invalid")
        if end <= start or start < previous_end - 1e-6:
            raise TranscriptSrtError("transcript_word_timing_invalid")
        candidate_text = _join_tokens([*group_tokens, text]) if group_tokens else _join_tokens([text])
        if group_tokens and (
            start - group_end >= pause_seconds - 1e-9
            or len(candidate_text) > max_chars
            or bool(_CLAUSE_END.search(group_tokens[-1]))
        ):
            flush()
        if not group_tokens:
            group_start = start
        group_tokens.append(text)
        group_end = end
        previous_end = end
    flush()
    return cues


def transcript_to_cues(
    document: dict[str, Any],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    pause_seconds: float = DEFAULT_PAUSE_SECONDS,
) -> list[tuple[float, float, str]]:
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise TranscriptSrtError("transcript_schema_invalid")
    if document.get("status") != "ok":
        raise TranscriptSrtError(f"transcript_not_ready:{document.get('status')}")
    if type(max_chars) is not int or max_chars < 1:
        raise TranscriptSrtError("max_chars_invalid")
    if isinstance(pause_seconds, bool) or not isinstance(pause_seconds, (int, float)) or not math.isfinite(pause_seconds) or pause_seconds <= 0:
        raise TranscriptSrtError("pause_seconds_invalid")
    segments = document.get("segments")
    if not isinstance(segments, list) or not segments:
        raise TranscriptSrtError("transcript_segments_missing")

    cues: list[tuple[float, float, str]] = []
    previous_end = 0.0
    for segment in segments:
        if not isinstance(segment, dict):
            raise TranscriptSrtError("transcript_segment_invalid")
        start = _finite_time(segment.get("start_sec"), "segment_start")
        end = _finite_time(segment.get("end_sec"), "segment_end")
        text = segment.get("text")
        if not isinstance(text, str):
            raise TranscriptSrtError("transcript_segment_text_invalid")
        if end < start or start < previous_end - 1e-6:
            raise TranscriptSrtError("transcript_segment_timing_invalid")
        words = segment.get("words")
        if isinstance(words, list) and words:
            segment_cues = _cues_from_words(words, max_chars=max_chars, pause_seconds=pause_seconds)
            if segment_cues and segment_cues[0][0] < previous_end - 1e-6:
                raise TranscriptSrtError("transcript_word_timing_invalid")
            cues.extend(segment_cues)
        else:
            cleaned = _CJK_SPACE.sub("", text).strip()
            if cleaned and round(end * 1000) > round(start * 1000):
                cues.append((start, end, cleaned))
        previous_end = end

    if not cues:
        raise TranscriptSrtError("transcript_has_no_subtitle_cues")
    return cues


def format_srt(cues: list[tuple[float, float, str]]) -> str:
    if not cues:
        raise TranscriptSrtError("transcript_has_no_subtitle_cues")
    return "\n\n".join(
        f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}"
        for index, (start, end, text) in enumerate(cues, 1)
    ) + "\n"


def convert_transcript_to_srt(
    transcript_path: Path,
    output_path: Path,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    pause_seconds: float = DEFAULT_PAUSE_SECONDS,
) -> dict[str, Any]:
    source = transcript_path.expanduser().resolve(strict=True)
    destination = output_path.expanduser().resolve()
    if destination == source:
        raise TranscriptSrtError("output_must_not_overwrite_input")
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TranscriptSrtError(f"transcript_unreadable:{exc}") from exc
    cues = transcript_to_cues(document, max_chars=max_chars, pause_seconds=pause_seconds)
    rendered = format_srt(cues)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, suffix=".srt.tmp", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(rendered)
            stream.close()
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return {"status": "ok", "cue_count": len(cues), "output": str(destination)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path, help="Input audio_transcript_v1 JSON file")
    parser.add_argument("--output", required=True, type=Path, help="Destination SRT file")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--pause-seconds", type=float, default=DEFAULT_PAUSE_SECONDS)
    args = parser.parse_args(argv)
    try:
        receipt = convert_transcript_to_srt(
            args.transcript,
            args.output,
            max_chars=args.max_chars,
            pause_seconds=args.pause_seconds,
        )
    except (TranscriptSrtError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
