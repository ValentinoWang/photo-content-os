from pathlib import Path
import json
import tempfile
import unittest
from types import SimpleNamespace
from _support import load_script

layout=load_script('migrate_media_layout.py','metadata_layout',register=True)
metadata=load_script('migrate_project_metadata.py','project_metadata_migration',register=True)
runner=load_script('mac_openclaw_runner.py','metadata_runner',register=True)

class ProjectMetadataMigrationTests(unittest.TestCase):
    def test_paths_change_but_chinese_title_and_original_media_bytes_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);media=root/'media';old=media/'old-projects/中文主题/中文项目'
            (old/'旧场景').mkdir(parents=True);clip=old/'旧场景/IMG_1234.MOV';clip.write_bytes(b'original media')
            original_title='原中文标题';doc=old/'manifest.json';doc.write_text(json.dumps({'relative_path':'旧场景/IMG_1234.MOV','project_dir':str(old),'title':original_title,'reason':'旧场景是人物的记忆'},ensure_ascii=False))
            note=old/'README.md';note.write_text('# 原中文标题\n\n- 源文件位置：`旧场景/IMG_1234.MOV`\n\n旧场景是人物的记忆。\n')
            roots=[media/'inbox',media/'old-projects',media/'library'];[p.mkdir(parents=True,exist_ok=True) for p in roots]
            plan={'roots':[str(p) for p in roots],'final_roots':[str(media/'inbox'),str(media/'projects'),str(media/'library')],
                  'moves':[{'from':str(media/'old-projects'),'to':str(media/'projects')},
                           {'from':str(old.parent),'to':str(old.parent.with_name('2026-theme'))},
                           {'from':str(old),'to':str(old.with_name('2026-project'))},
                           {'from':str(old/'旧场景'),'to':str(old/'scene')}]}
            layout.apply_plan(plan,execute=True,evidence=root/'rename');before=json.loads((root/'rename/before-files.json').read_bytes())
            final=media/'projects/2026-theme/2026-project'
            dry=metadata.migrate(plan,before,evidence=root/'metadata',execute=False)
            self.assertFalse((final/'project-manifest.json').exists())
            self.assertEqual(json.loads((final/'manifest.json').read_bytes())['relative_path'],'旧场景/IMG_1234.MOV')
            result=metadata.migrate(plan,before,evidence=root/'metadata',execute=True)
            data=json.loads((final/'manifest.json').read_bytes());self.assertEqual(data['relative_path'],'scene/IMG_1234.MOV')
            self.assertEqual(data['title'],original_title);self.assertEqual(data['reason'],'旧场景是人物的记忆')
            self.assertEqual((final/'scene/IMG_1234.MOV').read_bytes(),b'original media')
            self.assertEqual(json.loads((final/'project-manifest.json').read_bytes())['title'],'中文项目')
            self.assertIn('旧场景是人物的记忆',(final/'README.md').read_text())
            self.assertEqual(runner.find_project_by_id(SimpleNamespace(workspace_root=media),'中文项目'),final.resolve())

    def test_project_index_cannot_resolve_outside_media_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);projects=root/'media/projects';projects.mkdir(parents=True);outside=root/'outside';outside.mkdir()
            (projects/'.content-os-project-index.json').write_text(json.dumps({'old-project':str(outside)}))
            with self.assertRaises(runner.RunnerError):runner.find_project_by_id(SimpleNamespace(workspace_root=root/'media'),'old-project')
