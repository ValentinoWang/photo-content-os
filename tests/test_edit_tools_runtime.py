"""Locked tools, explicit missing-state diagnostics and runtime-path regression."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_repository_safety as safety
import edit_tools_runtime as runtime
import setup_edit_tools as setup
from edit_backends.openchatcut_adapter import Backend as ChatCut
from edit_backends.openfilm_adapter import Backend as Film


@pytest.mark.parametrize('token', ['/Users/private/tool', '~/Desktop/Opensource_Tool/tool', '自媒体创作Agent/tool'])
@pytest.mark.parametrize('relative', ['scripts/adapter.py', 'studio/helper.mjs'])
def test_machine_runtime_path_is_rejected(tmp_path, token, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(repr(token))
    errors = safety.source_violations(tmp_path, Path(relative))
    assert errors and 'machine-runtime-path:1:' in errors[0]
    assert 'environment configuration' in errors[0]


@pytest.mark.parametrize('relative', ['docs/history.md', 'scripts/README.md', 'tests/test_negative.py', 'scripts/fixtures/negative.json'])
def test_historical_docs_and_negative_fixtures_are_excluded(tmp_path, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text('/Users/private/Opensource_Tool')
    assert safety.source_violations(tmp_path, Path(relative)) == []


def test_read_failure_is_not_a_pass(tmp_path):
    errors = safety.source_violations(tmp_path, Path('scripts/missing.py'))
    assert 'cannot read source' in errors[0]


def test_legal_repository_path_passes(tmp_path):
    path = tmp_path / 'scripts/example.py'
    path.parent.mkdir()
    path.write_text("ROOT / '.tools/openchatcut'")
    assert safety.source_violations(tmp_path, Path('scripts/example.py')) == []


def test_uninstalled_and_corrupt_tools_are_explicit(tmp_path):
    (tmp_path / 'third_party').mkdir()
    (tmp_path / 'third_party/edit-tools.lock.json').write_text(json.dumps(runtime.read_lock()))
    for name in ['openfilm', 'openchatcut']:
        missing = runtime.tool_status(name, tmp_path)
        assert missing['status'] == 'unavailable' and not missing['installed']
        assert 'setup_edit_tools.py' in missing['action']
    path = tmp_path / '.tools/openfilm/node_modules/openfilm'
    path.mkdir(parents=True)
    (path / 'package.json').write_text('{bad json')
    corrupt = runtime.tool_status('openfilm', tmp_path)
    assert corrupt['installed'] and corrupt['status'] == 'unavailable'
    assert 'JSONDecodeError' in corrupt['reason']
    (path / 'package.json').write_text('{"version":"9.0.0"}')
    assert 'version mismatch' in runtime.tool_status('openfilm', tmp_path)['reason']


def test_default_paths_do_not_depend_on_home(tmp_path, monkeypatch):
    for key in list(__import__('os').environ):
        if key.startswith('CONTENT_OS_'):
            monkeypatch.delenv(key)
    monkeypatch.setenv('HOME', str(tmp_path))
    backend = ChatCut()
    assert backend.root == runtime.ROOT / '.tools/openchatcut'
    assert backend.node == runtime.ROOT / '.tools/node/bin/node'
    assert backend.slot == runtime.ROOT / 'scripts/qa/with_chromium_slot.sh'
    assert Film()._slot() == backend.slot
    assert Film()._node() == backend.node


def test_explicit_overrides_are_preserved(tmp_path, monkeypatch):
    for key in ['ROOT', 'NODE', 'BROWSER', 'REFINE_BROWSER']:
        monkeypatch.setenv('CONTENT_OS_OPENCHATCUT_' + key, str(tmp_path / key))
    backend = ChatCut()
    assert backend.root == tmp_path / 'ROOT'
    assert backend.node == tmp_path / 'NODE'
    assert backend.browser == tmp_path / 'BROWSER'
    assert backend.refine_browser == tmp_path / 'REFINE_BROWSER'


def test_chromium_slot_configuration_is_passed_through(monkeypatch):
    monkeypatch.setenv('MEDIA_CHROMIUM_MAX_CONCURRENCY', '1')
    monkeypatch.setenv('MEDIA_CHROMIUM_LOCK_ROOT', '/tmp/test-shared-slots')
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-enter-editor')
    env = ChatCut()._environment()
    assert env['MEDIA_CHROMIUM_MAX_CONCURRENCY'] == '1'
    assert env['MEDIA_CHROMIUM_LOCK_ROOT'] == '/tmp/test-shared-slots'
    assert 'OPENAI_API_KEY' not in env


def test_node_reuse_requires_exact_pinned_version():
    import subprocess
    with patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'v22.22.2\n')):
        assert setup.matching_node(Path('node'), '24.13.0') is False
    with patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'v24.13.0\n')):
        assert setup.matching_node(Path('node'), '24.13.0') is True


def test_unreadable_lock_is_explicit(tmp_path):
    status = runtime.tool_status('openfilm', tmp_path)
    assert status['status'] == 'unavailable'
    assert 'FileNotFoundError' in status['reason']


def test_node_archive_checksum_blocks_extraction(tmp_path, monkeypatch):
    (tmp_path / '.tools').mkdir()
    spec = {'version': '24.13.0', 'artifacts': {'darwin-arm64': {'file': 'bad.tar.gz', 'sha256': '0' * 64}}}
    monkeypatch.setattr(setup.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(setup.platform, 'machine', lambda: 'arm64')
    monkeypatch.setattr(setup, 'matching_node', lambda *args: False)
    monkeypatch.setattr(setup.shutil, 'which', lambda name: None)
    monkeypatch.setattr(setup.urllib.request, 'urlretrieve', lambda url, path: path.write_bytes(b'bad archive'))
    with patch.object(setup.tarfile, 'open') as extract:
        with pytest.raises(ValueError, match='SHA-256 mismatch'):
            setup.install_node(tmp_path, spec)
        extract.assert_not_called()
    assert not (tmp_path / '.tools/node').exists()


def test_incomplete_installation_cannot_report_online(tmp_path):
    (tmp_path / 'third_party').mkdir()
    (tmp_path / 'third_party/edit-tools.lock.json').write_text(json.dumps(runtime.read_lock()))
    package = tmp_path / '.tools/openfilm/node_modules/openfilm'
    (package / 'src').mkdir(parents=True)
    (package / 'package.json').write_text('{"version":"0.1.5"}')
    for name in ['render.mjs', 'host.mjs']:
        (package / 'src' / name).write_text('')
    core = package.parent / 'playwright-core'
    core.mkdir()
    (core / 'package.json').write_text('{"version":"1.61.1"}')
    status = runtime.tool_status('openfilm', tmp_path)
    assert status['status'] == 'unavailable'
    assert '.content-os-installed.json' in status['reason']
