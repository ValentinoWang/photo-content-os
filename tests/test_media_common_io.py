from datetime import datetime, timezone
from pathlib import Path
import sys
import json
import os
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import media_common
import jianying_roughcut_common
import media_project_selection


def test_time_entry_points_preserve_local_and_utc_types(monkeypatch):
    class FixedDatetime:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return datetime(2026, 11, 28, 1, 2, 3)
            assert tz is timezone.utc
            return datetime(2026, 11, 28, 1, 2, 3, 456789, tzinfo=tz)

    monkeypatch.setattr(media_common, 'datetime', FixedDatetime)
    assert jianying_roughcut_common.now_compact() == '20261128_010203'
    assert media_project_selection._now() == datetime(2026, 11, 28, 1, 2, 3, 456789, tzinfo=timezone.utc)


def test_shared_writers_support_format_random_name_fsync_and_mode(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(os, 'fsync', lambda fd: calls.append(fd))
    path = tmp_path / 'nested' / 'value.json'
    media_common.write_json_atomic(path, {'中文': 1}, random_temp=True,
        temp_prefix='.value.', temp_suffix='.tmp', fsync=True, mode=0o600,
        cleanup='always', ensure_ascii=True, sort_keys=True)
    assert path.read_bytes() == b'{\n  "\\u4e2d\\u6587": 1\n}\n'
    assert path.stat().st_mode & 0o777 == 0o600
    assert len(calls) == 1
    assert list(path.parent.iterdir()) == [path]
    media_common.write_text_atomic(path, '文字', hidden_temp=True)
    assert path.read_text(encoding='utf-8') == '文字'
    media_common.write_bytes_atomic(path, b'\x00\xff', random_temp=True, cleanup='always')
    assert path.read_bytes() == b'\x00\xff'
    media_common.write_json_atomic(path, {'中文': 1}, atomic=False)
    assert path.read_text(encoding='utf-8') == json.dumps({'中文': 1}, ensure_ascii=False, indent=2) + '\n'
    jianying_roughcut_common.write_json(path, {'中文': 1})
    assert path.read_text(encoding='utf-8') == json.dumps({'中文': 1}, ensure_ascii=False, indent=2) + '\n'


def test_shared_writer_preserves_destination_and_selected_cleanup_on_failure(tmp_path):
    path = tmp_path / 'state.json'
    path.write_bytes(b'old')
    with pytest.raises(ValueError):
        media_common.write_json_atomic(path, {'bad': float('nan')}, allow_nan=False,
                                       random_temp=True, cleanup='always')
    assert path.read_bytes() == b'old'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('policy,remaining', [('never', 1), ('write_error', 0), ('replace_error', 1), ('error', 0)])
def test_random_temp_cleanup_when_serialization_fails(tmp_path, policy, remaining):
    with pytest.raises(TypeError):
        media_common.write_json_atomic(tmp_path / 'state.json', {'bad': object()},
                                       random_temp=True, cleanup=policy)
    assert len(list(tmp_path.iterdir())) == remaining


@pytest.mark.parametrize('policy,remaining', [('never', 1), ('write_error', 1), ('replace_error', 0), ('error', 0)])
def test_random_temp_cleanup_when_replace_fails(tmp_path, monkeypatch, policy, remaining):
    def fail(*args):
        raise OSError('replace failed')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError, match='replace failed'):
        media_common.write_bytes_atomic(tmp_path / 'state', b'data', random_temp=True, cleanup=policy)
    assert len(list(tmp_path.iterdir())) == remaining


def test_budget_storage_wraps_replace_failure_and_keeps_old_state(tmp_path, monkeypatch):
    from studio.analysis_budget import AnalysisBudgetError, AnalysisBudgetStore
    store = AnalysisBudgetStore(tmp_path)
    store._atomic_write({'old': True})
    old = store.path.read_bytes()
    def fail(*args):
        raise OSError('replace failed')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(AnalysisBudgetError) as exc:
        store._atomic_write({'new': True})
    assert exc.value.code == 'analysis_budget_unavailable'
    assert store.path.read_bytes() == old
    assert list(tmp_path.iterdir()) == [store.path]
