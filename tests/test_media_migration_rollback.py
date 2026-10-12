from pathlib import Path
import json
import tempfile
import unittest
from _support import load_script

layout=load_script('migrate_media_layout.py','rollback_layout',register=True)
rollback=load_script('rollback_media_migration.py','media_migration_rollback',register=True)

class MediaMigrationRollbackTests(unittest.TestCase):
    def test_reverse_moves_restore_every_original_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'old';(old/'child').mkdir(parents=True)
            (old/'child/IMG_1234.MOV').write_bytes(b'original');(old/'child/note.md').write_bytes(b'old path')
            plan={'roots':[str(old)],'final_roots':[str(root/'new')], 'moves':[{'from':str(old),'to':str(root/'new')},{'from':str(old/'child'),'to':str(old/'renamed')}]}
            evidence=root/'evidence';layout.apply_plan(plan,execute=True,evidence=evidence/'rename')
            note=root/'new/renamed/note.md';backup=evidence/'note-before.md';backup.write_bytes(note.read_bytes());note.write_bytes(b'new path')
            created=root/'new/project-manifest.json';created.write_bytes(b'{"title":"test"}')
            record={'file':str(note),'backup':str(backup),'before_sha256':rollback.sha256(b'old path'),'after_sha256':rollback.sha256(b'new path')}
            (evidence/'metadata-migration.json').write_text(json.dumps({'records':[record]}));(evidence/'draft-rewrite.json').write_text(json.dumps({'records':[]}))
            (evidence/'final-verification.json').write_text(json.dumps({'created_files':[{'file':str(created),'sha256':rollback.sha256(created.read_bytes())}],'original_roots':[str(old)],'final_roots':[str(root/'new')]}))
            (evidence/'final-files.json').write_text(json.dumps(layout.inventory([root/'new'])))
            self.assertTrue(rollback.rollback(evidence,execute=False)['dry_run']);self.assertTrue(note.exists())
            note.write_bytes(b'user edit')
            with self.assertRaisesRegex(ValueError,'tree edited'):rollback.rollback(evidence,execute=False)
            self.assertEqual(note.read_bytes(),b'user edit')
            note.write_bytes(b'new path')
            self.assertTrue(rollback.rollback(evidence,execute=True)['original_file_hashes_restored'])
            self.assertEqual((old/'child/IMG_1234.MOV').read_bytes(),b'original');self.assertEqual((old/'child/note.md').read_bytes(),b'old path')
            self.assertFalse(created.exists())
            note=old/'child/note.md';note.write_bytes(b'user edit')
            with self.assertRaises((ValueError,FileNotFoundError)):rollback.rollback(evidence,execute=False)
