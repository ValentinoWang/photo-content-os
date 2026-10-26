import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {stylePayload,sourceText,generationText,howFirst,canGenerate} from '../studio/static/direct-style.js';
const fixture=JSON.parse(readFileSync(new URL('./fixtures/r283-direct/first-lib.json',import.meta.url),'utf8'));
const names=['扁平插画','数学动画','极简发布会','手绘白板','赛博故障','水墨国风','数据可视化','8-bit 像素','代码录屏'];
export function testLibraryFormulas(){
  const rows=[{dialogue:'测试台词'}],base={...fixture.styles.library[0],kind:'library'},state={mode:'base',base,adjust:'',accepted:false};
  assert.deepEqual(stylePayload(state,'p'),{styleBase:{kind:'library',id:'flat'},style:''});
  assert.deepEqual(stylePayload({...state,adjust:' 改成暖黄 '},'p'),{styleBase:{kind:'library',id:'flat'},style:'改成暖黄'});
  assert.deepEqual(generationText(rows,state),['风格：风格库「扁平插画」',false]);
  assert.deepEqual(generationText(rows,{...state,adjust:'改成暖黄'}),['风格：风格库「扁平插画」，改：改成暖黄',false]);
  assert.equal(sourceText({kind:'library',id:'flat',name:'扁平插画',instruction:''}),'用风格库「扁平插画」的风格');
  assert.deepEqual(generationText(rows,{...state,base:null}),['风格还没选：在下面选一个现成的风格，或者从头定',true]);
  assert.deepEqual(howFirst({...state,base:null}),['先在下面选一个风格','选好就能生成']);
  assert(!canGenerate(rows,{...state,base:null},false,false));assert(canGenerate(rows,state,false,false));assert(!canGenerate([],state,false,false));
  assert.deepEqual(fixture.styles.library.map(x=>x.name),names);
  console.log('PASS R283 library payloads, generation/source copy and no-selection lock');
}
export async function testLibraryBrowser(h){
  let {page,mock}=await h.open('first');
  const cards=page.locator('[data-design-id="DV-STYLE-LIB"] [data-style-card]');
  assert.equal(await cards.count(),9,'The library must always show nine cards in existing-style mode');
  assert.deepEqual(await cards.locator('b').allTextContents(),names);assert.equal(await cards.locator('small').count(),0);
  assert.equal(await cards.locator('[data-color]').count(),36);
  const jobCard=page.locator('[data-design-id="DV-STYLE-CARDS"] [data-style-card]').first();
  for(let i=0;i<9;i++){
    await cards.nth(i).click();assert.equal(await page.locator('[data-style-card][aria-pressed="true"]').count(),1);
    assert.equal(await jobCard.getAttribute('aria-pressed'),'false');
    assert.equal(await page.locator('.dv-sw-meta h4').textContent(),'风格库 · '+names[i]);
    const expected=fixture.styles.library[i];
    const v=page.locator('.dv-sw-preview video');
    assert.equal(await v.getAttribute('src'),expected.clipUrl);assert.equal(await v.getAttribute('poster'),expected.posterUrl);
    assert(await v.evaluate(e=>e.muted&&e.loop&&e.playsInline&&e.paused&&!e.controls&&e.getAttribute('aria-hidden')==='true'));
    assert.equal(await page.locator('.dv-sw-cap').textContent(),'样张 · 同一段台词');
    assert.equal(await page.locator('[data-gen-text]').textContent(),`风格：风格库「${names[i]}」`);
  }
  await jobCard.click();assert.equal(await page.locator('[data-style-card][aria-pressed="true"]').count(),1);assert.equal(await page.locator('.dv-sw-preview video').count(),0);
  await cards.first().click();await page.locator('[data-adjust]').fill('强调色换成暖黄，其余不动');
  assert.equal(await page.locator('[data-gen-text]').textContent(),'风格：风格库「扁平插画」，改：强调色换成暖黄，其余不动');
  await page.locator('[data-mode="new"]').click();await page.locator('[data-desc]').fill('从头定的说明');await page.locator('[data-mode="base"]').click();
  assert.equal(await page.locator('[data-adjust]').inputValue(),'强调色换成暖黄，其余不动');assert.equal(await cards.first().getAttribute('aria-pressed'),'true');
  const video=page.locator('.dv-sw-preview video');await page.emulateMedia({reducedMotion:'no-preference'});await video.scrollIntoViewIfNeeded();await page.waitForFunction(()=>!document.querySelector('.dv-sw-preview video').paused&&document.querySelector('.dv-sw-preview video').currentTime>0);
  await page.evaluate(()=>scrollTo(0,0));await page.waitForFunction(()=>document.querySelector('.dv-sw-preview video').paused);
  await video.scrollIntoViewIfNeeded();await page.waitForFunction(()=>!document.querySelector('.dv-sw-preview video').paused&&document.querySelector('.dv-sw-preview video').currentTime>0);await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('.dv-sw-preview video').paused);
  const poster=await video.getAttribute('poster');await video.evaluate(v=>v.dispatchEvent(new Event('error')));assert.equal(await page.locator('.dv-sw-preview video').count(),0);assert.equal(await page.locator('.dv-sw-preview img').getAttribute('src'),new URL(poster,page.url()).href);
  await cards.first().click();const oldVideo=await page.locator('.dv-sw-preview video').elementHandle();
  await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();
  assert.deepEqual(mock.creates.at(-1).styleBase,{kind:'library',id:'flat'});assert.equal(mock.creates.at(-1).style,'强调色换成暖黄，其余不动');
  assert(await oldVideo.evaluate(v=>!v.isConnected&&v.paused));await oldVideo.dispose();await page.close();
  ({page,mock}=await h.open('first-none'));
  assert.equal(await page.locator('[data-mode="base"]').getAttribute('aria-checked'),'true');assert(await page.locator('[data-mode="base"]').isEnabled());
  assert.equal(await page.locator('[data-design-id="DV-STYLE-CARDS"]').count(),0);assert.equal(await page.locator('[data-design-id="DV-STYLE-LIB"] [data-style-card]').count(),9);
  assert.equal(await page.locator('[data-style-card][aria-pressed="true"]').count(),0);assert(await page.locator('[data-generate]').isDisabled());
  assert.equal(await page.locator('.dv-sw-empty b').textContent(),'还没选风格');assert.equal(await page.locator('.dv-sw-empty span').textContent(),'在左边选一个');assert(await page.locator('[data-gen-text]').evaluate(e=>e.classList.contains('need')));
  await page.locator('[data-library="flat"]').click();assert(await page.locator('[data-generate]').isEnabled());await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.deepEqual(mock.creates.at(-1).styleBase,{kind:'library',id:'flat'});assert.equal(mock.creates.at(-1).style,'');await page.close();
  ({page}=await h.open('first-lib'));const detached=await page.locator('.dv-sw-preview video').elementHandle();await page.emulateMedia({reducedMotion:'no-preference'});await page.locator('.dv-sw-preview video').scrollIntoViewIfNeeded();await page.waitForFunction(()=>!document.querySelector('.dv-sw-preview video').paused&&document.querySelector('.dv-sw-preview video').currentTime>0);
  await page.evaluate(()=>{location.hash='view=projects';});await page.locator('[data-design-id="R208-PROJECTS"]').first().waitFor();assert(await detached.evaluate(v=>v.paused));await detached.dispose();await page.close();
  ({page}=await h.open('library'));assert.equal(await page.locator('.dv-design-src').textContent(),'用风格库「扁平插画」的风格');await page.close();
  for(const state of ['first-lib','first-none']){
    ({page}=await h.open(state,390));await page.evaluate(()=>document.fonts.ready);
    const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('.dv-sw-meta *')].filter(e=>e.getBoundingClientRect().right>e.closest('.dv-sw-meta').getBoundingClientRect().right+1).map(e=>e.className)}));
    assert.equal(layout.width,390);assert.equal(layout.scrollWidth,390,`${state}: phone page overflow`);assert.deepEqual(layout.overflow,[],`${state}: preview metadata overflow`);await page.close();
  }
  console.log('PASS R283 mounted Studio: nine-card selection, sample media lifecycle/fallback, empty state, library jobs and source');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)testLibraryFormulas();
