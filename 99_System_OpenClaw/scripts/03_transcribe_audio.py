#!/usr/bin/env python3
"""Create timestamped transcript evidence for extracted project audio.

Providers:
- ``dashscope``: DashScope-compatible online transcription; the configured
  endpoint receives the selected audio file.
- ``funasr``: local FunASR fallback when its optional runtime is installed.
- ``sidecar``: deterministic; reads an adjacent .srt/.json/.txt file.
- ``openai_api``: uses the OpenAI Transcription API and requests SRT output.
- ``pending``: records an explicit pending state without pretending audio was read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
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
) -> dict[str, Any]:
    previous_end = 0.0
    cleaned: list[dict[str, Any]] = []
    for segment in segments:
        start = round(float(segment.get("start_sec", 0)), 3)
        end = round(float(segment.get("end_sec", start)), 3)
        if start < 0 or end < start or start < previous_end - 0.001:
            raise TranscriptionError("transcript segments must be ordered and non-overlapping")
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        speaker = segment.get("speaker")
        confidence = segment.get("confidence")
        if confidence is not None:
            confidence = float(confidence)
            if not 0 <= confidence <= 1:
                raise TranscriptionError("confidence must be between 0 and 1")
        cleaned.append(
            {
                "start_sec": start,
                "end_sec": end,
                "speaker": str(speaker).strip() if speaker not in (None, "") else None,
                "text": text,
                "confidence": confidence,
            }
        )
        previous_end = end
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
        if path.suffix.lower() == ".srt":
            segments = parse_srt(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8").strip()
            segments = [{"start_sec": 0.0, "end_sec": 0.0, "speaker": None, "text": text, "confidence": None}] if text else []
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("segments"), list):
                segments = data["segments"]
                language = data.get("language") or language
            elif isinstance(data, dict) and isinstance(data.get("text"), str):
                segments = [{"start_sec": 0.0, "end_sec": 0.0, "speaker": None, "text": data["text"], "confidence": None}]
            else:
                raise TranscriptionError(f"unsupported sidecar JSON: {path}")
        return {"language": language, "segments": segments}


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
            chunks.extend((f"--{boundary}\\r\\n".encode(), f'Content-Disposition: form-data; name="{name}"\\r\\n\\r\\n'.encode(), value.encode(), b"\\r\\n"))
        chunks.extend((f"--{boundary}\\r\\n".encode(), f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\\r\\n'.encode(), b"Content-Type: application/octet-stream\\r\\n\\r\\n", audio_path.read_bytes(), b"\\r\\n", f"--{boundary}--\\r\\n".encode()))
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
        used_sentence_info = not payload.get("segments") and isinstance(payload.get("sentence_info"), list)
        raw_segments = payload.get("segments") or payload.get("sentence_info") or []
        segments: list[dict[str, Any]] = []
        if isinstance(raw_segments, list):
            for item in raw_segments:
                if not isinstance(item, dict):
                    continue
                start = item.get("start") if item.get("start") is not None else item.get("start_sec", 0)
                end = item.get("end") if item.get("end") is not None else item.get("end_sec", start)
                # DashScope sentence_info uses milliseconds even for a segment
                # shorter than one second. Compatible `segments` use seconds.
                if used_sentence_info:
                    start, end = float(start) / 1000, float(end) / 1000
                segments.append({"start_sec": start, "end_sec": end, "speaker": item.get("speaker"), "text": item.get("text") or item.get("sentence") or "", "confidence": item.get("confidence")})
        if not segments and isinstance(payload.get("text"), str):
            segments = [{"start_sec": 0, "end_sec": 0, "speaker": None, "text": payload["text"], "confidence": None}]
        return ProviderResult(language=payload.get("language") or language, segments=segments, provider=self.name, model=self.model)


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
        result = self.client.generate(input=str(audio_path), batch_size_s=300)
        first = result[0] if isinstance(result, list) and result else {}
        if not isinstance(first, dict):
            raise TranscriptionError("FunASR returned an invalid response")
        text = str(first.get("text") or "").strip()
        timestamps = first.get("timestamp")
        end = 0.0
        if isinstance(timestamps, list) and timestamps:
            last = timestamps[-1]
            if isinstance(last, (list, tuple)) and len(last) > 1:
                end = float(last[1]) / 1000
        return ProviderResult(
            language=language,
            segments=[{"start_sec": 0, "end_sec": end, "speaker": None, "text": text, "confidence": None}] if text else [],
            provider=self.name,
            model=self.model,
        )


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


def build_provider(name: str, *, model: str, sidecar_dir: Path | None) -> Provider:
    value = name.strip().lower()
    if value == "sidecar":
        return SidecarProvider(sidecar_dir)
    if value in {"openai", "openai_api", "openai-api"}:
        return OpenAIProvider(model)
    if value in {"dashscope", "dashscope_api", "dashscope-api"}:
        return DashscopeWithFunASRFallback(model or DEFAULT_DASHSCOPE_MODEL)
    if value in {"funasr", "local_funasr", "local-funasr"}:
        return FunASRProvider(model or DEFAULT_FUNASR_MODEL)
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
    args = parser.parse_args()
    project = project_path(args.project_dir)
    provider = build_provider(args.provider, model=args.model, sidecar_dir=args.sidecar_dir)
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
