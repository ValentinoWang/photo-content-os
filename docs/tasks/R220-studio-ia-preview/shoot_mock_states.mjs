// 设计稿各状态整页截图（给并排对照用）。用法：node shoot_mock_states.mjs <mock目录> <输出目录>
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire(process.env.PW_REQ);
const { chromium } = require('playwright');
const [M,OUT]=process.argv.slice(2);
const src=fs.readFileSync(path.join(path.dirname(decodeURIComponent(new URL(import.meta.url).pathname)),'export_states.mjs'),'utf8');
const P='view=piece&piece=2026-lzu-travel-and-sports';
const states=eval('['+src.split('const states=[')[1].split('\n];')[0]+']');
fs.mkdirSync(OUT,{recursive:true});
const b=await chromium.launch({args:['--allow-file-access-from-files']});
for (const [w,h] of [[1440,960],[1180,860],[900,900],[430,932]]) for (const [name,q,act] of states){
  const pg=await b.newPage({viewport:{width:w,height:h}});
  await pg.goto(`file://${M}/review.html?${q}`); await pg.waitForTimeout(700);
  if(act){await act(pg);await pg.waitForTimeout(700);}
  await pg.evaluate(()=>{const m=document.getElementById('mockbar');if(m)m.remove()});
  await pg.screenshot({path:`${OUT}/${name}-${w}.png`,fullPage:!name.startsWith('player')});
  await pg.close();
}
await b.close(); console.log('done');
