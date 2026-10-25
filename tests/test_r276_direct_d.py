"""Composition clocks remain independent of mutable job metadata."""
from datetime import datetime
import io

import pytest

from test_r276_direct_video import ready, wait, wav
from studio.direct_video import projection


def test_composed_at_initial_success_and_recomposition(tmp_path):
    gen, job, _, _ = ready(tmp_path)
    assert projection(job)['output']['composedAt'] is None
    gen.request_compose('project1', job['jobId'])
    first = wait(gen, job)
    stamp = first['output']['composedAt']
    assert datetime.fromisoformat(stamp) >= datetime.fromisoformat(job['createdAt'])
    assert projection(first)['output']['composedAt'] == stamp
    gen.request_compose('project1', job['jobId'])
    second = wait(gen, job)
    assert second['output']['composedAt'] > stamp


def test_rewrite_clears_composed_at(tmp_path):
    gen, job, _, _ = ready(tmp_path)
    gen._compose('project1', job['jobId'])
    assert gen.read('project1', job['jobId'])['output']['composedAt']
    response = gen.rewrite('project1', job['jobId'], '01', '数字再大一点')
    assert projection(response)['output']['composedAt'] is None
    assert projection(wait(gen, job))['output']['composedAt'] is None


@pytest.mark.parametrize('duration', [1, 10])
def test_narration_preserves_composed_at_through_retiming(tmp_path, duration):
    gen, job, _, _ = ready(tmp_path)
    gen._compose('project1', job['jobId'])
    before = gen.read('project1', job['jobId'])
    payload = wav(duration)
    response = gen.narration('project1', job['jobId'], io.BytesIO(payload), len(payload))
    assert response['output']['composedAt'] == before['output']['composedAt']
    after = wait(gen, job)
    assert after['updatedAt'] != before['updatedAt']
    assert projection(after)['output']['composedAt'] == before['output']['composedAt']
    assert after['output']['status'] == 'none'
    # Short narration rewrites shots; longer narration only rerenders.
    assert all(s['attempts'] == (2 if duration == 1 else 1) for s in after['shots'])


def test_failed_recomposition_clears_previous_success(tmp_path):
    gen, job, _, media = ready(tmp_path)
    gen._compose('project1', job['jobId'])
    assert gen.read('project1', job['jobId'])['output']['composedAt']
    def fail(*args):
        raise RuntimeError('synthetic composition failure')
    media.compose = fail
    gen.request_compose('project1', job['jobId'])
    after = wait(gen, job)
    assert after['output']['status'] == 'failed'
    assert projection(after)['output']['composedAt'] is None


def test_old_projection_does_not_infer_composed_at_from_updated_at(tmp_path):
    _, job, _, _ = ready(tmp_path)
    del job['output']['composedAt']
    job['output']['status'] = 'ready'
    job['updatedAt'] = '2026-10-26T02:15:17Z'
    assert projection(job)['output']['composedAt'] is None
