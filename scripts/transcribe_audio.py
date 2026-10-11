#!/usr/bin/env python3
"""Create timestamped transcript evidence for extracted project audio.

Providers:
- ``dashscope``: DashScope-compatible online transcription; the configured
  endpoint receives the selected audio file.
- ``funasr``: local FunASR fallback when its optional runtime is installed.
- ``fun_asr``: official asynchronous Fun-ASR file transcription (``--live``).
- ``sidecar``: deterministic; reads an adjacent .srt/.json/.txt file.
- ``openai_api``: uses the OpenAI Transcription API and requests SRT output.
- ``pending``: records an explicit pending state without pretending audio was read.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid
from pathlib import Path
from typing import Any, Protocol

from media_common import load_manifest, project_path, safe_project_file as _safe_audio_path, save_manifest, transcripts_dir

SCHEMA_VERSION = "audio_transcript_v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_DASHSCOPE_MODEL = "paraformer-v2"
DEFAULT_DASHSCOPE_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/transcriptions"
DEFAULT_FUNASR_MODEL = "paraformer-zh"


class TranscriptionError(RuntimeError):
    pass


class Provider(Protocol):
    name: str
    model: str

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]: ...


class ProviderResult(dict[str, Any]):
    """Provider output that preserves the provider that actually produced it."""


def text_key(text: str) -> str:
    return "".join(character.casefold() for character in text if character.isalnum())


def timing_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TranscriptionError("timestamps must be finite numbers")
    return float(value)


def normalize_words(words: Any, *, start: float, end: float) -> list[dict[str, Any]]:
    """Validate acoustic intervals without sorting, clamping or interpolation."""
    if not isinstance(words, list):
        raise TranscriptionError("words must be an array")
    result = []
    previous_end = start
    for word in words:
        if not isinstance(word, dict):
            raise TranscriptionError("word must be an object")
        begin, finish = timing_number(word.get("start")), timing_number(word.get("end"))
        text = word.get("text")
        if not isinstance(text, str) or not text.strip():
            raise TranscriptionError("word text must not be empty")
        if begin < previous_end or finish <= begin or finish > end:
            raise TranscriptionError("word times overlap, reverse or exceed their segment")
        result.append({"start": begin, "end": finish, "text": text})
        previous_end = finish
    return result


def vendor_words(items: Any, *, milliseconds: bool) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise TranscriptionError("provider words must be an array")
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise TranscriptionError("provider word must be an object")
        begin = item.get("begin_time", item.get("start"))
        finish = item.get("end_time", item.get("end"))
        scale = 1000 if milliseconds else 1
        punctuation = item.get("punctuation", "")
        text = item.get("text", item.get("word"))
        if not isinstance(text, str) or not isinstance(punctuation, str):
            raise TranscriptionError("provider word text must be a string")
        result.append({"start": timing_number(begin) / scale,
                       "end": timing_number(finish) / scale, "text": text + punctuation})
    return result


def normalize_asr_payload(payload: dict[str, Any], *, local: bool = False) -> dict[str, Any]:
    """Convert provider units; only explicitly aligned tokens retain word precision."""
    segments = []
    if "transcripts" in payload:
        transcripts = payload["transcripts"]
        if not isinstance(transcripts, list):
            raise TranscriptionError("transcripts must be an array")
        for transcript in transcripts:
            if not isinstance(transcript, dict) or transcript.get("channel_id", 0) != 0:
                raise TranscriptionError("only the selected first audio channel is supported")
            normalized = normalize_asr_payload({"sentences": transcript.get("sentences", []),
                                                "text": transcript.get("text", transcript.get("transcript", ""))})
            segments.extend(normalized["segments"])
        return {"segments": segments}
    source_key = next((key for key in ("segments", "sentence_info", "sentences") if payload.get(key)), None)
    raw_segments = payload[source_key] if source_key else [payload]
    if not isinstance(raw_segments, list):
        raise TranscriptionError("provider segments must be an array")
    for item in raw_segments:
        if not isinstance(item, dict):
            raise TranscriptionError("provider segment must be an object")
        text = item.get("text", item.get("sentence", ""))
        if not isinstance(text, str):
            raise TranscriptionError("provider segment text must be a string")
        if not text.strip():
            continue
        milliseconds = local or source_key in {"sentence_info", "sentences"} or "begin_time" in item
        scale = 1000 if milliseconds else 1
        start = item.get("begin_time", item.get("start", item.get("start_sec", 0)))
        end = item.get("end_time", item.get("end", item.get("end_sec", start)))
        words = vendor_words(item.get("words", []), milliseconds=milliseconds)
        # FunASR's raw_text is the acoustic token sequence. Display characters
        # cannot be substituted when its token count or text coverage differs.
        timestamps = item.get("timestamp")
        tokens = item.get("raw_text", "").split() if isinstance(item.get("raw_text"), str) else []
        if not words and local and isinstance(timestamps, list) and tokens and len(tokens) == len(timestamps):
            if text_key("".join(tokens)) == text_key(text):
                for token, interval in zip(tokens, timestamps):
                    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
                        raise TranscriptionError("invalid acoustic token interval")
                    words.append({"start": timing_number(interval[0]) / 1000,
                                  "end": timing_number(interval[1]) / 1000, "text": token})
        if source_key is None and words and end == start == 0:
            start, end = words[0]["start"] * scale, words[-1]["end"] * scale
        elif source_key is None and not words and local and isinstance(timestamps, list) and timestamps:
            start, end = timestamps[0][0], timestamps[-1][1]
        segments.append({"start_sec": timing_number(start) / scale, "end_sec": timing_number(end) / scale,
                         "text": text, "speaker": item.get("speaker", item.get("speaker_id")),
                         "confidence": item.get("confidence"), "words": words,
                         "precision": "chunk" if source_key is None and not words else "sentence"})
    return {"language": payload.get("language"), "segments": segments,
            "words": vendor_words(payload.get("words", []), milliseconds=False) if source_key else []}


def seconds_from_srt(value: str) -> float:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    if not match:
        raise TranscriptionError(f"invalid SRT timestamp: {value}")
    hours, minutes, seconds, millis = map(int, match.groups())
    return round(hours * 3600 + minutes * 60 + seconds + millis / 1000, 3)


def parse_srt(text: str) -> list[dict[str, Any]]:
    normalised = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalised:
        return []
    blocks = re.split(r"\n\s*\n", normalised)
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        timing_index = 1 if lines[0].isdigit() and len(lines) > 1 else 0
        if timing_index >= len(lines) or "-->" not in lines[timing_index]:
            raise TranscriptionError(f"invalid SRT block: {block[:120]}")
        start_text, end_text = [part.strip().split(" ", 1)[0] for part in lines[timing_index].split("-->", 1)]
        start = seconds_from_srt(start_text)
        end = seconds_from_srt(end_text)
        if end < start:
            raise TranscriptionError("SRT segment ends before it starts")
        body = "\n".join(lines[timing_index + 1 :]).strip()
        if not body:
            continue
        segments.append(
            {
                "start_sec": start,
                "end_sec": end,
                "speaker": None,
                "text": body,
                "confidence": None,
            }
        )
    return segments


def transcript_document(
    *,
    media_id: str,
    audio_ref: str,
    provider: str,
    model: str,
    language: str | None,
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(segments, list) or any(not isinstance(segment, dict) for segment in segments):
        raise TranscriptionError("segments must be an array of objects")
    if words is not None and not isinstance(words, list):
        raise TranscriptionError("words must be an array")
    previous_end = 0.0
    cleaned: list[dict[str, Any]] = []
    for segment in segments:
        start = timing_number(segment.get("start_sec", 0))
        end = timing_number(segment.get("end_sec", start))
        if start < 0 or end < start or start < previous_end:
            raise TranscriptionError("transcript segments must be ordered and non-overlapping")
        if not isinstance(segment.get("text"), str):
            raise TranscriptionError("segment text must be a string")
        text = segment["text"].strip()
        if not text:
            continue
        speaker = segment.get("speaker")
        confidence = segment.get("confidence")
        if confidence is not None:
            confidence = timing_number(confidence)
            if not 0 <= confidence <= 1:
                raise TranscriptionError("confidence must be between 0 and 1")
        segment_words = normalize_words(segment.get("words", []), start=start, end=end)
        precision = "chunk" if end == start or segment.get("precision") == "chunk" else "sentence"
        if segment_words and text_key("".join(word["text"] for word in segment_words)) == text_key(text):
            precision = "word"
        cleaned.append(
            {
                "start_sec": start,
                "end_sec": end,
                "speaker": str(speaker).strip() if speaker not in (None, "") else None,
                "text": text,
                "confidence": confidence,
                "words": segment_words,
                "precision": precision,
            }
        )
        previous_end = end
    if words:
        aligned = normalize_words(words, start=0, end=previous_end)
        assigned = []
        for segment in cleaned:
            contained = [word for word in aligned if word["start"] >= segment["start_sec"]
                         and word["end"] <= segment["end_sec"]]
            if segment["words"] and contained != segment["words"]:
                raise TranscriptionError("top-level and segment words disagree")
            segment["words"] = contained
            assigned.extend(contained)
            if contained and text_key("".join(word["text"] for word in contained)) == text_key(segment["text"]):
                segment["precision"] = "word"
        if assigned != aligned:
            raise TranscriptionError("word is outside every transcript segment")
    precision = "chunk" if not cleaned or any(item["precision"] == "chunk" for item in cleaned) else (
        "word" if all(item["precision"] == "word" for item in cleaned) else "sentence")
    return {
        "schema_version": SCHEMA_VERSION,
        "media_id": media_id,
        "audio_ref": audio_ref,
        "provider": provider,
        "model": model,
        "language": language,
        "status": "ok" if cleaned else ("pending" if provider == "pending" else "empty"),
        "segments": cleaned,
        "text": "\n".join(item["text"] for item in cleaned),
        "words": [word for segment in cleaned for word in segment["words"]],
        "precision": precision,
        "auto_cut_allowed": precision == "word",
    }


class SidecarProvider:
    name = "sidecar"
    model = "sidecar-v1"

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory.resolve() if directory else None

    def candidates(self, audio_path: Path) -> list[Path]:
        roots = [self.directory] if self.directory else [audio_path.parent]
        result: list[Path] = []
        for root in roots:
            if root is None:
                continue
            for suffix in (".transcript.json", ".json", ".srt", ".txt"):
                result.append(root / f"{audio_path.stem}{suffix}")
        return result

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        path = next((candidate for candidate in self.candidates(audio_path) if candidate.is_file()), None)
        if path is None:
            raise TranscriptionError(f"transcript sidecar not found for {audio_path.name}")
        words = []
        if path.suffix.lower() == ".srt":
            segments = parse_srt(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8").strip()
            segments = [{"start_sec": 0.0, "end_sec": 0.0, "speaker": None, "text": text, "confidence": None}] if text else []
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("segments"), list):
                segments = data["segments"]
                words = data.get("words", [])
                language = data.get("language") or language
            elif isinstance(data, dict) and any(key in data for key in ("transcripts", "sentence_info", "sentences", "timestamp")):
                return normalize_asr_payload(data, local="timestamp" in data or "sentence_info" in data)
            elif isinstance(data, dict) and isinstance(data.get("text"), str):
                segments = [{"start_sec": 0.0, "end_sec": 0.0, "speaker": None, "text": data["text"], "confidence": None}]
            else:
                raise TranscriptionError(f"unsupported sidecar JSON: {path}")
        return {"language": language, "segments": segments, "words": words}


class OpenAIProvider:
    name = "openai_api"

    def __init__(self, model: str) -> None:
        self.model = model
        if not os.getenv("OPENAI_API_KEY"):
            raise TranscriptionError("OPENAI_API_KEY is required for openai_api transcription")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - environment dependent
            raise TranscriptionError("openai Python package is required") from exc
        self.client = OpenAI()

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": self.model, "response_format": "srt"}
        if language:
            kwargs["language"] = language
        with audio_path.open("rb") as handle:
            response = self.client.audio.transcriptions.create(file=handle, **kwargs)
        if isinstance(response, str):
            text = response
        else:
            text = getattr(response, "text", None) or str(response)
        return {"language": language, "segments": parse_srt(text)}


class DashscopeProvider:
    """DashScope's OpenAI-compatible audio endpoint without an SDK dependency."""

    name = "dashscope"

    def __init__(self, model: str) -> None:
        self.model = model or DEFAULT_DASHSCOPE_MODEL
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.endpoint = os.getenv("DASHSCOPE_TRANSCRIPTION_ENDPOINT", DEFAULT_DASHSCOPE_ENDPOINT)
        if not self.api_key:
            raise TranscriptionError("DASHSCOPE_API_KEY is required for dashscope transcription")

    @staticmethod
    def _multipart(audio_path: Path, *, model: str, language: str | None) -> tuple[bytes, str]:
        boundary = f"----OpenClawMedia{uuid.uuid4().hex}"
        fields = [("model", model), ("response_format", "verbose_json")]
        if language:
            fields.append(("language", language))
        chunks: list[bytes] = []
        for name, value in fields:
            chunks.extend((f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), value.encode(), b"\r\n"))
        chunks.extend((f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\r\n'.encode(), b"Content-Type: application/octet-stream\r\n\r\n", audio_path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
        return b"".join(chunks), boundary

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        body, boundary = self._multipart(audio_path, model=self.model, language=language)
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - configured provider endpoint
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise TranscriptionError("DashScope transcription request failed") from exc
        if not isinstance(payload, dict):
            raise TranscriptionError("DashScope response must be a JSON object")
        result = normalize_asr_payload(payload)
        return ProviderResult(**{**result, "language": result.get("language") or language}, provider=self.name, model=self.model)


class FunASRProvider:
    name = "funasr"

    def __init__(self, model: str) -> None:
        self.model = model or DEFAULT_FUNASR_MODEL
        try:
            from funasr import AutoModel
        except Exception as exc:  # pragma: no cover - optional local runtime
            raise TranscriptionError("funasr Python package is required for funasr transcription") from exc
        self.client = AutoModel(model=self.model, disable_update=True)

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        result = self.client.generate(input=str(audio_path), batch_size_s=300, sentence_timestamp=True, return_raw_text=True)
        if not isinstance(result, list) or not result or any(not isinstance(item, dict) for item in result):
            raise TranscriptionError("FunASR returned an invalid response")
        segments = [segment for item in result for segment in normalize_asr_payload(item, local=True)["segments"]]
        return ProviderResult(
            language=language,
            segments=segments,
            provider=self.name,
            model=self.model,
        )


class FunASRFileProvider:
    """Official asynchronous Fun-ASR transport, independent of the other repo."""

    name = "fun_asr"

    def __init__(self, model: str) -> None:
        self.model = model
        self.api_key = os.getenv("SPEECH_TO_TEXT_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        base = os.getenv("SPEECH_TO_TEXT_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
        parsed = urlsplit(base)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise TranscriptionError("Fun-ASR requires a valid HTTPS service endpoint")
        if parsed.path.rstrip("/") not in {"", "/api/v1", "/compatible-mode/v1"}:
            raise TranscriptionError("invalid Fun-ASR service root")
        self.api_root = f"https://{parsed.netloc}/api/v1"
        if not self.api_key:
            raise TranscriptionError("SPEECH_TO_TEXT_API_KEY or DASHSCOPE_API_KEY is required")
        self.timeout = float(os.getenv("SPEECH_TO_TEXT_TIMEOUT_SECONDS", "60"))
        self.max_wait = float(os.getenv("SPEECH_TO_TEXT_MAX_WAIT_SECONDS", "900"))
        self.poll_interval = float(os.getenv("SPEECH_TO_TEXT_POLL_INTERVAL_SECONDS", "2"))
        if any(not math.isfinite(number) or number <= 0 for number in (self.timeout, self.max_wait, self.poll_interval)):
            raise TranscriptionError("Fun-ASR timeout and polling interval must be positive")

    def _request(self, url: str, *, data: bytes | None = None, headers: dict | None = None,
                 authenticated: bool = False, timeout: float | None = None, json_response: bool = True) -> Any:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise TranscriptionError("provider resource must use HTTPS")
        request_headers = dict(headers or {})
        if authenticated:
            if parsed.netloc != urlsplit(self.api_root).netloc:
                raise TranscriptionError("provider authentication cannot leave its service host")
            request_headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(url, data=data, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if json_response else None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise TranscriptionError("Fun-ASR transport failed") from exc

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        if not audio_path.is_file() or not 0 < audio_path.stat().st_size <= 20 * 1024 * 1024:
            raise TranscriptionError("Fun-ASR input must be nonempty and within the 20 MB upload budget")
        policy = self._request(self.api_root + "/uploads?action=getPolicy&model=" + self.model,
                               authenticated=True)["data"]
        object_key = policy["upload_dir"].rstrip("/") + "/" + uuid.uuid4().hex + audio_path.suffix
        fields = {name: str(policy[key]) for name, key in (
            ("OSSAccessKeyId", "oss_access_key_id"), ("Signature", "signature"), ("policy", "policy"),
            ("x-oss-object-acl", "x_oss_object_acl"), ("x-oss-forbid-overwrite", "x_oss_forbid_overwrite"))}
        fields.update(key=object_key, success_action_status="200")
        boundary = "----PhotoFunASR" + uuid.uuid4().hex
        parts = []
        for name, value in fields.items():
            parts.extend((f"--{boundary}\r\n".encode(),
                          f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                          value.encode(), b"\r\n"))
        parts.extend((f"--{boundary}\r\n".encode(),
                      b'Content-Disposition: form-data; name="file"; filename="audio.bin"\r\n',
                      b"Content-Type: application/octet-stream\r\n\r\n", audio_path.read_bytes(),
                      b"\r\n", f"--{boundary}--\r\n".encode()))
        self._request(policy["upload_host"], data=b"".join(parts),
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, json_response=False)
        parameters: dict[str, Any] = {"channel_id": [0]}
        if language:
            parameters["language_hints"] = [language]
        submitted = self._request(self.api_root + "/services/audio/asr/transcription", authenticated=True,
            headers={"Content-Type": "application/json", "X-DashScope-Async": "enable", "X-DashScope-OssResourceResolve": "enable"},
            data=json.dumps({"model": self.model, "input": {"file_urls": ["oss://" + object_key]},
                             "parameters": parameters}).encode())
        task_id = submitted["output"]["task_id"]
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", task_id) or self.api_key in task_id:
            raise TranscriptionError("invalid Fun-ASR task identity")
        deadline = time.monotonic() + self.max_wait
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TranscriptionError(f"Fun-ASR task timed out; task_id={task_id}; do not resubmit without checking it")
            polled = self._request(self.api_root + "/tasks/" + task_id, authenticated=True,
                                   timeout=min(self.timeout, remaining))
            output = polled["output"]
            if output.get("task_id", task_id) != task_id:
                raise TranscriptionError("Fun-ASR returned a mismatched task identity")
            status = output["task_status"]
            if status == "SUCCEEDED":
                results = output["results"]
                if not isinstance(results, list) or len(results) != 1 or results[0].get("subtask_status") != "SUCCEEDED":
                    raise TranscriptionError("Fun-ASR file subtask failed")
                raw = self._request(results[0]["transcription_url"])
                normalized = normalize_asr_payload(raw)
                return ProviderResult(**{**normalized, "language": language}, provider=self.name, model=self.model)
            if status not in {"PENDING", "RUNNING"}:
                raise TranscriptionError("Fun-ASR task failed or returned an unknown status")
            time.sleep(min(self.poll_interval, max(0, deadline - time.monotonic())))


class DashscopeWithFunASRFallback:
    """Use the accepted online default, then make the local fallback explicit."""

    name = "dashscope"

    def __init__(self, model: str) -> None:
        self.model = model or DEFAULT_DASHSCOPE_MODEL

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        try:
            return DashscopeProvider(self.model).transcribe(audio_path, language=language)
        except TranscriptionError:
            try:
                fallback = FunASRProvider(DEFAULT_FUNASR_MODEL)
                return fallback.transcribe(audio_path, language=language)
            except TranscriptionError as fallback_error:
                raise TranscriptionError(
                    "DashScope transcription failed and the local FunASR fallback is unavailable"
                ) from fallback_error


class PendingProvider:
    name = "pending"
    model = "none"

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> dict[str, Any]:
        return {"language": language, "segments": []}


def build_provider(name: str, *, model: str, sidecar_dir: Path | None, live: bool = False) -> Provider:
    value = name.strip().lower()
    if value in {"openai", "openai_api", "openai-api", "dashscope", "dashscope_api", "dashscope-api", "fun_asr"} and not live:
        raise TranscriptionError("online transcription requires explicit --live")
    if value == "sidecar":
        return SidecarProvider(sidecar_dir)
    if value in {"openai", "openai_api", "openai-api"}:
        return OpenAIProvider(model)
    if value in {"dashscope", "dashscope_api", "dashscope-api"}:
        return DashscopeWithFunASRFallback(model or DEFAULT_DASHSCOPE_MODEL)
    if value in {"funasr", "local_funasr", "local-funasr"}:
        return FunASRProvider(model or DEFAULT_FUNASR_MODEL)
    if value == "fun_asr":
        return FunASRFileProvider(model or "fun-asr")
    if value in {"pending", "none", "disabled"}:
        return PendingProvider()
    raise TranscriptionError(f"unsupported transcription provider: {name}")


def process_project(
    project: Path,
    *,
    provider: Provider,
    language: str | None,
    overwrite: bool,
    limit: int | None,
    allow_pending: bool,
) -> dict[str, int]:
    manifest = load_manifest(project)
    output_dir = transcripts_dir(project)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = skipped = pending = failed = 0
    for item in manifest.get("items", []):
        if limit is not None and generated >= limit:
            break
        if not isinstance(item, dict):
            continue
        audio = _safe_audio_path(project, item.get("audio_path"))
        if audio is None:
            continue
        media_id = str(item.get("media_id") or item.get("id") or audio.stem)
        output = output_dir / f"{media_id}.transcript.json"
        if output.exists() and not overwrite:
            try:
                cached = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cached = {}
            item["transcript_path"] = output.relative_to(project).as_posix()
            cached_status = str(cached.get("status") or "") if isinstance(cached, dict) else ""
            item["transcript_status"] = cached_status if cached_status in {"ok", "pending", "empty"} else "pending_manual"
            skipped += 1
            continue
        try:
            result = provider.transcribe(audio, language=language)
            actual_provider = str(result.get("provider") or provider.name)
            actual_model = str(result.get("model") or provider.model)
            document = transcript_document(
                media_id=media_id,
                audio_ref=audio.relative_to(project).as_posix(),
                provider=actual_provider,
                model=actual_model,
                language=result.get("language") or language,
                segments=result.get("segments") or [],
                words=result.get("words"),
            )
            if not document["segments"] and actual_provider != "pending":
                raise TranscriptionError("provider returned no transcript segments")
            temporary = output.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(output)
            item["transcript_path"] = output.relative_to(project).as_posix()
            item["transcript_status"] = "pending" if actual_provider == "pending" else "ok"
            generated += 1
            pending += int(actual_provider == "pending")
        except Exception as exc:
            failed += 1
            item["transcript_status"] = "pending_manual"
            item["transcript_error"] = type(exc).__name__
            if not allow_pending:
                save_manifest(project, manifest)
                raise
    save_manifest(project, manifest)
    return {"generated": generated, "skipped": skipped, "pending": pending, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--provider", default=os.getenv("OPENCLAW_TRANSCRIPTION_PROVIDER", "dashscope"))
    parser.add_argument("--model", default=os.getenv("OPENCLAW_TRANSCRIPTION_MODEL", DEFAULT_DASHSCOPE_MODEL))
    parser.add_argument("--language")
    parser.add_argument("--sidecar-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("--live", action="store_true", help="Explicitly enable paid online ASR")
    args = parser.parse_args()
    project = project_path(args.project_dir)
    provider = build_provider(args.provider, model=args.model, sidecar_dir=args.sidecar_dir, live=args.live)
    result = process_project(
        project,
        provider=provider,
        language=args.language,
        overwrite=args.overwrite,
        limit=args.limit,
        allow_pending=args.allow_pending,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
