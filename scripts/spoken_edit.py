#!/usr/bin/env python3
"""Produce local, reviewable edit candidates without editing the source media.

Animation input is a JSON array of {animation_id, spoken_text} objects. All
times are seconds on the original source clock. ``cut`` is null unless exact
acoustic word timing permits a downstream editor to propose that range.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import tempfile
from bisect import bisect_left
from pathlib import Path
from typing import Any


_spec = importlib.util.spec_from_file_location("spoken_transcription", Path(__file__).with_name("transcribe_audio.py"))
assert _spec and _spec.loader
_transcription = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_transcription)
text_key = _transcription.text_key


class SuggestionError(ValueError):
    pass


def positive_number(value: Any, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SuggestionError(f"{name} must be finite")
    if value < 0 or (value == 0 and not allow_zero):
        raise SuggestionError(f"{name} must be positive")
    return float(value)


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_duration(audio: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index,duration:format=duration", "-of", "json", str(audio)],
        check=True, capture_output=True, text=True, timeout=60)
    payload = json.loads(result.stdout)
    if len(payload.get("streams", [])) != 1:
        raise SuggestionError("source must have an audio stream")
    stream_duration = payload["streams"][0].get("duration")
    if stream_duration not in (None, "N/A"):
        return positive_number(float(stream_duration), "audio duration")
    # Containers can have a longer video clock. Decode only the selected audio
    # when the stream has no duration instead of adopting that container clock.
    with tempfile.TemporaryDirectory(prefix="spoken-audio-probe-") as directory:
        decoded = Path(directory) / "audio.flac"
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(audio), "-map", "0:a:0",
                        "-vn", "-c:a", "flac", str(decoded)], check=True, capture_output=True,
                       timeout=max(60, float(payload["format"]["duration"]) * 2))
        return probe_duration(decoded)


def parse_silences(log: str, *, duration: float, min_duration: float) -> list[tuple[float, float]]:
    """Read FFmpeg's measured intervals, including trailing digital silence."""
    duration = positive_number(duration, "duration")
    min_duration = positive_number(min_duration, "minimum silence duration")
    intervals = []
    start = None
    for match in re.finditer(r"silence_(start|end):\s*([0-9.eE+-]+)", log):
        event, raw_time = match.groups()
        timestamp = positive_number(float(raw_time), "silence time", allow_zero=True)
        if timestamp > duration + 0.001:
            raise SuggestionError("silence time exceeds the source duration")
        timestamp = min(timestamp, duration)
        if event == "start":
            if start is not None:
                raise SuggestionError("overlapping silence events")
            start = timestamp
        else:
            if start is None or timestamp < start:
                raise SuggestionError("unordered silence events")
            if timestamp - start + 1e-9 >= min_duration:
                intervals.append((start, timestamp))
            start = None
    if start is not None and duration - start + 1e-9 >= min_duration:
        intervals.append((start, duration))
    if any(current[0] < previous[1] for previous, current in zip(intervals, intervals[1:])):
        raise SuggestionError("silence intervals are unordered")
    return intervals


def detect_silences(audio: Path, *, threshold_db: float = -35, min_duration: float = 0.4,
                    duration: float | None = None) -> list[tuple[float, float]]:
    if isinstance(threshold_db, bool) or not math.isfinite(threshold_db) or threshold_db > 0:
        raise SuggestionError("silence threshold must be finite and at most 0 dB")
    positive_number(min_duration, "minimum silence duration")
    duration = probe_duration(audio) if duration is None else duration
    result = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(audio),
        "-map", "0:a:0", "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration}",
        "-f", "null", "-"], check=True, capture_output=True, text=True, timeout=max(60, duration * 2))
    return parse_silences(result.stderr, duration=duration, min_duration=min_duration)


def validate_transcript(document: dict[str, Any], *, duration: float) -> dict[str, Any]:
    if not isinstance(document, dict) or not isinstance(document.get("segments"), list):
        raise SuggestionError("a transcript with segments is required")
    normalized = _transcription.transcript_document(
        media_id=document.get("media_id", "local"), audio_ref=document.get("audio_ref", "local"),
        provider=document.get("provider", "sidecar"), model=document.get("model", "fixture"),
        language=document.get("language"), segments=document["segments"], words=document.get("words"))
    # Downstream consumers must not trust a forged precision or permission flag.
    for key in ("precision", "auto_cut_allowed"):
        if key in document and document[key] != normalized[key]:
            raise SuggestionError(f"transcript {key} disagrees with acoustic evidence")
    if any(segment["end_sec"] > duration + 0.001 for segment in normalized["segments"]):
        raise SuggestionError("transcript exceeds the source duration")
    return normalized


def candidate(kind: str, start: float, end: float, text: str, confidence: float, *,
              reason: str, auto_cut_allowed: bool = False, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "start": start, "end": end, "duration": end - start,
            "evidence_text": text, "confidence": confidence, "reason": reason,
            "needs_review": True, "auto_cut_allowed": auto_cut_allowed,
            "cut": {"start": start, "end": end} if auto_cut_allowed else None, **extra}


def repetition_suggestions(document: dict[str, Any], *, max_gap: float = 8,
                           min_chars: int = 4) -> list[dict[str, Any]]:
    """Exact lexical alignment creates candidates, never claims speaker intent."""
    positive_number(max_gap, "maximum repeat gap", allow_zero=True)
    if type(min_chars) is not int or min_chars < 1:
        raise SuggestionError("minimum repeat characters must be a positive integer")
    segments = document["segments"]
    allowed = document["auto_cut_allowed"]
    suggestions = []
    for first_index, first in enumerate(segments):
        before = text_key(first["text"])
        if len(before) < min_chars:
            continue
        for second_index in range(first_index + 1, len(segments)):
            second = segments[second_index]
            if second["start_sec"] - first["end_sec"] > max_gap:
                break
            after = text_key(second["text"])
            # Different speakers saying the same phrase is not a retake candidate.
            if first["speaker"] is not None and second["speaker"] is not None and first["speaker"] != second["speaker"]:
                continue
            common = 0
            for left, right in zip(before, after):
                if left != right:
                    break
                common += 1
            if common < min_chars:
                continue
            complete_prefix = common == len(before)
            reason = ("repeated_sentence" if before == after else "interrupted_restart") if complete_prefix else "suspected_prefix_restart"
            # A divergent tail is an ambiguous lexical match; show it for review
            # while withholding an automatically executable range.
            exact = complete_prefix and allowed and first["precision"] == second["precision"] == "word"
            start = first["words"][0]["start"] if exact else first["start_sec"]
            end = first["words"][-1]["end"] if exact else first["end_sec"]
            suggestions.append(candidate("repetition", start, end, first["text"], common / max(len(before), len(after)),
                reason=reason, auto_cut_allowed=exact, matched_text=second["text"],
                repeated_at={"start": second["start_sec"], "end": second["end_sec"]},
                precision="word" if exact else first["precision"]))
            break

    # ASR may put both attempts in one sentence. Compare whole acoustic tokens,
    # keeping the cuts on real word boundaries even when a phrase restarts.
    for segment in segments:
        words = segment["words"]
        if segment["precision"] != "word":
            repeated = re.search(r"(.{" + str(min_chars) + r",120}?)\1", text_key(segment["text"])) if min_chars <= 120 else None
            if repeated:
                suggestions.append(candidate("repetition", segment["start_sec"], segment["end_sec"],
                    segment["text"], 1.0, reason="sentence_text_repeat", precision=segment["precision"],
                    matched_text=repeated.group(1)))
            continue
        keys = [text_key(word["text"]) for word in words]
        positions: dict[str, list[int]] = {}
        for index, key in enumerate(keys):
            if key:
                positions.setdefault(key, []).append(index)
        for first_index, key in enumerate(keys):
            if not key:
                continue
            starts = positions[key]
            for second_index in starts[bisect_left(starts, first_index + 1):]:
                if words[second_index]["start"] - words[first_index]["end"] > max_gap:
                    break
                length = 0
                while (first_index + length < second_index and second_index + length < len(words)
                       and length < 120 and keys[first_index + length]
                       and keys[first_index + length] == keys[second_index + length]):
                    length += 1
                matched = "".join(keys[first_index:first_index + length])
                if len(matched) < min_chars:
                    continue
                start, end = words[first_index]["start"], words[first_index + length - 1]["end"]
                if any(item["type"] == "repetition" and item["start"] <= start and item["end"] >= end for item in suggestions):
                    continue
                exact = allowed and segment["precision"] == "word"
                suggestions.append(candidate("repetition", start, end,
                    "".join(word["text"] for word in words[first_index:first_index + length]), 1.0,
                    reason="word_aligned_restart", auto_cut_allowed=exact,
                    repeated_at={"start": words[second_index]["start"],
                                 "end": words[second_index + length - 1]["end"]}, precision="word"))
                break
    return suggestions


def animation_suggestions(document: dict[str, Any], animations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(animations, list):
        raise SuggestionError("animations must be an array")
    suggestions, unmatched = [], []
    seen = set()
    for animation in animations:
        if not isinstance(animation, dict) or not isinstance(animation.get("animation_id"), str) or not animation["animation_id"].strip():
            raise SuggestionError("each animation requires an animation_id")
        identity = animation["animation_id"]
        if identity in seen:
            raise SuggestionError("duplicate animation_id")
        seen.add(identity)
        spoken = animation.get("spoken_text")
        if not isinstance(spoken, str) or not text_key(spoken):
            raise SuggestionError("each animation requires nonempty spoken_text")
        key = text_key(spoken)
        matches = []
        if document["precision"] == "word":
            words = document["words"]
            search_text, coordinates = "", []
            for word_index, word in enumerate(words):
                token = text_key(word["text"])
                search_text += token
                coordinates.extend([word_index] * len(token))
            offset = 0
            while (index := search_text.find(key, offset)) >= 0:
                first, last = coordinates[index], coordinates[index + len(key) - 1]
                matches.append(candidate("animation", words[first]["start"], words[last]["end"], spoken, 1.0,
                    reason="exact_spoken_text", animation_id=identity, precision="word"))
                offset = index + 1
        else:
            for segment in document["segments"]:
                search_text = text_key(segment["text"])
                offset = 0
                while (index := search_text.find(key, offset)) >= 0:
                    matches.append(candidate("animation", segment["start_sec"], segment["end_sec"], spoken, 1.0,
                        reason="sentence_range_only", animation_id=identity, precision=segment["precision"]))
                    offset = index + 1
        if not matches:
            unmatched.append({"animation_id": identity, "spoken_text": spoken, "reason": "spoken_text_not_found"})
        for match_index, item in enumerate(matches, 1):
            item.update(match_index=match_index, match_count=len(matches), ambiguous=len(matches) > 1)
            suggestions.append(item)
    return suggestions, unmatched


def generate_suggestions(audio: Path, transcript: dict[str, Any], *, animations: list[dict[str, Any]] | None = None,
                         threshold_db: float = -35, min_silence: float = 0.4,
                         max_repeat_gap: float = 8, min_repeat_chars: int = 4) -> dict[str, Any]:
    audio = audio.expanduser().resolve(strict=True)
    digest = source_sha256(audio)
    duration = probe_duration(audio)
    document = validate_transcript(transcript, duration=duration)
    silences = detect_silences(audio, threshold_db=threshold_db, min_duration=min_silence, duration=duration)
    suggestions = []
    for start, end in silences:
        overlaps = [word for word in document["words"] if word["start"] < end and word["end"] > start]
        safe_ranges = []
        cursor = start
        for word in overlaps:
            if word["start"] - cursor + 1e-9 >= min_silence:
                safe_ranges.append((cursor, word["start"]))
            cursor = max(cursor, word["end"])
        if end - cursor + 1e-9 >= min_silence:
            safe_ranges.append((cursor, end))
        # The silence detector can include a crossing sample at a word edge.
        # Intersect with acoustic word gaps rather than weakening overlap checks.
        exact = document["auto_cut_allowed"] and bool(safe_ranges)
        for begin, finish in safe_ranges if exact else [(start, end)]:
            suggestions.append(candidate("silence", begin, finish,
                "".join(word["text"] for word in overlaps), 1.0, reason="ffmpeg_silencedetect",
                auto_cut_allowed=exact, detected_range={"start": start, "end": end},
                threshold_db=threshold_db, min_duration=min_silence))
    suggestions.extend(repetition_suggestions(document, max_gap=max_repeat_gap, min_chars=min_repeat_chars))
    animation_matches, unmatched = animation_suggestions(document, animations or [])
    suggestions.extend(animation_matches)
    suggestions.sort(key=lambda item: (item["start"], item["end"], item["type"]))
    if source_sha256(audio) != digest:
        raise SuggestionError("source changed while generating suggestions")
    return {"schema_version": "edit_suggestions_v1", "status": "candidate", "source_sha256": digest,
            "media_id": document["media_id"], "duration": duration,
            "precision": document["precision"], "auto_cut_allowed": document["auto_cut_allowed"],
            "transcript_sha256": hashlib.sha256(json.dumps(transcript, ensure_ascii=False, sort_keys=True,
                                                           allow_nan=False).encode()).hexdigest(),
            "parameters": {"silence_threshold_db": threshold_db, "min_silence_duration": min_silence,
                           "max_repeat_gap": max_repeat_gap, "min_repeat_chars": min_repeat_chars},
            "suggestions": suggestions, "unmatched_animations": unmatched}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--animations", type=Path)
    parser.add_argument("--output", type=Path, default=Path("edit_suggestions.json"))
    parser.add_argument("--silence-threshold-db", type=float, default=-35)
    parser.add_argument("--min-silence-duration", type=float, default=0.4)
    parser.add_argument("--max-repeat-gap", type=float, default=8)
    parser.add_argument("--min-repeat-chars", type=int, default=4)
    args = parser.parse_args()
    inputs = {path.resolve() for path in (args.audio, args.transcript, args.animations) if path is not None}
    output = args.output.expanduser().resolve()
    if output in inputs:
        parser.error("suggestion output must not overwrite any input")
    payload = generate_suggestions(args.audio, json.loads(args.transcript.read_text(encoding="utf-8")),
        animations=json.loads(args.animations.read_text(encoding="utf-8")) if args.animations else None,
        threshold_db=args.silence_threshold_db, min_silence=args.min_silence_duration,
        max_repeat_gap=args.max_repeat_gap, min_repeat_chars=args.min_repeat_chars)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            stream.close()
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps({"status": payload["status"], "suggestion_count": len(payload["suggestions"]),
                      "unmatched_animation_count": len(payload["unmatched_animations"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
