"""R282 frontend fixture coverage; runtime behavior lives in the mounted JS suite."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_handoff_contract_states_are_collected():
    result = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import {R282_STATES,blockSelectors} from './scripts/direct_video/rescript_frontend_gate.mjs';"
         "console.log(JSON.stringify(Object.fromEntries(R282_STATES.map(s=>[s,blockSelectors(s)]))));"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    selectors = json.loads(result.stdout)
    assert set(selectors) == {'first-handoff', 'rescript-newer'}
    contract = json.loads((ROOT / 'docs/tasks/R278-direct-rescript/design/contract.json').read_text())
    for state in ('first-handoff', 'rescript-newer'):
        assert set(selectors[state]) == {key for key in contract['states'] if key.startswith(state + '-')}
        assert all(selectors[state].values())
        data = json.loads((ROOT / f'tests/fixtures/r282-direct/{state}.json').read_text())
        assert len(data['handoff']['handoff']['shots']) == 7
        assert data['handoff']['handoff']['narration']['durationSeconds'] > 0
    legacy = json.loads((ROOT / 'tests/fixtures/r282-direct/first-handoff-legacy.json').read_text())
    expected = json.loads((ROOT / 'tests/fixtures/r282-direct/first-handoff.json').read_text())
    expected['handoff']['handoff'].update(revision=None, handedAt=None)
    assert legacy == expected
