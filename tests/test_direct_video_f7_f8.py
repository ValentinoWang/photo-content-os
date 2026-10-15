"""Real R131 cut coverage and pre-render animation-duration acceptance."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from _support import load_script
subtitles = load_script('video_subtitles', 'r131_f7_subtitles')
load_script('video_render/multi_shot.py', 'r131_f8_multi', register=True)
from video_render import compose as compositor
from video_render.multi_shot import RenderError

FIXTURES = Path(__file__).parent / 'fixtures'


class CrossShotCaptionTests(unittest.TestCase):
    def setUp(self):
        self.descriptor = json.loads((FIXTURES / 'direct-narration-r131-v2.json').read_text())

    def cues(self):
        return subtitles.build_subtitle_cues(self.descriptor, fps=30, total_frames=1719)

    def test_real_cuts_84_and_476_resume_on_the_first_frame(self):
        cues = self.cues()
        for cut in (84, 476):
            with self.subTest(cut=cut):
                previous = next(c for c in cues if c['startFrame'] <= cut-1 < c['endFrame'])
                active = [c for c in cues if c['startFrame'] <= cut < c['endFrame']]
                self.assertEqual(len(active), 1, 'spoken cue must continue at cut, not disappear')
                self.assertEqual(previous['endFrame'], cut, 'F3: exclusive end prevents old cue at cut')
                self.assertEqual(active[0]['startFrame'], cut)
                self.assertNotEqual(previous['text'], active[0]['text'], 'new proportional fragment at cut')
                self.assertNotIn(previous, active)
        self.assertEqual(''.join(c['text'] for c in cues), ''.join(t['text'] for t in self.descriptor['narration']['sentenceTimings']))

    def test_every_spoken_frame_of_the_real_full_film_has_a_caption(self):
        cues = self.cues()
        for timing in self.descriptor['narration']['sentenceTimings']:
            start = round(Fraction(str(timing['startSeconds'])) * 30)
            end = min(1718, round(Fraction(str(timing['endSeconds'])) * 30))
            for frame in range(start, end):
                with self.subTest(frame=frame):
                    self.assertEqual(sum(c['startFrame'] <= frame < c['endFrame'] for c in cues), 1)
        # Inspect every frame against the unquantized speech intervals too.
        # The existing exclusive final-frame rule permits one trailing frame;
        # no run of missing captions during speech may exceed two frames.
        missing_run = 0
        for frame in range(1719):
            spoken = any(t['startSeconds'] <= frame/30 < t['endSeconds'] for t in self.descriptor['narration']['sentenceTimings'])
            covered = any(c['startFrame'] <= frame < c['endFrame'] for c in cues)
            missing_run = missing_run+1 if spoken and not covered else 0
            self.assertLessEqual(missing_run, 2, f'speech caption gap at frame {frame}')
        for cue in cues:
            self.assertEqual(''.join(cue['lines']), cue['text'].rstrip('。，'))
            self.assertIn(len(cue['lines']), (1, 2))
            self.assertTrue(all(len(line) <= 14 and line[0] not in '。，、：；！？」）,.!?;:)]}》】”’' for line in cue['lines']))
            if len(cue['lines']) == 2:
                self.assertLessEqual(abs(len(cue['lines'][0])-len(cue['lines'][1])), 4)
                self.assertTrue(all(sum(ch.isalnum() for ch in line) >= 4 for line in cue['lines']))

    def test_multiple_cuts_and_punctuation_preserve_spoken_text(self):
        text = '先写下今天担心的事情，再回来逐条检查结果。'
        descriptor = {'script': text, 'narration': {'sentenceTimings': [{'text': text, 'startSeconds': 0, 'endSeconds': 3}]},
                      'shots': [{'shot': {'startSeconds': a, 'endSeconds': b}} for a,b in [(0,.8),(.8,1.6),(1.6,3)]]}
        cues = subtitles.build_subtitle_cues(descriptor, fps=30, total_frames=91)
        self.assertEqual(''.join(c['text'] for c in cues), text)
        for cut in (24,48):
            self.assertTrue(any(c['startFrame'] == cut for c in cues))
            self.assertFalse(any(c['startFrame'] < cut < c['endFrame'] for c in cues))
        self.assertTrue(all(any(c['startFrame'] <= frame < c['endFrame'] for c in cues) for frame in range(90)))

    def test_single_character_crossing_many_cuts_gets_new_cue_intervals(self):
        descriptor = {'script':'好','narration':{'sentenceTimings':[{'text':'好','startSeconds':0,'endSeconds':1}]},
                      'shots':[{'shot':{'startSeconds':a,'endSeconds':b}} for a,b in [(0,.2),(.2,.4),(.4,1)]]}
        cues = subtitles.build_subtitle_cues(descriptor, fps=30, total_frames=31)
        self.assertEqual([(c['startFrame'],c['endFrame'],c['text']) for c in cues],[(0,6,'好'),(6,12,'好'),(12,30,'好')])


class AnimationDurationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r131-f8-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        assets = self.root / 'assets'; assets.mkdir()
        (assets/'font.ttf').write_bytes(b'preflight-never-launches-browser')
        (assets/'04.html').write_bytes((FIXTURES/'r131-v2-shot-04.html').read_bytes())
        with wave.open(str(self.root/'voice.wav'), 'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(3000); wav.writeframes(b'\0\0' * 3100)
        self.manifest = {'width':96,'height':64,'fps':30,'assets_dir':'assets','fonts':[{'path':'assets/font.ttf'}],
                         'narration_wav':'voice.wav','shots':[{'id':'04','html':'04.html','frames':31}]}
        self.path = self.root/'manifest.json'

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_real_shot_04_is_blocked_before_any_renderer_or_candidate(self):
        self.save()
        with patch.object(compositor, 'render_shots', return_value={'status':'failed','shots':[]}) as render:
            with self.assertRaises(RenderError) as raised:
                compositor.compose(self.path, self.root/'output')
        self.assertEqual(raised.exception.code, 'animation_duration_too_short')
        self.assertIn('04', str(raised.exception)); self.assertIn('1.033333', str(raised.exception)); self.assertIn('1.540000', str(raised.exception))
        render.assert_not_called()
        report = json.loads((self.root/'output/animation-duration-checks.json').read_text())
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['shots'][0]['status'],'failed')
        self.assertAlmostEqual(report['shots'][0]['minimumSeconds'],1.54)
        self.assertIsNone(json.loads((self.root/'output/compose-status.json').read_text())['candidate'])
        self.assertFalse((self.root/'output/candidate.mp4').exists())

    def test_undeclared_is_explicitly_skipped_and_equal_threshold_passes(self):
        (self.root/'assets/04.html').write_text('<script>const D = 1;</script>')
        (self.root/'assets/05.html').write_text('<p>const D = 999;</p><script>// const D = 999;\nconst label = "const D = 999;";</script>')
        self.manifest.pop('narration_wav')
        self.manifest['shots']=[{'id':'04','html':'04.html','frames':21,'narration_wav':'voice.wav'},
                                {'id':'05','html':'05.html','frames':21,'narration_wav':'voice.wav'}]
        with wave.open(str(self.root/'voice.wav'),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(3000);wav.writeframes(b'\0\0'*2100)
        self.save()
        with patch.object(compositor,'render_shots',return_value={'status':'failed','shots':[]}):
            compositor.compose(self.path,self.root/'output')
        report=json.loads((self.root/'output/animation-duration-checks.json').read_text())
        self.assertEqual([s['status'] for s in report['shots']],['passed','not_declared'])
        self.assertEqual(report['shots'][1]['reason'],'未声明 const D，跳过时长检查')
        self.assertEqual(report['status'],'partial')

    def test_unreadable_and_invalid_declarations_never_become_undeclared(self):
        from video_render.animation_duration import animation_duration_checks, declared_duration
        for literal in ['0','-1','Infinity','NaN','1e999','duration','1+2',"'2.2'"]:
            with self.subTest(literal=literal):
                (self.root/'assets/04.html').write_text(f'<script>const D = {literal};</script>')
                report = animation_duration_checks({'fps':30,'shots':[{'id':'04','html':str(self.root/'assets/04.html'),'frames':31}]})
                self.assertEqual(report['status'],'failed')
                self.assertEqual(report['shots'][0]['code'],'animation_duration_invalid')
        with self.assertRaises(ValueError):
            declared_duration('<script>const D;</script>')
        report = animation_duration_checks({'fps':30,'shots':[{'id':'04','html':str(self.root/'missing.html'),'frames':31}]})
        self.assertEqual(report['shots'][0]['status'],'failed')
        self.assertEqual(declared_duration('<script>const W=1080, D=2.2e0;</script>'), Fraction(11,5))
        self.assertIsNone(declared_duration('<script type="application/json">{"text":"const D = 999;"}</script>'))


if __name__ == '__main__':
    unittest.main()
