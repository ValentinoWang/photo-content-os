from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from _support import load_script

rewrite = load_script('rewrite_media_references.py', 'media_reference_rewrite', register=True)

class MediaReferenceRewriteTests(unittest.TestCase):
    def test_preserves_whitespace_numbers_and_nonpath_values(self):
        raw = b'{\r\n "materials" : [{ "path": "/old/clip.mp4", "description":"/old/clip.mp4" }], "rate":1.00, "enabled":true}\r\n'
        changes = [{'json_pointer':'/materials/0/path', 'before':'/old/clip.mp4', 'after':'/new/clip.mp4'}]
        updated = rewrite.replace_fields(raw, changes)
        self.assertEqual(updated, raw.replace(b'"path": "/old/', b'"path": "/new/'))
        self.assertEqual(json.loads(updated)['materials'][0]['description'], '/old/clip.mp4')

    def test_escaped_keys_unicode_and_source_drift(self):
        raw = '{"a/b":{"~key":"中文"},"empty":[],"object":{}}'.encode()
        updated = rewrite.replace_fields(raw, [{'json_pointer':'/a~1b/~0key','before':'中文','after':'新标题'}])
        self.assertEqual(json.loads(updated)['a/b']['~key'], '新标题')
        with self.assertRaisesRegex(ValueError, 'source field drift'):
            rewrite.replace_fields(raw, [{'json_pointer':'/a~1b/~0key','before':'错误','after':'新标题'}])

    def test_backups_and_missing_paths_are_kept_and_validator_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); media=root/'media'; media.mkdir(); source=media/'old/clip.mp4'
            source.parent.mkdir(); source.write_bytes(b'original'); target=media/'new/clip.mp4'
            draft=root/'drafts/a'; draft.mkdir(parents=True); path=draft/'draft_content.json'
            missing=str(media/'old/missing.mp4'); raw=json.dumps({'materials':[{'path':str(source)},{'path':missing}],'tracks':[]}).encode()
            path.write_bytes(raw)
            plan={'roots':[str(media/'old')],'moves':[{'from':str(media/'old'),'to':str(media/'new')}]}
            dry=rewrite.rewrite_drafts(plan,draft_root=root/'drafts',backup_root=root/'backup',evidence=root/'evidence',execute=False)
            self.assertEqual(path.read_bytes(),raw); self.assertFalse((root/'backup').exists())
            result=rewrite.rewrite_drafts(plan,draft_root=root/'drafts',backup_root=root/'backup',evidence=root/'evidence',execute=True)
            record=result['records'][0]; self.assertEqual(Path(record['backup']).read_bytes(),raw)
            self.assertEqual(json.loads(path.read_bytes())['materials'][1]['path'],missing)
            self.assertEqual(len(result['unchanged_missing']),1)
            source.parent.rename(target.parent)
            self.assertTrue(rewrite.verify_rewrite(record)['targets_exist'])
            path.write_bytes(path.read_bytes().replace(b'"tracks": []', b'"tracks": [1]'))
            with self.assertRaisesRegex(ValueError,'bytes outside'):
                rewrite.verify_rewrite(record)

    def test_failed_atomic_write_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'draft.json'; path.write_bytes(b'original')
            with patch.object(rewrite.os,'replace',side_effect=OSError('No space left on device')):
                with self.assertRaises(OSError):rewrite.write_atomic(path,b'replacement')
            self.assertEqual(path.read_bytes(),b'original')
            self.assertEqual(list(path.parent.iterdir()),[path])
