"""Script alignment regressions, including the cached P3 real ASR result."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from _support import load_script

spoken = load_script('spoken_edit.py', 'sa_spoken')


def handoff(script):
    return {'identity': {'work_id': 'fixture', 'work_revision': 2}, 'script': script}


def transcript(text):
    words = []
    for i, char in enumerate(text):
        if char.isalnum():
            words.append({'text': char, 'start': i, 'end': i + .5})
        elif words:
            words[-1]['text'] += char
    return spoken.validate_transcript({'segments': [{'start_sec': 0, 'end_sec': len(text),
        'text': text, 'words': words}]}, duration=len(text))


def align(text, script, **kwargs):
    return spoken.script_alignment(transcript(text), handoff(script), threshold=.8, min_chars=4, **kwargs)


class ScriptAlignmentTests(unittest.TestCase):
    def test_keeps_last_complete_and_cuts_multiple_earlier_attempts(self):
        receipt, suggestions, _ = align('今天讲算法。今天讲算法。今天讲算法。', '今天讲算法。')
        self.assertEqual(receipt['alignment_rate'], 1)
        self.assertEqual(receipt['sentences'][0]['start'], 12)
        self.assertEqual([s['start'] for s in suggestions], [0, 6])
        self.assertTrue(all(s['auto_cut_allowed'] for s in suggestions))

    def test_same_sentence_in_script_preserves_required_occurrences(self):
        receipt, suggestions, _ = align('今天讲算法。今天讲算法。', '今天讲算法。\n今天讲算法。')
        self.assertEqual(receipt['alignment_rate'], 1)
        self.assertEqual(suggestions, [])

    def test_global_coverage_precedes_last_occurrence(self):
        receipt, suggestions, _ = align('今天讲算法。然后讲应用。今天讲算法。', '今天讲算法。然后讲应用。')
        self.assertEqual(receipt['alignment_rate'], 1)
        self.assertEqual(receipt['sentences'][0]['start'], 0)
        self.assertEqual(suggestions[0]['type'], 'review')
        self.assertFalse(suggestions[0]['auto_cut_allowed'])

    def test_prefix_restart_is_repeat_and_adlib_is_review_only(self):
        _, suggestions, _ = align('今天讲算法，顺便说趣事。今天讲算法和应用。', '今天讲算法和应用。')
        self.assertEqual([s['type'] for s in suggestions], ['repetition', 'review'])
        self.assertTrue(suggestions[0]['auto_cut_allowed'])
        self.assertEqual(suggestions[0]['reason'], 'script_interrupted_restart')
        self.assertIsNone(suggestions[1]['cut'])

    def test_divergent_tail_is_not_an_automatic_restart(self):
        _, suggestions, _ = align('今天讲算法太累。今天讲算法和应用。', '今天讲算法和应用。')
        self.assertEqual([s['type'] for s in suggestions], ['review'])

    def test_missing_sentence_has_no_fabricated_cut(self):
        receipt, suggestions, _ = align('今天讲算法和各种应用。', '今天讲算法和各种应用。好。')
        self.assertEqual(receipt['mode'], 'script')
        self.assertEqual(receipt['missing_sentences'], [{'sentence_index': 1, 'text': '好。'}])
        self.assertEqual(suggestions, [])

    def test_missing_low_alignment_and_threshold_are_explicit(self):
        d = transcript('今天讲算法。今天讲算法。')
        for h, reason in [(None, 'missing_script'), (handoff('完全不同的稿件。'), 'low_alignment')]:
            receipt, suggestions, _ = spoken.script_alignment(d, h, threshold=.8, min_chars=4)
            self.assertEqual(receipt['mode'], 'transcript_only')
            self.assertEqual(receipt['notice'], '没有按稿对齐')
            self.assertEqual(receipt['reason'], reason)
            self.assertEqual(receipt['threshold'], .8)
            self.assertEqual(suggestions, [])
        for threshold in [True, 0, 1.1, float('nan')]:
            with self.subTest(threshold=threshold), self.assertRaises(spoken.SuggestionError):
                spoken.script_alignment(d, None, threshold=threshold, min_chars=4)

    def test_coarse_and_other_speaker_never_receive_repeat_cut(self):
        d = spoken.validate_transcript({'segments': [{'start_sec': 0, 'end_sec': 5,
            'text': '今天讲算法。今天讲算法。'}]}, duration=5)
        _, suggestions, _ = spoken.script_alignment(d, handoff('今天讲算法。'), threshold=.8, min_chars=4)
        self.assertTrue(suggestions)
        self.assertTrue(all(s['cut'] is None for s in suggestions))
        d = transcript('今天讲算法。今天讲算法。')
        d['segments'][0]['speaker'] = 'A'
        # Preserve exact word evidence while assigning each sentence a speaker.
        first = d['segments'][0]
        d['segments'] = [{**first, 'text': '今天讲算法。', 'words': first['words'][:5], 'end_sec': 4.5},
                         {**first, 'text': '今天讲算法。', 'words': first['words'][5:], 'start_sec': 6, 'speaker': 'B'}]
        _, suggestions, _ = spoken.script_alignment(d, handoff('今天讲算法。'), threshold=.8, min_chars=4)
        self.assertFalse(any(s['auto_cut_allowed'] for s in suggestions))

    def test_descriptor_versions_and_disagreement(self):
        mx = handoff('今天讲算法。')
        h = {'script': mx['script'], 'mxHandoff': mx, 'documentRef': {'revision': 7}}
        receipt, _, _ = spoken.script_alignment(transcript(mx['script']), h, threshold=.8, min_chars=4)
        self.assertEqual((receipt['work_revision'], receipt['script_version']), (2, 7))
        self.assertEqual(receipt['version_basis'], 'documentRef.revision')
        h['script'] = '替换的稿件。'
        with self.assertRaises(spoken.SuggestionError):
            spoken.script_alignment(transcript(mx['script']), h, threshold=.8, min_chars=4)

    def test_retained_match_inside_acoustic_word_cannot_authorize_a_cut(self):
        d = spoken.validate_transcript({'segments': [{'start_sec': 0, 'end_sec': 4,
            'text': '今天讲算法。今天讲算法呀。', 'words': [
                {'start': 0, 'end': 1, 'text': '今天讲算法。'},
                {'start': 2, 'end': 4, 'text': '今天讲算法呀。'}]}]}, duration=4)
        _, suggestions, _ = spoken.script_alignment(d, handoff('今天讲算法。'), threshold=.8, min_chars=4)
        self.assertTrue(suggestions)
        self.assertTrue(all(s['cut'] is None for s in suggestions))

    def test_p3_cached_real_words_reject_both_false_positives(self):
        fixture = json.loads(Path(__file__).with_name('fixtures').joinpath('spoken_script_p3.json').read_text())
        d = spoken.validate_transcript(fixture['transcript'], duration=73.99)
        receipt, suggestions, _ = spoken.script_alignment(d, handoff(fixture['target_script']), threshold=.8, min_chars=4)
        self.assertEqual(receipt['alignment_rate'], 1)
        self.assertEqual([(s['reason'], s['start'], s['end']) for s in suggestions], [
            ('script_repeated_sentence', 6.59, 9.15), ('script_interrupted_restart', 39.64, 41.12)])
        self.assertTrue(all(s['auto_cut_allowed'] for s in suggestions))
        original, suggestions, _ = spoken.script_alignment(d, handoff(fixture['original_script']), threshold=.8, min_chars=4)
        self.assertEqual(original['alignment_rate'], 1)
        self.assertEqual(suggestions, [])

    def test_silence_only_between_sentences_and_fallback_detection(self):
        d = transcript('今天讲算法。然后讲应用。')
        with patch.object(spoken, 'source_sha256', return_value='unchanged'), patch.object(spoken, 'probe_duration', return_value=12), \
                patch.object(spoken, 'detect_silences', return_value=[(2.5, 3), (5, 6)]):
            result = spoken.generate_suggestions(Path(__file__), d, handoff=handoff('今天讲算法。然后讲应用。'))
        self.assertEqual([(s['start'], s['end']) for s in result['suggestions']], [(5, 6)])
        self.assertEqual(result['suggestions'][0]['basis'], 'silence')
        for h in [None, handoff('对不上的稿件。')]:
            with patch.object(spoken, 'source_sha256', return_value='unchanged'), patch.object(spoken, 'probe_duration', return_value=14), \
                    patch.object(spoken, 'detect_silences', return_value=[]):
                result = spoken.generate_suggestions(Path(__file__), transcript('今天讲算法。今天讲算法。'), handoff=h)
            self.assertEqual(result['script_alignment']['mode'], 'transcript_only')
            self.assertTrue(any(s['basis'] == 'repetition' for s in result['suggestions']))


if __name__ == '__main__':
    unittest.main()
