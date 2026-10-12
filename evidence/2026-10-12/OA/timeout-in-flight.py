"""Real render cancellation proof, independent of EI's preflight timeout case."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root/'scripts'))
from edit_backends import openfilm_adapter as adapter

fixture = Path('/Users/vsiyo/Desktop/创业项目/自媒体创作Agent/docs/development/video-pipeline-build/editor-shots/evidence/fixture')
evidence = Path(__file__).parent
backend = adapter.Backend()
observed = set()
original_stop = adapter._stop

def observed_stop(proc):
    observed.update(adapter._descendants(proc.pid))
    return original_stop(proc)

with tempfile.TemporaryDirectory(prefix='oa-timeout-proof-') as temp:
    output = Path(temp)/'render'
    try:
        with patch.object(adapter, '_stop', side_effect=observed_stop):
            backend.render(source=fixture/'source.mp4', suggestions_path=fixture/'edit_suggestions.json',
                           subtitles=fixture/'source.srt', animations=[{'path': str(fixture/'overlay.mov'), 'animation_id': 'overlay-1'}],
                           output_dir=output, project_id='oa-timeout-proof', project_revision=21, timeout_seconds=20)
    except adapter.BackendError:
        pass
    finally:
        close = backend.close()
    receipt = json.loads((output/'render-result.json').read_text())
    log = (output/'openfilm.log').read_text() if (output/'openfilm.log').exists() else ''
    current = adapter._process_table()
    proof = {'receipt': receipt, 'actual_frames_started': 'rendering 420 frames' in log,
             'observed_owned_pids': sorted(observed), 'remaining_observed_pids': sorted(observed.intersection(current)),
             'close': close, 'candidate_exists': (output/'candidate.mp4').exists()}
    (evidence/'timeout-in-flight.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    (evidence/'timeout-in-flight.log').write_text(log)
    assert proof['actual_frames_started'], 'queue wait is not an in-flight render proof'
    assert receipt['status'] == 'failed' and receipt['editor_backend'] == 'openfilm'
    assert not proof['remaining_observed_pids'] and not proof['candidate_exists']
print('actual render cancellation and process cleanup passed')
