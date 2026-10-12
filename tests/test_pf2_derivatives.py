"""Deterministic derivative and selected-cache rejection tests."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from _support import load_script

derivatives = load_script('video_derivatives', 'pf2_derivatives', register=True)
from openclaw_product_contract import ProductContractError
from video_render.multi_shot import RenderError, render_shots


class DerivativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pf2-unit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_jpeg_limits_full_decode_and_strip_metadata(self):
        source = self.root / 'frame.png'
        Image.new('RGB', (1280, 720), 'blue').save(source)
        output = self.root / 'poster.jpg'
        measured = derivatives.jpeg_frame(source, output)
        self.assertEqual(measured, {'width': 640, 'height': 360, 'shortEdge': 360})
        self.assertLessEqual(output.stat().st_size, 200000)
        with Image.open(output) as image:
            image.load(); self.assertEqual(image.getexif(), {})
        output.write_bytes(output.read_bytes()[:60])
        with self.assertRaises(ProductContractError):
            derivatives.inspect_jpeg(output)

    def test_render_code_sha_checked_before_writing(self):
        code = '<script>window.seekFrame=()=>{}</script>'
        value = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        self.assertEqual(derivatives.code_bytes(value), code.encode())
        value['code'] += 'changed'
        with self.assertRaises(ProductContractError) as caught:
            derivatives.code_bytes(value)
        self.assertEqual(caught.exception.code, 'photo_render_code_digest_rejected')

    def test_unselected_missing_cache_never_launches_browser(self):
        assets = self.root / 'assets'; assets.mkdir()
        manifest = {'assets_dir': str(assets), 'shots': [{'id': '01', 'frames': 1}, {'id': '02', 'frames': 1}]}
        with patch('video_render.multi_shot.runtime_identity', return_value={}), patch('video_render.multi_shot.request_for', return_value={}), patch('video_render.multi_shot.fingerprint', return_value='fixture'), patch('video_render.multi_shot.run_renderer', side_effect=AssertionError('Unselected cache launched renderer')):
            with self.assertRaises(RenderError) as caught:
                render_shots(manifest, self.root / 'output', render_shot_ids=['02'])
        self.assertEqual(caught.exception.code, 'unaffected_shot_changed')

    def test_invalid_scope_and_raw_retry_image_rejected(self):
        assets = self.root / 'assets'; assets.mkdir()
        manifest = {'assets_dir': str(assets), 'shots': [{'id': '01'}]}
        with patch('video_render.multi_shot.runtime_identity', return_value={}):
            for ids in ([], ['02'], ['01', '01']):
                with self.assertRaises(RenderError) as caught:
                    render_shots(manifest, self.root / 'output', render_shot_ids=ids)
                self.assertEqual(caught.exception.code, 'shot_revision_rejected')
        with self.assertRaises(ProductContractError) as caught:
            derivatives.create_shot_image(task={'action': 'retry_image', 'shotId': '01'}, source=None, manifest_path=None, output=self.root / 'image')
        self.assertEqual(caught.exception.code, 'photo_image_action_rejected')

    def test_cloned_frames_reuse_inode_and_status_does_not_mutate_previous(self):
        source = self.root / 'old'; (source / 'render/01/frames').mkdir(parents=True)
        frame = source / 'render/01/frames/frame-000000.png'
        Image.new('RGB', (96, 64), 'green').save(frame)
        (source / '.video-render-owner.json').write_text('{"purpose":"compose"}')
        state = {'shots': [{'id': '01', 'frames_dir': str(frame.parent)}]}
        (source / 'render/shot-status.json').write_text(json.dumps(state))
        destination = self.root / 'new'
        derivatives.clone_render_cache(source, destination)
        self.assertEqual(frame.stat().st_ino, (destination / 'render/01/frames/frame-000000.png').stat().st_ino)
        self.assertEqual(json.loads((source / 'render/shot-status.json').read_text()), state)
        self.assertNotEqual(json.loads((destination / 'render/shot-status.json').read_text()), state)

if __name__ == '__main__':
    unittest.main()
