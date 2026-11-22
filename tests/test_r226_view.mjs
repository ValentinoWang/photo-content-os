import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
const path=new URL('../studio/static/review-cut.js',import.meta.url);
const url=path.href;
const {presentPlan,noticeForFailure,beatMapOptions,createCutView}=await import(url);
const fixture=()=>JSON.parse(fs.readFileSync(new URL('./fixtures/r226-editing-techniques/api/cut-ready.json',import.meta.url),'utf8'));
test('presentation preserves backend metrics, occurrences and source ranges',()=>{
 const f=fixture(), p=presentPlan(f.roughcut,f.shots.shots,f.music.tracks);
 assert.equal(p.total,f.roughcut.plan.metrics.duration_sec);
 assert.equal(p.used,f.roughcut.plan.metrics.used_technique_count);
 assert.deepEqual(p.cuts,f.roughcut.plan.cuts);
 assert.equal(p.occ.length,f.roughcut.plan.occurrences.length);
 for(const c of p.clips){const raw=f.roughcut.plan.clips.find(x=>x.shot_id===c.shot.id);assert.equal(c.srcIn,raw.source_start);}
 for(const t of f.roughcut.plan.techniques)assert.equal(p.count(t.id),t.count);
});
test('shared beat map consumes every song and selected swap without local analysis',()=>{
 const f=fixture(), calls=[];
 const options=beatMapOptions(f.roughcut,'pause',2,t=>calls.push(t),i=>calls.push(i));
 assert.equal(options.lane,false);assert.equal(options.fadeOut,1.6);assert.equal(options.selectedSwap,2);
 assert.equal(options.songs.length,f.roughcut.plan.songs.length);
 assert.deepEqual(options.songs[0].beatMap,f.roughcut.analysis[0].beat_map);
 options.onSwapClick(2);assert.deepEqual(calls,[2]);
});
test('unreadable, unavailable and missing use distinct approved notices',()=>{
 assert.equal(noticeForFailure({code:'beat_analysis_unavailable'}).title,'拍子分析还不能用');
 assert.equal(noticeForFailure({code:'roughcut_state_unreadable'}).title,'读不到这件作品的粗剪记录');
 assert.equal(noticeForFailure({code:'revision_conflict'}).title,'这件作品刚在别处改过');
 assert.equal(noticeForFailure({code:'preview_failed'}).title,'预览没生成出来');
 assert.equal(noticeForFailure({code:'unregistered_failure'}),null);
});
test('route and confirmation enter the cut view',()=>{
 const view=fs.readFileSync(new URL('../studio/static/review-view.js',import.meta.url),'utf8');
 const shots=fs.readFileSync(new URL('../studio/static/review-shots.js',import.meta.url),'utf8');
 assert.match(view,/route\.step\s*===?\s*['"]cut['"]/);
 assert.match(shots,/step:'cut'/);
 assert.doesNotMatch(shots,/配乐卡点下一阶段上线/);
});
test('renderer exposes bounded lifecycle',()=>{assert.equal(typeof createCutView,'function');});
function fakeRoot(){return {innerHTML:'',dataset:{},classList:{add(){}},querySelector:()=>null,querySelectorAll:()=>[],onkeydown:null};}
const noMusic=()=>JSON.parse(fs.readFileSync(new URL('./fixtures/r226-editing-techniques/api/cut-no-music.json',import.meta.url),'utf8'));
function payloadFor(f,path){if(path.endsWith('/roughcut'))return f.roughcut;if(path.endsWith('/shots'))return f.shots;if(path.endsWith('/editor-capabilities'))return f.capabilities;if(path.endsWith('/editing-presets'))return f.presets;if(path.endsWith('/music'))return f.music;throw Error(path);}
test('stale load from another piece never overwrites the current view',async()=>{
 const f=noMusic(),root=fakeRoot();let release;const delayed=new Promise(r=>release=r);let active='a';
 const view=createCutView({root:()=>root,mark(){},active:id=>id===active,go(){},request:async path=>{if(path.includes('/pieces/a/'))await delayed;return payloadFor(f,path);}});
 const first=view.render({id:'a'},'A');active='b';await view.render({id:'b'},'B');const current=root.innerHTML;release();await first;
 assert.equal(root.innerHTML,current);assert.ok(root.innerHTML.startsWith('B'));view.stop();
});
test('read failures show an approved notice and never render an empty music library',async()=>{
 const root=fakeRoot();const view=createCutView({root:()=>root,mark(){},active:()=>true,request:async()=>{throw Object.assign(new Error('private diagnostic'),{code:'roughcut_state_unreadable'});}});
 const original=console.error;console.error=()=>{};
 try{await view.render({id:'test'},'');assert.match(root.innerHTML,/读不到这件作品的粗剪记录/);assert.doesNotMatch(root.innerHTML,/音乐库里的歌|private diagnostic|先给这/);}finally{console.error=original;view.stop();}
});
test('no-music view binds counts to confirmed backend selection, including escaping',async()=>{
 const f=noMusic(),root=fakeRoot();f.roughcut.source_summary.selected_shot_count=41;f.music.tracks[0].title='<script>alert(1)</script>';
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async path=>payloadFor(f,path)});
 await view.render({id:'test'},'');assert.match(root.innerHTML,/>41<\/span> 个镜头/);assert.match(root.innerHTML,/&lt;script&gt;/);assert.doesNotMatch(root.innerHTML,/<script>alert/);view.stop();
});
test('shared step label respects backend multi-source capability without weakening R228',async()=>{
 const {draftEditorNote}=await import('../studio/static/review-common.js');
 for(const [editor,label] of [['chatcut','ChatCut'],['openchatcut','OpenChatCut']])assert.equal(draftEditorNote({editor,method:'external'},[{id:'chatcut_mcp',status:'ready'}],{can_generate:false,block_reason:'multi_source_unverified'}),label+' 还出不了这件作品');
});
test('missing song analysis leaves no dangling metadata separator',async()=>{
 const f=noMusic(),root=fakeRoot();f.music.tracks[0].bpm=null;f.music.tracks[0].beat=null;
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async path=>payloadFor(f,path)});
 await view.render({id:'test'},'');assert.doesNotMatch(root.innerHTML,/ · <span data-design-data><\/span><\/small>/);view.stop();
});
test('stopped first arrangement returns to the approved music picker',async()=>{
 const f=noMusic(),root=fakeRoot();f.roughcut.status='stopped';f.roughcut.display.base_state=null;
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async path=>payloadFor(f,path)});
 await view.render({id:'test'},'');assert.match(root.innerHTML,/音乐库里的歌/);assert.equal(root.dataset.designState,'cut-no-music');view.stop();
});
test('reanalysis replays the failed selection with fresh revisions and no empty command',async()=>{
 const f=noMusic(),root=fakeRoot(),commands=[],song={dataset:{songUse:f.music.tracks[1].file_sha256}},retry={dataset:{failureAction:'重新分析'}};
 root.querySelectorAll=s=>s==='[data-song-use]'?[song]:s==='[data-failure-action]'?[retry]:[];
 const failure=JSON.parse(fs.readFileSync(new URL('./fixtures/r226-editing-techniques/api/cut-failed.json',import.meta.url),'utf8')).roughcut.failure;
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async(path,options={})=>{
  if(path.endsWith('/commands')){commands.push(structuredClone(options.body));f.roughcut.revision++;f.roughcut.selection.playlist=[{id:'song-new',track_id:song.dataset.songUse}];f.roughcut.status=commands.length===1?'failed':'arranging';f.roughcut.display.base_state=commands.length===1?'cut-failed':'cut-arranging';f.roughcut.failure=commands.length===1?failure:null;return {ok:true};}
  if(path.endsWith('/reanalyze')){assert.deepEqual(options.body,{part:'beat'});f.roughcut.revision=21;f.roughcut.project_revision=13;return {ok:true,beat:{status:'queued',queue_position:1}};}
  return payloadFor(f,path);
 }});
 await view.render({id:'test'},'');song.onclick();for(let i=0;i<20&&!root.innerHTML.includes('重新分析');i++)await new Promise(setImmediate);
 await retry.onclick();assert.equal(commands.length,2);assert.deepEqual(commands[1].command,commands[0].command);assert.equal(commands[1].expectedRevision,21);assert.equal(commands[1].projectRevision,13);assert.equal(commands[1].selectionDigest,f.roughcut.source_summary.selection_digest);view.stop();
});
function failedMusic(){return JSON.parse(fs.readFileSync(new URL('./fixtures/r226-editing-techniques/api/cut-failed.json',import.meta.url),'utf8'));}
test('reanalysis never replays after leaving the piece',async()=>{
 const f=failedMusic(),root=fakeRoot(),retry={dataset:{failureAction:'重新分析'}};let release,commands=0;const pending=new Promise(r=>release=r);
 root.querySelectorAll=s=>s==='[data-failure-action]'?[retry]:[];
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async(path)=>{if(path.endsWith('/reanalyze')){await pending;return {ok:true};}if(path.endsWith('/commands'))commands++;return payloadFor(f,path);}});
 await view.render({id:'test'},'');const action=retry.onclick();view.stop();release();await action;assert.equal(commands,0);
});
test('reanalysis does not replay when latest revisions cannot be read',async()=>{
 const f=failedMusic(),root=fakeRoot(),retry={dataset:{failureAction:'重新分析'}};let analyzed=false,commands=0;
 root.querySelectorAll=s=>s==='[data-failure-action]'?[retry]:[];
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async(path)=>{if(path.endsWith('/reanalyze')){analyzed=true;return {ok:true};}if(path.endsWith('/commands'))commands++;if(analyzed&&path.endsWith('/roughcut'))throw Object.assign(new Error('read failed'),{code:'roughcut_state_unreadable'});return payloadFor(f,path);}});
 await view.render({id:'test'},'');await retry.onclick();assert.equal(commands,0);assert.match(root.innerHTML,/读不到这件作品的粗剪记录/);view.stop();
});
function draftFixture(name){return JSON.parse(fs.readFileSync(new URL('./fixtures/r226-editing-techniques/api/'+name+'.json',import.meta.url),'utf8'));}
function surfaceRoot(){const root=fakeRoot(),overlays={'#songov':{hidden:true},'#libov':{hidden:true}};root.querySelector=s=>overlays[s]||null;return root;}
async function draftSurface(f,request){const root=surfaceRoot();const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:request|| (async path=>payloadFor(f,path))});await view.render({id:f.roughcut.piece_id},'');return {root,view};}
test('draft result state comes from independent draft projection, not roughcut status',async()=>{
 for(const [name,title,label] of [['cut-drafting','正在用','正在出草稿'],['cut-drafted','草稿出好了，可以在','草稿已出好'],['cut-drafted-guide','剪点清单出好了','草稿已出好'],['cut-draft-stale','粗剪改过了，草稿还是上一版','草稿是上一版']]){
  const f=draftFixture(name);assert.equal(f.roughcut.status,'ready');const {root,view}=await draftSurface(f);
  try{assert.equal(root.dataset.designState,name);assert.ok(root.innerHTML.includes(title));assert.ok(root.innerHTML.includes(label));assert.match(root.innerHTML,/role="status"/);if(name==='cut-drafting')assert.match(root.innerHTML,/disabled aria-disabled="true"[^>]*data-draft>正在出草稿/);else assert.match(root.innerHTML,/data-draft>重新出草稿/);if(name==='cut-draft-stale')assert.doesNotMatch(root.innerHTML,/R226-DRAFT-OPEN|R226-DRAFT-HANDOFF/);}finally{view.stop();}
 }
});
test('handoff uses the indexed artifact in a new tab; open follows can_open',async()=>{
 for(const canOpen of [true,false]){const f=draftFixture('cut-drafted');f.roughcut.draft.can_open=canOpen;const {root,view}=await draftSurface(f);
  try{assert.equal(root.innerHTML.includes('R226-DRAFT-OPEN'),canOpen);assert.match(root.innerHTML,/R226-DRAFT-HANDOFF[^>]*href="\/api\/review\/pieces\/[^\"]+\/roughcut\/media\/synthetic-guide"[^>]*target="_blank"[^>]*rel="noopener"/);assert.doesNotMatch(root.innerHTML,/download=|blob:/);}finally{view.stop();}
 }
});
test('draft failure shows N11, preserves timeline and removes status block',async()=>{
 const f=draftFixture('cut-drafted');f.roughcut.draft={...f.roughcut.draft,status:'failed',design_state:null,can_open:false,failure:{code:'draft_failed'}};const {root,view}=await draftSurface(f);
 try{assert.match(root.innerHTML,/草稿没出成/);assert.doesNotMatch(root.innerHTML,/role="status"|R226-DRAFT-OPEN/);assert.match(root.innerHTML,/R226-TIMELINE/);}finally{view.stop();}
});
test('open sends final draft digest and current revisions without a client file path',async()=>{
 const f=draftFixture('cut-drafted'),root=surfaceRoot(),open={};let body;
 root.querySelectorAll=s=>s==='[data-draft-open]'?[open]:[];
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async(path,options)=>{if(path.endsWith('/drafts/open')){body=options.body;return {ok:true,opened:true};}return payloadFor(f,path);}});
 try{await view.render({id:f.roughcut.piece_id},'');assert.equal(typeof open.onclick,'function');await open.onclick();assert.deepEqual(body,{expectedRevision:f.roughcut.revision,projectRevision:f.roughcut.project_revision,editorChoiceRevision:f.capabilities.choice.revision,edlDigest:f.roughcut.draft.edl_digest});assert.notEqual(body.edlDigest,f.roughcut.plan_input_binding.edl_digest);}finally{view.stop();}
});
test('draft job is polled while arrangement is ready; completion reloads and stop cancels next poll',async()=>{
 const f=draftFixture('cut-drafting'),timers=[],original=global.setTimeout;global.setTimeout=(fn)=>{timers.push(fn);return 0;};let polls=0;const root=surfaceRoot();
 const view=createCutView({root:()=>root,mark(){},active:()=>true,go(){},request:async path=>{if(path.includes('/roughcut-jobs/')){polls++;assert.ok(path.endsWith('/'+f.roughcut.draft.job_id));f.roughcut.draft=draftFixture('cut-drafted').roughcut.draft;return {status:'done'};}return payloadFor(f,path);}});
 try{await view.render({id:f.roughcut.piece_id},'');assert.equal(timers.length,1);await timers.shift()();assert.equal(polls,1);assert.equal(root.dataset.designState,'cut-drafted');assert.equal(timers.length,0);view.stop();}finally{global.setTimeout=original;view.stop();}
});
test('real music taxonomy supplies all three section labels',async()=>{
 const f=fixture();const {root,view}=await draftSurface(f);
 try{for(const section of f.music.taxonomy.sections)assert.ok(root.innerHTML.includes('>'+section.name+'</span>'));}finally{view.stop();}
});
test('timeline and preset geometry is not encoded in CSP-blocked style attributes',async()=>{
 const {root,view}=await draftSurface(fixture());
 try{assert.doesNotMatch(root.innerHTML,/\sstyle=/);}finally{view.stop();}
});
test('zero-duration mapped section boundaries do not become a song entry section or visible stripe',()=>{
 const f=draftFixture('cut-multi');const raw=f.roughcut.plan;const song=raw.songs[1];
 assert.ok(raw.mapped_sections.some(s=>s.song_id===song.id&&s.start===s.end));
 const before=structuredClone(raw.mapped_sections);const p=presentPlan(f.roughcut,f.shots.shots,f.music.tracks);
 assert.equal(p.songs[1].kind,raw.mapped_sections.find(s=>s.song_id===song.id&&s.end>s.start).kind);
 assert.ok(p.secs.every(s=>s.end>s.start));assert.deepEqual(raw.mapped_sections,before);
});
