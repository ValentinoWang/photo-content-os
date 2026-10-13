"""Direct receipts keep measured failures and completed-shot artwork public."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from video_candidate import failed_shot_progress


class DirectReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ps7-receipt-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frames = self.root / 'frames'
        self.frames.mkdir()
        Image.new('RGB', (108, 192), (30, 90, 70)).save(self.frames / 'frame-000000.png')
        self.native = {'shots': [
            {'id': '01', 'status': 'completed', 'progress_frames': 2, 'total_frames': 2, 'frames_dir': str(self.frames)},
            {'id': '02', 'status': 'failed', 'progress_frames': 0, 'total_frames': 3,
             'code': 'missing_asset', 'line': 14, 'file': '/Users/private/assets/figure.svg',
             'reason': 'private stack /Users/private/shot.html', 'source': 'private source'}]}
        self.descriptor = {'shots': [{'shot': {'shotId': sid}} for sid in ('01', '02')]}

    def test_partial_failure_keeps_real_poster_and_redacts_diagnostics(self):
        before = copy.deepcopy(self.native)
        result = failed_shot_progress(self.native, self.descriptor, 30, output_dir=self.root, workspace=self.root)
        complete, failed = result['shotProgress']
        self.assertEqual(result['failedShotId'], '02')
        self.assertEqual((failed['failedLine'], failed['missingAsset']), (14, 'figure.svg'))
        self.assertNotIn('/Users', json.dumps(result))
        self.assertNotIn('private source', json.dumps(result))
        self.assertNotIn('frames_dir', complete)
        with Image.open(self.root / complete['poster_ref']) as poster:
            self.assertEqual(poster.format, 'JPEG')
            self.assertEqual((poster.width, poster.height), (complete['poster_width'], complete['poster_height']))
            self.assertLessEqual(min(poster.size), 360)
        self.assertLessEqual((self.root / complete['poster_ref']).stat().st_size, 200000)
        self.assertEqual(self.native, before)

    def test_missing_diagnostics_are_unknown_and_retry_filters_unaffected_shot(self):
        descriptor = {**self.descriptor, 'retryShotId': '02'}
        for line, asset in [(None, None), (True, 'bad\nname.svg'), (-1, '..'), (14.2, 'image.svg?secret=x')]:
            with self.subTest(line=line, asset=asset):
                self.native['shots'][1].update(line=line, file=asset)
                result = failed_shot_progress(self.native, descriptor, 30, output_dir=self.root, workspace=self.root)
                self.assertEqual([s['shotId'] for s in result['shotProgress']], ['02'])
                self.assertNotIn('failedLine', result['shotProgress'][0])
                self.assertNotIn('missingAsset', result['shotProgress'][0])
        self.native['shots'][1].update(line=14, file=r'C:\private\figure.svg')
        result = failed_shot_progress(self.native, descriptor, 30)
        self.assertEqual(result['shotProgress'][0]['missingAsset'], 'figure.svg')
