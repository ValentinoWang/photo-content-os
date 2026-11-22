// 全流程设计稿：路由、外壳、共用组件、设计数据。只给设计用，不是实现代码。
// 页面登记：PCOS.reg(id, {group, name, nav, piece, line, states, crumb, title, sub, actions, flow, render, after})
//   group   设计稿状态条里的分组名        name   页面名（状态条下拉里显示）
//   nav     左侧导航高亮哪一项：home | inbox | projects | library | music | settings
//   piece   作品页才有：{tab:'vlog'|'script'|'tidy'|'archive', step:1-5}；有它就自动画作品分页和步骤条
//   line    脚本线的拍法：'spoken' 口播 | 'direct' 直出；不写就沿用当前拍法
//   states  [[状态编号, 状态名], ...]，第一个是主状态（最差的真实首屏）
//   crumb/title/sub/actions  顶栏；可以是字符串，也可以是 (state, ctx) => 字符串
//   flow    (state, ctx) => {notes:[5 句], done:[5 个布尔], warn:[要标警示色的步骤序号]}，改步骤条
//   render  (state, ctx) => 页面 HTML；after(root, state, ctx) 绑定页面里自己的交互
// 页面里的跳转：任何元素加 data-go="页面编号"（可加 data-s="状态"、data-line="spoken|direct"）；
//   只给反馈：data-toast="一句话"。
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const D = v => `<span data-design-data>${esc(v)}</span>`;
  const mmss = t => { t = Math.max(0, Math.round(t)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); };
  const s1 = t => (Math.round(t * 10) / 10).toFixed(1);

  // ---------- 图标（与 Studio 侧栏同一套 lucide 线框） ----------
  const svg = p => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
  const ICON = {
    home: svg('<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    inbox: svg('<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'),
    projects: svg('<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'),
    library: svg('<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'),
    music: svg('<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'),
    settings: svg('<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>'),
    upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>',
    lock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    sparkle: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/></svg>',
  };
  const NAV = [['home', '工作台', 'home'], ['inbox', '整理台', 'inbox'], ['projects', '项目', 'projects'], ['library', '素材库', 'library'], ['music', '音乐库', 'music'], ['settings', '设置与诊断', 'set-model']];

  // ---------- 设计数据 ----------
  const SHOTS = Array.isArray(window.SHOTS) ? window.SHOTS : [];
  const SEL = SHOTS.filter(s => s.status === 'selected');
  const SCENES = { 'selfie-moments': '自拍', 'sports-meet': '校运会', 'travel': '路上', 'travel/raw-pending': '路上' };
  const SITE = window.SITE || { projects: [], assets: [] };
  const TRACKS = Array.isArray(window.TRACKS) ? window.TRACKS : [];
  const frameOf = s => (s && Array.isArray(s.frames) ? (s.frames[1] || s.frames[0] || '') : '');
  // 读不到图时换成灰块，版面不变
  const img = (src, alt = '') => src
    ? `<img src="${esc(src)}" alt="${esc(alt)}" onerror="this.outerHTML='<span class=&quot;ph&quot;></span>'">`
    : '<span class="ph"></span>';
  const shotImg = s => img(frameOf(s), s ? (s.reason || '') : '');
  // 第 n 个镜头（循环取），没有设计数据时返回 null
  const shot = n => (SHOTS.length ? SHOTS[((n % SHOTS.length) + SHOTS.length) % SHOTS.length] : null);
  const sel = n => (SEL.length ? SEL[((n % SEL.length) + SEL.length) % SEL.length] : shot(n));
  const pieceOf = id => { for (const p of SITE.projects || []) for (const x of p.pieces || []) if (x.id === id) return x; return null; };
  const posterOf = (id, i = 0) => { const p = pieceOf(id); const o = p && p.outputs && p.outputs[i]; return o ? '../flow-studio--vlog-workflow--Pho_R208/' + o.poster : ''; };

  // 三件作品：vlog 用兰大那件；脚本线口播、直出各一件（用户本机真实作品名）
  const PIECE = {
    vlog: { id: '2026-lzu-travel-and-sports', title: '兰州大学 · 奔赴与校运会', project: '2026年重回兰州大学内容创作', date: '2026/5/14' },
    spoken: { id: 'project-fc6baa3294', title: '断更一年，我拆了四句话', project: '其他作品' },
    direct: { id: 'p5-f24c41f746', title: 'P5 直出实践：平均速度', project: '其他作品' },
  };

  // ---------- 步骤条 ----------
  const STEPS = {
    vlog: [['素材', 'v1'], ['挑镜头', 'v2'], ['配乐卡点', 'v3'], ['出草稿', 'v4'], ['人工精剪', 'v5']],
    spoken: [['写稿', 's1'], ['分镜', 's2'], ['对稿剪辑', 's3'], ['字幕与声音', 's4'], ['出片检查', 's5']],
    direct: [['写稿', 's1'], ['分镜', 's2'], ['逐镜动画', 's3d'], ['字幕与声音', 's4'], ['出片检查', 's5']],
  };
  const NOTES = {
    vlog: ['55 段视频 · 6 张照片', '27 个精选 · 已确认', '2 首歌 · 0:43', '用 Kdenlive', '在剪辑软件里改'],
    spoken: ['口播稿第 5 版', '9 镜 · 缺 2 镜', '12 处剪辑建议', '中文字幕 46 条', '还没出片'],
    direct: ['口播稿第 3 版', '7 镜 · 都配上了', '第 5 镜没渲染成', '中英字幕 · 1 条放不下', 'v2 通过检查'],
  };

  const ctx = { line: 'spoken', esc, D, mmss, s1, img, shotImg, shot, sel, SHOTS, SEL, SCENES, SITE, TRACKS, PIECE, ICON, posterOf, pieceOf, frameOf };
  try { const l = sessionStorage.getItem('pcos-line'); if (l === 'spoken' || l === 'direct') ctx.line = l; } catch (e) { /* 读不到就用默认 */ }

  const screens = {};
  const order = [];
  function reg(id, def) { if (!screens[id]) order.push(id); screens[id] = def; }

  // ---------- 共用组件 ----------
  const C = {};
  C.btn = (label, o = {}) => {
    const a = [`class="btn ${o.pri ? 'btn--pri' : ''} ${o.cls || ''}"`];
    if (o.go) a.push(`data-go="${o.go}"`);
    if (o.s) a.push(`data-s="${o.s}"`);
    if (o.line) a.push(`data-line="${o.line}"`);
    if (o.toast) a.push(`data-toast="${esc(o.toast)}"`);
    if (o.disabled) a.push('disabled');
    if (o.id) a.push(`data-design-id="${o.id}"`);
    return `<button ${a.join(' ')}>${label}</button>`;
  };
  C.link = (label, o = {}) => `<button class="link" ${o.go ? `data-go="${o.go}"` : ''} ${o.s ? `data-s="${o.s}"` : ''} ${o.toast ? `data-toast="${esc(o.toast)}"` : ''}>${label}</button>`;
  C.lineb = line => ({ vlog: '<span class="lineb lineb--vlog">按素材剪 vlog</span>', spoken: '<span class="lineb lineb--spoken">口播</span>', direct: '<span class="lineb lineb--direct">直出</span>' })[line] || '';
  // 页头：eyebrow 写「第 n 步 · 步骤名」
  C.head = ({ eyebrow, title, lede, actions = '', id }) => `<div class="stephead full" ${id ? `data-design-id="${id}"` : ''}><div>${eyebrow ? `<p class="eyebrow">${eyebrow}</p>` : ''}<h2>${title}</h2>${lede ? `<p>${lede}</p>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;
  // 提醒块：tone 'warn' 要你处理；'cut' 失败。正文字号，单独一块，带动作
  C.attn = ({ title, text = '', list, actions = '', tone = 'warn', id }) => `<div class="attention ${tone === 'cut' ? 'attention--cut' : ''}" role="alert" ${id ? `data-design-id="${id}"` : ''}><div><strong>${title}</strong>${text ? `<p>${text}</p>` : ''}${list ? `<ul>${list.map(x => `<li>${x}</li>`).join('')}</ul>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;
  C.note = (text, id) => `<div class="note" ${id ? `data-design-id="${id}"` : ''}>${text}</div>`;
  C.statusline = (text, action = '', id) => `<div class="statusline" ${id ? `data-design-id="${id}"` : ''}><span>${text}</span>${action}</div>`;
  C.st = (text, kind = '') => `<span class="st ${kind ? 'st--' + kind : ''}">${text}</span>`;
  C.meter = (p, done) => `<div class="meter ${done ? 'done' : ''}"><i style="width:${Math.max(0, Math.min(100, p))}%"></i></div>`;

  // 六项检查（收回成片和出片检查共用）。items: [[名称, 'ok'|'fail'|'unk', 右侧数值]]
  const CHECKS = ['能完整播放', '音画同步', '帧数和时长一致', '原片没有被改动', '字幕', '黑帧'];
  C.checks = (items, cls = '') => `<ul class="chk ${cls}" data-design-id="SHARED-CHECKS">${items.map(([name, st, val]) => `<li class="${st === 'fail' ? 'fail' : st === 'unk' ? 'unk' : ''}">${name}<span>${val || ''}</span></li>`).join('')}</ul>`;
  C.CHECKS = CHECKS;
  // 收回成片的拖放区。manual：剪辑软件读不回工程（剪映等）
  C.drop = ({ manual = false, editor = 'Kdenlive' } = {}) => `<section class="drop" data-design-id="SHARED-RETURN"><span class="ic-box">${ICON.upload}</span><div><h3>把导出的成片拖到这里</h3><p>在 ${esc(editor)} 里改完、导出 MP4 以后拖进来。收回后检查能不能完整播放、音画同不同步、帧数和原片，通过的才算一版。${manual ? '<br>这个软件读不回工程：剪点和字幕标「没核验」，只看实测四项。' : ''}</p></div><div class="actions">${C.btn('选择成片…', { toast: '打开系统的选择文件窗口' })}</div></section>`;
  // 候选成片卡
  C.cand = ({ v, editor, dur, frames, status, checks, poster, current, actions = '', note = '' }) => `<article class="cand" ${current ? 'aria-current="true"' : ''} data-design-id="SHARED-CANDIDATE"><div class="poster">${img(poster)}<span class="len">${D(dur)}</span></div><div class="facts"><header><h4>${D(v)} · ${D(editor)}</h4>${status === 'pass' ? C.st('通过检查') : status === 'fail' ? C.st('检查没通过', 'bad') : C.st('正在检查', 'run')}</header><p>${D(dur)}${frames ? ` · ${D(frames)} 帧` : ''}${note ? ` · ${note}` : ''}</p>${checks ? C.checks(checks) : ''}${actions ? `<div class="actions">${actions}</div>` : ''}</div></article>`;
  // 发布与复盘：facts [[名称, 值, 是否文字]]
  C.pub = facts => `<div class="pub" data-design-id="SHARED-PUBLISH">${facts.map(([k, v, txt]) => `<div><small>${k}</small><b class="${txt ? 'txt' : ''}">${v}</b></div>`).join('')}</div>`;

  // 作品分页
  function ptabs(def) {
    const tab = def.piece.tab;
    const t = (key, label, go, side) => `<button role="tab" ${side ? 'class="ptab-side"' : ''} aria-selected="${tab === key}" data-go="${go}">${label}</button>`;
    return `<div class="ptabs full" role="tablist" data-design-id="R208-PIECE-tabs">${t('vlog', '按素材剪 vlog', 'v2')}${t('script', '按脚本做视频', 's1')}${t('tidy', '素材整理', 'tidy', true)}${t('pack', '包装素材', 'pack')}${t('archive', '保存与归档', 'archive')}</div>`;
  }
  // 步骤条
  function flow(def, state) {
    if (def.piece.tab !== 'vlog' && def.piece.tab !== 'script') return '';
    const key = def.piece.tab === 'vlog' ? 'vlog' : ctx.line;
    const cur = def.piece.step - 1;
    const o = (def.flow && def.flow(state, ctx)) || {};
    const notes = NOTES[key].map((n, i) => (o.notes && o.notes[i] != null ? o.notes[i] : n));
    const done = STEPS[key].map((_, i) => (o.done ? !!o.done[i] : i < cur));
    const warn = new Set(o.warn || []);
    return `<nav class="flow full" aria-label="这件作品的步骤" data-design-id="FLOW-STEPS">${STEPS[key].map(([title, go], i) => `<button class="fstep ${done[i] && i !== cur ? 'done' : ''} ${i === cur ? 'cur' : ''} ${warn.has(i) ? 'fstep--warn' : ''}" ${i === cur ? 'aria-current="step"' : ''} data-go="${go}"><b>${done[i] && i !== cur ? '✓' : i + 1}</b><span><strong>${title}</strong><small data-design-data>${esc(notes[i])}</small></span></button>`).join('')}</nav>`;
  }
  function pieceTop(def) {
    const p = ['vlog', 'tidy', 'archive', 'pack'].includes(def.piece.tab) ? PIECE[def.pieceKey || 'vlog'] : PIECE[ctx.line];
    return p;
  }

  // ---------- 渲染 ----------
  let lastId = null;
  const val = (v, state) => (typeof v === 'function' ? v(state, ctx) : v);
  function parse() { return new URLSearchParams(location.hash.slice(1)); }
  function go(id, s, line) {
    const q = new URLSearchParams();
    q.set('p', id);
    if (s) q.set('s', s);
    if (line) q.set('line', line);
    const cur = parse();
    if (cur.get('chrome') === '0') q.set('chrome', '0');
    location.hash = q.toString();
  }
  function render() {
    const q = parse();
    let id = q.get('p') || 'home';
    if (!screens[id]) id = screens.home ? 'home' : order[0];
    const def = screens[id];
    if (!def) return;
    const lineQ = q.get('line');
    if (def.line) ctx.line = def.line; else if (lineQ === 'spoken' || lineQ === 'direct') ctx.line = lineQ;
    try { sessionStorage.setItem('pcos-line', ctx.line); } catch (e) { /* 只是记住拍法，失败无妨 */ }
    const states = def.states || [['default', '默认']];
    let state = q.get('s');
    if (!states.some(([k]) => k === state)) state = states[0][0];
    ctx.state = state; ctx.id = id;

    // 侧栏
    $('#nav').innerHTML = NAV.map(([key, label, target]) => `<button data-go="${target}" ${def.nav === key ? 'aria-current="true"' : ''}><span>${ICON[key]}</span>${label}${key === 'home' ? '<i class="badge" data-design-data>5</i>' : ''}</button>`).join('');
    $('#side-foot').innerHTML = '<div><i class="dot dot--ok"></i>本机可用</div><div><i class="dot"></i>上游中台没连上</div>';

    // 顶栏
    let crumb = val(def.crumb, state), title = val(def.title, state), sub = val(def.sub, state), actions = val(def.actions, state) || '';
    if (def.piece) {
      const p = pieceTop(def);
      if (crumb == null) crumb = `<button data-go="projects">项目</button>·${D(p.project)}`;
      if (title == null) title = D(p.title);
      if (sub == null && p.date) sub = D(p.date);
    }
    $('#topbar').innerHTML = `<div>${crumb ? `<div class="crumb">${crumb}</div>` : ''}<h1>${title || ''}</h1>${sub ? `<p class="sub">${sub}</p>` : ''}</div><div class="actions">${actions}</div>`;

    // 主区
    const body = val(def.render, state) || '';
    $('#screen').innerHTML = (def.piece ? ptabs(def) + flow(def, state) : '') + body;
    if (def.after) def.after($('#screen'), state, ctx);

    // 设计稿状态条
    const pbar = $('#pbar');
    if (q.get('chrome') === '0') { pbar.hidden = true; document.body.classList.add('no-chrome'); }
    else {
      pbar.hidden = false;
      const groups = {};
      order.forEach(k => { const g = screens[k].group || '其他'; (groups[g] = groups[g] || []).push(k); });
      pbar.innerHTML = `<select aria-label="跳到页面">${Object.entries(groups).map(([g, ids]) => `<optgroup label="${esc(g)}">${ids.map(k => `<option value="${k}" ${k === id ? 'selected' : ''}>${esc(screens[k].name || k)}</option>`).join('')}</optgroup>`).join('')}</select><b>状态</b>${states.map(([k, label]) => `<button data-state="${k}" aria-pressed="${k === state}">${esc(label)}</button>`).join('')}<a href="index.html">设计稿正文 ›</a>`;
      pbar.querySelector('select').onchange = e => go(e.target.value);
    }
    document.title = `${def.name || id} · Studio 全流程原型`;
    if (lastId !== id) window.scrollTo(0, 0);
    lastId = id;
  }

  let toastTimer = null;
  function toast(text) { const t = $('#toast'); t.textContent = text; t.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2400); }

  function start() {
    document.addEventListener('click', e => {
      const st = e.target.closest('[data-state]');
      if (st && st.closest('#pbar')) { const q = parse(); go(q.get('p') || 'home', st.dataset.state, q.get('line')); return; }
      const g = e.target.closest('[data-go]');
      if (g && !g.disabled) { e.preventDefault(); go(g.dataset.go, g.dataset.s, g.dataset.line); return; }
      const t = e.target.closest('[data-toast]');
      if (t && !t.disabled) toast(t.dataset.toast);
    });
    window.addEventListener('hashchange', render);
    render();
  }

  window.PCOS = { reg, start, render, go, toast, ctx, C, screens, order };
})();
