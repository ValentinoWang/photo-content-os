"""One real service-level sample and one revision; all media stays outside Git."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from studio.project_store import ProjectStore
from studio.direct_video import DirectVideo

EVIDENCE = ROOT / 'evidence/2026-10-26/R278-direct-rescript'
MEDIA = Path.home() / '.photo-content-os/evidence/R278-direct-rescript'
MEDIA.mkdir(parents=True, exist_ok=True)
state = Path(tempfile.mkdtemp(prefix='live-', dir=MEDIA))
result = {'state': state.name, 'transport': 'llm_common.generate_text / claude_cli / claude-opus-5-5',
          'account': '~/.claude-account3', 'scope': 'service-level, no HTTP server or UI browser', 'steps': []}
service = DirectVideo(ProjectStore(state))
project = service.store.create_project(title='R278 独立样张实测')
pid = project['id']
gen = service.generator
shot = json.loads(Path(os.environ['R278_STORYBOARD']).read_text())['shots'][0]
body = {'text': '浅米色底，深青做主色，结论只用橙色。标题要粗，数字特别大。每句只动一个东西，动完就停。',
        'shot': {'shotId': '01', 'dialogue': shot['dialogue']}}


def save():
    (EVIDENCE / 'live-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


def run_step(name, action):
    start = time.perf_counter()
    row = action()
    did = row['draftId']
    root = gen.path(pid, did)
    before = result.get('recordedEvents', 0)
    while gen.active:
        if shutil.disk_usage(state).free < 3 * 1024 ** 3:
            raise RuntimeError('disk_below_3gb')
        time.sleep(.5)
    elapsed = round(time.perf_counter() - start, 3)
    final = service.draft(pid, did)
    events = json.loads((root / 'metrics.json').read_text()) if (root / 'metrics.json').exists() else []
    current = events[before:]
    result['recordedEvents'] = len(events)
    step = {'step': name, 'elapsedSeconds': elapsed, 'status': final['status'], 'failureCode': final['failureCode'],
            'modelCalls': sum(e['phase'] in ('design', 'write') for e in current), 'events': current}
    result['steps'].append(step)
    save()
    print(json.dumps({key: step[key] for key in ('step', 'elapsedSeconds', 'status', 'failureCode', 'modelCalls')}, ensure_ascii=False), flush=True)
    if final['status'] != 'ready':
        return did, False
    for kind, folder in [('poster.jpg', 'posters'), ('clip.mp4', 'clips')]:
        path = service.artifact(pid, did, kind, '01')
        raw = path.read_bytes()
        assert raw
        destination = state / 'inspected-artifacts' / (name + '-' + kind)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        step[kind] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'externalEvidenceRelative': str(destination.relative_to(MEDIA))}
    step['sample'] = final['sample']
    step['design'] = final['design']
    save()
    return did, True


try:
    did, passed = run_step('initial', lambda: service.draft(pid, body=body))
    if passed:
        _, passed = run_step('revised', lambda: service.draft(pid, did, {'instruction': '主色再深一点'}, revise=True))
    result['passed'] = passed
except Exception as exc:
    result.update(passed=False, error=type(exc).__name__)
finally:
    # This process owns only this freshly-created state directory.
    for path in state.rglob('cache'):
        shutil.rmtree(path)
    result['remainingFrameFiles'] = sum(1 for _ in state.rglob('frame-*.png'))
    result['totalModelCalls'] = sum(s['modelCalls'] for s in result['steps'])
    result['processComplete'] = True
    save()
