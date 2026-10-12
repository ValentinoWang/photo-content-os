"""OA safety invariants, independent of the pinned runtime installation."""
import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from edit_backends.interface import BackendError
from edit_backends.openfilm_adapter import Backend
from edit_backends.registry import get_backend


def test_registration_has_real_adapter_and_no_runtime_side_effects():
    with patch('subprocess.Popen') as popen:
        backend = get_backend('openfilm')
        assert backend.describe()['id'] == 'openfilm'
        assert backend.describe()['capabilities']['read_back'] is True
        popen.assert_not_called()


def test_failure_receipt_when_runtime_missing(tmp_path, monkeypatch):
    monkeypatch.setenv('CONTENT_OS_OPENFILM_PACKAGE', str(tmp_path / 'absent'))
    backend = Backend()
    with patch('edit_backends.kdenlive_render.render') as fallback:
        with pytest.raises(BackendError, match='runtime_unavailable'):
            backend.render(source=tmp_path/'source', suggestions_path=tmp_path/'suggestions', output_dir=tmp_path/'out')
        fallback.assert_not_called()
    receipt = json.loads((tmp_path/'out/render-result.json').read_text())
    assert receipt['status'] == 'failed' and receipt['editor_backend'] == 'openfilm'
    assert not (tmp_path/'out/candidate.mp4').exists()
    assert backend.probe()['runnable'] is False


def test_existing_output_and_receipt_are_immutable(tmp_path):
    receipt = tmp_path/'render-result.json'
    receipt.write_text('human-owned')
    with pytest.raises(BackendError, match='already_exists'):
        Backend().render(source=tmp_path/'source', suggestions_path=tmp_path/'suggestions', output_dir=tmp_path)
    assert receipt.read_text() == 'human-owned'


def state():
    return {'doc': {'stage': {'w': 640, 'h': 360}, 'tracks': [{'clips': [
        {'id': 'first', 'src': 'assets/source.mp4', 'time': [0, 4]},
        {'id': 'second', 'src': 'assets/source.mp4', 'time': [6, 8], 'at': 4},
    ]}]}, 'rev': 'actual-revision'}


@pytest.mark.parametrize('change', ['reorder', 'overlap', 'speed', 'muted', 'outside', 'remote'])
def test_unrepresentable_user_edits_fail_closed(change):
    edited = state()
    track = edited['doc']['tracks'][0]
    if change == 'reorder':
        track['clips'][1]['time'] = [2, 4]
    elif change == 'overlap':
        track['clips'][1]['at'] = 3
    elif change == 'speed':
        track['clips'][1]['speed'] = 2
    elif change == 'muted':
        track['muted'] = True
    elif change == 'outside':
        track['clips'][1]['time'] = [6, 21]
    else:
        track['clips'].append({'src': 'https://example.com/raw.mp4', 'time': [0, 1]})
    with pytest.raises(BackendError):
        Backend._time_map(edited, {'source_duration': 20, 'animation_assets': []})


def test_readback_is_current_project_and_cannot_mutate_internal_binding(tmp_path):
    root = tmp_path/'openfilm-project'
    root.mkdir()
    kwargs = {'source': '/local/source', 'suggestions_path': '/local/plan', 'subtitles': None,
              'animations': [], 'project_id': 'owned', 'project_revision': 2, 'timeout_seconds': 120}
    (root/'adapter-project.json').write_text(json.dumps({'kwargs': kwargs, 'source_duration': 20, 'animation_assets': []}))
    backend = Backend()
    actual = state()
    actual['doc']['tracks'][0]['clips'].pop(0)
    actual['doc']['tracks'][0]['clips'][0]['at'] = 0
    with patch.object(backend, '_state', return_value=actual):
        read = backend.read_back(project_dir=tmp_path)
    assert read['time_map'] == [{'source_start': 6, 'source_end': 8, 'output_start': 0}]
    read['render_kwargs']['project_revision'] = 999
    assert backend._readback['kwargs'] == kwargs


def test_close_is_idempotent_without_starting_an_editor():
    backend = Backend()
    assert backend.close() == backend.close() == {'id': 'openfilm', 'started_pids': [], 'remaining_pids': []}


def test_existing_vp9_alpha_survives_the_working_copy_conversion(tmp_path):
    import os
    import subprocess
    import time
    import PIL.Image

    fixture_value = os.environ.get('EI_TEST_FIXTURE')
    if not fixture_value:
        pytest.skip('real alpha conversion requires the shared synthetic fixture')
    fixture = Path(fixture_value)
    original = tmp_path/'original-alpha.webm'
    try:
        subprocess.run(['ffmpeg','-v','error','-i',str(fixture/'overlay.mov'),'-an',
                        '-c:v','libvpx-vp9','-lossless','1','-pix_fmt','yuva420p',str(original)], check=True, timeout=30)
        kwargs = {'source': str(fixture/'source.mp4'), 'suggestions_path': str(fixture/'edit_suggestions.json'),
                  'subtitles': None, 'animations': [{'path': str(original), 'animation_id': 'overlay-1'}],
                  'project_id': 'alpha-negative', 'project_revision': 1, 'timeout_seconds': 30}
        project, config = Backend()._compile(kwargs, tmp_path/'compiled', time.monotonic()+30)
        command = config['conversions'][1]['command']
        assert command[command.index('-i')-2:command.index('-i')] == ['-c:v','libvpx-vp9']
        raw = subprocess.run(['ffmpeg','-v','error','-c:v','libvpx-vp9','-i',str(project/'assets/overlay-0.webm'),
                              '-frames:v','1','-pix_fmt','rgba','-f','rawvideo','-'],
                             capture_output=True, check=True, timeout=30).stdout
        pixels = PIL.Image.frombytes('RGBA', (160,90), raw)
        histogram = pixels.getchannel('A').histogram()
        assert histogram[0] > 100 and histogram[255] > 100
    finally:
        import shutil
        shutil.rmtree(tmp_path/'compiled', ignore_errors=True)
        original.unlink(missing_ok=True)
