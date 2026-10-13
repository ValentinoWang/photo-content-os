"""The same fractional duration and guide steps have one display meaning."""
import json
from pathlib import Path
import subprocess
import unittest


class StudioDisplayTests(unittest.TestCase):
    def test_rounding_carries_minutes_and_empty_animations_skip_the_step(self):
        module = (Path(__file__).resolve().parents[1] / 'studio/static/handoff.js').as_uri()
        code = r'''
import assert from 'node:assert/strict';
const {formatDuration,renderHandoff}=await import(MODULE);
for(const [seconds,label] of [[0,'0:00'],[59.49,'0:59'],[59.5,'1:00'],[65.49,'1:05'],[65.5,'1:06'],[65.8,'1:06'],[74,'1:14'],[3599.5,'60:00']]){
 assert.equal(formatDuration(seconds),label);
}
for(const invalid of [null,undefined,NaN,Infinity])assert.equal(formatDuration(invalid),'—');
globalThis.location={origin:'http://127.0.0.1:8765'};
globalThis.window={addEventListener(){},removeEventListener(){}};
const target={querySelector(){return null},querySelectorAll(){return []}};
const actions={photoOrigin:location.origin};
const data={state:'guide',title:'时长验证',sourceDuration:74,sourceFps:30,
 choice:{method:'guide',editor:'otio_kdenlive'},editors:[{id:'otio_kdenlive',display_name:'Kdenlive',capabilities:{read_back:true},probe:{installed:true,runnable:true,version:'fixture'}}],
 suggestions:[{type:'silence',automatic:true,id:0,start:1,end:9.2,text:'合成静音'}],
 animations:[],materials:[],shots:[],scriptAlignment:{mode:'script',script_version:3,alignment_rate:1},subtitleAvailable:true};
renderHandoff(target,structuredClone(data),actions);
assert(!target.innerHTML.includes('data-design-id="guide-animations"'));
assert.deepEqual([...target.innerHTML.matchAll(/class="step-no">(\d+)/g)].map(m=>Number(m[1])),[1,2]);
assert(target.innerHTML.includes('字幕按预剪后的 1:06 排'));
const animated=structuredClone(data);
animated.suggestions.push({id:1,type:'animation',animationId:'02',start:30,end:38,text:'动画'});
animated.animations.push({shotId:'02',title:'动画',duration:8,totalFrames:240});
renderHandoff(target,animated,actions);
assert(target.innerHTML.includes('data-design-id="guide-animations"'));
assert.deepEqual([...target.innerHTML.matchAll(/class="step-no">(\d+)/g)].map(m=>Number(m[1])),[1,2,3]);
const returned=structuredClone(data);
returned.state='returned';returned.candidate={status:'candidate',durationSeconds:65.8,frameCount:1974};
renderHandoff(target,returned,actions);
assert(target.innerHTML.includes('<p>1:06 · 1974 帧'));
assert(target.innerHTML.includes('workSummary.预计剪后">1:06'));
'''.replace('MODULE', json.dumps(module))
        result = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
