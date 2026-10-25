"""Capture actual HTTP responses with synthetic data and a fake Claude binary."""
import json
from pathlib import Path
import sys
import tempfile
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests')]
from test_r276_direct_api import api, create
from test_r277_api import idle
from test_r277_revisions import image_claude, ImageMedia
import llm_common

output = Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='r277-api-proof-') as temp, pytest.MonkeyPatch.context() as monkey:
    tmp = Path(temp)
    image_claude.__wrapped__(tmp, monkey)
    fixture = api.__wrapped__(tmp / 'state')
    try:
        client = next(fixture)
        request, csrf, pid, app, _ = client
        app.direct_video.generator.model_call = llm_common.generate_text
        app.direct_video.generator.media = ImageMedia()
        path, initial = create(client)
        result = {'initial': initial}
        lines = [{'text': '柱子变灰', 'boxId': 'b3', 'action': 'dim'}]*3 + [{'text': '底色不动', 'own': True}]
        result['reviseAccepted'] = request(path + '/shots/01/revise', 'POST', {'lines': lines}, csrf)[2]
        idle(app)
        result['revised'] = request(path)[2]
        result['logPending'] = request('/api/direct/revision-log')[2]
        proposal = result['logPending']['categories'][0]['proposals'][0]['proposalId']
        result['adopted'] = request('/api/direct/rules/proposals/' + proposal + '/adopt', 'POST', {}, csrf)[2]
        result['reverted'] = request(path + '/shots/01/current', 'POST', {'version': 1}, csrf)[2]
        result['sampleSaved'] = request(path + '/shots/01/sample', 'PUT', {}, csrf)[2]
        result['samples'] = request('/api/direct/samples')[2]
        poster_url = result['samples']['samples'][0]['posterUrl']
        status, headers, image = request(poster_url)
        import hashlib
        result['sampleImage'] = {'status': status, 'contentType': headers['Content-Type'], 'sha256': hashlib.sha256(image).hexdigest()}
        (output / 'api-examples.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
print('Captured actual API responses; temporary server and state removed.')
