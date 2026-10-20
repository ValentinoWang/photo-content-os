import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(process.env.PW_REQ);
const { chromium } = require('playwright');
const [M,OUT]=process.argv.slice(2);
const P='view=piece&piece=2026-lzu-travel-and-sports';
const states=[
 ['home','view=home'],['inbox','view=inbox'],['projects','view=projects'],['project','view=project&project=2026-lzu-revisit'],
 ['piece-review',P],['piece-review-alt',P,async pg=>{await pg.click('.alts .card >> nth=0');await pg.waitForTimeout(300);await pg.click('.more-d summary');}],
 ['piece-confirmed',P+'&state=confirmed'],['piece-partial',P+'&state=partial'],['piece-running',P+'&state=running'],['piece-empty',P+'&state=empty'],
 ['piece-not-started','view=piece&piece=2026-lzu-400m-pov'],['piece-not-started-photos','view=piece&piece=2026-lzu-group-and-honors'],['piece-script',P,async pg=>{await pg.click('[data-ptab="script"]');}],
 ['player-reel','view=home',async pg=>{await pg.click('[data-reel]');}],['player-versions','view=project&project=2026-lzu-revisit',async pg=>{await pg.click('.playv >> nth=0');}],
 ['library','view=library'],['library-empty','view=library&state=empty'],
 ['music','view=music'],['music-empty','view=music&state=empty'],['music-importing','view=music&state=importing'],['music-dup','view=music&state=dup'],['music-vip','view=music&state=vip'],['music-douyin','view=music&state=douyin'],
 ...['places','tools','models','music','account','doctor'].map(t=>['settings-'+t,'view=settings&tab='+t]),
];
const b=await chromium.launch({args:['--allow-file-access-from-files']});
const pg=await b.newPage({viewport:{width:1440,height:960}});
const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
let side='', parts=[];
for (const [name,q,act] of states){
  await pg.goto(`file://${M}/review.html?${q}`); await pg.waitForTimeout(500);
  if(act) {await act(pg); await pg.waitForTimeout(500);}
  const html=await pg.evaluate(()=>{const ov=document.querySelector('#ov');return document.querySelector('.main').outerHTML+(ov&&!ov.hidden?ov.outerHTML:'')});
  if(!side) side=await pg.evaluate(()=>document.querySelector('.side').outerHTML);
  parts.push(`<section data-design-state="${name}">${html}</section>`);
}
fs.writeFileSync(OUT,`<!doctype html><html lang="zh-CN"><body>${side}${parts.join('\n')}</body></html>`);
await b.close();
console.log(errs.length?errs.join('\n'):`exported ${parts.length} states`);
