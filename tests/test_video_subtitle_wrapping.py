"""Chinese display wrapping without changing spoken-text provenance."""
import json
from pathlib import Path
import tempfile
import unittest

from _support import load_script
subtitles = load_script('video_subtitles', 'subtitle_wrapping')


class SubtitleWrappingTests(unittest.TestCase):
    def assert_display_rules(self, raw, lines):
        self.assertEqual(''.join(lines), raw.rstrip('。，'))
        self.assertIn(len(lines), [1, 2])
        for line in lines:
            self.assertTrue(line)
            self.assertLessEqual(len(line), 14)
            self.assertNotIn(line[0], '。，、：；！？」）,.!?;:)]}》】”’')
            self.assertFalse(all(not ch.isalnum() for ch in line), 'punctuation-only line')
        self.assertFalse(lines[-1].endswith(('。', '，')))
        if len(raw.rstrip('。，')) <= 14:
            self.assertEqual(len(lines), 1)
        if len(lines) == 2:
            self.assertLessEqual(abs(len(lines[0])-len(lines[1])), 4)
            for line in lines:
                self.assertGreaterEqual(sum(ch.isalnum() for ch in line), 4)

    def test_four_real_captions_have_no_orphan_punctuation_or_short_tail(self):
        for text in ['别人的注意，远比我们以为的少。', '第二句：担心的事，一定会发生。',
                     '所以我先写下几条标准，满足了就发。', '我只给自己一条规矩：不连着断两次。']:
            with self.subTest(text=text):
                self.assert_display_rules(text, subtitles._lines(text))

    def test_full_film_45_cues_preserve_raw_speech_and_obey_display_rules(self):
        descriptor=json.loads((Path(__file__).parent/'fixtures/direct-narration-r131.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'subtitles.srt'
            cues=subtitles.write_direct_subtitles(descriptor,path,fps=30,total_frames=4276)
            self.assertEqual(len(cues),45)
            raw=''.join(t['text'] for t in descriptor['narration']['sentenceTimings'])
            self.assertEqual(''.join(c['text'] for c in cues),raw)
            exported=subtitles.review_module().read_srt_cues(path)
            self.assertEqual(''.join(c[2].replace('\n','') for c in exported),raw)
            for i,cue in enumerate(cues):
                with self.subTest(cue=i+1,raw=cue['text']):
                    self.assert_display_rules(cue['text'],cue['lines'])

    def test_single_line_and_question_exclamation_marks_are_preserved(self):
        for text in ['今天写两行字。','今天先做一件小事，','你准备好了吗？','继续发！','十四个字以内的单行字幕。']:
            with self.subTest(text=text):
                lines=subtitles._lines(text)
                self.assert_display_rules(text,lines)
                self.assertEqual(len(lines),1)

    def test_balanced_punctuation_break_is_preferred_and_closing_marks_cannot_lead(self):
        text='把今天担心的事写下，过两天再回来对照结果。'
        lines=subtitles._lines(text)
        self.assert_display_rules(text,lines)
        self.assertTrue(lines[0].endswith('，'))
        for text in ['甲乙丙丁戊己庚辛壬癸子丑寅，卯辰巳午未申酉戌亥甲乙。',
                     '我说「先做一件小事，再回来看看」就好。']:
            with self.subTest(text=text):self.assert_display_rules(text,subtitles._lines(text))


if __name__=='__main__':unittest.main()
