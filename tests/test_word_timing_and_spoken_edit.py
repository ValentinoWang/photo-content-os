from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import jsonschema

from _support import load_script

transcribe = load_script("transcribe_audio.py", "pa_transcribe")
spoken = load_script("spoken_edit.py", "pa_spoken")
SYSTEM = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((SYSTEM / "schemas/audio-transcript.schema.json").read_text())


def sentence(start, end, text, words=None, speaker=None):
    return {"start_sec": start, "end_sec": end, "text": text,
            "speaker": speaker, "confidence": None, "words": words or []}


def document(segments, **kwargs):
    return transcribe.transcript_document(media_id="fixture", audio_ref="audio.wav",
        provider="sidecar", model="stub-asr", language="zh", segments=segments, **kwargs)


def raw_asr():
    return {"transcripts": [{"channel_id": 0, "sentences": [
        {"begin_time": 0, "end_time": 1600, "text": "今天讲算法。", "words": [
            {"begin_time": 0, "end_time": 600, "text": "今天"},
            {"begin_time": 600, "end_time": 1000, "text": "讲"},
            {"begin_time": 1000, "end_time": 1600, "text": "算法", "punctuation": "。"}]},
        {"begin_time": 2400, "end_time": 4000, "text": "今天讲算法。", "words": [
            {"begin_time": 2400, "end_time": 3000, "text": "今天"},
            {"begin_time": 3000, "end_time": 3400, "text": "讲"},
            {"begin_time": 3400, "end_time": 4000, "text": "算法", "punctuation": "。"}]}]}]}


class WordTimingTests(unittest.TestCase):
    def test_cloud_words_are_preserved_as_acoustic_seconds(self):
        normalized = transcribe.normalize_asr_payload(raw_asr())
        result = document(normalized["segments"])
        self.assertEqual(result["precision"], "word")
        self.assertTrue(result["auto_cut_allowed"])
        self.assertEqual(result["words"][3], {"start": 2.4, "end": 3.0, "text": "今天"})
        self.assertEqual(result["words"][-1]["text"], "算法。")
        jsonschema.validate(result, SCHEMA)

    def test_no_words_never_interpolates(self):
        raw = raw_asr()
        for item in raw["transcripts"][0]["sentences"]:
            item.pop("words")
        result = document(transcribe.normalize_asr_payload(raw)["segments"])
        self.assertEqual(result["precision"], "sentence")
        self.assertEqual(result["words"], [])
        self.assertFalse(result["auto_cut_allowed"])
        jsonschema.validate(result, SCHEMA)

    def test_partial_word_coverage_disables_auto_cut(self):
        result = document([sentence(0, 1, "今天算法", [{"start": 0, "end": 0.5, "text": "今天"}])])
        self.assertEqual(result["precision"], "sentence")
        self.assertFalse(result["auto_cut_allowed"])
        self.assertEqual(len(result["words"]), 1)

    def test_mixed_segments_use_weakest_precision(self):
        normalized = transcribe.normalize_asr_payload(raw_asr())["segments"]
        normalized[1]["words"] = []
        result = document(normalized)
        self.assertEqual(result["precision"], "sentence")
        self.assertFalse(result["auto_cut_allowed"])

    def test_chunk_and_pending_are_explicit(self):
        for segments in ([], [sentence(0, 0, "未对齐文本")],
                         transcribe.normalize_asr_payload({"text": "未对齐文本"})["segments"]):
            with self.subTest(segments=segments):
                result = document(segments)
                self.assertEqual(result["precision"], "chunk")
                self.assertFalse(result["auto_cut_allowed"])
                jsonschema.validate(result, SCHEMA)

    def test_invalid_word_intervals_fail_closed(self):
        for word in ({"start": -1, "end": .5, "text": "词"},
                     {"start": .8, "end": .5, "text": "词"},
                     {"start": .2, "end": .2, "text": "词"},
                     {"start": 0, "end": 1.1, "text": "词"},
                     {"start": float("nan"), "end": 1, "text": "词"},
                     {"start": True, "end": 1, "text": "词"},
                     {"start": 0, "end": 1, "text": ""}):
            with self.subTest(word=word), self.assertRaises(transcribe.TranscriptionError):
                document([sentence(0, 1, "词", [word])])

    def test_overlapping_or_reversed_words_fail(self):
        for words in ([{"start": 0, "end": .8, "text": "一"}, {"start": .7, "end": 1, "text": "二"}],
                      [{"start": .7, "end": 1, "text": "二"}, {"start": 0, "end": .5, "text": "一"}]):
            with self.subTest(words=words), self.assertRaises(transcribe.TranscriptionError):
                document([sentence(0, 1, "一二", words)])

    def test_nonfinite_sentence_and_confidence_fail(self):
        for item in (sentence(0, float("inf"), "词"), {**sentence(0, 1, "词"), "confidence": float("nan")}):
            with self.subTest(item=item), self.assertRaises(transcribe.TranscriptionError):
                document([item])

    def test_top_level_words_are_bound_to_their_segment(self):
        words = [{"start": 0, "end": 1, "text": "今天"}]
        result = document([sentence(0, 1, "今天")], words=words)
        self.assertTrue(result["auto_cut_allowed"])
        self.assertEqual(result["segments"][0]["words"], words)
        with self.assertRaises(transcribe.TranscriptionError):
            document([sentence(0, .4, "今天"), sentence(.6, 1, "明天")], words=words)

    def test_local_funasr_pairs_only_explicit_raw_tokens(self):
        raw = {"text": "今天算法", "raw_text": "今天 算法", "timestamp": [[100, 400], [400, 900]]}
        result = document(transcribe.normalize_asr_payload(raw, local=True)["segments"])
        self.assertEqual(result["words"], [{"start": .1, "end": .4, "text": "今天"},
                                          {"start": .4, "end": .9, "text": "算法"}])
        self.assertTrue(result["auto_cut_allowed"])
        for invalid in ({**raw, "raw_text": "今天 算 法"}, {**raw, "raw_text": "今天 错误"},
                        {key: value for key, value in raw.items() if key != "raw_text"}):
            with self.subTest(invalid=invalid):
                fallback = document(transcribe.normalize_asr_payload(invalid, local=True)["segments"])
                self.assertEqual(fallback["words"], [])
                self.assertFalse(fallback["auto_cut_allowed"])

    def test_sidecar_raw_cloud_and_normalized_word_results(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "a.wav"
            audio.write_bytes(b"fixture")
            sidecar = audio.with_suffix(".json")
            for payload in (raw_asr(), document(transcribe.normalize_asr_payload(raw_asr())["segments"])):
                sidecar.write_text(json.dumps(payload, ensure_ascii=False))
                normalized = transcribe.SidecarProvider().transcribe(audio)
                result = document(normalized["segments"], words=normalized.get("words"))
                self.assertTrue(result["auto_cut_allowed"])

    def test_paid_providers_require_explicit_live(self):
        for provider in ("openai_api", "dashscope", "fun_asr"):
            with self.subTest(provider=provider), patch.object(transcribe.urllib.request, "urlopen") as request:
                with self.assertRaisesRegex(transcribe.TranscriptionError, "--live"):
                    transcribe.build_provider(provider, model="fun-asr", sidecar_dir=None)
                request.assert_not_called()

    def test_cloud_transport_uses_real_protocol_without_paid_calls(self):
        requests = []
        policy = {"upload_dir": "test/audio", "upload_host": "https://upload.example.test", "policy": "stub",
                  "signature": "signature", "oss_access_key_id": "key",
                  "x_oss_object_acl": "private", "x_oss_forbid_overwrite": "true"}
        responses = [json.dumps({"data": policy}).encode(), b"", json.dumps({"output": {"task_id": "task-1"}}).encode(),
                     json.dumps({"output": {"task_status": "RUNNING", "task_id": "task-1"}}).encode(),
                     json.dumps({"output": {"task_status": "SUCCEEDED", "task_id": "task-1", "results": [
                         {"subtask_status": "SUCCEEDED", "transcription_url": "https://result.example.test/transcript"}]}}).encode(),
                     json.dumps(raw_asr()).encode()]
        class Response:
            def __init__(self, raw): self.raw = raw
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return self.raw
        def request(req, **kwargs):
            requests.append(req)
            return Response(responses.pop(0))
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,
                {"SPEECH_TO_TEXT_BASE_URL": "https://asr.example.test/api/v1", "SPEECH_TO_TEXT_API_KEY": "stub-secret"}):
            audio = Path(directory) / "audio.wav"
            audio.write_bytes(b"fixture")
            with patch.object(transcribe.urllib.request, "urlopen", side_effect=request), patch.object(transcribe.time, "sleep") as sleep:
                provider = transcribe.build_provider("fun_asr", model="fun-asr", sidecar_dir=None, live=True)
                result = provider.transcribe(audio, language="zh")
            self.assertTrue(document(result["segments"])["auto_cut_allowed"])
            self.assertEqual(len(requests), 6)
            sleep.assert_called_once()
            self.assertIsNone(requests[1].get_header("Authorization"))
            self.assertIsNone(requests[-1].get_header("Authorization"))
            self.assertEqual(requests[2].get_header("Authorization"), "Bearer stub-secret")
            self.assertEqual(json.loads(requests[2].data)["model"], "fun-asr")
            self.assertIn(b"\r\n", requests[1].data)
            self.assertNotIn(b"\\r\\n", requests[1].data)

    def test_cloud_rejects_mismatched_task_or_failed_subtask(self):
        for output in ({"task_id": "other", "task_status": "RUNNING"},
                       {"task_id": "task-1", "task_status": "SUCCEEDED", "results": [{"subtask_status": "FAILED"}]},
                       {"task_id": "task-1", "task_status": "FAILED"}):
            with self.subTest(output=output), tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SPEECH_TO_TEXT_API_KEY": "stub-secret"}):
                audio = Path(directory) / "a.wav"
                audio.write_bytes(b"fixture")
                provider = transcribe.FunASRFileProvider("fun-asr")
                policy = {"upload_dir": "test", "upload_host": "https://upload.test", "policy": "stub",
                    "signature": "signature", "oss_access_key_id": "key", "x_oss_object_acl": "private", "x_oss_forbid_overwrite": "true"}
                with patch.object(provider, "_request", side_effect=[{"data": policy}, None, {"output": {"task_id": "task-1"}}, {"output": output}]):
                    with self.assertRaises(transcribe.TranscriptionError):
                        provider.transcribe(audio)

    def test_schema_forbids_auto_cut_without_words(self):
        result = document([sentence(0, 1, "今天")])
        result["auto_cut_allowed"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(result, SCHEMA)


class SuggestionTests(unittest.TestCase):
    def test_repeated_sentence_and_half_sentence_restart(self):
        for second, reason in (("今天讲算法。", "repeated_sentence"), ("今天讲算法和复杂度。", "interrupted_restart")):
            result = document([sentence(0, 1, "今天讲算法。"), sentence(2, 4, second)])
            matches = spoken.repetition_suggestions(result)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["reason"], reason)
            self.assertFalse(matches[0]["auto_cut_allowed"])
            self.assertIsNone(matches[0]["cut"])

    def test_word_repetition_has_only_original_clock_cut(self):
        result = document(transcribe.normalize_asr_payload(raw_asr())["segments"])
        matches = spoken.repetition_suggestions(result)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["cut"], {"start": 0, "end": 1.6})
        self.assertTrue(matches[0]["needs_review"])

    def test_restart_inside_one_asr_sentence(self):
        words = [{"start": index * .5, "end": (index + 1) * .5, "text": text}
                 for index, text in enumerate(("今天", "我们", "今天", "我们", "讲算法"))]
        result = document([sentence(0, 2.5, "今天我们今天我们讲算法", words)])
        matches = spoken.repetition_suggestions(result)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["cut"], {"start": 0, "end": 1})
        self.assertEqual(matches[0]["repeated_at"], {"start": 1, "end": 2})

    def test_sentence_only_repeat_inside_one_segment_has_no_cut(self):
        result = document([sentence(0, 3, "今天我们今天我们讲算法")])
        matches = spoken.repetition_suggestions(result)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reason"], "sentence_text_repeat")
        self.assertEqual((matches[0]["start"], matches[0]["end"]), (0, 3))
        self.assertIsNone(matches[0]["cut"])
        self.assertEqual(spoken.repetition_suggestions(result, min_chars=121), [])

    def test_repeat_gap_and_minimum_text_boundaries(self):
        result = document([sentence(0, 1, "今天我们"), sentence(3, 4, "今天我们讲算法")])
        self.assertEqual(len(spoken.repetition_suggestions(result, max_gap=2, min_chars=4)), 1)
        self.assertEqual(spoken.repetition_suggestions(result, max_gap=1.999), [])
        self.assertEqual(spoken.repetition_suggestions(result, min_chars=5), [])

    def test_repetition_can_skip_an_intervening_filler_segment(self):
        result = document([sentence(0, 1, "今天我们讲算法"), sentence(1.2, 1.5, "嗯"),
                           sentence(2, 3, "今天我们讲算法")])
        matches = spoken.repetition_suggestions(result)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["repeated_at"], {"start": 2, "end": 3})

    def test_divergent_restart_remains_review_only_even_with_words(self):
        result = document([sentence(0, 1, "今天我们先", [{"start": 0, "end": .5, "text": "今天我们"},
                                                     {"start": .5, "end": 1, "text": "先"}]),
                           sentence(2, 3, "今天我们把算法", [{"start": 2, "end": 2.5, "text": "今天我们"},
                                                          {"start": 2.5, "end": 3, "text": "把算法"}])])
        matches = spoken.repetition_suggestions(result)
        self.assertEqual(matches[0]["reason"], "suspected_prefix_restart")
        self.assertIsNone(matches[0]["cut"])
        self.assertFalse(matches[0]["auto_cut_allowed"])

    def test_different_speakers_do_not_become_retake(self):
        result = document([sentence(0, 1, "今天我们", speaker="a"), sentence(2, 3, "今天我们", speaker="b")])
        self.assertEqual(spoken.repetition_suggestions(result), [])

    def test_animation_word_boundaries_ambiguity_and_unmatched(self):
        result = document(transcribe.normalize_asr_payload(raw_asr())["segments"])
        matches, unmatched = spoken.animation_suggestions(result, [
            {"animation_id": "a1", "spoken_text": "讲算法"}, {"animation_id": "a2", "spoken_text": "不存在的口播"}])
        self.assertEqual([(item["start"], item["end"]) for item in matches], [(.6, 1.6), (3, 4)])
        self.assertTrue(all(item["ambiguous"] and item["match_count"] == 2 for item in matches))
        self.assertTrue(all(item["cut"] is None for item in matches))
        self.assertEqual(unmatched[0]["animation_id"], "a2")

    def test_animation_can_cross_segment_boundaries(self):
        result = document([sentence(0, 1, "今天", [{"start": 0, "end": 1, "text": "今天"}]),
                           sentence(1.2, 2, "算法", [{"start": 1.2, "end": 2, "text": "算法"}])])
        matches, _ = spoken.animation_suggestions(result, [{"animation_id": "a", "spoken_text": "今天算法"}])
        self.assertEqual((matches[0]["start"], matches[0]["end"]), (0, 2))

    def test_sentence_animation_has_only_coarse_bounds(self):
        result = document([sentence(0, 3, "今天讲算法")])
        matches, _ = spoken.animation_suggestions(result, [{"animation_id": "a", "spoken_text": "讲算法"}])
        self.assertEqual((matches[0]["start"], matches[0]["end"]), (0, 3))
        self.assertEqual(matches[0]["precision"], "sentence")
        self.assertFalse(matches[0]["auto_cut_allowed"])

    def test_sentence_only_animation_repeated_in_same_sentence_is_ambiguous(self):
        result = document([sentence(0, 3, "今天我们今天我们讲算法")])
        matches, _ = spoken.animation_suggestions(result, [{"animation_id": "a", "spoken_text": "今天我们"}])
        self.assertEqual(len(matches), 2)
        self.assertTrue(all(item["ambiguous"] for item in matches))
        self.assertTrue(all((item["start"], item["end"]) == (0, 3) for item in matches))

    def test_animation_duplicate_ids_and_empty_text_fail(self):
        result = document([])
        for animations in ([{"animation_id": "a", "spoken_text": ""}],
                           [{"animation_id": "a", "spoken_text": "算法"}] * 2):
            with self.subTest(animations=animations), self.assertRaises(spoken.SuggestionError):
                spoken.animation_suggestions(result, animations)

    def test_forged_precision_and_out_of_source_timing_fail(self):
        result = document([sentence(0, 1, "今天")])
        for bad in ({**result, "precision": "word", "auto_cut_allowed": True},
                    {**result, "segments": [sentence(0, 5, "今天")]}):
            with self.subTest(bad=bad), self.assertRaises(spoken.SuggestionError):
                spoken.validate_transcript(bad, duration=4)

    def test_silence_duration_boundaries_and_eof(self):
        log = "silence_start: 1\nsilence_end: 1.4\nsilence_start: 2.5\n"
        self.assertEqual(spoken.parse_silences(log, duration=3, min_duration=.4), [(1, 1.4), (2.5, 3)])
        self.assertEqual(spoken.parse_silences(log, duration=3, min_duration=.400001), [(2.5, 3)])
        for bad in ("silence_end: 1", "silence_start: 2\nsilence_end: 1", "silence_start: 4"):
            with self.subTest(bad=bad), self.assertRaises(spoken.SuggestionError):
                spoken.parse_silences(bad, duration=3, min_duration=.4)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required for synthetic audio tests")
class SyntheticAudioTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.audio = self.root / "audio.wav"
        # A repeated tone stands in for speech acoustically; ASR text is stubbed.
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1.6",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono:d=0.8", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1.6",
            "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]", "-map", "[out]", str(self.audio)], check=True, capture_output=True, timeout=30)
        self.transcript = document(transcribe.normalize_asr_payload(raw_asr())["segments"])

    def test_real_ffmpeg_and_stub_asr_find_silence_and_repeat(self):
        before = spoken.source_sha256(self.audio)
        result = spoken.generate_suggestions(self.audio, self.transcript,
            animations=[{"animation_id": "a", "spoken_text": "讲算法"}])
        self.assertEqual(result["status"], "candidate")
        self.assertAlmostEqual(result["duration"], 4, places=3)
        silence = next(item for item in result["suggestions"] if item["type"] == "silence")
        self.assertAlmostEqual(silence["start"], 1.6, places=3)
        self.assertAlmostEqual(silence["end"], 2.4, places=3)
        self.assertTrue(silence["auto_cut_allowed"])
        self.assertEqual(len([item for item in result["suggestions"] if item["type"] == "repetition"]), 1)
        self.assertEqual(len([item for item in result["suggestions"] if item["type"] == "animation"]), 2)
        self.assertEqual(spoken.source_sha256(self.audio), before)
        self.assertEqual(result["source_sha256"], before)

    def test_minimum_silence_duration_is_adjustable(self):
        self.assertEqual(len(spoken.detect_silences(self.audio, min_duration=.8)), 1)
        self.assertEqual(spoken.detect_silences(self.audio, min_duration=.801), [])

    def test_probe_uses_audio_clock_when_video_is_longer(self):
        source = self.root / "different-clocks.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=10:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1", "-c:v", "libx264", "-c:a", "aac", str(source)],
            check=True, capture_output=True, timeout=30)
        self.assertAlmostEqual(spoken.probe_duration(source), 1, places=3)

    def test_noise_threshold_is_adjustable(self):
        quiet = self.root / "quiet.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.audio), "-af", "volume=0.01", str(quiet)], check=True, capture_output=True, timeout=30)
        self.assertEqual(spoken.detect_silences(quiet, threshold_db=-55), [(0, 4)])
        intervals = spoken.detect_silences(quiet, threshold_db=-65)
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 1.6, places=3)

    def test_sentence_timing_disables_every_cut(self):
        raw = raw_asr()
        for item in raw["transcripts"][0]["sentences"]:
            item.pop("words")
        result = spoken.generate_suggestions(self.audio, document(transcribe.normalize_asr_payload(raw)["segments"]))
        self.assertFalse(result["auto_cut_allowed"])
        self.assertTrue(result["suggestions"])
        self.assertTrue(all(item["cut"] is None and not item["auto_cut_allowed"] for item in result["suggestions"]))

    def test_asr_word_overlap_vetoes_silence_auto_cut(self):
        words = [{"start": 0, "end": 2, "text": "今天"}, {"start": 2, "end": 4, "text": "算法"}]
        result = spoken.generate_suggestions(self.audio, document([sentence(0, 4, "今天算法", words)]))
        silence = next(item for item in result["suggestions"] if item["type"] == "silence")
        self.assertFalse(silence["auto_cut_allowed"])
        self.assertIsNone(silence["cut"])

    def test_cli_writes_suggestions_only_and_preserves_inputs(self):
        transcript = self.root / "transcript.json"
        transcript.write_text(json.dumps(self.transcript, ensure_ascii=False))
        output = self.root / "edit_suggestions.json"
        hashes = [spoken.source_sha256(path) for path in (self.audio, transcript)]
        run = subprocess.run([sys.executable, str(SYSTEM / "scripts/spoken_edit.py"), str(self.audio), str(transcript), "--output", str(output)],
                             check=True, capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(run.stdout)["suggestion_count"], 2)
        self.assertEqual(json.loads(output.read_text())["status"], "candidate")
        self.assertEqual([spoken.source_sha256(path) for path in (self.audio, transcript)], hashes)
        rejected = subprocess.run([sys.executable, str(SYSTEM / "scripts/spoken_edit.py"), str(self.audio), str(transcript), "--output", str(self.audio)],
                                  capture_output=True, text=True, timeout=30)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(spoken.source_sha256(self.audio), hashes[0])

    def test_process_project_sidecar_persists_word_contract(self):
        analysis = self.root / "ai-analysis"
        analysis.mkdir()
        (analysis / "media-manifest.json").write_text(json.dumps({"items": [{"media_id": "fixture", "audio_path": "audio.wav"}]}))
        self.audio.with_suffix(".json").write_text(json.dumps(raw_asr(), ensure_ascii=False))
        result = transcribe.process_project(self.root, provider=transcribe.SidecarProvider(), language="zh",
                                            overwrite=False, limit=None, allow_pending=False)
        self.assertEqual(result, {"generated": 1, "skipped": 0, "pending": 0, "failed": 0})
        persisted = json.loads((analysis / "transcripts/fixture.transcript.json").read_text())
        self.assertEqual(persisted["precision"], "word")
        jsonschema.validate(persisted, SCHEMA)


if __name__ == "__main__":
    unittest.main()
