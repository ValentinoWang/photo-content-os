import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';

const source=name=>fs.readFileSync(new URL('../studio/static/'+name,import.meta.url),'utf8');
const moduleUrl=text=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
const commonUrl=moduleUrl(source('review-common.js'));
const common=await import(commonUrl);
const {createShotView}=await import(moduleUrl(source('review-shots.js').replace("'/review-common.js'",JSON.stringify(commonUrl))));
const checks=[{id:'chatcut_mcp',status:'unavailable'},{id:'asset_library',status:'not_configured'}];
const piece=(title,editor='otio_kdenlive',method='external')=>({id:title,title,editorChoice:{editor,method}});
const D=value=>`<span data-design-data>${String(value).replaceAll('&','&amp;').replaceAll('<','&lt;')}</span>`;

for(const [editor,status,expected,method='external'] of [
 ['otio_kdenlive','unavailable','用 Kdenlive'],['chatcut','ready','用 ChatCut'],
 ['chatcut','unavailable','ChatCut 还没连上'],['openfilm','unavailable','用 OpenFilm'],
 ['openchatcut','unavailable','用 OpenChatCut'],
 ['otio_kdenlive','unavailable','在剪映里照清单剪','guide'],
 ['chatcut','unavailable','在剪映里照清单剪','guide'],
 ['otio_kdenlive','unavailable','用 OpenFilm','self'],
 ['chatcut','unavailable','用 OpenFilm','self']
])test('real shot flow: '+method+' '+editor+' '+status,async()=>{
 const p={...piece('作品',editor,method),connected:true,photos:1};
 const root={innerHTML:'',classList:{add(){}}};
 globalThis.document={querySelector:()=>null,querySelectorAll:()=>[]};
 const view=createShotView({state:{diagnostics:{checks:[{id:'chatcut_mcp',status}]}},
  api:async()=>({shots:[],counts:{selected:0},hook_candidates:[]}),root:()=>root,
  route:()=>({view:'piece',ptab:'vlog',piece:p.id}),mark(){},refreshCatalog(){},
  common(){},D,esc:String,button:()=>'',notice(){}});
 await view.render(p,'');
 assert.match(root.innerHTML,new RegExp('<strong>出草稿</strong><small>'+expected+'</small>'));
 view.stop();
});

test('unused ChatCut is optional, including when ready',()=>{
 const groups=common.diagnosticGroups(checks,[],D);
 assert.equal(groups.issues.length,0);
 assert.deepEqual(groups.optional.map(c=>c.id),['chatcut_mcp','asset_library']);
 assert.equal(common.diagnosticGroups([{id:'chatcut_mcp',status:'ready'}],[],D).good.length,1);
});
test('one selected work, escaped dynamic title',()=>{
 const groups=common.diagnosticGroups(checks,[piece('<校园>','chatcut'),piece('别的')],D);
 assert.equal(groups.issues.length,1);
 assert.equal(groups.issues[0].title,'ChatCut 还没连上本机');
 assert.equal(groups.issues[0].note,'「'+D('<校园>')+'」选了在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者在作品里改用 Kdenlive。');
 assert.ok(!groups.optional.some(c=>c.id==='chatcut_mcp'));
});
test('two selected works count only ChatCut; connection clears issue',()=>{
 const pieces=[piece('一','chatcut'),piece('二','chatcut'),piece('三','openfilm')];
 assert.equal(common.diagnosticGroups(checks,pieces,D).issues[0].note,'有 '+D(2)+' 件作品选了在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者在作品里改用 Kdenlive。');
 assert.equal(common.diagnosticGroups([{id:'chatcut_mcp',status:'ready'}],pieces,D).issues.length,0);
});
for(const method of ['guide','self'])test(method+' ignores stored ChatCut editor in optional and issue counts',()=>{
 const excluded=piece('不使用 ChatCut 的作品','chatcut',method);
 const optional=common.diagnosticGroups(checks,[excluded],D);
 assert.equal(optional.issues.length,0);
 assert.ok(optional.optional.some(c=>c.id==='chatcut_mcp'));
 const one=common.diagnosticGroups(checks,[excluded,piece('外部精剪','chatcut')],D);
 assert.equal(one.issues.length,1);
 assert.equal(one.issues[0].note,'「'+D('外部精剪')+'」选了在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者在作品里改用 Kdenlive。');
 const two=common.diagnosticGroups(checks,[excluded,piece('外部一','chatcut'),piece('外部二','chatcut')],D);
 assert.equal(two.issues[0].note,'有 '+D(2)+' 件作品选了在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者在作品里改用 Kdenlive。');
});
test('unreadable choice is an explicit issue, never optional ChatCut',()=>{
 const groups=common.diagnosticGroups(checks,[{id:'bad',title:'作品',editorChoice:{error:{code:'editor_choice_unreadable',message:'无法读取本机记录'}}}],D);
 assert.equal(groups.issues.length,1);
 assert.equal(groups.issues[0].title,'无法读取本机记录');
 assert.equal(groups.issues[0].note,D('作品'));
 assert.ok(!groups.optional.some(c=>c.id==='chatcut_mcp'));
});
test('draft copy guard: all three consumers use approved copy',()=>{
 for(const name of ['review-common.js','review-shots.js','review-view.js'])
  assert.doesNotMatch(source(name),/剪映或 ChatCut|出草稿[^\n。]*剪映|没连上之前，出草稿只能用剪映/,`studio.draft-editor-copy: ${name}: use selected editor; preserve manual Jianying copy`);
 assert.equal(common.draftEditorNote({method:'guide',editor:'otio_kdenlive'},checks),'在剪映里照清单剪');
 assert.ok(source('review-view.js').includes('每件作品出草稿时，用你给它选的剪辑软件，没选过的默认用 Kdenlive。选了 ChatCut 但没连上时，不会悄悄换成别的，会在工作台提醒你。'));
 assert.ok(source('review-view.js').includes("['剪映',ready('jianying')"));
 assert.ok(source('handoff.js').includes('剪映指导'));
 assert.ok(source('review-music.js').includes('可以在剪映里直接用原声'));
});
