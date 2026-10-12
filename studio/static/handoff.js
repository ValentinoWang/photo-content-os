const escape = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;'}[c]));
const time = seconds => Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}` : '';
const seconds = value => `${Number(value.toFixed(2))} 秒`;
const row = (label, value) => value === undefined || value === null || value === '' ? '' : `<div><span>${label}</span><b data-design-data="local.fact">${escape(value)}</b></div>`;

function suggestionsView(data) {
  const cuts = data.suggestions.filter(s => s.type !== 'animation');
  const automatic = cuts.filter(s => s.automatic), review = cuts.length - automatic.length;
  // Merge overlapping ranges, matching the editor's actual removed-time arithmetic.
  const intervals = automatic.map(s => [s.start, s.end]).sort((a,b) => a[0]-b[0]);
  let end = 0, removed = 0;
  for (const [start, finish] of intervals) { removed += Math.max(0, finish - Math.max(start, end)); end = Math.max(end, finish); }
  const line = item => `<li><span class="t" data-design-data="suggestion.start">${time(item.start)}</span><i class="${item.type === 'animation' ? 'a' : !item.automatic ? 'review' : item.type === 'silence' ? 'g' : ''}">${item.type === 'animation' ? `动画 ${escape(item.animationId)}` : !item.automatic ? '只复核' : item.type === 'silence' ? '静音' : '重说'}</i><span class="x" data-design-data="suggestion.text" title="${escape(item.text)}">${escape(item.text)}</span><span class="len" data-design-data="suggestion.duration">${seconds(item.end - item.start)}</span></li>`;
  const animations = data.suggestions.filter(s => s.type === 'animation');
  return `<h2 data-design-id="edit-suggestions">剪辑建议<small>只给位置，精修在剪辑软件里做</small></h2><div class="sec" data-design-data="suggestions.summary">剪辑建议 ${cuts.length} 处 · 可自动剪 ${automatic.length} 处共 ${time(removed)}，复核 ${review} 处</div><ul class="sug">${cuts.slice(0,8).map(line).join('')}${cuts.length > 8 ? `<li><span class="t">…</span><i class="g" data-design-data="suggestions.remaining">另 ${cuts.length-8} 处</i><span class="x" data-design-data="suggestions.remainingStart" title="${escape(cuts.slice(8).map(s=>`${time(s.start)} · ${s.text}`).join('；'))}">${time(cuts[8].start)} 之后</span><span class="len"></span></li>` : ''}</ul>${animations.length ? `<div class="sec" data-design-data="suggestions.animations">动画建议位置 ${animations.length} 处（交给剪辑软件叠到口播上）</div><ul class="sug">${animations.map(line).join('')}</ul>` : ''}`;
}

function materialsView(data) {
  const labels = {original: '口播原片', subtitles: '字幕', transcript: '转写', images: '图片素材'};
  const materials = data.materials.filter(m => labels[m.role]);
  const materialRows = items => `${items.map(m => `<li><b>${labels[m.role]}</b><small data-design-data="materials.details">${m.role === 'images' ? `${m.count} 张` : m.role === 'transcript' ? `${m.characters} 字${m.precision === 'word' ? ' · 按词对齐时间' : ''}` : m.role === 'subtitles' && Number.isInteger(m.count) ? `按转写生成 · ${m.count} 条` : escape(m.name)}${m.role === 'original' && data.sourceDuration ? ` · ${time(data.sourceDuration)}` : ''}</small>${m.role === 'transcript' ? '<span class="st">已完成</span>' : m.role === 'subtitles' ? '<span class="st">已生成</span>' : m.role === 'images' && m.pending ? `<span class="st w" data-design-data="materials.pending">${m.pending} 张待确认</span>` : ''}</li>`).join('')}`;
  return `<h2>交过去的素材<small>都在你电脑上</small></h2><ul class="pack" data-design-id="handoff-pack">${materialRows(materials.filter(m=>['original','transcript'].includes(m.role)))}${data.animations.map(a => `<li><b>讲解动画 ${escape(a.shotId)}</b><small data-design-data="animation.details">${escape(a.title)}${Number.isFinite(a.duration) ? ` · ${seconds(a.duration)}` : ''}${Number.isInteger(a.frames) && Number.isInteger(a.totalFrames) ? ` · ${a.frames === a.totalFrames ? a.totalFrames : `${a.frames} / ${a.totalFrames}`} 帧` : ''}</small>${a.status === 'completed' ? '<span class="st">已渲染</span>' : a.status === 'running' ? '<span class="st r">渲染中</span>' : ''}</li>`).join('')}${materialRows(materials.filter(m=>['subtitles','images'].includes(m.role)))}</ul>`;
}

function editorView(data) {
  const cc = data.tools.chatcut, selected = data.choice.editor === 'kdenlive';
  if (data.state === 'returned') {
    const c = data.candidate, checks = c.checks || {};
    const passed = [['playable','能完整播放'], ['avSync',Number.isFinite(checks.avOffsetSeconds) ? `音画相差 ${Number(checks.avOffsetSeconds.toFixed(2))} 秒` : null], ['frameCount','帧数和时长一致'], ['sourceUnchanged','原片没有被改动']].filter(([key, text]) => checks[key] === 'pass' && text);
    const returned = c.returnedAt ? new Date(c.returnedAt) : null;
    return `<h2>剪辑软件</h2><div class="cc"><div class="done" data-design-id="return-receipt" data-design-data="candidate.returnedAt">导出的成片已收回${returned && !Number.isNaN(+returned) ? ` · ${returned.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false})}` : ''}</div><div class="rows" data-design-id="return-facts">${row('剪辑软件',data.editorName)}${row('项目',data.title)}${data.exported ? row('导出','已导出') : ''}${row('成片',Number.isFinite(c.durationSeconds) && Number.isInteger(c.frameCount) ? `${time(c.durationSeconds)} · ${c.frameCount} 帧` : null)}${row('成片检测剪点',Number.isInteger(c.cutCount) && Number.isFinite(c.removedSeconds) ? `${c.cutCount} 处 · ${time(c.removedSeconds)}` : null)}${data.animationCount ? row('动画',`${data.animationCount} 段已叠入`) : ''}</div><ul class="chk" data-design-id="return-checks">${passed.map(([,text]) => `<li data-design-data="candidate.check">${text}</li>`).join('')}</ul>${data.uploaded ? '<p class="pnote" data-design-id="candidate-upload">低清候选已回传 MediaClaw，在作品页确认是否采用。</p>' : ''}</div>`;
  }
  let attention = '';
  if (!cc.handshake && !selected) {
    const missing = cc.installed === false, loggedOut = cc.login === false;
    const title = missing ? '本机没有安装 ChatCut' : loggedOut ? 'ChatCut 还没登录' : 'ChatCut 的本机连接还未握手';
    const explanation = missing ? '请先安装桌面版，再检查登录和本机连接。' : loggedOut ? '登录后，Studio 会检查本机连接；握手成功才可以交接。' : 'Studio 需要通过本机连接检查，才能交入素材。';
    const action = missing ? '<a class="btn" href="https://chatcut.io/desktop-plugin" target="_blank" rel="noopener">下载 ChatCut</a>' : loggedOut ? '<a class="btn btn--pri" href="chatcut://">打开 ChatCut 登录</a>' : '<button class="btn btn--pri" data-recheck>检查本机连接</button>';
    attention = `<div class="attn" role="alert" data-design-id="chatcut-action"><b>${title}</b><span>${explanation}</span>${action}</div>`;
  }
  const review = data.suggestions.filter(s => s.type !== 'animation' && !s.automatic).length;
  const receipt = cc.projectRef && Number.isInteger(data.precutCount) ? `<div class="done" data-design-id="precut-receipt" data-design-data="editor.precutCount">第一版已预剪好 · 预剪 ${data.precutCount} 处${review ? `，<span class="review-summary">另 ${review} 处只供复核</span>` : ''}</div>` : '';
  const expectation = selected && data.state === 'offline' ? '下次交接使用 Kdenlive 自动剪第一版有声成片；无需登录，完成后由 Studio 收回检查。' : cc.projectRef ? `项目〈${escape(data.title)}〉已交给 ChatCut。请在那里试听、撤回、精修，导出后回到 Studio 检查。` : cc.handshake ? '本机连接已握手。交接成功后才会创建本项目和预剪第一版；尚未收到项目回执。' : `交接成功后，ChatCut 里会出现项目〈${escape(data.title)}〉及按建议预剪的第一版。你在那里试听、撤回、精修，导出后回到这里检查。`;
  return `<h2>剪辑软件</h2><div class="cc">${attention}<div class="rows" data-design-id="chatcut-probe">${row('安装',cc.installed ? `已安装${cc.version ? ` · ${cc.version}` : ''}` : '未安装')}${row('登录',cc.login === true ? '已登录' : cc.login === false ? '未登录' : '未知')}${row('本机连接',cc.handshake ? '已握手' : '未握手')}${row('本项目',cc.projectRef ? '已存在' : cc.handshake ? '尚无本项目' : '尚未交接')}</div>${receipt}<p class="pnote" data-design-id="handoff-expectation" data-design-data="project.title">${expectation}</p>${cc.projectUrl ? `<a class="btn btn--pri project-link" href="${escape(cc.projectUrl)}">在 ChatCut 打开</a>` : ''}<div class="state-tools" data-design-id="editor-fallback"><h3>Kdenlive · 自动备用</h3><div class="editor-choice"><div><b data-design-data="tools.kdenlive.version">${data.tools.kdenlive.installed ? `已安装${data.tools.kdenlive.version ? ` · ${escape(data.tools.kdenlive.version)}` : ''}` : '未安装'}</b><small>无需登录。可自动剪一版有声成片，收回后沿用同一套检查。</small></div><button class="btn" data-editor-choice aria-pressed="${selected}" ${!data.tools.kdenlive.installed && !selected ? 'disabled' : ''}>${selected ? '改用 ChatCut' : '改用 Kdenlive'}</button></div><p class="pnote" data-backend-note>${selected ? '已选择 Kdenlive：下次交接使用备用剪辑，现有项目回执不变。' : '当前选择：ChatCut；不会自动切换。'}</p></div></div>`;
}

function timelineView(data) {
  const duration = data.sourceDuration;
  if (!Number.isFinite(duration) || duration <= 0) return '';
  const percent = value => Math.max(0, Math.min(100, value / duration * 100));
  const spans = data.suggestions.filter(s => s.type !== 'animation').map(s => `<span class="interval ${!s.automatic ? 'review' : s.type === 'silence' ? 'gap' : 'cut'}" data-position="${percent(s.start)}" data-length="${percent(s.end)-percent(s.start)}"></span>`).join('');
  const waves = data.waveformPeaks.map((p,i,peaks) => `<rect x="${i / peaks.length * 1000}" y="${20-p*18}" width="${800/peaks.length}" height="${Math.max(1,p*36)}"/>`).join('');
  return `<section class="tl" aria-label="时间线" data-design-id="suggestion-timeline"><header><b>建议位置</b><span>红色是重说预剪建议，灰色是静音，虚线框只复核，竖线是动画建议。</span></header><div class="track"><span>段落</span><div class="segs">${data.shots.map(s => `<i data-position="${percent(s.start)}">${escape(s.shotId)}</i>`).join('')}</div></div><div class="track"><span>原片</span><div class="lane">${waves ? `<svg viewBox="0 0 1000 40" preserveAspectRatio="none" aria-hidden="true">${waves}</svg>` : ''}${spans}${data.suggestions.filter(s => s.type === 'animation').map(s => `<span class="mk" data-position="${percent(s.start)}"><b>${escape(s.animationId)}</b></span>`).join('')}</div></div><div class="ruler">${[0,duration/4,duration/2,duration*3/4,duration].map((s,i) => `<span data-design-data="timeline.time" data-position="${i*25}">${time(s)}</span>`).join('')}</div></section>`;
}

export function renderHandoff(target, data, actions) {
  target.innerHTML = `<div class="handoff" data-design-state="${data.state}" data-design-id="studio-${data.state}"><div class="work"><section class="card">${materialsView(data)}</section><section class="card">${suggestionsView(data)}</section><section class="card editor-card">${editorView(data)}</section></div>${timelineView(data)}</div>`;
  // The loopback CSP rejects style attributes in HTML; numeric CSSOM writes
  // keep time-derived geometry without relaxing that policy.
  target.querySelectorAll('[data-position]').forEach(node => {
    node.style.left = `${Number(node.dataset.position)}%`;
    if (node.hasAttribute('data-length')) node.style.width = `${Number(node.dataset.length)}%`;
  });
  const button = target.querySelector('[data-editor-choice]');
  if (button) button.onclick = async () => {
    const before = {...data.choice};
    data.choice = {editor:before.editor === 'kdenlive' ? 'chatcut' : 'kdenlive', revision:before.revision};
    renderHandoff(target,data,actions);
    target.querySelector('[data-editor-choice]').disabled = true;
    try { data.choice = await actions.choose(data.choice); }
    catch { data.choice = before; }
    renderHandoff(target,data,actions);
  };
  const recheck = target.querySelector('[data-recheck]');
  if (recheck) recheck.onclick = async () => { recheck.disabled = true; try { await actions.recheck(); } finally { recheck.disabled = false; } };
}
