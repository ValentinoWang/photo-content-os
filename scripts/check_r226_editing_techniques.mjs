// R226 gate: 36 schema-shaped synthetic fixtures, seven viewports, browser numbers,
// design inventory and complete captures. Real Studio proof and reference-image
// pairing are recorded separately; this gate never substitutes for that proof.
// Runtime guard r226.swap-title-overlap: all real shared-map title/button rectangles,
// seven widths, with a deliberate collision proving detection before restoration.
// Repair only scoped R226 CSS (TASK B6a); missing inputs fail closed. Slow visual gate.
// Retire this local guard when an equivalent shared-map integration guard replaces it.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawn,spawnSync} from 'node:child_process';
import {createServer} from 'node:http';
const out=path.resolve(process.env.R226_EVIDENCE||path.join(os.homedir(),'.photo-content-os/evidence/R226-editing-techniques/impl'));
fs.mkdirSync(out,{recursive:true});
for(const file of ['design-inventory.json','browser-results.json','screenshot-manifest.json','panel-frames.json']){const target=path.join(out,file);if(fs.existsSync(target))fs.unlinkSync(target);}
const root=process.cwd();
const studioCsp=fs.readFileSync(path.join(root,'studio/server.py'),'utf8').match(/self\.send_header\("Content-Security-Policy", "([^"]+)"\)/)?.[1];
if(!studioCsp)throw new Error('r226.csp-unreadable: cannot read the Studio policy; do not run an unprotected fixture page.');
const core=process.env.HARNESS_CORE_ROOT||path.dirname(path.dirname(fs.realpathSync(path.join(root,'develop/harness/fullstack-ai-harness.md'))));
const schemaCheck=spawnSync(path.join(root,'.venv/bin/python'),['-c',String.raw`
import copy,json
from pathlib import Path
from jsonschema import Draft202012Validator
root=Path.cwd();schema=json.loads((root/'schemas/roughcut-api.schema.json').read_text());presets=json.loads((root/'schemas/editing-presets.schema.json').read_text());files=list((root/'tests/fixtures/r226-editing-techniques/api').glob('cut-*.json'))
assert {f.stem for f in files}==set(json.loads((root/'docs/tasks/R226-editing-techniques/mock/design-contract.json').read_text())['states']),'r226.fixture-schema: fixtures must cover exactly the approved 36 states'
for file in files:
 f=json.loads(file.read_text());assert f['synthetic'] is True
 for key,ref in [('roughcut','state_response'),('capabilities','capabilities_response')]:
  doc=copy.deepcopy(schema);doc['$ref']='#/$defs/'+ref;Draft202012Validator(doc).validate(f[key])
 Draft202012Validator(presets).validate(f['presets'])
print('PASS: 36 fixtures match current roughcut, capabilities and preset-library schemas')
`],{encoding:'utf8'});
fs.writeFileSync(path.join(out,'fixture-schema.log'),schemaCheck.stdout+schemaCheck.stderr);
if(schemaCheck.status!==0){console.error('r226.fixture-schema: update synthetic fixtures to the current owned API schemas; see fixture-schema.log');process.exit(1);}
const script=String.raw`
import json,sys,re,hashlib,datetime,os,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(sys.argv[1]);out=Path(sys.argv[2]);core=Path(sys.argv[3]);base=os.environ.get('R226_STATIC_URL','http://127.0.0.1:8927')
collect=(core/'skills/ui-copy-quality/assets/collect_design_inventory.js').read_text().split('if (typeof module')[0]
fixtures=sorted((root/'tests/fixtures/r226-editing-techniques/api').glob('cut-*.json'))
duration=json.loads((root/'tests/fixtures/r226-editing-techniques/api/cut-ready.json').read_text())['roughcut']['plan']['metrics']['duration_sec']
video_path=out/'synthetic-preview.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x253133:s=160x90:r=10','-f','lavfi','-i','sine=frequency=220:sample_rate=22050','-t',str(duration),'-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-af','volume=0.01','-movflags','+faststart','-y',str(video_path)],check=True)
video_bytes=video_path.read_bytes()
inventory={'states':{}};records=[];failures=[];numbers=[];panels=[];preview_audits=[];beat_audits=[];swap_negative=[];value_negative=[]
section_tokens=dict(re.findall(r'--sec-(quiet|build|peak):([^;}]+)',(root/'studio/static/styles.css').read_text()))
assert set(section_tokens)=={'quiet','build','peak'},'r226.section-token-unreadable: styles.css must declare all three section colors'
html=(root/'studio/static/index.html').read_text();html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
svg='<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect fill="#253133" width="320" height="180"/><path fill="#2e5f65" d="M0 180L100 60L180 140L240 90L320 180Z"/></svg>'
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 for file in fixtures:
  name=file.stem;fixture=json.loads(file.read_text());context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN',timezone_id='Asia/Shanghai')
  context.route('https://fonts.googleapis.com/**',lambda route:route.abort())
  context.route('**/test-frame.svg',lambda route:route.fulfill(body=svg,content_type='image/svg+xml'))
  page=context.new_page();csp=page.request.get(base+'/').headers.get('content-security-policy');assert csp, 'r226.csp-missing: fixture HTTP server must use the real Studio policy'
  page.on('console',lambda m:failures.append(dict(state=name,kind='r226.csp-inline-style',message=m.text)) if 'Applying inline style violates' in m.text else None)
  page.on('pageerror',lambda e:failures.append({'state':name,'kind':'runtime','message':str(e)}))
  def media(route):
   if 'synthetic-guide' in route.request.url:route.fulfill(body='合成交接说明：切点与手法。',content_type='text/plain; charset=utf-8');return
   if page.evaluate('!!window.mediaFailed'):route.fulfill(status=503,body='unavailable');return
   if page.evaluate('!!window.mediaExpired'):route.fulfill(status=409,json={'ok':False,'error':{'code':'revision_conflict'}});return
   headers={'Accept-Ranges':'bytes'};body=video_bytes;status=200
   match=re.match(r'bytes=(\d+)-(\d*)',route.request.headers.get('range',''))
   if match:
    start=int(match[1]);end=min(int(match[2]) if match[2] else len(body)-1,len(body)-1);headers['Content-Range']=f'bytes {start}-{end}/{len(body)}';body=body[start:end+1];status=206
   route.fulfill(status=status,body=body,content_type='video/mp4',headers=headers)
  context.route('**/api/review/pieces/*/roughcut/media/**',media)
  context.route(base+'/',lambda route:route.fulfill(body=html,content_type='text/html',headers={'Content-Security-Policy':csp}));page.goto(base+'/')
  page.evaluate('''async ({f,base})=>{
   document.querySelector('#screen-title').textContent='合成作品';document.querySelector('#screen-title').dataset.designData='';document.querySelector('.topbar').removeAttribute('data-design-id');
   document.querySelector('.brand').dataset.designId='R208-NAV';document.querySelector('.side-foot').dataset.designId='R208-NAV';
   const {createCutView}=await import(base+'/review-cut.js');const {mountBeatMap}=await import(base+'/beat-map.js');
   const root=()=>document.querySelector('#review-screen');window.syntheticFixture=f;
   window.r226InvalidVisible=()=>{const text=document.querySelector('.r226-cut').innerText;return ['undefined','NaN','null'].filter(value=>text.includes(value));};
   window.r226SwapTitleFindings=()=>{const bad=[];for(const swap of document.querySelectorAll('.bm-swap'))for(const title of document.querySelectorAll('.bm-song-names span')){const a=swap.getBoundingClientRect(),b=title.getBoundingClientRect();if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)bad.push({kind:'r226.swap-title-overlap',title:title.textContent,swap:a.toJSON(),name:b.toJSON(),repair:'Separate rows in review-cut.css with :where(.r226-cut); do not edit R223 files.'});}return bad;};
   window.requests=[];window.r226=createCutView({root,state:{csrf:'synthetic-token'},active:()=>true,
    mark:s=>document.querySelector('.main').dataset.designState=s,common(){},refreshCatalog:async()=>{},go:r=>window.nextRoute=r,mountBeatMap:(container,options)=>{container.r226BeatOptions=options;return mountBeatMap(container,options);},
    request:async(path,options={})=>{window.requests.push({path,options});
     if(path.endsWith('/roughcut'))return structuredClone(f.roughcut);if(path==='/api/review/editing-presets')return f.presets;if(path.endsWith('/editor-capabilities'))return f.capabilities;if(path.endsWith('/shots'))return f.shots;if(path==='/api/review/music')return f.music;
     if(path.startsWith('/api/projects/')&&options.method==='PATCH'){const option=f.capabilities.editors.find(e=>e.choice.editor===options.body.videoEditor.editor&&e.choice.method===options.body.videoEditor.method);f.capabilities.choice={...options.body.videoEditor,revision:options.body.videoEditor.revision+1};f.capabilities.selected=option.capability;f.capabilities.selected_option_id=option.id;f.capabilities.project_revision++;f.roughcut.project_revision++;f.roughcut.display.draft_allowed=option.capability.can_generate;f.roughcut.display.draft_blockers=option.capability.can_generate?[]:[option.capability.block_reason];return {ok:true};}
     if(path.endsWith('/commands')&&window.retryScenario){
      const c=options.body.command;window.retryCalls=(window.retryCalls||0)+1;
      if(window.retryCalls===1){
       if(c.type==='select_music')f.roughcut.selection.playlist=c.track_ids.map((track_id,i)=>({id:'retry-'+i,track_id}));
       if(c.type==='add_song')f.roughcut.selection.playlist.push({id:'retry-song',track_id:c.track_id});
       if(c.type==='replace_song')f.roughcut.selection.playlist.find(s=>s.id===c.song_instance_id).track_id=c.track_id;
      }
      f.roughcut.revision++;f.roughcut.status=window.retryCalls===1?'failed':'queued';f.roughcut.display.base_state=window.retryCalls===1?'cut-failed':'cut-beat-queued';
      f.roughcut.failure=window.retryCalls===1?{code:'beat_failed',details:{track_id:c.track_id||c.track_ids[0]}}:null;
      if(window.retryCalls>1){f.roughcut.job={job_id:'synthetic-retry',kind:'arrange',revision:f.roughcut.revision};f.roughcut.analysis=f.roughcut.selection.playlist.map(s=>({song_instance_id:s.id,track_id:s.track_id,status:'queued',beat_count:null,beat_map:null,failure:null}));}
      return {ok:true,revision:f.roughcut.revision};
     }
     if(path.includes('/roughcut-jobs/')&&options.method==='POST'&&options.body.action==='stop'){f.roughcut.status='stopped';f.roughcut.job=null;f.roughcut.failure=null;f.roughcut.display.base_state=null;return {ok:true};}
     if(path.includes('/reanalyze')){if(window.retryScenario){f.roughcut.revision+=5;f.roughcut.project_revision+=2;f.roughcut.source_summary.selection_digest='9'.repeat(64);window.replayVersion={expectedRevision:f.roughcut.revision,projectRevision:f.roughcut.project_revision,selectionDigest:f.roughcut.source_summary.selection_digest};}return {ok:true,beat:{status:'queued',queue_position:1}};}
     if(path.endsWith('/drafts/open'))return {ok:true,opened:true};
     if(path.endsWith('/drafts')){window.draftPollCount=0;f.roughcut.revision++;f.roughcut.draft={...window.readyDraft,status:'queued',design_state:'cut-drafting',job_id:'synthetic-flow-draft',can_open:false};return {ok:true,job_id:'synthetic-flow-draft'};}
     if(path.endsWith('/roughcut-jobs/synthetic-flow-draft')){window.draftPollCount++;if(window.draftPollCount===1)return {status:'running'};f.roughcut.draft=window.draftOutcome==='failed'?{...window.readyDraft,status:'failed',design_state:null,can_open:false,failure:{code:'draft_failed'}}:structuredClone(window.readyDraft);return {status:window.draftOutcome==='failed'?'failed':'done'};}
     if(path.includes('/roughcut-jobs/'))return {status:'running',analysis:f.roughcut.analysis,progress:{phase:'cuts',completed:18,total:27,determinate:true}};
     throw Object.assign(new Error('unhandled synthetic request'),{code:'request_invalid'});
    }});
   await window.r226.render({id:f.roughcut.piece_id},'<nav class="ptabs full" data-design-id="R208-PIECE-tabs"><button role="tab" aria-selected="true">按素材剪 vlog</button><button role="tab" aria-selected="false">按脚本做视频</button></nav>');
  }''',{'f':fixture,'base':base})
  # Local state is entered through the same controls used in Studio.
  if name in ['cut-presets','cut-presets-unreadable-mine']:
   page.locator('[data-lib]').click()
   if name.endswith('-mine'):page.locator('[data-cat="我的"]').click()
  elif name in ['cut-editor','cut-editor-kdenlive-missing','cut-editor-chatcut-connected','cut-editor-guide-missing','cut-editor-openfilm','cut-editor-unreadable']:page.locator('[data-editor-open]').click()
  elif name=='cut-add-song':page.locator('[data-add-song]').click()
  elif name=='cut-replace-song':page.locator('[data-replace-song]').first.click()
  elif name=='cut-occurrence':page.locator('[data-first="jcut"]').click()
  elif name=='cut-multi-swap':page.locator('.bm-swap').first.click()
  for width in [1440,1180,960,768,620,430,375]:
   page.set_viewport_size({'width':width,'height':1000})
   page.evaluate('document.fonts.ready')
   findings=page.evaluate('''f=>{
    const bad=[];
    for(const el of document.querySelectorAll('.blk[data-clip],[data-occ],.pv-bar i,.pv-bar b,.dia-row>div i')){const box=el.getBoundingClientRect();if(box.width<=0||box.height<=0)bad.push({kind:'r226.zero-geometry',selector:el.className,clip:el.dataset.clip,occurrence:el.dataset.occ,box:box.toJSON(),repair:'Set geometry through DOM style properties under the Studio CSP; compare the real response to the fixture.'});}
    const ticks=[...document.querySelectorAll('.tl2-ruler i')];for(let i=0;i<ticks.length;i++)for(let j=i+1;j<ticks.length;j++){const a=ticks[i].getBoundingClientRect(),b=ticks[j].getBoundingClientRect();if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)bad.push({kind:'r226.tick-overlap',texts:[ticks[i].textContent,ticks[j].textContent]});}
    const legend=document.querySelector('.tl2-legend');if(f.roughcut.plan&&f.music.taxonomy.sections.some(k=>!legend?.innerText.includes(k.name)))bad.push({kind:'r226.legend-missing',actual:legend?.innerText,expected:f.music.taxonomy.sections.map(k=>k.name)});
    const invalid=window.r226InvalidVisible();if(invalid.length)bad.push({kind:'r226.invalid-visible-value',values:invalid});
    if(document.documentElement.scrollWidth>innerWidth+1)bad.push({kind:'overflow',width:innerWidth,scroll:document.documentElement.scrollWidth});
    for(const row of document.querySelectorAll('.lane')){const rs=[...row.querySelectorAll('button')].map(e=>e.getBoundingClientRect()).sort((a,b)=>a.left-b.left);for(let i=1;i<rs.length;i++)if(rs[i].left<rs[i-1].right-.5)bad.push({kind:'marker-overlap'});}
    const swaps=[...document.querySelectorAll('.bm-swap')],titles=[...document.querySelectorAll('.bm-song-names span')],songs=f.roughcut.plan?.songs||[];
    if(songs.length>1&&(titles.length!==songs.length||swaps.length!==songs.length-1))bad.push({kind:'r226.beat-map-input-missing',songs:songs.length,titles:titles.length,swaps:swaps.length,repair:'Load the real beat-map.js and inspect .bm-song-names span / .bm-swap.'});
    bad.push(...window.r226SwapTitleFindings());
    const map=document.querySelector('#cut-beat-map');if(map){const box=map.getBoundingClientRect();for(const el of map.querySelectorAll('.bm-band,.bm-song-names span,.bm-swap')){const r=el.getBoundingClientRect();if(r.top<box.top-.5||r.bottom>box.bottom+.5)bad.push({kind:'r226.beat-map-outside-row',selector:el.className||el.tagName,repair:'Fit the shared map within the scoped R226 music row in review-cut.css.'});}}
    const scroll=document.querySelector('.tl2-scroll');
    if(scroll&&innerWidth>=960&&scroll.scrollWidth>scroll.clientWidth+1)bad.push({kind:'r226.timeline-desktop-scroll'});
    for(const block of document.querySelectorAll('.tl2-video .blk')){const label=block.querySelector('b'),visible=getComputedStyle(label).display!=='none';if(visible!==(block.getBoundingClientRect().width>=14))bad.push({kind:'r226.clip-number-threshold',width:block.getBoundingClientRect().width});}
    for(const [i,lane] of [...document.querySelectorAll('.tl2-lanes .lane')].entries()){
     const technique=f.roughcut.plan.techniques[i],marks=[...lane.querySelectorAll('[data-occ]')],expected=technique.enabled?technique.count:0;
     if(marks.length!==expected)bad.push({kind:'r226.lane-count',technique:technique.id,expected,actual:marks.length});
     if(technique.status==='off'&&!lane.innerText.includes('关掉了'))bad.push({kind:'r226.lane-off-label',technique:technique.id});
     for(const mark of marks){const r=mark.getBoundingClientRect(),style=getComputedStyle(mark);if(r.width<=0||r.height<=0||style.display==='none'||style.backgroundColor==='rgba(0, 0, 0, 0)')bad.push({kind:'r226.marker-invisible',technique:technique.id});if(innerWidth>=960&&scroll&&(r.left<scroll.getBoundingClientRect().left-1||r.right>scroll.getBoundingClientRect().right+1))bad.push({kind:'r226.marker-outside-desktop',technique:technique.id});}
    }
    if(innerWidth===430){const subtitle=document.querySelector('.fstep.cur small');if(!subtitle||getComputedStyle(subtitle).display==='none'||subtitle.getBoundingClientRect().height===0)bad.push({kind:'r226.current-step-subtitle'});}
    for(const chip of document.querySelectorAll('.style-top .chip'))if(chip.textContent==='AI 推荐'&&parseFloat(getComputedStyle(chip).borderTopWidth)<1)bad.push({kind:'r226.recommendation-border'});
    for(const card of document.querySelectorAll('.r226-cut .style[data-style]')){
     const selected=card.getAttribute('aria-checked')==='true',plan=f.roughcut.plan,source=selected?{duration_sec:plan.metrics.duration_sec,preview_shot_ids:plan.metrics.preview_shot_ids,cuts:plan.cuts,mapped_sections:plan.mapped_sections}:f.roughcut.preset_previews.find(p=>p.preset_id===card.dataset.style),sections=[...card.querySelectorAll('.pv-bar i')],cuts=[...card.querySelectorAll('.pv-bar b')],images=[...card.querySelectorAll('.pv-thumbs img')];
     const mappedSections=source?.mapped_sections.filter(s=>s.end>s.start)||[];
     if(!source||sections.length!==mappedSections.length||cuts.length!==source.cuts.length||images.length!==source.preview_shot_ids.length)bad.push({kind:'r226.preset-preview-count',preset:card.dataset.style});
     else if(sections.some((el,i)=>Math.abs(parseFloat(el.style.left)-mappedSections[i].start/source.duration_sec*100)>.011||Math.abs(parseFloat(el.style.width)-(mappedSections[i].end-mappedSections[i].start)/source.duration_sec*100)>.011)||cuts.some((el,i)=>Math.abs(parseFloat(el.style.left)-source.cuts[i].position*100)>.0011)||images.some((el,i)=>el.dataset.shotId!==source.preview_shot_ids[i]))bad.push({kind:'r226.preset-preview-source',preset:card.dataset.style});
    }
    const progress=document.querySelector('.r226-cut .progress');if(progress){const steps=progress.querySelector('.steps'),cs=getComputedStyle(progress),expected=progress.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);if(Math.abs(steps.getBoundingClientRect().width-expected)>1)bad.push({kind:'r226.progress-width'});}
    const draft=document.querySelector('[data-draft]');if(draft?.disabled){const s=getComputedStyle(draft);if(draft.getAttribute('aria-disabled')!=='true'||s.backgroundColor!==getComputedStyle(document.querySelector('.r226-cut')).getPropertyValue('--panel-2').trim()&&s.backgroundColor==='rgb(79, 179, 189)')bad.push({kind:'disabled-draft'});}
    for(const el of document.querySelectorAll('.r226-cut button,.r226-cut p,.r226-cut strong')){const s=getComputedStyle(el);if(s.overflow==='hidden'&&el.scrollWidth>el.clientWidth+2&&s.textOverflow!=='ellipsis')bad.push({kind:'clipped',text:el.textContent});}
    return bad;
   }''',fixture);failures.extend(dict(state=name,width=width,**f) for f in findings)
   audit=page.evaluate('''tokens=>{
    const rgb=value=>{const e=document.createElement('i');e.style.color=value;document.body.append(e);const c=getComputedStyle(e).color;e.remove();return c;};
    const colors=Object.entries(tokens).map(([kind,value])=>{const token=getComputedStyle(document.documentElement).getPropertyValue('--sec-'+kind).trim(),expected=rgb(value),nodes=[...document.querySelectorAll('.bm-band i.'+kind+','+(kind==='quiet'?'.pv-bar i:not(.b):not(.p)':'.pv-bar i.'+({build:'b',peak:'p'}[kind]))+',.tl2-legend .sw--'+kind)];return {kind,declared:value,token,expected,count:nodes.length,actual:nodes.map(e=>getComputedStyle(e).backgroundColor),pass:rgb(token)===expected&&nodes.every(e=>getComputedStyle(e).backgroundColor===expected)};});
    const rect=e=>({text:e.textContent,box:e.getBoundingClientRect().toJSON()});return {width:innerWidth,module:!!document.querySelector('.bm-overview[data-design-id="R223-BEAT-overview"]'),titles:[...document.querySelectorAll('.bm-song-names span')].map(rect),swaps:[...document.querySelectorAll('.bm-swap')].map(rect),colors};
   }''',section_tokens)
   if name=='cut-ready':
    proof=page.evaluate('''()=>{const e=document.querySelector('.tl2-legend [data-design-data]'),old=e.textContent,checks=[];for(const word of ['undefined','NaN','null']){e.textContent=old+word;checks.push({word,detected:window.r226InvalidVisible().includes(word)});}e.textContent=old;return {width:innerWidth,checks,restored:window.r226InvalidVisible().length===0};}''')
    value_negative.append(proof)
    if not proof['restored'] or not all(c['detected'] for c in proof['checks']):failures.append(dict(state=name,width=width,kind='r226.invalid-value-negative-undetected',details=proof))
   if name=='cut-multi':
    negative=page.evaluate('''()=>{const button=document.querySelector('.bm-swap'),title=document.querySelector('.bm-song-names span'),overview=document.querySelector('.bm-overview');if(!button||!title||!overview)throw Error('r226.swap-title-negative: required real DOM missing');const old=button.style.top,before=window.r226SwapTitleFindings();button.style.top=(title.getBoundingClientRect().top-overview.getBoundingClientRect().top)+'px';const red=window.r226SwapTitleFindings();button.style.top=old;const after=window.r226SwapTitleFindings();return {width:innerWidth,before,red,after,detected:red.length>0,restored:after.length===before.length};}''')
    swap_negative.append(negative)
    if not negative['detected'] or not negative['restored']:failures.append(dict(state=name,width=width,kind='r226.swap-title-negative-undetected',details=negative))
   beat_audits.append(dict(state=name,**audit))
   if fixture['roughcut']['plan'] and not audit['module']:failures.append(dict(state=name,width=width,kind='r226.real-beat-map-missing'))
   for c in audit['colors']:
    if not c['pass'] or fixture['roughcut']['plan'] and not c['count']:failures.append(dict(state=name,width=width,kind='r226.section-color',details=c))
   if width in [1440,430]:
    # Walk the real scrolling page before taking a complete capture.
    page.evaluate('''async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=800){scrollTo(0,y);await new Promise(requestAnimationFrame);}scrollTo(0,0);}''')
    target=out/f'impl-{name}-{width}.png';page.screenshot(path=str(target),full_page=True)
    records.append(dict(state=name,route=base,viewport={'width':width,'height':1000},file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),coverage='full document; modal inner scroll captured separately when needed',font_mode='fallback-local',review_result='PENDING'))
    body=page.locator('.ov:not([hidden]) .lib-body')
    if body.count() and body.evaluate('(e)=>e.scrollHeight>e.clientHeight+1'):
     item={'state':name,'width':width,'frames':[]};body.locator('xpath=../header').screenshot(path=str(out/f'panel-{name}-{width}-header.png'));item['header']=f'panel-{name}-{width}-header.png'
     geometry=body.evaluate('(e)=>({height:e.clientHeight,total:e.scrollHeight})');item.update(geometry);offset=0;index=0
     while True:
      actual=body.evaluate('(e,t)=>{e.scrollTop=t;return e.scrollTop;}',offset);filename=f'panel-{name}-{width}-frame-{index:02}.png';body.screenshot(path=str(out/filename));item['frames'].append({'offset':actual,'file':filename})
      if actual+geometry['height']>=geometry['total']-1:break
      offset=min(geometry['total']-geometry['height'],actual+geometry['height']-100);index+=1
     body.evaluate('(e)=>e.scrollTop=0');panels.append(item)
    if width==1440:
     preview_audits.append({'state':name,'cards':page.locator('.r226-cut .style[data-style]').evaluate_all("es=>es.map(e=>({preset:e.dataset.style,selected:e.getAttribute('aria-checked')==='true',thumbs:[...e.querySelectorAll('.pv-thumbs img')].map(i=>i.dataset.shotId),sections:[...e.querySelectorAll('.pv-bar i')].map(i=>({left:i.style.left,width:i.style.width})),cuts:[...e.querySelectorAll('.pv-bar b')].map(i=>i.style.left)}))")})
     entry=page.evaluate(collect+'\ncollectDesignInventory({states:{'+json.dumps(name)+':"#app"}})');inventory['states'].update(entry['states'])
  plan=fixture['roughcut']['plan']
  if plan:
   checks=page.evaluate('''f=>{
    const p=f.roughcut.plan,m=p.metrics,q=s=>document.querySelector(s),text=q('#review-screen').innerText;
    const mm=t=>{t=Math.floor(t+.5);return Math.floor(t/60)+':'+String(t%60).padStart(2,'0');};
    const fields={};const assert=(id,ok,why='')=>fields[id]={result:ok?'PASS':'FAIL',why};
    const na=(id,why)=>fields[id]={result:'N/A',why};
    assert('F01',q('.stephead').innerText.includes(mm(p.cuts.at(-1).t+m.fade_out_sec))&&q('#pos').innerText.endsWith(mm(m.duration_sec)));
    const cards=[...document.querySelectorAll('.styles:not(.lib-grid) [data-style]')];
    assert('F02',cards.every(c=>{const preview=f.roughcut.preset_previews.find(x=>x.preset_id===c.dataset.style);return c.querySelector('.rh')?.innerText.includes(mm(c.getAttribute('aria-checked')==='true'?m.duration_sec:preview.duration_sec));}));
    assert('F03',cards.every(c=>{const preview=f.roughcut.preset_previews.find(x=>x.preset_id===c.dataset.style),duration=c.getAttribute('aria-checked')==='true'?m.duration_sec:preview.duration_sec;return c.querySelector('.rh')?.innerText.includes((Math.round((duration-m.fade_out_sec)/m.shot_count*10)/10).toFixed(1));}));
    assert('F04',cards.every(c=>{const ids=c.getAttribute('aria-checked')==='true'?m.preview_shot_ids:f.roughcut.preset_previews.find(x=>x.preset_id===c.dataset.style).preview_shot_ids;return [...c.querySelectorAll('.pv-thumbs img')].every((img,i)=>img.dataset.shotId===ids[i]);})&&m.preview_shot_ids.every((id,i)=>id===p.clips[Math.floor(i*(m.shot_count-1)/5+.5)].shot_id));
    assert('F05',q('.preset-more').innerText.includes('共 '+f.presets.total+' 个')&&[...document.querySelectorAll('[data-cat]')].every(b=>{const count=f.presets.categories.find(c=>c.label===b.dataset.cat).count;return count==null?!b.querySelector('i'):Number(b.querySelector('i').innerText)===count;}));
    if(q('[data-design-id="R226-TECH"]')){
     const heading=q('[data-design-id="R226-TECH"] h3').innerText;
     assert('F06',heading.includes('用了 '+p.techniques.filter(t=>t.enabled&&t.count>0).length+' 种'));
     assert('F07',heading.includes('共 '+p.occurrences.filter(o=>o.live).length+' 处'));
     assert('F08',p.techniques.every(t=>{const row=q('[data-technique-row="'+t.id+'"] .nm i'),speech=f.roughcut.display.speech;const value=t.enabled?(speech.mode==='all'&&speech.affected_techniques.includes(t.id)?'要先转写自拍':t.count+' 处'):t.status==='off'?'关掉了':'这个预设不用';return row?.innerText===value;}));
    }else ['F06','F07','F08'].forEach(id=>na(id,'detail panel replaces technique list'));
    const occurrence=q('[data-design-id="R226-OCC"]');
    if(occurrence){const current=p.occurrences.find(o=>q('[data-occ="'+CSS.escape(o.id)+'"]')?.getAttribute('aria-current')==='true');assert('F09',occurrence.innerText.includes('第 '+current.index+' / '+current.total+' 处'));}else na('F09','occurrence panel closed');
    assert('F10',q('#nowbox').innerText.includes('/ '+m.shot_count+' 个镜头'));
    if(q('[data-design-id="R226-STYLES"] > .why')&&f.roughcut.selection.preset_id===f.roughcut.recommendation.preset_id)assert('F11',q('[data-design-id="R226-STYLES"] > .why').innerText.includes('（'+f.roughcut.recommendation.dominant_count+' 个）')&&q('[data-design-id="R226-STYLES"] > .why').innerText.includes('（'+f.roughcut.recommendation.sports_count+' 个）'));else na('F11','non-recommended preset');
    const speech=f.roughcut.display.speech;assert('F12',!speech.missing_video_count||[...document.querySelectorAll('[data-design-id="R226-PARTIAL"],[data-design-id="R226-PARTIAL-NONE"]')].every(e=>e.innerText.includes('有 '+speech.missing_video_count+' 段自拍')));
    assert('F13',document.querySelectorAll('.song-chip').length===m.song_count);
    assert('F14',[...document.querySelectorAll('.song-chip small')].every((e,i)=>e.innerText.startsWith(mm(p.songs[i].start)+'–'+mm(p.songs[i].end))));
    const swap=q('[data-design-id="R226-SWAP"]'),options=q('#cut-beat-map')?.r226BeatOptions;
    if(swap){const w=p.swaps[options.selectedSwap-1];assert('F15',swap.querySelector('h3').innerText.includes(mm(w.at)));assert('F16',swap.innerText.includes(w.speed_relation==='same'?'一样快':(w.speed_relation==='faster'?'快 ':'慢 ')+Math.abs(w.bpm_delta)+' 拍'));assert('F17',swap.querySelectorAll('[data-swap-to]').length===w.alternatives.length);}else ['F15','F16','F17'].forEach(id=>na(id,'swap panel closed'));
    assert('F18',[...document.querySelectorAll('[data-occ]')].every(e=>{const o=p.occurrences.find(o=>o.id===e.dataset.occ);return Math.abs(parseFloat(e.style.left)-o.position*100)<.0011;}));
    assert('F19',options?.cuts.every((c,i)=>c.t===p.cuts[i].t));
    assert('F20',options?.songs.every((s,i)=>s.offset===p.songs[i].offset));
    assert('F21',!p.swaps.length||[...document.querySelectorAll('.bm-swap')].every((e,i)=>Math.abs(parseFloat(e.style.left)-p.swaps[i].at/m.duration_sec*100)<.0011));
    if(occurrence){const o=p.occurrences.find(o=>q('[data-occ="'+CSS.escape(o.id)+'"]')?.getAttribute('aria-current')==='true');if(o.technique==='action')assert('F22',occurrence.innerText.includes(o.reason_data.peak_sec.toFixed(1)));else na('F22','not an action occurrence');if(o.technique==='jcut')assert('F23',occurrence.innerText.includes(o.reason_data.lead_sec.toFixed(1)+' 秒'));else na('F23','not an audio-lead occurrence');if(o.technique==='bed')assert('F24',occurrence.innerText.includes('共 '+o.shot_ids.length+' 个'));else na('F24','not a bed occurrence');}else ['F22','F23','F24'].forEach(id=>na(id,'occurrence panel closed'));
    return fields;
   }''',fixture)
   numbers.append(dict(state=name,checks=checks));failures.extend(dict(state=name,kind='number-formula',message=k,details=v) for k,v in checks.items() if v['result']=='FAIL')
  if name=='cut-ready':
   for technique,formula in [('action','F22'),('bed','F24')]:
    page.locator('[data-first="'+technique+'"]').click()
    panel=page.locator('[data-design-id="R226-OCC"]').inner_text();raw=next(o for o in plan['occurrences'] if o['technique']==technique and o['live'])
    expected=(f"{raw['reason_data']['peak_sec']:.1f} 秒动作最猛" if technique=='action' else f"共 {len(raw['shot_ids'])} 个")
    ok=expected in panel;numbers.append(dict(state=name+'-'+technique,checks={formula:{'result':'PASS' if ok else 'FAIL'}}))
    if not ok:failures.append(dict(state=name,kind='number-formula',message=formula))
    page.screenshot(path=str(out/f'impl-occurrence-{technique}-375.png'),full_page=True)
    page.locator('[data-back]').click()
  if name=='cut-ready':
   page.set_viewport_size({'width':1440,'height':1000})
   page.locator('[data-editor-open]').click();page.locator('.editor-pop [data-editor-pick="chatcut"]').click();page.wait_for_selector('[data-design-id="R226-BLOCKED"]')
   checks=page.evaluate('''()=>({grey:document.querySelector('[data-draft]').disabled&&document.querySelector('[data-draft]').getAttribute('aria-disabled')==='true',step:document.querySelectorAll('.fstep')[3].innerText.includes('ChatCut 还没连上'),warning:!!document.querySelector('[data-design-id="R226-BLOCKED"]')})''')
   if not all(checks.values()):failures.append({'state':name,'kind':'synthetic-R228-H02','details':checks})
   page.locator('[data-editor-open]').click();page.locator('.editor-pop [data-editor-pick="otio_kdenlive"]').click();page.wait_for_function("()=>(document.querySelectorAll('.fstep')[3].innerText.includes('用 Kdenlive'))")
   (out/'synthetic-R228-H02.json').write_text(json.dumps(dict(checks=checks,restored=True,real_transport=False),ensure_ascii=False,indent=2))
  if name=='cut-failed':
   page.locator('[data-failure-action="重新分析"]').click()
   page.wait_for_function("()=>(window.requests.some(r=>r.path.endsWith('/reanalyze')))")
   reanalysis=page.evaluate("window.requests.find(r=>r.path.endsWith('/reanalyze'))")
   if reanalysis['options']['body']!={'part':'beat'}:failures.append({'state':name,'kind':'reanalyze-body'})
  if name=='cut-ready':
   flow_results=[]
   # The same UI controls exercise stop without inventing a new design state.
   for old_plan in [False,True]:
    seed=json.loads((root/'tests/fixtures/r226-editing-techniques/api'/('cut-ready.json' if old_plan else 'cut-arranging.json')).read_text())
    seed['roughcut']['status']='arranging';seed['roughcut']['display']['base_state']='cut-arranging';seed['roughcut']['job']={'job_id':'stop-demo','kind':'arrange','revision':2}
    page.evaluate("""async f=>{Object.assign(window.syntheticFixture,f);window.retryScenario=null;await window.r226.render({id:f.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);} """,seed)
    page.locator('[data-stop]').click()
    page.wait_for_selector('[data-design-id="R226-STYLES"]' if old_plan else '[data-design-id="R226-PICK"]')
    check=page.evaluate("""old=>({old_plan:old,state:document.querySelector('#review-screen').dataset.designState,extra_notice:!!document.querySelector('[data-design-id="R226-NOTICE"]'),plan:window.syntheticFixture.roughcut.plan})""",old_plan)
    ok=not check['extra_notice'] and (check['state']=='cut-ready' if old_plan else check['state']=='cut-no-music') and check['plan']==seed['roughcut']['plan']
    flow_results.append({'kind':'stop','old_plan':old_plan,'pass':ok})
    if not ok:failures.append({'state':name,'kind':'r226.stop-return','details':check})
    for width in [1440,430]:
     page.set_viewport_size({'width':width,'height':1000});page.screenshot(path=str(out/f'impl-flow-stopped-{old_plan}-{width}.png'),full_page=True)
   for kind in ['select_music','add_song','replace_song']:
    seed=json.loads((root/'tests/fixtures/r226-editing-techniques/api'/('cut-no-music.json' if kind=='select_music' else 'cut-ready.json')).read_text())
    page.set_viewport_size({'width':1440,'height':1000})
    page.evaluate("""async ({f,kind})=>{Object.assign(window.syntheticFixture,f);window.requests=[];window.retryScenario=kind;window.retryCalls=0;await window.r226.render({id:f.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);} """,{'f':seed,'kind':kind})
    if kind=='add_song':page.locator('[data-add-song]').click()
    if kind=='replace_song':page.locator('[data-replace-song]').first.click()
    page.locator('[data-song-use]').first.click();page.wait_for_selector('[data-failure-action="重新分析"]');page.locator('[data-failure-action="重新分析"]').click()
    page.wait_for_function("()=>(window.retryCalls===2)")
    trace=page.evaluate("""()=>({requests:window.requests.filter(r=>r.path.endsWith('/commands')||r.path.endsWith('/reanalyze')),version:window.replayVersion})""")
    cmds=[r['options']['body'] for r in trace['requests'] if r['path'].endswith('/commands')];reanalysis=next(r for r in trace['requests'] if r['path'].endswith('/reanalyze'))
    ok=len(cmds)==2 and cmds[0]['command']==cmds[1]['command'] and all(cmds[1][key]==value for key,value in trace['version'].items()) and reanalysis['options']['body']=={'part':'beat'} and (cmds[0]['command'].get('track_id') or cmds[0]['command']['track_ids'][0]) in reanalysis['path']
    flow_results.append({'kind':kind,'pass':ok,'trace':trace})
    if not ok:failures.append({'state':name,'kind':'r226.retry-command','details':trace})
    page.evaluate('window.r226.stop()')
   (out/'U6-U7-flows.json').write_text(json.dumps(flow_results,ensure_ascii=False,indent=2))
   edge_counts=[]
   for mode in ['off','skipped']:
    seed=json.loads((root/'tests/fixtures/r226-editing-techniques/api/cut-ready.json').read_text());p=seed['roughcut']['plan'];t=next(t for t in p['techniques'] if t['id']=='jcut');occ=[o for o in p['occurrences'] if o['technique']=='jcut']
    if mode=='off':
     t.update(enabled=False,count=0,status='off');seed['roughcut']['customization']['disabled']=['jcut']
     for o in occ:o['live']=False
    else:occ[0].update(live=False,skipped=True);t['count']-=1
    p['metrics']['occurrence_count']=sum(o['live'] for o in p['occurrences']);p['metrics']['used_technique_count']=sum(t['enabled'] and t['count']>0 for t in p['techniques'])
    page.evaluate("""async f=>{Object.assign(window.syntheticFixture,f);window.retryScenario=null;await window.r226.render({id:f.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);} """,seed)
    for width in [1440,1180,960,768,620,430,375]:
     page.set_viewport_size({'width':width,'height':1000});count=page.locator('.lane[data-technique="jcut"] [data-occ]').count();label=page.locator('[data-technique-row="jcut"] .nm i').inner_text()
     ok=count==t['count'] and label==('关掉了' if mode=='off' else str(t['count'])+' 处');edge_counts.append({'mode':mode,'width':width,'expected':t['count'],'actual':count,'label':label,'pass':ok})
     if not ok:failures.append({'state':name,'width':width,'kind':'r226.lane-count-edge','mode':mode})
   (out/'U2-edge-counts.json').write_text(json.dumps(edge_counts,ensure_ascii=False,indent=2))
  if name in ['cut-drafting','cut-drafted','cut-drafted-guide','cut-draft-stale']:
   d=fixture['roughcut']['draft'];surface=page.evaluate("""()=>({state:document.querySelector('#review-screen').dataset.designState,status:document.querySelector('.draft-status')?.getAttribute('role'),tone:document.querySelector('.draft-status')?.dataset.tone,step:document.querySelectorAll('.fstep')[3].innerText,done:document.querySelectorAll('.fstep')[3].classList.contains('done'),label:document.querySelector('[data-draft]').innerText,disabled:document.querySelector('[data-draft]').disabled,opens:document.querySelectorAll('[data-draft-open]').length,links:[...document.querySelectorAll('[data-design-id="R226-DRAFT-HANDOFF"]')].map(a=>({href:a.getAttribute('href'),target:a.target,rel:a.rel,download:a.hasAttribute('download')}))})""")
   expected_label='正在出草稿' if d['status']=='running' else '重新出草稿'
   valid=surface['state']==name and surface['status']=='status' and surface['label']==expected_label and surface['done']==(d['status']=='ready') and surface['opens']==int(d['can_open']) and len(surface['links'])==int(d['status']=='ready')
   if d['status']=='ready':valid=valid and surface['links'][0]==dict(href=fixture['roughcut']['artifacts'][0]['url'],target='_blank',rel='noopener',download=False)
   if not valid:failures.append({'state':name,'kind':'r226.draft-projection','details':surface})
   if name=='cut-drafted':
    page.set_viewport_size({'width':1440,'height':1000});page.locator('[data-draft-open]').click();page.wait_for_function("()=>(window.requests.some(r=>r.path.endsWith('/drafts/open')))")
    opening=page.evaluate("window.requests.find(r=>r.path.endsWith('/drafts/open')).options.body")
    expected=dict(expectedRevision=fixture['roughcut']['revision'],projectRevision=fixture['roughcut']['project_revision'],editorChoiceRevision=fixture['capabilities']['choice']['revision'],edlDigest=d['edl_digest'])
    if opening!=expected:failures.append({'state':name,'kind':'r226.open-binding','actual':opening,'expected':expected})
    with page.expect_popup() as popup_info:page.locator('[data-design-id="R226-DRAFT-HANDOFF"]').click()
    popup=popup_info.value;popup.wait_for_load_state();handoff_ok=popup.url.endswith('/roughcut/media/synthetic-guide') and '合成交接说明' in popup.locator('body').inner_text();popup.close()
    if not handoff_ok:failures.append({'state':name,'kind':'r226.guide-new-tab'})
    # A playable video comes through the artifact URL, even while audio verification
    # remains false. Its media clock is the sole source of playback progress.
    page.evaluate("""async()=>{const f=window.syntheticFixture;f.roughcut.artifacts.push({id:'synthetic-preview',kind:'preview',url:'/api/review/pieces/'+f.roughcut.piece_id+'/roughcut/media/synthetic-preview',content_type:'video/mp4',revision:f.roughcut.revision,shot_id:null});f.roughcut.playback={status:'ready',preview_artifact_id:'synthetic-preview',duration_sec:f.roughcut.plan.metrics.duration_sec,audio_verified:false,failure:null};await window.r226.render({id:f.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);}""")
    page.wait_for_function("()=>(document.querySelector('#stage video')?.readyState>=2)")
    if page.locator('#stage video').evaluate('(v)=>v.controls'):failures.append({'state':name,'kind':'r226.duplicate-player-controls'})
    page.locator('#play').click();page.wait_for_function("()=>(document.querySelector('#stage video').currentTime>.25)")
    page.evaluate("window.originalPreview=document.querySelector('#stage video')");page.locator('[data-editor-open]').click()
    kept=page.evaluate("window.originalPreview===document.querySelector('#stage video') && document.querySelector('#stage video').currentTime>.25")
    page.locator('[data-editor-x]').click();page.locator('#play').click();page.wait_for_function("()=>(document.querySelector('#stage video').paused)")
    paused=page.evaluate("document.querySelector('#stage video').currentTime");page.wait_for_timeout(250);stable=abs(page.evaluate("document.querySelector('#stage video').currentTime")-paused)<.02
    page.locator('[data-clip="3"]').click();page.wait_for_function("()=>(Math.abs(document.querySelector('#stage video').currentTime-window.syntheticFixture.roughcut.plan.clips[2].start)<.1)")
    sought=page.evaluate("({time:document.querySelector('#stage video').currentTime,pos:document.querySelector('#pos').innerText,src:document.querySelector('#stage video').getAttribute('src')})")
    page.locator('[data-from0]').click();page.wait_for_function("()=>(document.querySelector('#stage video').currentTime<1 && !document.querySelector('#stage video').paused)")
    for width in [1440,430]:page.set_viewport_size({'width':width,'height':1000});page.screenshot(path=str(out/f'preview-playing-{width}.png'),full_page=True)
    page.locator('#play').click();page.wait_for_function("()=>(document.querySelector('#stage video').paused)")
    # Simulate a server invalidation while the browser still owns the old URL.
    page.evaluate("""()=>{window.mediaExpired=true;window.syntheticFixture.roughcut.playback={status:'queued',preview_artifact_id:null,duration_sec:null,audio_verified:false,failure:null};const v=document.querySelector('#stage video');v.src=v.getAttribute('src')+'?expired=1';v.load();}""")
    page.wait_for_function("()=>(!document.querySelector('#stage video') && document.querySelector('#play').disabled)")
    expired=page.evaluate("({disabled:document.querySelector('#play').disabled,from0:document.querySelector('[data-from0]').disabled,pos:document.querySelector('#pos').innerText,notice:document.querySelector('[data-design-id=\"R226-NOTICE\"]')?.innerText})")
    expire_ok=expired['disabled'] and expired['from0'] and expired['pos'].startswith('0:00') and not expired.get('notice')
    flow=dict(open_binding=opening,handoff_new_tab=handoff_ok,video_preserved=kept,paused_clock_stable=stable,seek=sought,expired=expired,pass_=kept and stable and expire_ok)
    if not flow['pass_']:failures.append({'state':name,'kind':'r226.preview-flow','details':flow})
    (out/'preview-draft-flows.json').write_text(json.dumps(flow,ensure_ascii=False,indent=2))
    page.evaluate("""async()=>{window.mediaExpired=false;window.mediaFailed=true;window.syntheticFixture.roughcut.playback={status:'ready',preview_artifact_id:'synthetic-preview',duration_sec:window.syntheticFixture.roughcut.plan.metrics.duration_sec,audio_verified:false,failure:null};await window.r226.render({id:window.syntheticFixture.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);}""")
    page.wait_for_function("()=>(document.querySelector('[data-design-id=\"R226-NOTICE\"]')?.innerText.includes('预览没生成出来') && document.querySelector('#play').disabled)")
    page.evaluate("window.mediaFailed=false;window.requests=[]");page.locator('[data-notice-action="重试"]').click();page.wait_for_function("()=>(document.querySelector('#stage video')?.readyState>=2)")
    failure_retry=page.evaluate("!document.querySelector('#play').disabled && !window.requests.some(r=>r.path.endsWith('/drafts')||r.path.endsWith('/drafts/open'))")
    if not failure_retry:failures.append({'state':name,'kind':'r226.preview-failure-retry'})
    flow['media_failure_retry']=failure_retry;(out/'preview-draft-flows.json').write_text(json.dumps(flow,ensure_ascii=False,indent=2))
    # Exercise draft start -> independent job polling -> success and failure.
    page.evaluate("""async()=>{window.mediaExpired=false;window.readyDraft=structuredClone(window.syntheticFixture.roughcut.draft);window.syntheticFixture.roughcut.draft={...window.readyDraft,status:'none',design_state:null,can_open:false};window.draftOutcome='ready';window.requests=[];await window.r226.render({id:window.syntheticFixture.roughcut.piece_id},document.querySelector('.ptabs').outerHTML);}""")
    page.locator('[data-draft]').click();page.wait_for_selector('[data-design-id="R226-DRAFTING-STATUS"]');assert page.locator('[data-draft]').is_disabled()
    page.wait_for_selector('[data-design-id="R226-DRAFTED-STATUS"]',timeout=10000)
    page.evaluate("window.draftOutcome='failed'");page.locator('[data-draft]').click();page.wait_for_selector('[data-design-id="R226-DRAFTING-STATUS"]');page.wait_for_function("()=>(document.querySelector('[data-design-id=\"R226-NOTICE\"]')?.innerText.includes('草稿没出成'))",timeout=10000)
    failure_ok=page.locator('.draft-status').count()==0 and page.locator('[data-design-id="R226-TIMELINE"]').count()==1
    for width in [1440,430]:page.set_viewport_size({'width':width,'height':1000});page.screenshot(path=str(out/f'draft-failed-{width}.png'),full_page=True)
    page.evaluate("window.draftOutcome='ready'");page.locator('[data-notice-action="重试"]').click();page.wait_for_selector('[data-design-id="R226-DRAFTED-STATUS"]',timeout=10000)
    jobs=page.evaluate("window.requests.filter(r=>r.path.includes('/roughcut-jobs/')||r.path.endsWith('/drafts'))")
    draft_flow=dict(failure_preserves_plan=failure_ok,retry_ready=True,requests=jobs)
    if not failure_ok:failures.append({'state':name,'kind':'r226.draft-failure-plan'})
    (out/'draft-poll-flows.json').write_text(json.dumps(draft_flow,ensure_ascii=False,indent=2))
  page.evaluate('window.r226.stop()');context.close()
 browser.close()
(out/'design-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
(out/'screenshot-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
(out/'preset-preview-audit.json').write_text(json.dumps(preview_audits,ensure_ascii=False,indent=2))
(out/'panel-frames.json').write_text(json.dumps(panels,indent=2))
(out/'invalid-value-negative-proof.json').write_text(json.dumps(value_negative,ensure_ascii=False,indent=2))
assert len(value_negative)==7,'r226.invalid-value-negative: all seven widths required'
(out/'swap-title-negative-proof.json').write_text(json.dumps(swap_negative,ensure_ascii=False,indent=2))
assert len(swap_negative)==7,'r226.swap-title-negative: all seven widths required'
(out/'beat-map-audit.json').write_text(json.dumps(beat_audits,ensure_ascii=False,indent=2))
(out/'browser-results.json').write_text(json.dumps(dict(failures=failures,numbers=numbers),ensure_ascii=False,indent=2))
print(json.dumps(dict(states=len(fixtures),captures=len(records),failures=len(failures))))
sys.exit(bool(failures) or len(fixtures)!=36)
`;
let server;
let base=process.env.R226_STATIC_URL;
if(!base){
 const staticRoot=path.resolve(process.env.R226_STATIC_ROOT||path.join(root,'studio/static'));
 server=createServer(async(req,res)=>{
  try{
   const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
   const target=path.resolve(staticRoot,pathname==='/'?'index.html':'.'+pathname);
   if(req.method!=='GET'||!target.startsWith(staticRoot+path.sep)){res.writeHead(404);res.end();return;}
   const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'};
   const content=await fs.promises.readFile(target);res.writeHead(200,{'Content-Security-Policy':studioCsp,'Content-Type':(types[path.extname(target)]||'application/octet-stream')+'; charset=utf-8'});res.end(content);
  }catch{res.writeHead(404);res.end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port;
}
let run;
try{
 run=await new Promise((resolve,reject)=>{
  const child=spawn('uv',['run','--with','playwright','python','-',root,out,core],{env:{...process.env,R226_STATIC_URL:base},stdio:['pipe','pipe','pipe']});
  let stdout='',stderr='';child.stdout.on('data',chunk=>stdout+=chunk);child.stderr.on('data',chunk=>stderr+=chunk);
  child.on('error',reject);child.on('close',status=>resolve({status,stdout,stderr}));child.stdin.end(script);
 });
}finally{if(server)await new Promise(resolve=>server.close(resolve));}

fs.writeFileSync(path.join(out,'browser.log'),run.stdout+'\n'+run.stderr);process.stdout.write(run.stdout);process.stderr.write(run.stderr);
let bad=run.status!==0;
for(const [name,args] of [
 ['design-contract',[path.join(core,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract','docs/tasks/R226-editing-techniques/mock/design-contract.json','--approved-extras','docs/tasks/R226-editing-techniques/mock/approved-extras.json','--inventory',path.join(out,'design-inventory.json'),'--json']],
 ['ui-copy',[path.join(core,'skills/ui-copy-quality/scripts/check_ui_copy_quality.py'),'studio/static/review-cut.js','--evidence-dir',path.join(out,'copy-quality')]]
]){const r=spawnSync('python3',args,{encoding:'utf8'});fs.writeFileSync(path.join(out,name+'.log'),r.stdout+r.stderr);console.log(name+': '+r.status);bad ||= r.status!==0;}
process.exitCode=bad?1:0;
