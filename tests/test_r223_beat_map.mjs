import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PW_REQ)('playwright');
const base=process.env.STUDIO_URL;if(!base||new URL(base).port==='8765')throw Error('Use the isolated Studio URL');
const browser=await chromium.launch({channel:'chrome'});
try {
 const page=await browser.newPage({viewport:{width:900,height:700}});
 await page.route('**/r223-module-test',r=>r.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'"},body:'<link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/review.css"><div id="map" style="width:800px;padding:30px"></div>'}));
 await page.goto(base+'/r223-module-test');
 const result=await page.evaluate(async()=>{
  const mod=await import('/beat-map.js'),seeks=[],swaps=[],host=document.querySelector('#map');
  const beatMap={duration_seconds:16,beats:Array.from({length:32},(_,i)=>i/2),downbeats:[0,2,4,6,8,10,12,14],beat_energy:Array(32).fill(.5),sections:[{start:0,end:8,kind:'quiet'},{start:8,end:16,kind:'peak'}]};
  const instance=mod.mountBeatMap(host,{duration:24,songs:[{id:'a',title:'One',start:0,end:12,offset:2,beatMap,peaks:[.1,.3,.5,.8]},{id:'b',title:'Two',start:12,end:24,offset:0,beatMap,peaks:[.1,.3,.5,.8]}],cuts:[{t:4,selected:false},{t:9,selected:true}],fadeOut:1.6,lane:false,onSeek:t=>seeks.push(t),onSwapClick:i=>swaps.push(i),selectedSwap:null});
  const initial={swapTag:host.querySelector('.bm-swap').tagName,lanes:host.querySelectorAll('.bm-lane').length,nums:host.querySelectorAll('.bn').length,cuts:host.querySelectorAll('.bm-cut').length,selectedWidth:getComputedStyle(host.querySelector('.bm-cut.selected')).width,fadeWidth:host.querySelector('.bm-fade').style.width,fadePaint:getComputedStyle(host.querySelector('.bm-fade')).backgroundImage.includes('linear-gradient'),barNumber:host.querySelector('.bm-bar-line').dataset.bar,names:host.querySelectorAll('.bm-song-names span').length,swapVisible:host.querySelector('.bm-swap').getBoundingClientRect().top>=0,noOverflow:document.documentElement.scrollWidth<=innerWidth};
  host.querySelector('.bm-swap').click();instance.update({selectedSwap:1});const selected=host.querySelector('.bm-swap').getAttribute('aria-pressed');
  const overview=host.querySelector('.bm-overview'),rect=overview.getBoundingClientRect();overview.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:rect.left+rect.width/2}));
  instance.setTime(8);const stable=host.querySelector('.bm-overview')===overview;
  instance.update({lane:true});instance.setTime(8);const lane=host.querySelector('.bm-lane'),energyNode=lane.querySelector('.bc'),laneData={start:lane.dataset.windowStart,height:energyNode.style.height,number:lane.querySelector('.bn').textContent};
  window.testBeatMap=instance;
  return {signature:mod.mountBeatMap.length,methods:Object.keys(instance).sort(),initial,selected,seeks,swaps,stable,laneData,metrics:mod.beatMetrics(beatMap),intro:mod.barAt({downbeats:[8,10]},2),start:mod.laneStart(0,16),end:mod.laneStart(15,16)};
 });
 assert.equal(result.signature,2);assert.deepEqual(result.methods,['destroy','setTime','update']);
 assert.deepEqual(result.initial,{swapTag:'BUTTON',lanes:0,nums:0,cuts:2,selectedWidth:'2px',fadeWidth:'6.66667%',fadePaint:true,barNumber:'2',names:2,swapVisible:true,noOverflow:true});
 assert.equal(result.selected,'true');assert.deepEqual(result.swaps,[1]);assert.deepEqual(result.seeks,[12]);assert(result.stable);assert.equal(result.laneData.start,'4');assert.equal(result.laneData.height,'30px');assert.equal(result.laneData.number,'4');assert.deepEqual(result.metrics,{bpm:120,meter:4});assert.equal(result.intro,0);assert.equal(result.start,0);assert.equal(result.end,8);
 if(process.env.R223_SCREENSHOTS)await page.screenshot({path:process.env.R223_SCREENSHOTS+'/r226-module.png',fullPage:true});
 assert.equal(await page.evaluate(()=>{testBeatMap.destroy();testBeatMap.setTime(2);testBeatMap.update({lane:true});return document.querySelector('#map').children.length;}),0);
 console.log('PASS beat map: signature lifecycle, cuts, fade, offsets, multi-song swap, lane:false, seek, stable overview, formulas, visible swap, no overflow');
} finally {await browser.close();}
