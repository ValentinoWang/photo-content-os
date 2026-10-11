"""Real local-browser/FFmpeg tests; no ASR, TTS, model or editor calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from _support import load_script

multi = load_script('video_render/multi_shot.py', 'pc_multi_shot', register=True)
from video_render.compose import audio_inputs, compose
from video_render.multi_shot import RenderError, load_manifest, owned_workspace, render_shots, sha256
from video_render.teaching_clips import teaching_clips

FONT = Path(os.environ.get('VIDEO_RENDER_TEST_FONT', '/System/Library/Fonts/Supplemental/Arial.ttf'))
CHROME = Path(os.environ.get('VIDEO_RENDER_TEST_BROWSER', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))


def create_fixture(workspace: Path, *, shots: int = 3) -> Path:
    assets = workspace / 'assets'
    assets.mkdir(parents=True)
    shutil.copyfile(FONT, assets / 'font.ttf')
    colors = ['red', 'green', 'blue']
    storyboard = []
    for index in range(shots):
        shot_id = f'shot-{index + 1}'
        (assets / f'{shot_id}.html').write_text(f'''<!doctype html>
<html><head><meta charset="utf-8"></head><body>
<div id="box" style="position:absolute;left:0;top:0;width:24px;height:24px;background:{colors[index]}">A</div>
<script>
window.seekFrame = async (frame, fps) => {{
  document.getElementById('box').style.left = (frame * 3) + 'px';
}};
</script></body></html>''', encoding='utf-8')
        storyboard.append({'id': shot_id, 'html': f'{shot_id}.html', 'frames': 6, 'start_frame': index * 6,
                           'animation_requirement': 'Move box', 'spoken_text': f'fixture {index + 1}'})
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-f', 'lavfi', '-i',
                    f'sine=frequency=440:sample_rate=48000:duration={shots * 0.5}', '-c:a', 'pcm_s16le', str(workspace / 'voice.wav')], check=True)
    manifest = workspace / 'manifest.json'
    manifest.write_text(json.dumps({'width': 96, 'height': 64, 'fps': 12, 'timeout_seconds': 20,
                                    'assets_dir': 'assets', 'fonts': [{'path': 'assets/font.ttf'}],
                                    'browser_executable': str(CHROME), 'narration_wav': 'voice.wav', 'shots': storyboard}), encoding='utf-8')
    return manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='pc-unit-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'assets').mkdir()
        (self.root / 'assets/font.ttf').write_bytes(b'unit-font')
        self.manifest = self.root / 'manifest.json'
        self.value = {'width': 96, 'height': 64, 'fps': 12, 'assets_dir': 'assets',
                      'fonts': [{'path': 'assets/font.ttf'}], 'shots': [{'id': 'one', 'html': 'one.html', 'frames': 6}]}

    def load(self):
        self.manifest.write_text(json.dumps(self.value))
        return load_manifest(self.manifest)

    def assert_invalid(self, code='invalid_input'):
        with self.assertRaises(RenderError) as error:
            self.load()
        self.assertEqual(error.exception.code, code)

    def test_rejects_gap_and_overlap(self):
        for start in (5, 7):
            with self.subTest(start=start):
                self.value['shots'] = [{'id': 'one', 'html': 'one.html', 'frames': 6}, {'id': 'two', 'html': 'two.html', 'frames': 6, 'start_frame': start}]
                self.assert_invalid()

    def test_rejects_duplicate_and_unsafe_ids(self):
        self.value['shots'].append(dict(self.value['shots'][0]))
        self.assert_invalid()
        self.value['shots'] = [{'id': '../escape', 'html': 'one.html', 'frames': 6}]
        self.assert_invalid()

    def test_requires_explicit_fixed_font(self):
        self.value['fonts'] = []
        self.assert_invalid('font_missing')
        self.value['fonts'] = [{'path': 'missing.ttf'}]
        self.assert_invalid('font_missing')

    def test_rejects_escape_and_invalid_frame_geometry(self):
        self.value['shots'][0]['html'] = '../outside.html'
        self.assert_invalid('asset_outside_root')
        self.value['shots'][0]['html'] = 'one.html'
        for key, value in [('width', 95), ('fps', False), ('height', 0)]:
            with self.subTest(key=key):
                original = self.value[key]
                self.value[key] = value
                self.assert_invalid()
                self.value[key] = original

    def test_timeout_must_be_finite(self):
        for timeout in (0, -1, True, float('nan'), float('inf')):
            with self.subTest(timeout=timeout):
                self.value['timeout_seconds'] = timeout
                self.assert_invalid()

    def test_refuses_unowned_output_and_overlapping_roots(self):
        manifest = self.load()
        for output in [self.root, self.root / 'assets/render']:
            with self.assertRaises(RenderError) as error:
                render_shots(manifest, output)
            self.assertEqual(error.exception.code, 'invalid_output')
        output = self.root / 'output'
        output.mkdir()
        (output / 'unrelated.txt').write_text('keep')
        with self.assertRaises(RenderError):
            render_shots(manifest, output)
        self.assertEqual((output / 'unrelated.txt').read_text(), 'keep')

    def test_audio_required_and_mixed_modes_rejected(self):
        with self.assertRaises(RenderError) as error:
            audio_inputs(self.load())
        self.assertEqual(error.exception.code, 'audio_missing')
        self.value['narration_wav'] = 'voice.wav'
        self.value['shots'][0]['narration_wav'] = 'one.wav'
        self.assert_invalid()

    def test_export_ownership_lock_and_reusable_workspace(self):
        output = self.root / 'owned'
        assets = self.root / 'assets'
        with owned_workspace(output, assets, 'compose'):
            with self.assertRaises(RenderError) as error:
                with owned_workspace(output, assets, 'compose'):
                    self.fail('Second writer acquired the same workspace')
            self.assertEqual(error.exception.code, 'render_busy')
        with owned_workspace(output, assets, 'compose'):
            pass
        with self.assertRaises(RenderError) as error:
            with owned_workspace(output, assets, 'teaching'):
                self.fail('Incompatible output owner was accepted')
        self.assertEqual(error.exception.code, 'invalid_output')

    def test_failed_preflight_clears_previous_candidate_receipt(self):
        self.load()
        output = self.root / 'previous-compose'
        with owned_workspace(output, self.root / 'assets', 'compose'):
            (output / 'compose-status.json').write_text(json.dumps({'status': 'completed', 'candidate': 'old.mp4'}))
        with self.assertRaises(RenderError):
            compose(self.manifest, output)
        receipt = json.loads((output / 'compose-status.json').read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertIsNone(receipt['candidate'])
        self.assertEqual(receipt['code'], 'audio_missing')

    def test_runtime_failure_updates_status_and_preserves_verified_cache(self):
        manifest = self.load()
        output = self.root / 'previous-render'
        output.mkdir()
        previous = {'status': 'completed', 'shots': [{'id': 'one', 'status': 'completed', 'fingerprint': 'verified'}]}
        (output / 'shot-status.json').write_text(json.dumps(previous))
        with patch('video_render.multi_shot.runtime_identity', side_effect=RenderError('runtime_unavailable', 'fixture runtime missing')):
            with self.assertRaises(RenderError):
                render_shots(manifest, output)
        receipt = json.loads((output / 'shot-status.json').read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['code'], 'runtime_unavailable')
        self.assertEqual(receipt['shots'], previous['shots'])


@unittest.skipUnless(FONT.is_file() and CHROME.is_file() and shutil.which('node') and shutil.which('ffmpeg') and shutil.which('ffprobe') and os.environ.get('VIDEO_RENDER_PLAYWRIGHT_MODULE'),
                     'Requires explicitly configured local Playwright module, font, browser and FFmpeg')
class BrowserRenderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='pc-browser-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = create_fixture(self.root)
        self.output = self.root / 'output'

    def test_three_shot_mp4_schedule_tracks_and_original_inputs(self):
        original = sha256(self.root / 'voice.wav')
        events = []
        result = compose(self.manifest, self.output, on_event=events.append)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['checks']['frames'], 18)
        self.assertEqual(result['checks']['duration_seconds'], 1.5)
        self.assertLessEqual(abs(result['checks']['audio_duration_seconds'] - 1.5), 0.1)
        self.assertEqual(result['checks']['video_codec'], 'h264')
        self.assertEqual(result['checks']['audio_codec'], 'aac')
        self.assertEqual(original, sha256(self.root / 'voice.wav'))
        self.assertTrue(any(event.get('progress_frames') == 1 for event in events))
        self.assertTrue(all(shot['progress_frames'] == 6 for shot in result['shots']))

    def test_missing_line14_repair_only_renders_failed_shot(self):
        broken = self.root / 'assets/shot-2.html'
        original = broken.read_text()
        broken.write_text('\n' * 13 + '<img src="fig-3.png">\n' + original)
        first = compose(self.manifest, self.output)
        self.assertEqual(first['status'], 'failed')
        states = first['shots']
        self.assertEqual([shot['status'] for shot in states], ['completed', 'failed', 'completed'])
        self.assertEqual(states[1]['code'], 'missing_asset')
        self.assertEqual(states[1]['line'], 14)
        self.assertIn('第 14 行要读 fig-3.png，素材目录里没有', states[1]['reason'])
        unchanged = {name: (self.output / 'render' / name / 'frames/frame-000000.png').stat().st_mtime_ns for name in ['shot-1', 'shot-3']}
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-f', 'lavfi', '-i',
                        'color=yellow:s=16x16', '-frames:v', '1', str(self.root / 'assets/fig-3.png')], check=True)
        second = compose(self.manifest, self.output)
        self.assertEqual(second['status'], 'completed', second)
        self.assertEqual([shot['cached'] for shot in second['shots']], [True, False, True])
        self.assertEqual([shot['attempts'] for shot in second['shots']], [1, 2, 1])
        for name, timestamp in unchanged.items():
            self.assertEqual(timestamp, (self.output / 'render' / name / 'frames/frame-000000.png').stat().st_mtime_ns)

    def test_same_input_produces_same_frame_hashes_and_explicit_seek(self):
        manifest = load_manifest(self.manifest)
        first = render_shots(manifest, self.root / 'first')
        second = render_shots(manifest, self.root / 'second')
        self.assertEqual(first['status'], 'completed', first)
        self.assertEqual(second['status'], 'completed', second)
        self.assertEqual([shot['frame_hashes'] for shot in first['shots']], [shot['frame_hashes'] for shot in second['shots']])
        hashes = first['shots'][0]['frame_hashes']
        self.assertEqual(len(set(hashes)), 6)

    def test_corrupt_cached_frame_invalidates_only_that_shot(self):
        manifest = load_manifest(self.manifest)
        first = render_shots(manifest, self.output)
        self.assertEqual(first['status'], 'completed', first)
        (self.output / 'shot-2/frames/frame-000000.png').write_bytes(b'corrupt')
        second = render_shots(manifest, self.output)
        self.assertEqual(second['status'], 'completed', second)
        self.assertEqual([shot['cached'] for shot in second['shots']], [True, False, True])
        self.assertEqual(first['shots'][1]['frame_hashes'], second['shots'][1]['frame_hashes'])

    def test_timeout_is_bounded_and_other_shots_continue(self):
        value = json.loads(self.manifest.read_text())
        value['shots'][1]['timeout_seconds'] = 2
        self.manifest.write_text(json.dumps(value))
        (self.root / 'assets/shot-2.html').write_text('<script>window.seekFrame = () => new Promise(() => {});</script>')
        started = time.monotonic()
        result = render_shots(load_manifest(self.manifest), self.output)
        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual([shot['status'] for shot in result['shots']], ['completed', 'failed', 'completed'])
        self.assertEqual(result['shots'][1]['code'], 'shot_timeout')

    def test_remote_asset_is_rejected(self):
        (self.root / 'assets/shot-2.html').write_text('<img src="https://example.invalid/private.png"><script>window.seekFrame=()=>{};</script>')
        result = render_shots(load_manifest(self.manifest), self.output)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['shots'][1]['code'], 'remote_asset')

    def test_independent_solid_and_alpha_teaching_clips(self):
        solid = teaching_clips(self.manifest, self.root / 'solid')
        self.assertEqual(solid['status'], 'completed', solid)
        alpha = teaching_clips(self.manifest, self.root / 'alpha', transparent=True)
        self.assertEqual(alpha['status'], 'completed', alpha)
        for clip in alpha['clips']:
            probe = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', clip['file']], capture_output=True, text=True, check=True)
            stream = json.loads(probe.stdout)['streams'][0]
            self.assertEqual(stream['codec_name'], 'prores')
            self.assertEqual(int(stream['nb_read_frames']), 6)
            self.assertTrue(stream['pix_fmt'].startswith('yuva'))
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', alpha['clips'][0]['file'], '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'])
        self.assertEqual(raw[-1], 0)
        self.assertEqual(raw[(10 * 96 + 10) * 4 + 3], 255)
        self.assertTrue(all(clip['file'].endswith('.mp4') for clip in solid['clips']))

    def test_per_shot_wav_and_mismatch_rejection(self):
        value = json.loads(self.manifest.read_text())
        del value['narration_wav']
        for index, shot in enumerate(value['shots']):
            name = f'voice-{index}.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'lavfi', '-i', 'sine=duration=0.5:sample_rate=48000', str(self.root / name)], check=True)
            shot['narration_wav'] = name
        self.manifest.write_text(json.dumps(value))
        result = compose(self.manifest, self.output)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['checks']['frames'], 18)
        value['shots'][0]['frames'] = 24
        value['shots'][1]['start_frame'] = 24
        value['shots'][2]['start_frame'] = 30
        self.manifest.write_text(json.dumps(value))
        with self.assertRaises(RenderError) as error:
            compose(self.manifest, self.output)
        self.assertEqual(error.exception.code, 'audio_timing_mismatch')


if __name__ == '__main__':
    unittest.main()
