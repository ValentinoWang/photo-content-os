// 按素材剪 vlog：1 素材 → 2 挑镜头 → 3 配乐卡点 → 4 出草稿 → 5 人工精剪。见 SPEC.md 第 3、4 节。
// 故事：「兰州大学 · 奔赴与校运会」从刚连上素材一步步往前走。
// 画面数据取自 R208 设计数据（SHOTS，兰大 128 个镜头）；转写句子、草稿记录、发布数据是设计用的示例，不是正式结果。
(function () {
  'use strict';
  const { reg, C, ctx } = PCOS;
  const { esc, D, mmss, s1, img, shotImg, SHOTS, SEL, SCENES, TRACKS, posterOf, pieceOf } = ctx;
  const META = window.META || { median: 1500, hooks: [] };
  const LZU = '2026-lzu-travel-and-sports';
  const playBtn = () => '<button class="btn btn--play" data-toast="打开成片播放器：v1、v2 两版可以来回切">看已出的成片 <span data-design-data>v1 · v2</span></button>';
  const eager = root => root.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; });
  const nameOf = s => String((s && s.src) || '').split('/').pop().replace(/\.[^.]+$/, '').replace(/_LIVE\d+$/, '').replace(/_/g, ' ');
  const sceneOf = s => SCENES[s.scene] || '路上';
  // 设计数据里的 AI 理由有几句带「据文件名」和镜头编号，界面不该出现：去掉这些分句
  const clean = t => { const parts = String(t || '').replace(/。；/g, '；').split(/[，；。]/).map(x => x.trim()).filter(x => x && !/文件名|S[0-9a-f]{6,}|视觉标记/.test(x)); return parts.length ? parts.join('，') + '。' : ''; };
  const outDur = i => { const p = pieceOf(LZU); const o = p && p.outputs && p.outputs[i]; return o ? mmss(o.dur) : '0:33'; };

  // ---------- 素材：按原文件归并镜头 ----------
  const MATS = (() => {
    const by = new Map();
    SHOTS.forEach(s => {
      if (!by.has(s.src)) by.set(s.src, { src: s.src, scene: s.scene, kind: s.kind, shots: [], end: 0 });
      const m = by.get(s.src); m.shots.push(s); m.end = Math.max(m.end, s.end || 0);
    });
    return [...by.values()].map((m, i) => ({ ...m, i, name: nameOf(m.shots[0]), reason: clean((m.shots.find(s => s.reason) || {}).reason), talk: m.scene === 'selfie-moments' && m.kind === 'video' }));
  })();
  const med = META.median || 1500;
  function health(m) {
    const t = [];
    if (m.shots.some(s => s.sharp != null && s.sharp < 0.4 * med)) t.push('有点糊');
    if (m.shots.some(s => (s.flags || []).includes('shake'))) t.push('有点抖');
    if (m.shots.some(s => s.over > 0.25)) t.push('过曝');
    if (m.shots.some(s => s.under > 0.25)) t.push('欠曝');
    if (m.shots.some(s => s.kind === 'video' && s.dur < 0.8)) t.push('有太短的片段');
    if (m.shots.some(s => s.vflags && s.vflags.has_watermark)) t.push('有水印');
    return t;
  }
  // 设计用的转写示例（自拍视频才有）
  const TALK = [
    [['0:01', '终于到兰州了。'], ['0:04', '先回学校看一眼，下午去校运会。'], ['0:09', '这个机场比我上学的时候大了好多。']],
    [['0:00', '今天是校运会第一天。'], ['0:03', '我报了四百米，有点紧张。']],
    [['0:02', '跑完了，腿是软的。'], ['0:05', '比去年快了一秒多。']],
  ];
  const talkOf = m => TALK[m.i % TALK.length];
  let curMat = Math.max(0, MATS.findIndex(m => m.talk));
  const SCENE_ORDER = ['travel', 'sports-meet', 'selfie-moments', 'travel/raw-pending'];
  const SCENE_NAME = { 'travel': '路上', 'sports-meet': '校运会', 'selfie-moments': '自拍', 'travel/raw-pending': '待处理' };

  function matCard(m, queued) {
    const f = m.shots[0].frames || [];
    const tags = queued ? '<span class="tag">还没看</span>' : [...health(m).map(t => `<span class="tag tag--warn">${t}</span>`), m.talk ? '<span class="tag tag--hook">有人说话</span>' : '', m.kind === 'photo' ? '<span class="tag">照片</span>' : ''].join('');
    const len = m.kind === 'photo' ? '照片' : mmss(m.end);
    return `<button class="card vl-mat ${queued ? 'vl-queued' : ''}" data-mat="${m.i}" aria-selected="${m.i === curMat}" data-design-id="V1-MATERIAL"><div class="strip">${[0, 1, 2].map(k => img(f[k] || f[0])).join('')}<span class="len" data-design-data>${len}</span></div><div class="card-body"><div class="card-top"><b data-design-data>${esc(m.name)}</b></div>${queued ? '<p class="reason vl-wait">排在队里，看完会写一句 AI 看到的。</p>' : `<p class="reason" data-design-data>${esc(m.reason)}</p>`}${m.talk && !queued ? `<p class="vl-talk" data-design-data>「${esc(talkOf(m)[Math.floor(m.i / 3) % talkOf(m).length][1])}」</p>` : ''}<div class="tags">${tags}</div></div></button>`;
  }

  function matRail(state) {
    const m = MATS[curMat] || MATS[0];
    if (!m) return '<aside class="rail"><div class="rail-body"><h3>读不到这件作品的素材</h3><p class="vl-mute">素材文件夹没连上或被移动了。</p>' + C.btn('重新读取', { cls: 'btn--sm', toast: '重新读取素材文件夹' }) + '</div></aside>';
    const s = m.shots[0];
    const sharpPct = s.sharp != null ? Math.round(100 * s.sharp / med) : null;
    const tags = health(m);
    const talk = m.talk ? `<div class="verdict" data-design-id="V1-TRANSCRIPT"><small>说了什么 · 本机转写</small>${talkOf(m).map(([t, x]) => `<p class="vl-line"><span class="mono">${t}</span>${D(x)}</p>`).join('')}</div>` : '<div class="verdict"><small>说了什么</small><p class="vl-mute">没有人声，只有现场声。</p></div>';
    return `<aside class="rail" data-design-id="V1-DETAIL"><div class="viewer">${img((s.frames || [])[1] || (s.frames || [])[0])}</div><div class="rail-body"><h3 data-design-data>${esc(m.name)}</h3><p class="where">${D(SCENE_NAME[m.scene] || '路上')} · ${m.kind === 'photo' ? '照片' : '视频 ' + D(mmss(m.end))} · 切成 ${D(m.shots.length)} 个候选镜头</p>
      <div class="verdict" data-design-id="V1-AI-SAW"><small>AI 看到的</small><p data-design-data>${esc(m.reason)}</p></div>${talk}
      <div class="kv"><span>清晰度</span><strong>${sharpPct == null ? '没量出来' : sharpPct < 40 ? `<em>有点糊</em> · 本作品一般水平的 ${D(sharpPct)}%` : `正常 · 本作品一般水平的 ${D(sharpPct)}%`}</strong></div>
      <div class="kv"><span>曝光</span><strong>${s.over > 0.25 ? '<em>过曝</em>' : s.under > 0.25 ? '<em>欠曝</em>' : '正常'}</strong></div>
      <div class="kv"><span>抖动</span><strong>${(s.flags || []).includes('shake') ? '<em>有点抖</em>' : s.shake == null ? '没量出来' : '稳'}</strong></div>
      <div class="kv"><span>体检</span><strong>${tags.length ? `<em>${tags.join('、')}</em>` : '没有问题'}</strong></div>
      <div class="rail-foot">${C.btn('移到待处理', { cls: 'btn--sm', toast: '移到「素材整理 › 待处理」，要写一句原因' })}${C.btn('收进素材库', { cls: 'btn--sm', go: 'library' })}</div></div></aside>`;
  }

  function matList(state) {
    const groups = SCENE_ORDER.map(k => [k, MATS.filter(m => m.scene === k)]).filter(([, l]) => l.length);
    const nIssue = MATS.filter(m => health(m).length).length, nTalk = MATS.filter(m => m.talk).length;
    const pills = `<div class="subfilters" data-design-id="V1-FILTERS"><button class="pill" aria-pressed="true">全部 <i>61</i></button><button class="pill" aria-pressed="false">体检有问题 <i data-design-data>${nIssue}</i></button><button class="pill" aria-pressed="false">有人说话 <i data-design-data>${nTalk}</i></button>${state === 'analyzing' ? '<button class="pill" aria-pressed="false">还没看 <i data-design-data>19</i></button>' : ''}</div>`;
    const queuedMini = state === 'analyzing' ? `<section class="pending" data-design-id="V1-QUEUE"><h3>还没看的 <span data-design-data>19 个 · 大约 6 分钟</span></h3><div class="mini">${MATS.slice(0, 10).map(m => `<figure>${img((m.shots[0].frames || [])[0])}<figcaption data-design-data>${esc(m.name.slice(0, 10))}</figcaption></figure>`).join('')}</div></section>` : '';
    return `<div class="stack">${pills}<div class="list">${groups.map(([k, list]) => `<section data-design-id="V1-SCENE"><div class="scene-head"><h2>${SCENE_NAME[k]}</h2><span data-design-data>${list.length} 个素材</span></div><div class="grid">${list.slice(0, 6).map(m => matCard(m, false)).join('')}</div>${list.length > 6 ? `<div class="vl-more-row">${C.btn(`展开其余 ${list.length - 6} 个`, { cls: 'btn--sm', toast: '展开这个场景的全部素材' })}</div>` : ''}</section>`).join('')}${queuedMini}</div></div>`;
  }

  function tiers(state) {
    const T = [
      ['只看信息', '时长、尺寸、拍摄时间和地点。不用模型，很快。', '61 / 61', 100, 'done'],
      ['看预览图', '每个素材取 3 张图给看图模型，写一句看到什么；同时量糊、曝光、抖。', state === 'done' ? '61 / 61' : '42 / 61', state === 'done' ? 100 : 69, state === 'done' ? 'done' : 'run'],
      ['深看', '精选确认以后，只对精选多取图，并把说话转成文字。', state === 'done' ? '27 / 27' : '等精选确认', state === 'done' ? 100 : 0, state === 'done' ? 'done' : 'wait'],
    ];
    return `<section class="pnl full" data-design-id="V1-ANALYSIS"><div class="pnl-h"><h3>AI 看素材 <span class="meta" data-design-data>${state === 'done' ? '都看完了' : '大约还要 6 分钟'}</span></h3>${state === 'done' ? '' : C.btn('暂停', { cls: 'btn--sm', toast: '暂停以后，已经看完的会留着' })}</div><div class="vl-tiers">${T.map(([n, d, c, p, st]) => `<div class="vl-tier ${st}"><div class="row"><b>${n}</b><span class="grow"></span>${st === 'run' ? C.st('正在看', 'run') : st === 'wait' ? C.st('还没开始', 'off') : C.st('看完了')}</div><p>${d}</p><div class="row vl-tier-n">${C.meter(p, st === 'done')}<span class="mono" data-design-data>${c}</span></div></div>`).join('')}</div><div class="pnl-f"><p>每个素材看 <b data-design-data>3</b> 张预览图，声音最多转写 <b data-design-data>60</b> 分钟；看图用 <b data-design-data>Codex</b>，转写在本机。原片不上传，只有选中的预览图会发给看图模型。</p>${C.link('改', { go: 'set-model' })}</div></section>`;
  }

  function v1(state) {
    if (state === 'fresh') {
      return `${C.head({ eyebrow: '第 1 步 · 素材', title: '连上了 61 个素材，还没开始看', lede: '素材留在原来的文件夹里，只读不改。开始以后 AI 会分三步看：先读信息，再看预览图写一句看到什么，精选确认以后再深看。' , id: 'V1-HEAD' })}
      <div class="empty vl-fresh" data-design-id="V1-FRESH"><h2>从这个文件夹读素材</h2><p>素材文件夹里的「2026年重回兰州大学内容创作 › 兰州大学 · 奔赴与校运会」。读之前不会动任何文件。</p><div class="facts"><span>视频<b>55</b>段</span><span>照片<b>6</b>张</span><span>看图模型<b>Codex</b></span><span>大约<b>9</b>分钟</span></div><div class="actions">${C.btn('开始看素材', { pri: true, s: 'analyzing', go: 'v1' })}${C.btn('改看多少', { go: 'set-model' })}</div></div>`;
    }
    const head = state === 'done'
      ? C.head({ eyebrow: '第 1 步 · 素材', title: '61 个素材都看过了', lede: '按拍摄地点分成路上、校运会、自拍三个场景。点一个素材，右边看 AI 看到了什么、说了什么、体检结果。', actions: C.btn('去挑镜头', { pri: true, go: 'v2' }), id: 'V1-HEAD' })
      : C.head({ eyebrow: '第 1 步 · 素材', title: '61 个素材，AI 已经看了 42 个', lede: '看完的素材会写一句 AI 看到的和体检结果；剩下 19 个还在看。全部看完才能挑镜头，你可以先离开，看完会在工作台提醒你。', actions: `<span class="vl-hint">看完才能挑</span>${C.btn('去挑镜头', { pri: true, disabled: true })}`, id: 'V1-HEAD' });
    const extra = C.statusline(`整理台有 1 批像这件作品的补充素材：<b data-design-data>10/24</b> 拍的 <b data-design-data>38</b> 个文件。`, C.btn('去整理台', { cls: 'btn--sm', go: 'inbox' }), 'V1-INBOX-HINT');
    const summary = state === 'done' ? C.statusline(`体检有问题 <b data-design-data>${MATS.filter(m => health(m).length).length}</b> 个 · 有人说话 <b data-design-data>${MATS.filter(m => m.talk).length}</b> 个 · 深看了 <b data-design-data>27</b> 个精选`, C.link('改看多少', { go: 'set-model' }), 'V1-SUMMARY') : tiers(state);
    return `${head}${summary}${extra}<div class="cols">${matList(state)}${matRail(state)}</div>`;
  }

  reg('v1', {
    group: '按素材剪 vlog', name: 'vlog 1 素材', nav: 'projects', piece: { tab: 'vlog', step: 1 },
    states: [['analyzing', '分析到一半'], ['fresh', '刚连上还没看'], ['done', '全部看完']],
    flow: s => s === 'fresh' ? { notes: ['刚连上 · 还没看', '等素材看完', '等精选', '等粗剪', '等草稿'], done: [false, false, false, false, false] }
      : s === 'analyzing' ? { notes: ['看了 42 / 61', '等素材看完', '等精选', '等粗剪', '等草稿'], done: [false, false, false, false, false] }
        : { notes: ['61 个都看过了', '可以开始挑', '等精选', '等粗剪', '等草稿'], done: [true, false, false, false, false] },
    render: v1,
    after: root => { eager(root); root.querySelectorAll('[data-mat]').forEach(b => b.addEventListener('click', () => { curMat = +b.dataset.mat; PCOS.render(); })); },
  });

  // ================= 2 挑镜头（沿用现状） =================
  const SCENE_RANK = { 'travel': 0, 'sports-meet': 1, 'selfie-moments': 2, 'travel/raw-pending': 3 };
  const pickList = (SEL.length ? SEL : SHOTS.slice(0, 27)).map((s, i) => [s, i]).sort((a, b) => (SCENE_RANK[a[0].scene] ?? 9) - (SCENE_RANK[b[0].scene] ?? 9) || a[1] - b[1]).map(x => x[0]);
  let curPick = 0;
  const dur = s => (s.kind === 'photo' ? 1.5 : s.dur || 0);
  const total = pickList.reduce((a, s) => a + dur(s), 0);
  const hooks = new Set(META.hooks || []);

  function v2() {
    const s = pickList[curPick] || {};
    const prog = pickList.map((x, i) => `<button class="${i === curPick ? 'cur' : ''}" style="flex:${Math.max(0.6, dur(x)).toFixed(2)}" data-pick="${i}" aria-label="第 ${i + 1} 个">${i < curPick ? '<i style="width:100%"></i>' : ''}</button>`).join('');
    const boardScenes = ['travel', 'sports-meet', 'selfie-moments', 'travel/raw-pending'].map(k => [k, pickList.map((x, i) => [x, i]).filter(([x]) => x.scene === k)]).filter(([, l]) => l.length);
    const alts = SHOTS.filter(x => x.status === 'usable').slice(0, 8);
    return `${C.head({ eyebrow: '第 2 步 · 挑镜头', title: `AI 给这条视频挑了 ${D(pickList.length)} 个镜头`, lede: `串起来 ${D(mmss(total))}。先从头看一遍，不合适的在右边改成「可用」或「不用」；最下面还有 ${D(71)} 个可用的备选。确认后，下一步配乐卡点会从${C.link('音乐库', { go: 'music' }).replace('class="link"', 'class="link inl"')}挑一首歌，按拍子把这些镜头排起来。`, actions: C.btn('重新挑选', { toast: '按现在的素材重新挑一遍，你改过的会保留' }) + C.btn('确认精选', { pri: true, go: 'v3' }), id: 'V2-HEAD' })}
    <section class="hero full" data-design-id="V2-PLAYER"><div class="stage-wrap"><div class="stage">${shotImg(s)}<button class="big-play" data-toast="从第 ${curPick + 1} 个镜头开始连播" aria-label="播放">▶</button></div><div class="prog">${prog}</div><div class="hero-ctl"><button class="btn-round" data-toast="连播精选" aria-label="播放">▶</button>${C.btn('上一个', { cls: 'btn--sm', toast: '上一个镜头' })}${C.btn('下一个', { cls: 'btn--sm', toast: '下一个镜头' })}${C.btn('声音开', { cls: 'btn--sm', toast: '关掉现场声' })}<span class="hero-pos">第 ${D(curPick + 1)} / ${D(pickList.length)} 个 · 0:00 / ${D(mmss(total))}</span></div></div>
    <div class="shot-panel"><div><p class="eyebrow">第 ${D(curPick + 1)} / ${D(pickList.length)} 个精选</p><h3 data-design-data>${esc(nameOf(s))}</h3><p class="where">${D(sceneOf(s))} · ${D(s1(dur(s)))} 秒 · ${s.kind === 'photo' ? '照片' : `原片第 ${D(s1(s.start || 0))}–${D(s1(s.end || 0))} 秒`}</p><div class="verdict"><small>为什么选它</small><p data-design-data>${esc(clean(s.reason))}</p></div><div class="decide"><small>不同意就改，改了以你为准</small><div class="seg"><button aria-pressed="true">精选</button><button aria-pressed="false" data-toast="改成可用：从精选里拿掉，留在备选">可用</button><button aria-pressed="false" data-toast="改成不用：这个镜头不再推荐">不用</button></div></div><details class="more-d"><summary>打分细节</summary><div class="kv"><span>美感</span><strong data-design-data>${s.aes != null ? s.aes.toFixed(1) : '没量出来'}</strong></div><div class="kv"><span>清晰度</span><strong data-design-data>${s.sharp != null ? `本作品一般水平的 ${Math.round(100 * s.sharp / med)}%` : '没量出来'}</strong></div><div class="kv"><span>扣分</span><strong data-design-data>${s.penalty ? s.penalty.toFixed(2) : '没有'}</strong></div><div class="kv"><span>总分</span><strong data-design-data>${s.total != null ? s.total.toFixed(2) : '—'}</strong></div></details></div></div></section>
    <section class="full" data-design-id="V2-BOARD"><h2 class="section-title">精选顺序 <span>按场景排，配乐卡点时会按节奏重排</span></h2><div class="board">${boardScenes.map(([k, l]) => `<div class="board-scene"><h3>${SCENE_NAME[k]}<span data-design-data>${l.length}</span></h3><div class="sb-row">${l.map(([x, i]) => `<button class="sb" data-pick="${i}" ${i === curPick ? 'aria-current="true"' : ''}>${shotImg(x)}<span class="n">${i + 1}</span><span class="d">${x.kind === 'photo' ? '照片' : s1(dur(x)) + '″'}</span>${hooks.has(x.id) ? '<i class="hk" title="开头候选"></i>' : ''}</button>`).join('')}</div></div>`).join('')}</div></section>
    <section class="alts full" data-design-id="V2-ALTS"><div class="alts-head"><h2 class="section-title">可用的备选 <span data-design-data>71 个</span></h2></div><div class="grid">${alts.map(x => `<article class="card"><div class="strip">${(x.frames || []).slice(0, 3).map(f => img(f)).join('') || img('')}<span class="len">${s1(dur(x))}″</span></div><div class="card-body"><div class="card-top"><b data-design-data>${esc(nameOf(x))}</b></div><p class="reason" data-design-data>${esc(clean(x.reason))}</p><div class="row">${C.btn('加进精选', { cls: 'btn--sm', toast: '加到精选末尾，确认前可以调' })}</div></div></article>`).join('')}</div></section>`;
  }
  reg('v2', {
    group: '按素材剪 vlog', name: '挑镜头（沿用现状）', nav: 'projects', piece: { tab: 'vlog', step: 2 },
    states: [['review', '等你过目']],
    actions: playBtn,
    flow: () => ({ notes: ['61 个都看过了', '27 个精选 · 等你过目', '确认精选以后', '等粗剪', '等草稿'], done: [true, false, false, false, false] }),
    render: v2,
    after: root => { eager(root); root.querySelectorAll('[data-pick]').forEach(b => b.addEventListener('click', () => { curPick = +b.dataset.pick; PCOS.render(); })); },
  });

  // ================= 3 配乐卡点（沿用 R226 设计稿，两首歌的状态） =================
  const TECH = [
    { id: 'jcut', name: '声音先进', fam: 'snd', n: 4, desc: '下一个镜头的声音提前半秒进来，先听到再看到，换场不突兀。' },
    { id: 'bed', name: '现场声连着', fam: 'snd', n: 1, desc: '同一个地方连着好几个镜头时，用一段现场声从头铺到尾，听起来是连着的一件事。' },
    { id: 'duck', name: '说话时压低音乐', fam: 'snd', n: 5, desc: '自拍里你说话的时候，背景音乐压低 12 分贝，说完再回来。' },
    { id: 'pause', name: '停顿处切', fam: 'cut', n: 5, desc: '自拍说话的镜头，切在两句话之间的停顿上，不切在半句话中间。' },
    { id: 'action', name: '动作做完再切', fam: 'cut', n: 2, desc: '起跑、冲刺这类镜头，动作最猛的那一下落在切点前 0.25 秒，做完才切走。' },
  ];
  const tqTag = (t, off) => `<span class="vl-tq-tag ${t.fam === 'snd' ? 'snd' : ''} ${off ? 'off' : ''}">${t.name}</span>`;
  const SONG_A = TRACKS.find(t => t.title === 'Turn Back Time') || { title: 'Turn Back Time', artist: 'Rich Edwards / Emelie', bpm: 117.5 };
  const SONG_B = TRACKS.find(t => t.title === 'Fever Pitch') || { title: 'Fever Pitch', artist: 'Richz', bpm: 123 };
  const TOTAL = 43;
  const STORY = (() => { const by = k => pickList.filter(s => s.scene === k); const sf = by('selfie-moments'), h = Math.ceil(sf.length / 2); return [...by('travel'), ...sf.slice(0, h), ...by('sports-meet'), ...sf.slice(h), ...by('travel/raw-pending')]; })();
  // 粗剪示意：27 个精选按时长比例排进 0:43（设计示意，不是正式排法）
  const CLIPS = (() => { const raw = STORY.map(s => Math.min(Math.max(dur(s), 0.9), 2.6)); const k = TOTAL / raw.reduce((a, b) => a + b, 0); let t = 0; return STORY.map((s, i) => { const c = { s, i, t0: t, d: raw[i] * k }; t += c.d; return c; }); })();
  const swapIdx = Math.max(1, CLIPS.findIndex(c => c.s.scene === 'sports-meet'));
  const swapT = CLIPS[swapIdx] ? CLIPS[swapIdx].t0 : 26;
  const SWAP_TXT = mmss(swapT);
  const P = t => (100 * t / TOTAL).toFixed(2) + '%';
  const at = i => (CLIPS[i] ? CLIPS[i].t0 : 0);
  const EV = { jcut: [5, 12, 18, 23], pause: [3, 7, 9, 15, 21], action: [19, 24] };
  const DUCK = [[3, 5], [7, 8], [9, 10], [15, 16], [21, 22]];
  const BED = [13, 18];

  function presetCard(key, name, line, meta, uses, checked, ai) {
    const thumbs = [0, 4, 9, 14, 19, 24].map(i => img(((STORY[(i + key.length) % STORY.length] || {}).frames || [])[1])).join('');
    const bars = [[0, 22, ''], [22, 50, 'b'], [50, 78, 'p'], [78, 88, 'b'], [88, 100, 'p']].map(([a, b, c]) => `<i class="${c}" style="left:${a}%;width:${b - a}%"></i>`).join('') + (n => Array.from({ length: n }, (_, i) => `<b style="left:${(100 * (i + 1) / (n + 1)).toFixed(1)}%"></b>`).join(''))(key === 'race' ? 34 : key === 'calm' ? 16 : 26);
    return `<button class="vl-style" role="radio" aria-checked="${checked}" data-toast="套用「${name}」：按它的切点密度和手法重排粗剪" data-design-id="V3-PRESET"><div class="vl-pv"><div class="vl-pv-thumbs">${thumbs}</div><div class="vl-pv-bar">${bars}</div></div><div class="vl-style-body"><div class="vl-style-top"><span class="vl-radio"></span><b>${name}</b>${ai ? '<span class="chip chip--ac">AI 推荐</span>' : ''}</div><p>${line}</p><span class="vl-rh" data-design-data>${meta}</span><div class="vl-uses">${TECH.map(t => tqTag(t, !uses.includes(t.id))).join('')}</div></div></button>`;
  }

  function v3() {
    const cur = CLIPS[0] || { s: {} };
    const secA = [[0, 8, ''], [8, 20, 'b'], [20, swapT, 'p']], secB = [[swapT, 37, 'b'], [37, TOTAL, 'p']];
    const ruler = [0, 15, 30, TOTAL].map(t => `<i style="left:${P(t)}">${mmss(t)}</i>`).join('');
    const music = [...secA, ...secB].map(([a, b, c]) => `<span class="vl-seg ${c}" style="left:${P(a)};width:${P(b - a)}"></span>`).join('') + `<span class="vl-fade" style="left:${P(swapT - 1)};width:${P(1)}"></span>`;
    const video = CLIPS.map(c => `<button class="vl-blk" style="left:${P(c.t0)};width:calc(${P(c.d)} - 2px)" ${c.i === 0 ? 'aria-current="true"' : ''} data-toast="跳到第 ${c.i + 1} 个镜头"><span class="ph-in">${shotImg(c.s)}</span><b>${c.i + 1}</b></button>`).join('');
    const audio = CLIPS.map(c => { const inBed = c.i > BED[0] && c.i <= BED[1]; return `<span class="vl-au ${inBed ? 'mute' : ''}" style="left:${P(c.t0)};width:calc(${P(c.d)} - 2px)"></span>`; }).join('') + EV.jcut.map(i => `<span class="vl-au lead" style="left:${P(at(i) - 0.5)};width:${P(0.5)}"></span>`).join('') + `<span class="vl-bed" style="left:${P(at(BED[0]))};width:${P(at(BED[1] + 1) - at(BED[0]))}"></span>`;
    const lane = t => { if (t.id === 'bed') return `<span class="vl-span" style="left:${P(at(BED[0]))};width:${P(at(BED[1] + 1) - at(BED[0]))}"></span>`; if (t.id === 'duck') return DUCK.map(([a, b]) => `<span class="vl-span" style="left:${P(at(a))};width:${P(at(b) - at(a) + 0.6)}"></span>`).join(''); return (EV[t.id] || []).map(i => `<span class="vl-ev" style="left:${P(at(i))}"></span>`).join(''); };
    return `${C.head({ eyebrow: '第 3 步 · 配乐卡点', title: `用 ${D(2)} 首歌排好了 ${D('0:43')} 的粗剪`, lede: `${D(pickList.length)} 个镜头，切点都对在各自那首歌的拍子上，从自拍进校运会时换成《${D(SONG_B.title)}》。用的是「轻快旅行」预设。先从头看一遍，不想要的剪辑手法在右边关掉。`, actions: `<span class="vl-draft-to">用 Kdenlive ${C.link('换', { toast: '打开「这件作品用什么出草稿」：Kdenlive、ChatCut、OpenChatCut、剪映' })}</span>${C.btn('出草稿', { pri: true, go: 'v4', s: 'running' })}`, id: 'V3-HEAD' })}
    <section class="full" data-design-id="V3-PRESETS"><h2 class="section-title">剪辑预设 <span>每张卡都是用这件作品的镜头排出来的样子；换预设会重新排切点和手法</span></h2><div class="vl-styles" role="radiogroup" aria-label="剪辑预设">${presetCard('trip', '轻快旅行', '路上一段段往前走，到了校运会再提速，结尾慢下来。', '0:43 · 平均 1.6 秒一切', ['jcut', 'bed', 'duck', 'pause', 'action'], true, true)}${presetCard('race', '赛场热血', '比赛镜头放到前面，切得更密，动作做完再切。', '0:31 · 平均 1.1 秒一切', ['jcut', 'bed', 'duck', 'action'], false)}${presetCard('calm', '松弛日常', '镜头留得久，多听现场声和你说的话。', '0:59 · 平均 2.1 秒一切', ['bed', 'duck', 'pause'], false)}<button class="vl-more" data-toast="打开预设库：全部、旅行、运动、日常、我的"><b>更多预设</b><small>共 6 个，按旅行、运动、日常分好了</small><span>打开预设库 ›</span></button></div><p class="vl-why">推荐理由：<b>路上</b>的镜头最多（14 个），中间有一段<b>校运会</b>（7 个），适合先松后紧。</p></section>
    <section class="hero full vl-hero3" data-design-id="V3-PLAYER"><div class="stage-wrap"><div class="stage">${shotImg(cur.s)}<button class="big-play" data-toast="从头播粗剪" aria-label="播放">▶</button></div><div class="hero-ctl"><button class="btn-round" data-toast="播放粗剪" aria-label="播放">▶</button>${C.btn('从头播', { cls: 'btn--sm', toast: '从 0:00 播放' })}<span class="hero-pos">${D('0:00')} / ${D('0:43')}</span></div><div class="vl-now"><small>此刻</small><p>第 ${D(1)} / ${D(pickList.length)} 个镜头 · ${D(sceneOf(cur.s))} · 原片第 ${D(s1(cur.s.start || 0))}–${D(s1((cur.s.start || 0) + (CLIPS[0] ? CLIPS[0].d : 0)))} 秒 · 配乐《${D(SONG_A.title)}》</p><p class="vl-mute">这一段没有用剪辑手法</p></div></div>
    <div class="shot-panel"><div><p class="eyebrow">剪辑手法 · 轻快旅行</p><h3>用了 ${D(5)} 种，共 ${D(17)} 处</h3><ul class="vl-tq" data-design-id="V3-TECHNIQUES">${TECH.map(t => `<li><button class="vl-sw" role="switch" aria-checked="true" data-toast="关掉「${t.name}」：粗剪按规则重排，数字跟着变" aria-label="${t.name}"></button><div><div class="vl-nm"><b class="${t.fam}">${t.name}</b><i>${D(t.n)} 处</i></div><p>${t.desc}</p><div class="vl-foot"><span class="vl-does">出草稿时直接做好</span>${C.link('看第 1 处', { toast: `跳到「${t.name}」的第 1 处` })}</div></div></li>`).join('')}</ul></div></div></section>
    <section class="vl-tl full" data-design-id="V3-TIMELINE"><div class="vl-tl-head"><h2 class="section-title">粗剪时间轴 <span>点任意位置跳过去；点手法那几行里的点或条，看这一处怎么做</span></h2><div class="vl-legend"><span><i class="q"></i>安静</span><span><i class="b"></i>推进</span><span><i class="p"></i>高潮</span></div></div>
      <div class="vl-songs"><span class="vl-lab">配乐</span>${[[SONG_A, '0:00–' + SWAP_TXT], [SONG_B, SWAP_TXT + '–0:43']].map(([t, r], i) => `<div class="vl-song"><b>${i + 1}</b><div><strong data-design-data>${esc(t.title)}</strong><small data-design-data>${r} · ${Math.round(t.bpm || 0)} BPM</small></div><span class="vl-acts">${C.link('换一首', { toast: '从音乐库换一首' })}${i ? C.link('去掉', { toast: '去掉第二首，粗剪重排' }) : ''}</span></div>`).join('')}${C.btn('加一首歌', { cls: 'btn--sm', go: 'music' })}</div>
      <div class="vl-grid"><div class="vl-labs"><span class="l-ruler"></span><span class="l-songs"></span><span class="l-music">音乐</span><span class="l-video">画面</span><span class="l-audio">现场声</span>${TECH.map(t => `<span class="l-lane ${t.fam}">${t.name}</span>`).join('')}</div>
      <div class="vl-body"><div class="vl-ruler">${ruler}</div><div class="vl-songrow"><span class="vl-sn" style="left:0;width:${P(swapT)}">${esc(SONG_A.title)}</span><span class="vl-swap" style="left:${P(swapT)}" data-toast="换歌处：前一首淡出 1 秒，后一首从副歌前进来">换歌</span><span class="vl-sn" style="left:${P(swapT + 1)};width:${P(TOTAL - swapT - 1)}">${esc(SONG_B.title)}</span></div><div class="vl-music">${music}</div><div class="vl-video">${video}</div><div class="vl-audio">${audio}</div><div class="vl-lanes">${TECH.map(t => `<div class="vl-lane ${t.fam}">${lane(t)}</div>`).join('')}</div><span class="vl-ph" style="left:0"></span></div></div>
      <p class="vl-tl-note">现场声那一行：斜线是静掉的现场声，洋红框是用一段现场声铺底，洋红条是提前进来的声音。</p></section>`;
  }
  reg('v3', {
    group: '按素材剪 vlog', name: '配乐卡点（沿用 R226 设计稿）', nav: 'projects', piece: { tab: 'vlog', step: 3 },
    states: [['two-songs', '两首歌排好了']],
    actions: playBtn,
    flow: () => ({ notes: ['61 个都看过了', '27 个精选 · 已确认', '2 首歌 · 0:43', '用 Kdenlive', '在剪辑软件里改'], done: [true, true, false, false, false] }),
    render: v3,
    after: eager,
  });

  // ================= 4 出草稿 =================
  const KD_ROWS = [
    ['声音先进', 'snd', 4, true, '下一镜的现场声提前 0.5 秒，音轨上能看到错开的剪口'],
    ['现场声连着', 'snd', 1, true, '第 14–19 镜用第 15 镜的现场声铺底，其余镜头的声音静掉'],
    ['说话时压低音乐', 'snd', 5, true, '音乐轨上 5 段音量线，说话时压低 12 分贝，前后各 0.3 秒过渡'],
    ['停顿处切', 'cut', 5, true, '切点已经挪到两句话之间的停顿上'],
    ['动作做完再切', 'cut', 2, true, '切点已经挪到动作做完以后'],
    ['换歌', 'snd', 1, true, `进校运会时换歌：第一首在 ${SWAP_TXT} 淡出 1 秒，第二首从副歌前 2 小节进来`],
    ['切点淡变', 'snd', 26, true, '每个切点的现场声前后各淡入淡出 30 毫秒'],
  ];
  const HISTORY = (cur) => `<aside class="stack" data-design-id="V4-HISTORY"><section class="pnl"><div class="pnl-h"><h3>草稿记录</h3></div><ul class="rows"><li><div><b>草稿 2 ${cur === 'stale' ? C.st('是上一版', 'wait') : cur === 'failed' ? C.st('没出成', 'bad') : cur === 'running' ? C.st('正在出', 'run') : C.st('现在')}</b><small data-design-data>10/25 21:40 · 轻快旅行 · 2 首歌 · 0:43</small></div></li><li><div><b>草稿 1</b><small data-design-data>10/24 18:05 · 赛场热血 · 1 首歌 · 0:31</small></div><span class="end">${C.btn('打开', { cls: 'btn--sm', toast: '在 Kdenlive 里打开草稿 1' })}</span></li></ul></section>
    <section class="pnl"><div class="pnl-b"><div class="kv"><span>剪辑软件</span><strong>Kdenlive ${D('26.04')} ${C.link('换', { go: 'set-editors' })}</strong></div><div class="kv"><span>放在哪</span><strong>这件作品的草稿文件夹</strong></div><div class="kv"><span>原素材</span><strong>没有改动</strong></div></div></section></aside>`;

  function contents(mode) {
    const dim = mode !== 'ready';
    const h = { ready: ['草稿里有什么', '和第 3 步的粗剪一一对上'], stale: ['草稿 2 里有什么', '改粗剪之前的样子'], failed: ['草稿 2 要做成的样子', ''] }[mode];
    return `<section class="pnl ${dim ? 'vl-dim' : ''}" data-design-id="V4-CONTENTS"><div class="pnl-h"><h3>${h[0]}</h3>${h[1] ? `<p>${h[1]}</p>` : ''}</div><div class="vl-facts"><div><small>镜头</small><b data-design-data>27</b></div><div><small>配乐</small><b data-design-data>2 首</b></div><div><small>时长</small><b data-design-data>0:43</b></div><div><small>切点对上拍子</small><b data-design-data>27 / 27</b></div></div>
      <table class="vl-table"><thead><tr><th>剪辑手法</th><th>几处</th><th>出草稿时</th><th>在 Kdenlive 里是什么样</th></tr></thead><tbody>${KD_ROWS.map(([n, fam, c, done, how]) => `<tr><td><span class="vl-tq-tag ${fam === 'snd' ? 'snd' : ''}">${n}</span></td><td class="mono" data-design-data>${c}</td><td>${done ? '<span class="vl-does">直接做好了</span>' : '<span class="vl-does handoff">要你做</span>'}</td><td data-design-data>${how}</td></tr>`).join('')}</tbody></table>
      <div class="pnl-f"><p>草稿里没有的，要你在 Kdenlive 里加：<b>调色</b>、<button class="link" data-go="pack" data-s="review">片头标题</button>、<b>封面</b>。</p>${C.link('让 AI 做标题卡', { go: 'pack', s: 'new' })}</div></section>`;
  }

  function v4(state) {
    if (state === 'running') {
      const steps = [['排时间线', '27 个镜头、2 首歌按粗剪摆好', 100, 'done'], ['写 Kdenlive 工程', '写入镜头、音轨、音量线和淡变', 64, 'run'], ['读回核对', '用 Kdenlive 打开工程读回来，和粗剪逐个镜头对一遍', 0, 'wait']];
      return `${C.head({ eyebrow: '第 4 步 · 出草稿', title: '正在出草稿', lede: '可以离开这一页，出好了会在工作台提醒你。', actions: C.btn('取消', { toast: '停下来，已经写的草稿文件会删掉' }), id: 'V4-HEAD' })}
      <div class="cols"><section class="pnl" data-design-id="V4-RUNNING"><div class="pnl-h"><h3>Kdenlive 草稿 <span class="meta" data-design-data>大约还要 40 秒</span></h3></div><ol class="vl-steps">${steps.map(([n, d, p, st], i) => `<li class="${st}"><b>${st === 'done' ? '✓' : i + 1}</b><div><strong>${n}</strong><p>${d}</p>${st === 'run' ? C.meter(p) : ''}</div><span class="end">${st === 'done' ? C.st('好了') : st === 'run' ? C.st(`${p}%`, 'run') : C.st('等着', 'off')}</span></li>`).join('')}</ol></section>${HISTORY('running')}</div>`;
    }
    if (state === 'failed') {
      return `${C.head({ eyebrow: '第 4 步 · 出草稿', title: '草稿没出成', lede: '草稿 1 还在，可以先用它。', id: 'V4-HEAD' })}
      ${C.attn({ tone: 'cut', id: 'V4-FAILED', title: '读回核对没通过：第 12 个镜头的原片找不到', text: 'Kdenlive 打开工程时，「兰州大学校运会短跑弯道冲刺」这段原片不在原来的位置，可能被移动或改了名字。找回来以后再出一次就行。', actions: C.btn('找回这个素材', { go: 'v1' }) + C.btn('重试', { toast: '重新出草稿 2' }) + C.btn('换剪辑软件', { go: 'set-editors' }) })}
      <div class="cols">${contents('failed')}${HISTORY('failed')}</div>`;
    }
    if (state === 'stale') {
      return `${C.head({ eyebrow: '第 4 步 · 出草稿', title: '粗剪改过了，草稿还是上一版', lede: '草稿 2 是 10/25 21:40 出的；之后你在第 3 步改了粗剪。重新出一份，旧的会留在草稿记录里。', id: 'V4-HEAD' })}
      ${C.attn({ id: 'V4-STALE', title: '草稿 2 和现在的粗剪对不上', list: ['关掉了「声音先进」', `第二首歌换成了《CRUSH VIBE》，换歌处从 ${SWAP_TXT} 挪到校运会第 3 个镜头`], actions: C.btn('先看改了什么', { go: 'v3' }) + C.btn('重新出草稿', { pri: true, go: 'v4', s: 'running' }) })}
      <div class="cols">${contents('stale')}${HISTORY('stale')}</div>`;
    }
    return `${C.head({ eyebrow: '第 4 步 · 出草稿', title: `草稿出好了：Kdenlive 时间线 · ${D('0:43')}`, lede: '27 个镜头、2 首歌，切点和声音处理都按第 3 步的粗剪做进去了，打开就能接着精剪。', actions: C.btn('打开剪点清单', { toast: '打开剪点清单：每个镜头的原片、入点、出点和手法' }) + C.btn('在访达中显示', { toast: '在访达里打开这件作品的草稿文件夹' }) + C.btn('在 Kdenlive 里打开', { pri: true, toast: '用 Kdenlive 打开草稿 2' }), id: 'V4-HEAD' })}
    <div class="cols"><div class="stack">${contents('ready')}${C.statusline('在 Kdenlive 里改完、导出成片以后，拖回 Studio 检查，通过的才算一版。', C.btn('去收回成片', { cls: 'btn--sm', go: 'v5' }), 'V4-NEXT')}</div>${HISTORY('ready')}</div>`;
  }
  reg('v4', {
    group: '按素材剪 vlog', name: 'vlog 4 出草稿', nav: 'projects', piece: { tab: 'vlog', step: 4 },
    states: [['ready', '草稿出好了'], ['running', '正在出'], ['stale', '草稿是上一版'], ['failed', '出草稿失败']],
    actions: playBtn,
    flow: s => ({ notes: ['61 个都看过了', '27 个精选 · 已确认', '2 首歌 · 0:43', { ready: '草稿 2 · 出好了', running: '正在出', stale: '草稿是上一版', failed: '没出成' }[s], '在剪辑软件里改'], done: [true, true, true, s === 'ready', false], warn: s === 'stale' || s === 'failed' ? [3] : [] }),
    render: v4,
    after: eager,
  });

  // ================= 5 人工精剪 =================
  const allOk = () => C.CHECKS.map(n => [n, 'ok', n === '音画同步' ? '差 0.01 秒' : n === '帧数和时长一致' ? '1290 帧' : n === '字幕' ? '没有字幕，跳过' : n === '黑帧' ? '没有' : '']);
  const WILL = [['能完整播放', '从头解码到尾，不报错'], ['音画同步', '声音和画面相差不超过 0.04 秒'], ['帧数和时长一致', '和草稿里的时长对得上'], ['原片没有被改动', '素材的指纹和出草稿时一样'], ['字幕', '这件作品没有字幕，跳过'], ['黑帧', '中间不能有超过 0.5 秒的黑屏']];
  const pastCands = () => `<section data-design-id="V5-OUTPUTS"><h2 class="section-title">已出的成片 <span data-design-data>2 版</span></h2><div class="cands">${C.cand({ v: 'v2', editor: '以前导出', dur: outDur(1), frames: '975', status: 'pass', poster: posterOf(LZU, 1), current: true, note: '发布版', actions: C.btn('播放', { cls: 'btn--sm', toast: '播放 v2' }) })}${C.cand({ v: 'v1', editor: '以前导出', dur: outDur(0), frames: '975', status: 'pass', poster: posterOf(LZU, 0), actions: C.btn('播放', { cls: 'btn--sm', toast: '播放 v1' }) })}</div></section>`;

  function v5(state) {
    const v3poster = (((pickList[3] || {}).frames) || [])[1] || '';
    if (state === 'failed') {
      const ck = C.CHECKS.map(n => [n, n === '音画同步' || n === '黑帧' ? 'fail' : 'ok', n === '音画同步' ? '差 0.21 秒 · 允许 0.04' : n === '黑帧' ? '0:27 处 0.8 秒' : n === '字幕' ? '没有字幕，跳过' : n === '帧数和时长一致' ? '1308 帧' : '']);
      return `${C.head({ eyebrow: '第 5 步 · 人工精剪', title: 'v3 检查没通过，这一版不能用', lede: '收回的成片已经留着，不会覆盖 v1、v2。在 Kdenlive 里改好再导出一次，拖回来重新检查。', id: 'V5-HEAD' })}
      ${C.attn({ tone: 'cut', id: 'V5-FAILED', title: '两项没通过', list: ['音画同步：实测声音比画面晚 0.21 秒，允许 0.04 秒。常见原因是导出时改了帧率。', '黑帧：0:27 有一段 0.8 秒的黑屏，在第 18、19 个镜头之间。'], actions: C.btn('看黑屏那一段', { toast: '从 0:25 开始播放 v3' }) + C.btn('重新选择成片…', { toast: '打开系统的选择文件窗口' }) })}
      <section data-design-id="V5-CANDIDATE"><h2 class="section-title">刚收回的</h2><div class="cands">${C.cand({ v: 'v3', editor: 'Kdenlive', dur: '0:43', frames: '1308', status: 'fail', poster: v3poster, checks: ck })}</div></section>${pastCands()}`;
    }
    if (state === 'published') {
      return `${C.head({ eyebrow: '第 5 步 · 人工精剪', title: 'v3 通过检查，定为发布版', lede: '发布以后把平台和数据记在下面，复盘会留在这件作品里；发布满一个月可以冷归档。', actions: C.btn('去保存与归档', { go: 'archive' }), id: 'V5-HEAD' })}
      <div class="cols"><div class="stack"><div class="cands" data-design-id="V5-CANDIDATE">${C.cand({ v: 'v3', editor: 'Kdenlive', dur: '0:43', frames: '1290', status: 'pass', poster: v3poster, current: true, note: '发布版', checks: allOk() })}</div>
      <section class="pnl" data-design-id="V5-PUBLISH"><div class="pnl-h"><h3>发布与复盘</h3>${C.btn('记一条发布', { cls: 'btn--sm', toast: '再记一个平台的发布' })}</div>${C.pub([['平台', '抖音', true], ['发布时间', '10/26 20:00'], ['播放', '1.2 万'], ['点赞', '486']])}<div class="pnl-b"><label class="vl-label" for="vl-retro">一句话复盘</label><div class="vl-textarea" id="vl-retro" data-design-data>开头机场那两个镜头太长，前 3 秒走了不少人；校运会那段换歌之后完播明显好。</div><div class="row vl-mt">${C.btn('保存复盘', { cls: 'btn--sm', toast: '复盘已保存' })}<span class="vl-mute">复盘留在这件作品里，以后打开还能看到。</span></div></div></section></div>
      <aside class="pnl" data-design-id="V5-REVIEW"><div class="pnl-h"><h3>成片复核</h3><p>本机算的</p></div><div class="pnl-b"><div class="kv"><span>切点对上拍子</span><strong data-design-data>23 / 27</strong></div><div class="kv"><span>黑帧</span><strong data-design-data>0 处</strong></div><div class="kv"><span>音画差</span><strong data-design-data>0.01 秒</strong></div><div class="kv"><span>开头 3 秒</span><strong>有人物动作</strong></div><div class="kv"><span>切在半句话上</span><strong data-design-data>0 处</strong></div><p class="vl-note2">4 个没对上拍子的切点都在换歌前后，是你在 Kdenlive 里手动挪过的。</p></div></aside></div>`;
    }
    return `${C.head({ eyebrow: '第 5 步 · 人工精剪', title: '在 Kdenlive 里精剪，改完把成片拖回来', lede: '草稿 2 是 10/25 出的。改完导出 MP4，拖到下面。', actions: C.btn('在 Kdenlive 里打开草稿', { toast: '用 Kdenlive 打开草稿 2' }), id: 'V5-HEAD' })}
    ${C.drop({ editor: 'Kdenlive' })}
    <section class="pnl" data-design-id="V5-WILL-CHECK"><div class="pnl-h"><h3>收回以后检查什么</h3><p>没通过的会写清哪一项、差多少</p></div><ul class="vl-will">${WILL.map(([n, d]) => `<li><b>${n}</b><span>${d}</span></li>`).join('')}</ul></section>
    ${pastCands()}`;
  }
  reg('v5', {
    group: '按素材剪 vlog', name: 'vlog 5 人工精剪', nav: 'projects', piece: { tab: 'vlog', step: 5 },
    states: [['waiting', '还没收回成片'], ['failed', '检查没通过'], ['published', '通过并发布']],
    actions: playBtn,
    flow: s => ({ notes: ['61 个都看过了', '27 个精选 · 已确认', '2 首歌 · 0:43', '草稿 2 · 出好了', { waiting: '还没收回成片', failed: 'v3 检查没通过', published: 'v3 已发布' }[s]], done: [true, true, true, true, s === 'published'], warn: s === 'failed' ? [4] : [] }),
    render: v5,
    after: eager,
  });
})();
