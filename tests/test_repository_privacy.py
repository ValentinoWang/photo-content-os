from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_repository_safety.py'
MEDIA_POLICY = 'scripts/repository-safety-media-allowlist.json'
PATH_BASELINE = 'scripts/repository-safety-path-baseline.json'


class RepositoryPrivacyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.write('scripts/runtime.py', 'print("ok")\n')
        self.write('evidence/old.json', '{"root":"/Users/example/media"}\n')
        self.commit('initial historical evidence')
        self.anchor = self.git('rev-parse', 'HEAD').strip()
        digest = hashlib.sha256((self.root / 'evidence/old.json').read_bytes().rstrip(b'\n')).hexdigest()
        self.baseline = {'schema_version': 1, 'source_commit': self.anchor,
                         'entries': {'evidence/old.json': {digest: 1}}}
        self.policy = {'schema_version': 1, 'files': {}}
        self.save_policies()
        self.commit('freeze policy')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content if isinstance(content, bytes) else content.encode())

    def save_policies(self):
        self.write(MEDIA_POLICY, json.dumps(self.policy))
        self.write(PATH_BASELINE, json.dumps(self.baseline))

    def commit(self, message):
        self.git('add', '--all')
        self.git('commit', '-qm', message)

    def check(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args],
                              text=True, capture_output=True)

    def assert_rejected(self, path, *args):
        result = self.check(*args)
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(path, result.stderr)
        return result.stderr

    def test_new_evidence_png_is_rejected(self):
        self.write('evidence/private.PNG', b'fake synthetic png')
        self.git('add', 'evidence/private.PNG')
        message = self.assert_rejected('evidence/private.PNG')
        self.assertIn('~/.photo-content-os/evidence/', message)

    def test_new_json_with_local_path_is_rejected(self):
        self.write('evidence/new.json', '{"root":"/Users/example/private"}')
        self.git('add', 'evidence/new.json')
        self.assertIn('相对素材根', self.assert_rejected('evidence/new.json'))

    def test_allowlisted_test_image_passes_and_replacement_fails(self):
        content = b'synthetic fixture'
        path = 'tests/fixtures/synthetic.png'
        self.write(path, content)
        self.policy['files'][path] = {'reason': '合成的无人像测试图',
                                     'sha256': hashlib.sha256(content).hexdigest()}
        self.save_policies()
        self.git('add', '--all')
        result = self.check()
        self.assertEqual(0, result.returncode, result.stderr)
        self.write(path, b'replaced private photo')
        self.assert_rejected(path)

    def test_stale_baseline_entry_requires_removal(self):
        self.write('evidence/old.json', '{}\n')
        self.assertIn('删掉', self.assert_rejected('evidence/old.json'))
        self.baseline['entries'] = {}
        self.save_policies()
        self.git('add', '--all')
        self.assertEqual(0, self.check().returncode, self.check().stderr)

    def test_baseline_cannot_grow(self):
        self.write('evidence/new.json', '/home/example/private\n')
        self.baseline['entries']['evidence/new.json'] = {
            hashlib.sha256(b'/home/example/private').hexdigest(): 1}
        self.save_policies()
        self.git('add', '--all')
        self.assert_rejected(PATH_BASELINE)

    def test_new_line_in_historical_file_and_duplicate_are_rejected(self):
        self.write('evidence/old.json', '{"root":"/Users/example/media"}\n' * 2)
        self.assert_rejected('evidence/old.json')

    def test_staged_secret_is_checked_even_if_worktree_is_clean(self):
        self.write('docs/tasks/new.json', '/private/var/private\n')
        self.git('add', '--all')
        self.write('docs/tasks/new.json', '{}\n')
        self.assert_rejected('docs/tasks/new.json')

    def test_intermediate_media_and_text_are_rejected_even_when_deleted(self):
        self.write('evidence/private.png', b'fake png')
        self.write('acceptance/private.json', '/Users/example/private\n')
        self.commit('leak')
        self.git('rm', 'evidence/private.png', 'acceptance/private.json')
        self.commit('delete leak')
        message = self.assert_rejected('evidence/private.png', '--base', self.base)
        self.assertIn('acceptance/private.json', message)

    def test_invalid_base_and_unreadable_policy_fail_closed(self):
        self.assertNotEqual(0, self.check('--base', 'missing-ref').returncode)
        self.write(PATH_BASELINE, '{broken')
        self.assert_rejected(PATH_BASELINE)

    def test_each_required_extension_is_rejected(self):
        for extension in ('jpg', 'jpeg', 'png', 'heic', 'webp', 'gif', 'mp4', 'mov', 'm4a', 'mp3', 'wav', 'aac'):
            with self.subTest(extension=extension):
                path = 'docs/private.' + extension.upper()
                self.write(path, b'not real media')
                self.git('add', path)
                self.assert_rejected(path)
                self.git('rm', '-f', path)

    def test_each_text_scope_and_token_is_rejected(self):
        for directory in ('evidence', 'acceptance', 'docs/tasks'):
            for token in ('/Users/', '/private/var/', '/home/'):
                with self.subTest(directory=directory, token=token):
                    path = directory + '/private.json'
                    self.write(path, token + 'example/private')
                    self.git('add', path)
                    self.assert_rejected(path)
                    self.git('rm', '-f', path)

    def test_utf16_text_cannot_hide_local_path(self):
        self.write('evidence/utf16.json', '/Users/example/private'.encode('utf-16'))
        self.git('add', '--all')
        self.assert_rejected('evidence/utf16.json')

    def test_allowlist_requires_exact_path_and_reason(self):
        path = 'tests/fixtures/*.png'
        self.policy['files'][path] = {'reason': 'test', 'sha256': '0' * 64}
        self.save_policies()
        self.git('add', '--all')
        self.assert_rejected(MEDIA_POLICY)
        self.policy['files'] = {'tests/fixtures/a.png': {'reason': '', 'sha256': '0' * 64}}
        self.save_policies()
        self.git('add', '--all')
        self.assert_rejected(MEDIA_POLICY)

    def test_removed_baseline_entry_cannot_be_restored_in_range(self):
        old = self.baseline['entries']
        self.baseline['entries'] = {}
        self.write('evidence/old.json', '{}')
        self.save_policies()
        self.commit('remove historical path')
        self.write('evidence/old.json', '{"root":"/Users/example/media"}\n')
        self.baseline['entries'] = old
        self.save_policies()
        self.commit('restore historical path')
        self.assert_rejected(PATH_BASELINE, '--base', self.base)

    def test_outside_text_scope_is_allowed(self):
        self.write('docs/reference.md', '/Users/example/test fixture\n')
        self.git('add', '--all')
        result = self.check()
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == '__main__':
    unittest.main()
