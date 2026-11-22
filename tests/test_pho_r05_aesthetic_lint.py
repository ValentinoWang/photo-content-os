"""Protect upstream R1–R3 and the direct-video canvas and subtitle safe zone."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from direct_video.lint import lint


def shot(*, body='', elements='', canvas='width:1080px;height:1920px'):
    return f"""<!doctype html><html><head><style>
html,body{{margin:0;{canvas};overflow:hidden}}
</style></head><body {body}><header data-role="header">标题</header>
{elements}<script>const D = 6; window.seekFrame = (frame, fps) => {{}};</script>
</body></html>"""


class AestheticLintTest(unittest.TestCase):
    def assertWarning(self, code, good, bad, *, seconds=6):
        self.assertEqual(lint(good, '', seconds), {'errors': [], 'warnings': []})
        result = lint(bad, '', seconds)
        self.assertEqual(result['errors'], [])
        self.assertIn(code, [warning['code'] for warning in result['warnings']])

    def test_r1_key_information_holds_one_second(self):
        def markup(settled):
            return shot(body=f'data-hold="{settled}-6"',
                        elements=f'<div data-key-landed data-motion-end="{settled}">结论</div>')
        self.assertWarning('aesthetic_r1_key_hold', markup(5), markup(5.1))

    def test_r1_hold_counts_only_time_after_key_lands(self):
        code = shot(body='data-hold="4-6"',
                    elements='<div data-key-landed data-motion-end="5.5">结论</div>')
        self.assertIn('aesthetic_r1_key_hold', [item['code'] for item in lint(code, '', 6)['warnings']])

    def test_r2_half_second_tail_hold(self):
        good = shot(body='data-batch-entrance data-hold="1-2,5.5-6"')
        bad = shot(body='data-batch-entrance data-hold="1-2,5.6-6"')
        self.assertWarning('aesthetic_r2_tail_hold', good, bad)

    def test_r2_declared_motion_is_not_linear(self):
        def markup(curve):
            return shot(elements=f'<div data-motion-easing="{curve}" data-motion-start="1" data-motion-end="2">主画面</div>')
        self.assertWarning('aesthetic_r2_linear_motion', markup('ease-out'), markup('linear'))

    def test_r3_opening_arc_last_at_least_three_seconds(self):
        self.assertWarning('aesthetic_r3_opening_arc',
                           shot(body='data-opening-arc="0.5-3.5"'),
                           shot(body='data-opening-arc="0.5-3.4"'))

    def test_subtitle_safe_band_scales_with_canvas_height(self):
        tall = shot(elements='<div data-subtitle-safe style="top:820px;height:45px">正文</div>')
        wide = shot(elements='<div data-subtitle-safe style="top:820px;height:45px">正文</div>',
                    canvas='width:1920px;height:1080px')
        self.assertWarning('subtitle_safe_zone', tall, wide)
        boundary = shot(elements='<div data-subtitle-safe style="top:820px;height:44px">正文</div>',
                        canvas='width:1920px;height:1080px')
        self.assertEqual(lint(boundary, '', 6), {'errors': [], 'warnings': []})

    def test_unreadable_canvas_is_an_error(self):
        code = shot(canvas='width:1920px;height:100%')
        result = lint(code, '', 6)
        self.assertEqual([error['code'] for error in result['errors']], ['canvas_size_unreadable'])

    def test_landscape_directory_entry_uses_actual_duration(self):
        code = shot(body='data-hold="4-6"',
                    elements='<div data-key-landed data-motion-end="4" data-subtitle-safe '
                             'style="top:820px;height:44px">结论</div>',
                    canvas='width:1920px;height:1080px')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / '01.html').write_text(code, encoding='utf-8')
            run = [sys.executable, str(ROOT / 'scripts/direct_video/lint.py'), str(root)]
            good = subprocess.run(run, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(good.stdout)['01'], {'errors': [], 'warnings': []})
            durations = root / 'duration.json'
            durations.write_text('{"fps":30,"frames":{"01":145}}')
            truncated = subprocess.run([*run, '--durations', str(durations)],
                                       capture_output=True, text=True, check=True)
            self.assertEqual(
                [item['code'] for item in json.loads(truncated.stdout)['01']['warnings']],
                ['duration_differs', 'aesthetic_r1_key_hold'],
            )


if __name__ == '__main__':
    unittest.main()
