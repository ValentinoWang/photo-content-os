from pathlib import Path
import json
import unittest
from tempfile import TemporaryDirectory
from _support import load_script

migration = load_script('migrate_media_layout.py', 'media_layout_migration', register=True)

class MediaLayoutMigrationTests(unittest.TestCase):
    def test_nested_moves_preserve_every_file_hash_and_dry_run_is_read_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'old'
            child = original / 'nested'
            child.mkdir(parents=True)
            media = child / 'IMG_1234.MOV'
            media.write_bytes(b'original media bytes')
            note = child / 'note.md'
            note.write_text('unchanged explanation')
            plan = {'roots': [str(original)], 'final_roots': [str(root / 'new')],
                    'moves': [{'from':str(original), 'to':str(root/'new')},
                              {'from':str(child), 'to':str(original/'renamed')},
                              {'from':str(note), 'to':str(child/'readme.md')}]}
            dry = migration.apply_plan(plan, execute=False, evidence=root/'evidence')
            self.assertTrue(media.exists())
            self.assertFalse((root/'new').exists())
            result = migration.apply_plan(plan, execute=True, evidence=root/'evidence')
            self.assertEqual(dry['before'], result['after'])
            self.assertTrue(result['hashes_equal'])
            self.assertEqual((root/'new/renamed/IMG_1234.MOV').read_bytes(), b'original media bytes')
            self.assertEqual((root/'new/renamed/readme.md').read_text(), 'unchanged explanation')

    def test_existing_target_is_rejected_before_any_moves(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            target = root/'target'
            source.mkdir(); target.mkdir()
            plan = {'roots':[str(source)], 'final_roots':[str(target)],
                    'moves':[{'from':str(source),'to':str(target)}]}
            with self.assertRaises(FileExistsError):
                migration.apply_plan(plan, execute=True, evidence=root/'evidence')
            self.assertTrue(source.exists())
