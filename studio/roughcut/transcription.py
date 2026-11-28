"""Selected-source local FunASR transcription, with no whole-project rewrite."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from studio.roughcut.store import RoughcutError, atomic_json, safe_path


class LocalTranscriber:
    def __init__(self, *, provider_factory=None, run=subprocess.run):
        self.provider_factory = provider_factory
        self.run_process = run
        self.provider = None

    def _provider(self):
        if self.provider is None:
            if self.provider_factory:
                self.provider = self.provider_factory()
            else:
                from pipeline.transcribe_audio import FunASRProvider, DEFAULT_FUNASR_MODEL
                cache = Path(os.environ.get('MODELSCOPE_CACHE', Path.home() / '.cache/modelscope'))
                model = cache / 'models/iic--speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/snapshots/master'
                # Missing local models are a readiness problem, not an implicit download.
                if not all((model / name).is_file() for name in ('config.yaml', 'model.pt')):
                    raise RoughcutError('transcription_unavailable')
                self.provider = FunASRProvider(str(model))
                # The filesystem locator is not the model identifier in the transcript contract.
                self.provider.model = DEFAULT_FUNASR_MODEL
        return self.provider

    def run(self, context, media_ids, cancelled):
        from pipeline.transcribe_audio import transcript_document
        root = context['root']
        try:
            provider = self._provider()
        except Exception as exc:
            if isinstance(exc, RoughcutError):
                raise
            raise RoughcutError('transcription_unavailable') from exc
        for mid in media_ids:
            if cancelled():
                return
            if not re.fullmatch(r'[A-Za-z0-9_-]+', mid):
                raise RoughcutError('transcript_selection_invalid')
            item = context['items_by_media'][mid]
            output = context['transcript_paths'][mid]
            safe_path(output, root, 'transcript_unreadable', absent=True)
            audio_ref = item.get('audio_path')
            if audio_ref:
                audio = safe_path(root / audio_ref, root / 'ai-analysis/audio', 'transcription_unavailable')
            else:
                source = safe_path(context['sources_by_media'][mid], root, 'transcription_unavailable')
                audio = root / 'ai-analysis/audio' / (mid + '.wav')
                safe_path(audio, root, 'transcription_unavailable', absent=True)
                audio.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=mid + '-', suffix='.wav', dir=audio.parent)
                os.close(fd)
                try:
                    self.run_process(['ffmpeg', '-nostdin', '-hide_banner', '-v', 'error', '-y',
                                      '-i', str(source), '-vn', '-ac', '1', '-ar', '16000', temporary],
                                     capture_output=True, check=True, timeout=180, start_new_session=True)
                    if cancelled():
                        return
                    os.replace(temporary, audio)
                except (OSError, subprocess.SubprocessError) as exc:
                    raise RoughcutError('transcript_failed') from exc
                finally:
                    Path(temporary).unlink(missing_ok=True)
            try:
                result = provider.transcribe(audio, language='zh')
                if not isinstance(result, dict):
                    raise RoughcutError('transcript_failed')
                document = transcript_document(media_id=mid, audio_ref=audio.relative_to(root).as_posix(),
                    provider=str(result.get('provider') or provider.name), model=str(result.get('model') or provider.model),
                    language=result.get('language') or 'zh', segments=result.get('segments') or [], words=result.get('words'))
                if not document['segments']:
                    raise RoughcutError('transcript_failed')
                if cancelled():
                    return
                atomic_json(output, document, 'transcript_failed')
            except Exception as exc:
                if isinstance(exc, RoughcutError):
                    raise
                raise RoughcutError('transcript_failed') from exc
