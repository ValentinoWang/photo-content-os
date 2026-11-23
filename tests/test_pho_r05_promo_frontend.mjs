import assert from 'node:assert/strict';
import {barSeconds, autoBars, promoTotals, promoMissing, promoPayload, splitRows, recipeRewriteBody} from '../studio/static/direct-promo.js';
assert.equal(barSeconds(120), 2);
assert.equal(autoBars({seconds: 4.1}, 120), 3);
assert.deepEqual(promoTotals([{visual:'a', bars:'auto', recipeId:null}],120,[]),{bars:2,seconds:4});
assert.equal(promoMissing({shots:[],track:null,style:null}), 'shots');
assert.deepEqual(splitRows('a\nb').map(x=>x.visual),['a','b']);
assert.equal(promoPayload({brief:'x',track:{id:'t'},startBar:1,shots:[{visual:'a',bars:'auto',recipeId:null}]}).kind,'promo');
console.log('PASS promo calculations');

const {newPromoDraft, promoDraftAfter, failureMessage} = await import('../studio/static/direct-view.js');
const track={id:'music-1',beat:{bpm:120,bars:8}};
const shots=[{visual:'界面',text:'标题',recipeId:'r1',bars:2,imageId:'img1'},{visual:'  ',bars:'auto'}];
assert.deepEqual(promoPayload({brief:'介绍',track,startBar:3,shots}),{kind:'promo',promo:{brief:'介绍',trackId:'music-1',startBar:3,fadeOutSeconds:1,shots:[{visual:'界面',text:'标题',recipeId:'r1',bars:2,imageId:'img1'}]}});
assert.equal(promoMissing({shots:[],track:null,style:null}), 'shots');
assert.equal(promoMissing({shots,track:null,style:null}), 'track');
assert.equal(promoMissing({shots,track,startBar:8,style:null}), 'short');
assert.equal(promoMissing({shots,track,startBar:1,style:null}), 'style');
assert.equal(promoMissing({shots,track,startBar:1,style:{id:'ui'}}), null);
const draft={brief:'介绍',shots,track,startBar:3};
assert.equal(promoDraftAfter(draft,'switch-to-talk'),draft);
assert.deepEqual(promoDraftAfter(draft,'generated'),newPromoDraft());
assert.deepEqual(promoDraftAfter(draft,'leave-project'),newPromoDraft());
for(const code of ['beat_map_unavailable','track_too_short','recipe_not_found']) assert.ok(!failureMessage(code).includes('错误码'));
console.log('PASS F3 request, missing fields, and draft lifecycle');

assert.equal(autoBars({seconds:null}, 120), 2);
assert.deepEqual(recipeRewriteBody('r2'), {recipeId:'r2'});
console.log('PASS F4 recipe rewrite and unknown duration');

// Exercise the detail handler and its real mutation path through the POST body.
const {readFileSync}=await import('node:fs');
const {runInNewContext}=await import('node:vm');
const detail=readFileSync(new URL('../studio/static/direct-shot-detail.js',import.meta.url),'utf8');
const code=detail.slice(detail.indexOf('  async function mutate('),detail.indexOf("  container.querySelector('[data-revise]')?.addEventListener"));
let click, request;
const detailContainer={isConnected:true,querySelector:()=>({addEventListener:(_,fn)=>{click=fn;}})};
const detailShot={shotId:'02',recipe:{id:'r1'}};
runInNewContext(code,{container:detailContainer,locked:false,draft:{},redraw:()=>{},api:async()=>({csrfToken:'token'}),fetch:async(url,options)=>{request={url,options};return {ok:true,json:async()=>({ok:true})};},base:'/api/projects/p/direct/jobs/j/shots/02',message:()=>'',job:{shots:[detailShot]},shot:detailShot,state:{shotId:'02'},onRewrite:()=>{},renderShotDetail:()=>{},projectId:'p',loadPromo:async()=>({recipes:[],categories:[]}),pickerHost:{},openRecipePicker:(_host,opts)=>opts.onChoose('r2'),recipeRewriteBody,JSON});
await click();
await new Promise(resolve=>setImmediate(resolve));
assert.equal(request.url,'/api/projects/p/direct/jobs/j/shots/02/rewrite');
assert.equal(request.options.method,'POST');
assert.deepEqual(JSON.parse(request.options.body),{recipeId:'r2'});
console.log('PASS F4 picker sends selected recipe to shot rewrite');
