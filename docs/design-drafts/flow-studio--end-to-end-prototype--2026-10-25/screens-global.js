// 全局页和作品侧页：工作台、整理台、项目、素材库、音乐库、设置、素材整理、保存与归档。见 SPEC.md 第 3、4 节。
(function () {
  'use strict';
  const { reg, C, ctx } = PCOS;
  const { esc, D, img, shotImg, sel, posterOf, PIECE, ICON } = ctx;

  // ================= 工作台 =================
  // 主状态：5 件事等你处理（2 件出了问题、3 件等你决定）。第一次打开：还没有作品。
  const CAPS = [
    ['ok', '看图和写稿模型', 'Codex · 挑镜头、写摘要、改稿都用它', 'set-model'],
    ['ok', '转写', '本机 FunASR，不上传', 'set-model'],
    ['ok', '剪辑软件', 'Kdenlive、剪映、OpenChatCut、OpenFilm 可用', 'set-editors'],
    ['', 'ChatCut', '没连上 · 选了它的作品出不了草稿', 'set-editors'],
    ['', '上游中台', '没连上 · 直出的配音和英文字幕拿不到', 'set-upstream'],
  ];
  // 每一行都能点，进设置里对应的那一项
  const caps = () => `<aside class="pnl" data-design-id="HOME-CAPS"><div class="pnl-h"><h3>本机能力</h3></div><ul class="rows gl-caps">${CAPS.map(([st, name, note, go]) => `<li><button data-go="${go}"><i class="dot ${st === 'ok' ? 'dot--ok' : ''}"></i><div><b>${name}</b><small data-design-data>${note}</small></div><i class="gl-chev" aria-hidden="true">›</i></button></li>`).join('')}</ul><div class="pnl-f">${C.btn('设置与诊断', { go: 'set-model', cls: 'btn--sm' })}</div></aside>`;

  // 作品卡：有成片用成片封面，脚本线作品没有画面时用「要记住的那一句」做封面
  const RECENT = [
    { line: 'vlog', title: PIECE.vlog.title, step: '第 2 步 挑镜头 · 等你过目', cover: () => shotImg(sel(0)), go: 'v2' },
    { line: 'spoken', title: PIECE.spoken.title, step: '第 3 步 对稿剪辑 · 4 处要你定', quote: '断更不是懒，是怕发出去没人看。', go: 's3' },
    { line: 'direct', title: PIECE.direct.title, step: '第 3 步 逐镜动画 · 第 01 镜必须改', quote: '平均速度不是速度的平均。', go: 's3d' },
    { line: 'vlog', title: '400米比赛 · 第一视角', step: '已出 v1 · 发布冷却期', cover: () => img(posterOf('2026-lzu-400m-pov')), go: 'archive', s: 'ready' },
    { line: 'vlog', title: '第一视角体验清华毕业典礼', step: '已出 7 版 · 副本核对没通过', cover: () => img(posterOf('2026-tsinghua-graduation-pov')), go: 'archive', s: 'cooling' },
    { line: 'spoken', title: '断更一年，我的担心准吗', step: '第 1 步 写稿 · 还没拍', quote: '我担心的三件事，只有一件发生了。', go: 's1' },
  ];
  const pieceCard = (r, id = 'HOME-PIECE') => `<button class="piece" data-go="${r.go}" ${r.s ? `data-s="${r.s}"` : ''} ${r.line !== 'vlog' ? `data-line="${r.line}"` : ''} data-design-id="${id}"><div class="cover gl-cover">${r.cover ? r.cover() : `<blockquote class="gl-quote" data-design-data>${esc(r.quote)}</blockquote>`}${r.chip ? `<span class="chip ${r.chipCls || ''}">${r.chip}</span>` : ''}</div><div class="piece-body">${C.lineb(r.line)}<b data-design-data>${esc(r.title)}</b><small data-design-data>${esc(r.step)}</small></div></button>`;

  function homeBusy() {
    const thumbs = [0, 3, 7, 11, 16].map(i => shotImg(sel(i))).join('');
    return `<div class="cols"><div class="stack">
      <section class="stack" data-design-id="HOME-PROBLEMS">
        <h2 class="section-title">出了问题 <span data-design-data>2 件</span></h2>
        ${C.attn({ tone: 'cut', title: `${D(PIECE.direct.title)}：AI 写的第 01 镜动画比配音长`, text: '7 镜动画代码写好了。第 01 镜按字数估了 2.4 秒，配音实测只有 1.6 秒，切镜时「≠」还没出来；另有 3 处提醒。', actions: C.btn('去看这一镜', { go: 's3d', s: 'review' }) })}
        ${C.attn({ title: '第一视角体验清华毕业典礼：移动硬盘副本少了 3 个文件', text: '上次核对 10/22。补拷之前，这件作品不能冷归档，也不能腾出 Mac 上的空间。', actions: C.btn('去补拷', { go: 'archive', s: 'cooling' }) })}
      </section>
      <section class="todo" data-design-id="HOME-TODO">
        <h2 class="section-title">等你决定 <span data-design-data>3 件</span></h2>
        <div class="task"><div><strong>${D(PIECE.vlog.title)}：AI 挑了 27 个精选</strong><p>串起来 1:32，最下面还有 71 个可用的备选。过目、确认以后才能配乐卡点。</p><div class="thumbs5">${thumbs}</div></div><div class="actions">${C.btn('先播一遍', { toast: '打开精选播放器，从第 1 个镜头开始放' })}${C.btn('去过目', { pri: true, go: 'v2' })}</div></div>
        <div class="task task--soft"><div><strong>${D(PIECE.spoken.title)}：对稿剪辑有 4 处要你定</strong><p>8 处重说和静音已经按稿剪好，另有 4 处是稿子外的话，要不要留由你定；还有 1 句稿子里写了但没说到。</p></div><div class="actions">${C.btn('去看', { go: 's3', line: 'spoken' })}</div></div>
        <div class="task task--soft"><div><strong>整理台：2 批新素材还没定放哪</strong><p>10/24 拍的 38 个文件像是「兰州大学 · 奔赴与校运会」的补充素材；10/25 的 12 个文件没认出是哪件作品。</p></div><div class="actions">${C.btn('去整理台', { go: 'inbox' })}</div></div>
      </section>
      <section data-design-id="HOME-RECENT">
        <h2 class="section-title">最近的作品 <span data-design-data>12 件</span></h2>
        <div class="pieces">${RECENT.map(pieceCard).join('')}</div>
      </section>
    </div>${caps()}</div>`;
  }

  function homeFirst() {
    return `<div class="empty" data-design-id="HOME-FIRST"><h2>先放进一批照片和视频</h2><p>素材留在这台电脑上。导入后按拍摄时间和地点自动分批，你定每批放进哪件作品；也可以先建作品，再连上已有的素材文件夹。</p><div class="facts"><span>素材文件夹<b>~/Desktop/照片筛选</b></span><span>看图模型<b>Codex</b></span><span>剪辑软件<b>Kdenlive</b></span></div><div class="actions">${C.btn('导入照片和视频', { pri: true, go: 'inbox' })}${C.btn('新建作品', { toast: '打开「新建作品」：作品名、做法（按素材剪 vlog / 按脚本做视频）、素材文件夹' })}</div></div>`;
  }

  reg('home', {
    group: '全局', name: '工作台', nav: 'home',
    states: [['busy', '5 件等你处理'], ['first', '第一次打开']],
    title: '工作台', sub: '等你处理的事和最近的作品',
    actions: s => s === 'first' ? '' : C.btn('导入照片和视频', { go: 'inbox' }) + C.btn('新建作品', { pri: true, toast: '打开「新建作品」：作品名、做法（按素材剪 vlog / 按脚本做视频）、素材文件夹' }),
    render: s => (s === 'first' ? homeFirst() : homeBusy()),
  });

  // ================= 共用小件 =================
  const { shot, SHOTS, TRACKS, mmss } = ctx;
  const svgI = p => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
  const GI = {
    drive: svgI('<line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/>'),
    scissors: svgI('<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/><path d="M20 4 8.12 15.88"/><circle cx="6" cy="18" r="3"/><path d="M14.8 14.8 20 20"/>'),
    cpu: svgI('<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>'),
    download: svgI('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>'),
    cloud: svgI('<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>'),
    activity: svgI('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'),
  };
  const th = (s, extra = '') => `<span class="gl-th ${extra}">${shotImg(s)}</span>`;
  // 某个场景里第 n 个镜头（不分是否精选），给整理、连拍这类「还没挑过」的素材用
  const inScene = (scene, n) => { const list = SHOTS.filter(s => s.scene === scene); return list.length ? list[n % list.length] : shot(n); };
  // 一组镜头的全部取帧，做连拍组的缩略图
  const framesOf = (src, count) => { const list = SHOTS.filter(s => (s.src || '').includes(src)); const out = []; for (const s of list) { for (const f of s.frames || []) { out.push(f); if (out.length >= count) return out; } } while (out.length < count) out.push(''); return out; };
  const playBtn = '<button class="btn btn--play" data-toast="打开已出的成片：v1、v2">看已出的成片 <span data-design-data>v1 · v2</span></button>';

  // ================= 整理台 =================
  // 主状态：2 批新素材没定去处 + 7 个可清理文件。另一状态：没有新素材。
  const BATCHES = [
    { id: 'b1', when: '10月24日 下午', place: '兰州大学榆中校区', files: 38, photos: 31, videos: 7, live: 4, span: '14:02–17:46', guess: PIECE.vlog.title, why: `拍摄日期和地点都和「${PIECE.vlog.title}」一样，画面里也是同一条跑道和计时屏。`, pick: [1, 9, 10, 13, 14, 15, 16, 26, 7, 8, 4, 12] },
    { id: 'b2', when: '10月25日 上午', place: '照片里没有地点信息', files: 12, photos: 12, videos: 0, live: 0, span: '09:15–09:40', guess: '', why: '拍摄时间和现有作品都对不上，照片里也没有地点信息，认不出属于哪件作品。', pick: [19, 20, 25, 24, 17, 18] },
  ];
  const CLEAN = [
    ['时长过短', [['IMG_4471.MOV', '0.4 秒，短于 1 秒的下限', true], ['IMG_4493.MOV', '0.7 秒，短于 1 秒的下限', true]]],
    ['文件损坏', [['IMG_4502.HEIC', '打不开：探测结果是文件头损坏', false]]],
    ['完全相同', [['IMG_4488 2.JPG', '和 IMG_4488.JPG 每一个字节都一样', true], ['IMG_4490 2.JPG', '和 IMG_4490.JPG 每一个字节都一样', false], ['IMG_4491 2.HEIC', '和 IMG_4491.HEIC 每一个字节都一样', false]]],
    ['相机低清代理', [['DJI_0042.LRF', '高清原件 DJI_0042.MP4 也在这一批里', false]]],
  ];
  let inboxSel = 'b1';
  const DEST = [
    ['piece', '放进已有作品', '进这件作品的「素材整理 › 补充素材」，你确认场景以后才合并。'],
    ['new', '新建作品', '用这一批建一件新作品，建好以后进第 1 步「素材」。'],
    ['later', '先不决定', '留在整理台，不算进工作台的待办。'],
  ];
  function batchCard(b) {
    return `<button class="gl-batch" aria-selected="${inboxSel === b.id}" data-batch="${b.id}" data-design-id="INBOX-BATCH"><span class="thumbrow">${b.pick.slice(0, 4).map(i => `<span>${shotImg(sel(i))}</span>`).join('')}</span><b>${D(b.when)} · ${D(b.place)}</b><small>${D(b.files)} 个文件 · ${D(b.photos)} 张照片${b.videos ? ` · ${D(b.videos)} 段视频` : ''}${b.live ? ` · 实况照片 ${D(b.live)} 组` : ''}</small>${b.guess ? `<span class="gl-guess">像是「${D(b.guess)}」的补充素材</span>` : '<span class="gl-guess gl-guess--none">没认出是哪件作品</span>'}</button>`;
  }
  function batchDetail(b) {
    const chosen = b.guess ? 'piece' : '';
    return `<section class="pnl gl-bdetail" data-design-id="INBOX-DETAIL">
      <div class="pnl-h"><h3>${D(b.when)} · ${D(b.place)}<span>${D(b.files)} 个文件 · ${D(b.span)}</span></h3>${C.link('全部看一遍', { toast: '打开这一批的播放器，照片和视频按拍摄时间排' })}</div>
      <div class="pnl-b stack">
        <div class="gl-bgrid">${b.pick.map(i => th(sel(i))).join('')}<span class="gl-th gl-more"><span>+${D(b.files - b.pick.length)}</span></span></div>
        <div class="verdict ${b.guess ? '' : 'verdict--warn'}" data-design-id="INBOX-AI"><small>${b.guess ? 'AI 建议' : 'AI 没认出来'}</small><p>${b.guess ? `放进「${D(b.guess)}」：` : ''}${D(b.why)}</p></div>
        <div class="gl-dest" role="radiogroup" aria-label="这一批放到哪" data-design-id="INBOX-DEST">${DEST.map(([k, t, d]) => `<button class="gl-opt" role="radio" aria-checked="${chosen === k}" data-dest="${k}"><i aria-hidden="true"></i><span><b>${t}</b><small>${d}</small>${k === 'piece' ? `<span class="gl-select" data-design-data>${b.guess ? esc(b.guess) : '选一件作品…'} ▾</span>` : ''}</span></button>`).join('')}</div>
      </div>
      <div class="pnl-f"><p data-dest-note>${chosen ? `确认后这 ${D(b.files)} 个文件移进那件作品的补充素材文件夹，文件名不变。` : '先选这一批放到哪。'}</p><div class="actions"><button class="btn btn--pri" data-confirm-dest ${chosen ? 'data-go="tidy" data-s="additions"' : 'disabled'}>确认去处</button></div></div>
    </section>`;
  }
  function cleanPanel() {
    const total = CLEAN.reduce((n, [, rows]) => n + rows.length, 0);
    return `<section class="pnl" data-design-id="INBOX-CLEAN"><div class="pnl-h"><h3>可清理文件<span>${D(total)} 个</span></h3><p>只列机器能证明的四类。相似的照片不在这里，到作品的「连拍与相似」里由你挑。</p></div>
      <div class="gl-clean">${CLEAN.map(([kind, rows]) => `<div class="gl-cgroup" data-design-id="INBOX-CLEAN-${kind}"><h4>${kind}<span>${D(rows.length)}</span></h4>${rows.map(([f, why, on]) => `<label class="gl-crow"><input type="checkbox" data-clean ${on ? 'checked' : ''}><b class="mono" data-design-data>${esc(f)}</b><small data-design-data>${esc(why)}</small></label>`).join('')}</div>`).join('')}</div>
      <div class="pnl-f"><p>勾选的文件移到系统废纸篓，在废纸篓里还能放回去。</p><div class="actions"><button class="btn btn--sm" data-clean-all>全选</button><span class="gl-count" data-clean-n>已选 3 个</span><button class="btn btn--danger" data-clean-go data-toast="弹出确认：逐个列出这 3 个文件，再点一次「移到废纸篓」才会移走">移到废纸篓…</button></div></div></section>`;
  }
  reg('inbox', {
    group: '全局', name: '整理台', nav: 'inbox',
    states: [['batches', '2 批没定去处'], ['empty', '没有新素材']],
    title: '整理台', sub: '新导入的素材先在这里分批，定好放进哪件作品',
    actions: () => C.btn('导入照片和视频', { pri: true, toast: '选择一个文件夹，或把照片和视频拖进来' }),
    render: s => {
      if (s === 'empty') {
        return C.statusline('<b>没有新素材，也没有可清理的文件。</b>整理台看着素材文件夹里的 <span class="mono">inbox</span> 目录：把照片和视频放进去，或点右上角「导入照片和视频」。', '', 'INBOX-EMPTY') +
          `<section class="pnl full" data-design-id="INBOX-HISTORY"><div class="pnl-h"><h3>最近定过的去处</h3></div><ul class="rows"><li><div><b>${D('10月19日')} · ${D('41')} 个文件</b><small>放进「${D(PIECE.vlog.title)}」· 补充素材，已合并</small></div><span class="end">${C.btn('去看', { go: 'tidy', s: 'additions', cls: 'btn--sm' })}</span></li><li><div><b>${D('10月12日')} · ${D('224')} 张照片</b><small>新建作品「${D('兰州大学校运会 · 合照与荣誉展厅JPG补充包')}」</small></div><span class="end">${C.btn('去看', { go: 'projects', s: 'pieces', cls: 'btn--sm' })}</span></li></ul></section>`;
      }
      const b = BATCHES.find(x => x.id === inboxSel) || BATCHES[0];
      return C.head({ title: `${D(BATCHES.length)} 批新素材等你定放哪`, lede: '按拍摄时间和地点分好了批。AI 只建议放哪，你点「确认去处」才会动文件；先不决定的留在这里。', id: 'INBOX-HEAD' }) +
        `<div class="gl-inbox full"><div class="stack" data-design-id="INBOX-LIST">${BATCHES.map(batchCard).join('')}</div>${batchDetail(b)}</div>` +
        `<div class="full">${cleanPanel()}</div>`;
    },
    after: root => {
      root.querySelectorAll('[data-batch]').forEach(btn => btn.onclick = () => { inboxSel = btn.dataset.batch; PCOS.render(); });
      const confirm = root.querySelector('[data-confirm-dest]');
      const b = BATCHES.find(x => x.id === inboxSel) || BATCHES[0];
      root.querySelectorAll('[data-dest]').forEach(opt => opt.onclick = () => {
        root.querySelectorAll('[data-dest]').forEach(o => o.setAttribute('aria-checked', String(o === opt)));
        const k = opt.dataset.dest, note = root.querySelector('[data-dest-note]');
        confirm.disabled = false;
        ['data-go', 'data-s', 'data-toast'].forEach(a => confirm.removeAttribute(a));
        if (k === 'piece') { confirm.dataset.go = 'tidy'; confirm.dataset.s = 'additions'; note.innerHTML = `确认后这 ${D(b.files)} 个文件移进那件作品的补充素材文件夹，文件名不变。`; }
        if (k === 'new') { confirm.dataset.go = 'v1'; confirm.dataset.s = 'fresh'; note.textContent = '确认后打开「新建作品」，作品名先按拍摄日期填好，你可以改。'; }
        if (k === 'later') { confirm.dataset.toast = '这一批留在整理台，工作台不再提醒'; note.textContent = '这一批留在整理台，以后随时可以再定。'; }
      });
      const boxes = [...root.querySelectorAll('[data-clean]')], n = root.querySelector('[data-clean-n]'), del = root.querySelector('[data-clean-go]'), all = root.querySelector('[data-clean-all]');
      const sync = () => { const k = boxes.filter(x => x.checked).length; if (n) n.textContent = `已选 ${k} 个`; if (del) { del.disabled = !k; del.dataset.toast = `弹出确认：逐个列出这 ${k} 个文件，再点一次「移到废纸篓」才会移走`; } if (all) all.textContent = k === boxes.length ? '取消全选' : '全选'; };
      boxes.forEach(x => x.onchange = sync);
      if (all) all.onclick = () => { const on = boxes.some(x => !x.checked); boxes.forEach(x => x.checked = on); sync(); };
    },
  });

  // ================= 项目 =================
  // 列表沿用现状；右上「选择」、底部「最近删除」与 R275 设计稿一致（R275 在另一个会话里实现）。
  const collage = urls => `<div class="collage ${urls.length === 1 ? 'one' : ''}">${urls.map(u => img(u)).join('')}</div>`;
  const PROJECTS = [
    { title: '2026年清华毕业典礼内容创作', n: 1, chips: [['1 件出过成片'], ['副本核对没通过', 'wait']], covers: () => [posterOf('2026-tsinghua-graduation-pov')], s: 'pieces' },
    { title: '2026年重回兰州大学内容创作', n: 3, chips: [['1 件等你过目', 'ac'], ['2 件出过成片']], covers: () => [ctx.frameOf(sel(1)), posterOf('2026-lzu-400m-pov'), ctx.frameOf(sel(7))], s: 'pieces' },
    { title: '其他作品', n: 8, chips: [['口播 6 件'], ['直出 2 件'], ['1 件检查没通过', 'bad']], covers: null, s: 'other' },
  ];
  const projChip = ([t, k]) => (k === 'ac' ? `<span class="chip chip--ac">${t}</span>` : k ? C.st(t, k) : `<span class="chip">${t}</span>`);
  const PIECES_LZU = [
    { line: 'vlog', title: PIECE.vlog.title, step: '第 2 步 挑镜头 · 27 个精选等你过目', cover: () => shotImg(sel(2)), go: 'v2', chip: '等你过目', chipCls: 'chip--ac' },
    { line: 'vlog', title: '400米比赛 · 第一视角', step: '已出 v1 · 发布冷却期，可以冷归档了', cover: () => img(posterOf('2026-lzu-400m-pov')), go: 'archive', s: 'ready', chip: '出过成片' },
    { line: 'vlog', title: '兰州大学校运会 · 合照与荣誉展厅JPG补充包', step: '224 张照片 · 还没开始做', cover: () => shotImg(sel(26)), go: 'v1', s: 'fresh', chip: '已有素材' },
  ];
  const PIECES_OTHER = [
    { line: 'spoken', title: PIECE.spoken.title, step: '第 3 步 对稿剪辑 · 4 处要你定', quote: '断更不是懒，是怕发出去没人看。', go: 's3', chip: '等你决定', chipCls: 'chip--ac' },
    { line: 'direct', title: PIECE.direct.title, step: '第 5 步 出片检查 · v1 没通过', quote: '平均速度不是速度的平均。', go: 's5', chip: '检查没通过', chipCls: 'gl-chip-bad' },
    { line: 'spoken', title: 'P4 教学实践：平均速度', step: '第 2 步 分镜 · 缺 2 镜', quote: '算平均速度，先问总路程和总时间。', go: 's2' },
    { line: 'direct', title: 'P3 合成口播实践：平均速度', step: '第 3 步 逐镜动画 · 正在渲染', quote: '同一段路，快慢两半，平均速度是多少？', go: 's3d' },
    { line: 'spoken', title: '断更一年，我的担心准吗', step: '第 1 步 写稿 · 10月20日建', quote: '我担心的三件事，只有一件发生了。', go: 's1' },
    { line: 'spoken', title: '断更一年，我的担心准吗', step: '还没开始 · 10月21日建', quote: '', go: 's1', s: 'blank' },
    { line: 'spoken', title: '断更一年后，我才发现自己在躲什么', step: '还没开始 · 10月20日建', quote: '', go: 's1', s: 'blank' },
    { line: 'spoken', title: '断更一年后，我才发现自己在躲什么', step: '还没开始 · 10月21日建', quote: '', go: 's1', s: 'blank' },
  ];
  const otherCard = r => pieceCard(r.quote ? r : { ...r, cover: () => '<span class="gl-noquote">还没写口播稿</span>' }, 'PROJ-PIECE');
  const recentDeleted = `<button class="gl-trash full" data-toast="打开「最近删除」：删掉的作品先放在这里，随时可以恢复" data-design-id="PROJ-TRASH"><span>最近删除</span><small>删掉的作品先放在这里，随时可以恢复</small><i aria-hidden="true">›</i></button>`;
  reg('projects', {
    group: '全局', name: '项目', nav: 'projects',
    states: [['list', '3 个项目'], ['pieces', '兰州项目里的作品'], ['other', '其他作品']],
    crumb: s => (s === 'list' ? '' : '<button data-go="projects">项目</button>'),
    title: s => (s === 'list' ? '项目' : s === 'pieces' ? D('2026年重回兰州大学内容创作') : '其他作品'),
    sub: s => (s === 'list' ? `${D(3)} 个项目 · ${D(12)} 件作品` : s === 'pieces' ? `${D(3)} 件作品` : `${D(8)} 件作品 · 不属于任何项目`),
    actions: () => C.btn('选择', { toast: '进入选择：每张卡片左上角出现勾选框，勾好后在底部点「删除 N 件」' }) + C.btn('新建作品', { pri: true, toast: '打开「新建作品」：作品名、做法（按素材剪 vlog / 按脚本做视频）、素材文件夹' }),
    render: s => {
      if (s === 'pieces') return `<div class="pieces full gl-pieces" data-design-id="PROJ-PIECES">${PIECES_LZU.map(r => pieceCard(r, 'PROJ-PIECE')).join('')}</div>${recentDeleted}`;
      if (s === 'other') return C.statusline(`有 ${D(2)} 组同名作品：「断更一年，我的担心准吗」「断更一年后，我才发现自己在躲什么」各 ${D(2)} 件。用右上角「选择」可以删掉多余的。`, '', 'PROJ-DUP') + `<div class="pieces full gl-pieces" data-design-id="PROJ-PIECES">${PIECES_OTHER.map(otherCard).join('')}</div>${recentDeleted}`;
      return `<div class="full gl-filter" data-design-id="PROJ-FILTER"><div class="tabs"><button aria-pressed="true">使用中 <i data-design-data>3</i></button><button aria-pressed="false" data-toast="已冷归档的项目：只留索引卡和成片，打开时先读索引卡">已冷归档</button></div></div>
        <div class="projects full" data-design-id="PROJ-LIST">${PROJECTS.map(p => `<button class="proj ${p.covers ? '' : 'gl-proj-nocover'}" data-go="projects" data-s="${p.s}">${p.covers ? collage(p.covers()) : ''}<div><h2 data-design-data>${esc(p.title)}</h2><p>${D(p.n)} 件作品</p><div class="chips">${p.chips.map(projChip).join('')}</div></div><i aria-hidden="true">›</i></button>`).join('')}</div>${recentDeleted}`;
    },
  });

  // ================= 素材库 =================
  // 主状态：有 9 项。另：还是空的；从分镜来挑（给直出第 4 镜挑画面）。
  const LIB = [
    { i: 2, title: '兰州中川机场大厅行走', dur: 4.7, range: '0.0–4.7', src: '兰州中川机场大厅行走.mp4', uses: ['可复用镜头'], tags: ['机场', '室内', '纵深'], used: '' },
    { i: 1, title: '校运会 100 米赛事现场', dur: 7.7, range: '12.4–20.1', src: '兰州大学校运会100米赛事现场_4K.mp4', uses: ['可复用镜头', '封面候选'], tags: ['跑道', '比赛', '4K'], used: `${PIECE.vlog.title} · v2` },
    { i: 16, title: '短跑终点冲刺', dur: 3.8, range: '6.2–10.0', src: '兰州大学校运会短跑终点冲刺_观众近景.mp4', uses: ['可复用镜头', '手机常用'], tags: ['跑道', '冲刺'], used: `${PIECE.vlog.title} · v1、v2` },
    { i: 11, title: '兰州西站扶梯到达', dur: 3.3, range: '2.1–5.4', src: '兰州西站扶梯到达.mp4', uses: ['可复用镜头'], tags: ['车站', '扶梯', '纵深'], used: '' },
    { i: 7, title: '号码布镜前自拍', dur: 3.8, range: '0.8–4.6', src: '兰州大学校运会号码布镜前自拍视频.mp4', uses: ['封面候选', '手机常用'], tags: ['自拍', '镜前'], used: `${PIECE.vlog.title} · v2` },
    { i: 12, title: '榆中校区人像自拍', dur: 5.8, range: '0.0–5.8', src: '兰州大学榆中校区人像自拍视频_近景.mp4', uses: ['手机常用'], tags: ['自拍', '近景'], used: '' },
    { i: 26, title: '跑道旁自拍', dur: null, range: '', src: '兰州大学校运会跑道自拍_LIVE01.HEIC', uses: ['纪念'], tags: ['自拍', '跑道', '实况照片'], used: '' },
    { i: 22, title: '白云机场窗边行走', dur: 5.3, range: '9.1–14.4', src: '广州白云机场起飞前窗外云层_氛围.mp4', uses: ['可复用镜头'], tags: ['机场', '窗边'], used: '' },
    { i: 18, title: '广州南站站厅人流', dur: 1.7, range: '3.0–4.7', src: '广州南站地铁站厅奔赴_氛围.mp4', uses: ['可复用镜头'], tags: ['车站', '人流'], used: '' },
  ];
  const PICK_AI = { 16: '画面里的人正在全速冲刺，正好配「快」的那半圈。', 1: '7.7 秒里能看到从起跑到途中跑，可以讲「跑完全程用了多久」。', 11: '扶梯匀速往上走，适合拿来对照「速度一直不变」。' };
  let libSel = 1, pickSel = 16;
  const libItem = a => {
    const s = sel(a.i);
    return `<button class="asset gl-asset" aria-selected="${(ctx.state === 'pick' ? pickSel : libSel) === a.i}" data-asset="${a.i}" data-design-id="LIB-ASSET"><div class="cover">${shotImg(s)}${a.dur ? `<span class="len">${D(ctx.s1(a.dur))}″</span>` : '<span class="len">照片</span>'}</div><div class="gl-asset-b"><b data-design-data>${esc(a.title)}</b><small>来自「${D(PIECE.vlog.title)}」</small><span class="tags">${a.uses.map(u => `<i class="tag">${u}</i>`).join('')}</span></div></button>`;
  };
  function libRail(a, pick) {
    const s = sel(a.i);
    return `<aside class="rail keep gl-librail" data-design-id="LIB-DETAIL"><div class="viewer">${shotImg(s)}</div><div class="rail-body"><h3 data-design-data>${esc(a.title)}</h3><p class="where">来自「${D(PIECE.vlog.title)}」· <span class="mono" data-design-data>${esc(a.src)}</span>${a.range ? ` 第 ${D(a.range)} 秒` : ''}</p>
      <div class="verdict" data-design-id="LIB-AI"><small>${pick && PICK_AI[a.i] ? '为什么推荐它' : 'AI 看到的'}</small><p data-design-data>${esc(pick && PICK_AI[a.i] ? PICK_AI[a.i] : (s && s.reason) || '画面描述读不到')}</p></div>
      <div class="kv"><span>用途</span><strong>${a.uses.map(u => `<i class="tag">${u}</i>`).join(' ')}</strong></div>
      <div class="kv"><span>标签</span><strong data-design-data>${esc(a.tags.join(' · '))}</strong></div>
      <div class="kv"><span>用在了</span><strong data-design-data>${a.used ? esc(a.used) : '还没用过'}</strong></div>
      <div class="kv"><span>原件</span><strong>留在作品里<small>素材库只登记了这张卡片</small></strong></div>
      <div class="rail-foot">${pick ? C.btn('放进第 4 镜', { pri: true, go: 's2', line: 'direct' }) : C.btn('加入作品…', { pri: true, toast: '选一件作品，这条素材登记进它的素材里，原件不复制' })}${C.btn('在访达中显示', { toast: '在访达里打开原件所在的文件夹' })}</div></div></aside>`;
  }
  function libFilled(pick) {
    const list = pick ? [...LIB.filter(a => PICK_AI[a.i]).sort((x, y) => (x.i === 16 ? -1 : y.i === 16 ? 1 : 0)), ...LIB.filter(a => !PICK_AI[a.i])] : LIB;
    const cur = LIB.find(a => a.i === (pick ? pickSel : libSel)) || LIB[0];
    const count = u => LIB.filter(a => a.uses.includes(u)).length;
    const tree = `<nav class="tree gl-tree" aria-label="素材分类" data-design-id="LIB-TREE"><button aria-current="true">全部素材 <i data-design-data>${LIB.length}</i></button><p>用途</p>${['可复用镜头', '封面候选', '纪念', '手机常用'].map(u => `<button data-toast="只看「${u}」">${u} <i data-design-data>${count(u)}</i></button>`).join('')}<p>来自作品</p><button data-toast="只看来自这件作品的素材">${esc(PIECE.vlog.title)} <i data-design-data>${LIB.length}</i></button><small>一条素材可以有几种用途，所以加起来比全部多。</small></nav>`;
    const tagCount = t => LIB.filter(a => a.tags.includes(t)).length;
    const filters = `<div class="subfilters" data-design-id="LIB-TAGS"><button class="pill" aria-pressed="true">全部标签</button>${['跑道', '机场', '自拍', '车站', '纵深'].map(t => `<button class="pill" aria-pressed="false" data-toast="只看带「${t}」的">${t}<i data-design-data>${tagCount(t)}</i></button>`).join('')}</div>`;
    const grid = `<div class="assets gl-assets">${list.map(a => (pick && PICK_AI[a.i] ? libItem(a).replace('<div class="gl-asset-b">', '<div class="gl-asset-b"><span class="chip chip--ac gl-ai">AI 推荐</span>') : libItem(a))).join('')}</div>`;
    return `<div class="gl-lib full">${tree}<div class="stack">${filters}${grid}</div>${libRail(cur, pick)}</div>`;
  }
  reg('library', {
    group: '全局', name: '素材库', nav: 'library',
    states: [['filled', '有 9 项'], ['empty', '还是空的'], ['pick', '从分镜来挑']],
    crumb: s => (s === 'pick' ? `<button data-go="s2" data-line="direct">${D(PIECE.direct.title)}</button>·分镜` : ''),
    title: '素材库',
    sub: s => (s === 'pick' ? '给分镜第 4 镜挑画面' : '跨作品复用的镜头和照片'),
    actions: s => (s === 'pick' ? '' : C.btn('登记素材', { toast: '从本机选一个镜头或照片，登记成素材库卡片' })),
    render: s => {
      if (s === 'empty') return `<div class="empty" data-design-id="LIB-EMPTY"><h2>素材库还是空的</h2><p>在作品的「挑镜头」里选中一个镜头，点「收进素材库」，它就会出现在这里，别的作品也能直接用。</p><div class="actions">${C.btn('去看项目', { pri: true, go: 'projects' })}${C.btn('登记素材', { toast: '从本机选一个镜头或照片，登记成素材库卡片' })}</div></div>`;
      if (s === 'pick') {
        return `<div class="gl-pickbar full" data-design-id="LIB-PICK"><div><strong>正在给「${D(PIECE.direct.title)}」第 4 镜挑画面</strong><p>这一镜说：「${D('同样跑 400 米，前半圈快、后半圈慢，平均速度看的是总路程除以总时间。')}」AI 按这句话把最像的 3 条排在前面。</p></div><div class="actions">${C.btn('返回分镜', { go: 's2', line: 'direct' })}</div></div>` + libFilled(true);
      }
      return libFilled(false);
    },
    after: (root, s) => root.querySelectorAll('[data-asset]').forEach(b => b.onclick = () => { if (s === 'pick') pickSel = +b.dataset.asset; else libSel = +b.dataset.asset; PCOS.render(); }),
  });

  // ================= 音乐库（沿用现状） =================
  const SRC = { local: '本机文件', netease: '网易云音乐', netease_client: '网易云音乐', qishui: '汽水音乐' };
  const MTAG = {
    'CRUSH VIBE': { row: ['电子', '旋律优美', '纯音乐'], genre: ['电子'], style: 'Trance', mood: ['旋律优美', '太空感'], scene: [], voice: ['纯音乐'], inst: ['合成器', '鼓'], date: '2026/10/19' },
    'Turn Back Time': { row: ['电子', '夏日', '有人声'], genre: ['电子'], style: 'Tropical House', mood: ['深沉', '欢快'], scene: ['夏日'], voice: ['有人声'], inst: ['贝斯', '合成器', '键盘'], date: '2026/10/20' },
    'Fever Pitch': { row: ['电子', '夏日'], genre: ['电子'], style: 'House', mood: ['深沉', '暗黑'], scene: ['夏日'], voice: [], inst: ['鼓', '合成器'], date: '2026/10/20' },
  };
  const FALLBACK_TRACKS = [
    { title: 'CRUSH VIBE', artist: '未知歌手', platform: 'local', dur: 96, bpm: 143.6, peaks: [], sections: [] },
    { title: 'Turn Back Time', artist: 'Rich Edwards / Emelie', platform: 'netease', dur: 189.9, bpm: 117.5, peaks: [], sections: [] },
    { title: 'Fever Pitch', artist: 'Richz', platform: 'qishui', dur: 135.5, bpm: 123, peaks: [], sections: [] },
  ];
  let musicSel = 'Turn Back Time';
  function waveBars(t, n = 120) {
    const p = t.peaks || [];
    if (!p.length) return Array.from({ length: n }, () => '<i style="height:20%"></i>').join('');
    const max = Math.max(...p.map(v => Math.abs(Array.isArray(v) ? Math.max(...v) : v))) || 1;
    return Array.from({ length: n }, (_, k) => { const v = p[Math.floor(k * p.length / n)]; const a = Math.abs(Array.isArray(v) ? Math.max(...v) : v) / max; return `<i style="height:${Math.max(6, Math.round(a * 100))}%"></i>`; }).join('');
  }
  const KIND = { quiet: ['', '安静'], build: ['b', '推进'], peak: ['p', '高潮'] };
  function musicPage() {
    const tracks = TRACKS.length ? TRACKS : FALLBACK_TRACKS;
    const m = tracks.find(t => t.title === musicSel) || tracks[0];
    const tg = MTAG[m.title] || { row: [], genre: [], mood: [], scene: [], voice: [], inst: [], date: '' };
    const n = k => tracks.filter(t => t.platform === k).length;
    const tagN = (g, v) => tracks.filter(t => (MTAG[t.title] || {})[g]?.includes(v)).length;
    const tf = [['场景', 'scene', ['夏日']], ['情绪', 'mood', ['深沉', '暗黑', '欢快', '旋律优美', '太空感']], ['人声', 'voice', ['有人声', '纯音乐']], ['风格', 'genre', ['电子']]];
    const secs = (m.sections || []).map(x => `<i class="${KIND[x.kind]?.[0] || ''}" style="left:${(100 * x.start / m.dur).toFixed(2)}%;width:${(100 * (x.end - x.start) / m.dur).toFixed(2)}%"></i>`).join('');
    const tgRow = (name, vals, extra = '') => `<div class="gl-tgrow"><span>${name}</span><div>${vals.length ? vals.map(v => `<i class="tag">${v}</i>`).join('') : '<em>听不准</em>'}${extra}</div></div>`;
    return `<form class="import" data-design-id="R208-MUSIC-import" onsubmit="return false"><label for="paste">粘贴分享链接导入</label><div class="import-row"><input id="paste" placeholder="粘贴汽水音乐或网易云音乐的分享文字">${C.btn('导入', { pri: true, toast: '下载这首歌，分析节拍和段落，再用 AI 标注风格和情绪' })}</div><small>每首只下载一次，之后都用本机这份。</small></form>
      <div class="subfilters full" data-design-id="R208-MUSIC-filters"><button class="pill" aria-pressed="true">全部<i data-design-data>${tracks.length}</i></button><button class="pill">汽水音乐<i data-design-data>${n('qishui')}</i></button><button class="pill">网易云音乐<i data-design-data>${n('netease') + n('netease_client')}</i></button><button class="pill">本机文件<i data-design-data>${n('local')}</i></button></div>
      <div class="gl-tagfilters full" data-design-id="R223-TAG-filters">${tf.map(([label, g, vals]) => `<span class="gl-tf">${label}</span>${vals.map(v => `<button class="pill">${v}<i data-design-data>${tagN(g, v)}</i></button>`).join('')}`).join('')}</div>
      <div class="cols"><div class="tracks" data-design-id="R208-MUSIC-list"><div class="trow head"><span></span><span>歌名</span><span>来源</span><span>时长</span><span>速度</span><span>导入时间</span></div>${tracks.map(t => { const g = MTAG[t.title] || { row: [], date: '' }; return `<button class="trow" data-track="${esc(t.title)}" aria-selected="${t === m}"><span class="play" aria-label="播放">▶</span><span class="t"><b data-design-data>${esc(t.title)}</b><small data-design-data>${esc(t.artist)}</small><span class="tags">${g.row.map(x => `<i class="tag">${x}</i>`).join('')}</span></span><span>${SRC[t.platform] || '本机文件'}</span><span class="num" data-design-data>${mmss(t.dur)}</span><span class="num"><b data-design-data>${Math.round(t.bpm)}</b> BPM</span><span class="num" data-design-data>${g.date}</span></button>`; }).join('')}</div>
      <aside class="rail" data-design-id="R223-BEAT-rail"><div class="wave"><div class="bars">${waveBars(m)}</div><div class="bm-band">${secs}</div><div class="bm-legend"><span><i class="sw sw--quiet"></i>安静</span><span><i class="sw sw--build"></i>推进</span><span><i class="sw sw--peak"></i>高潮</span></div><div class="bm-transport"><button aria-label="播放" data-toast="从头播放">▶</button><span class="mono gl-ptime">0:00 / ${D(mmss(m.dur))}</span><span class="bm-where">第 1 小节 <span class="bm-kind bm-kind--${(m.sections && m.sections[0] && m.sections[0].kind) || 'quiet'}">${KIND[(m.sections && m.sections[0] && m.sections[0].kind) || 'quiet'][1]}</span></span></div></div>
        <div class="rail-body"><h3 data-design-data>${esc(m.title)}</h3><p class="where" data-design-data>${esc(m.artist)}</p><div class="gl-tg" data-design-id="R223-TAG-panel"><div class="gl-tghead">AI 标注</div>${tgRow('风格', tg.genre, tg.style ? `<small data-design-data>${tg.style}</small>` : '')}${tgRow('情绪', tg.mood)}${tgRow('场景', tg.scene)}${tgRow('人声', tg.voice)}${tgRow('乐器', tg.inst)}</div>
        <div class="kv"><span>来源</span><strong>${SRC[m.platform] || '本机文件'}${m.platform !== 'local' ? '<small><button class="link" data-toast="打开这首歌在平台上的原页面">打开原页面</button></small>' : ''}</strong></div><div class="kv"><span>时长</span><strong data-design-data>${mmss(m.dur)}</strong></div><div class="kv"><span>速度</span><strong><span data-design-data>${Math.round(m.bpm)}</span> BPM<small>每小节 <span data-design-data>4</span> 拍</small></strong></div><div class="kv"><span>导入时间</span><strong data-design-data>${tg.date}</strong></div></div></aside></div>`;
  }
  reg('music', {
    group: '全局', name: '音乐库（沿用现状）', nav: 'music',
    states: [['default', '3 首歌']],
    title: '音乐库', sub: '配乐卡点从这里选歌',
    actions: () => C.btn('从文件夹导入', { toast: '从本机或网易云客户端的下载目录导入' }),
    render: musicPage,
    after: root => root.querySelectorAll('[data-track]').forEach(b => b.onclick = () => { musicSel = b.dataset.track; PCOS.render(); }),
  });

  // ================= 设置与诊断 =================
  // 版式沿用现在的设置页：左边分类，右边内容。只画模型、剪辑软件、上游账号三项。
  const SETNAV = [['存放位置', GI.drive, '', '存放位置沿用 R225 设计稿，本稿没有重画'], ['剪辑软件', GI.scissors, 'set-editors'], ['模型', GI.cpu, 'set-model'], ['音乐下载', GI.download, '', '音乐下载沿用现状，本稿没有重画'], ['上游账号', GI.cloud, 'set-upstream']];
  const setShell = (active, main) => `<div class="gl-set full" data-design-id="SET-SHELL"><nav class="gl-setnav" aria-label="设置分类"><p>设置</p>${SETNAV.map(([t, ic, go, toast]) => `<button ${go ? `data-go="${go}"` : `data-toast="${toast}"`} ${active === go ? 'aria-current="true"' : ''}>${ic}${t}</button>`).join('')}<p>检查</p><button data-toast="诊断沿用现状，本稿没有重画">${GI.activity}诊断</button></nav><section class="set-main">${main}</section></div>`;
  const MODELS = [
    ['看图挑镜头', 'Codex · gpt-5.6-terra', '关键帧拼图发给 OpenAI', 'vision'],
    ['写素材摘要', 'Codex · gpt-5.6-terra', '关键帧发给 OpenAI', 'vision'],
    ['改稿（只改你选中的段落）', 'Codex · gpt-5.6-terra', '稿子发给 OpenAI', 'vision'],
    ['按稿配素材', 'Codex · gpt-5.6-terra', '稿子和素材摘要发给 OpenAI', 'vision'],
    ['写镜头和包装动画的代码', 'Claude Code（Anthropic）', '本机调用，分镜和口播发给 Anthropic', 'code'],
    ['改镜头代码（改短、不用素材图）', '上游中台（MediaClaw）', '网页中台', 'upstream'],
    ['检查镜头代码', '不用模型，本机按规则检查', '本机', 'rules'],
    ['音乐标注', 'Essentia 标注模型', '本机', 'local'],
    ['转写', 'FunASR · paraformer-zh', '本机，不上传', 'local'],
    ['字幕翻译', '上游中台（MediaClaw）', '网页中台', 'upstream'],
  ];
  function modelMain(missing) {
    const row = ([name, model, where, kind]) => {
      const off = missing && kind === 'vision';
      const status = off ? C.st('用不了', 'bad') : kind === 'upstream' ? C.st('没连上', 'wait') : C.st('可用');
      const act = off ? '' : kind === 'upstream' ? C.btn('去连接', { cls: 'btn--sm', go: 'set-upstream' }) : (kind === 'local' && name === '音乐标注') || kind === 'rules' ? '' : C.btn('换', { cls: 'btn--sm', toast: `给「${name}」换一个模型` });
      return `<div class="gl-mrow" data-design-id="SET-MODEL-ROW"><b>${name}</b><span class="${off ? 'gl-none' : ''}" data-design-data>${off ? '没登记' : esc(model)}</span><span data-design-data>${off ? '—' : esc(where)}</span><span>${status}</span><span class="gl-mact">${act}</span></div>`;
    };
    const budget = [['每件素材预览几张图', 3, '张', '先从每段视频均匀取几张给模型看'], ['深看几张', 8, '张', '精选确认以后，对要用的素材再多看几张'], ['预览最多看多少件', 60, '件', '超过的按清晰度和时长排，先看前面的'], ['深看最多看多少件', 15, '件', '只深看精选里的素材'], ['音频最多转写几分钟', 60, '分钟', '在本机转写，不上传']];
    return `<h3>模型</h3><p>每项 AI 能力用哪个模型、在哪里跑。发给模型的只有关键帧拼图、转写文字和稿子；原片不上传。</p>
      ${missing ? C.attn({ title: '还没登记看图模型：挑镜头、写素材摘要用不了', text: '改稿和按稿配素材也要用它。转写和音乐标注在本机跑，不受影响。', actions: C.btn('登记模型', { pri: true, toast: '登记一个看图模型：服务、模型名、密钥放在钥匙串里' }), id: 'SET-MODEL-MISSING' }) : ''}
      <div class="gl-mtab ${missing ? 'gl-mtab--after' : ''}" data-design-id="SET-MODEL-TABLE"><div class="gl-mrow gl-mhead"><span>能力</span><span>用的模型</span><span>在哪跑</span><span>状态</span><span></span></div>${MODELS.map(row).join('')}</div>
      <section class="set-sec" data-design-id="SET-BUDGET"><h4>看多少</h4><p>素材多时先粗看、再细看。数字越大看得越准，也越慢、调用越多。</p><div class="gl-budget">${budget.map(([l, v, u, d]) => `<label class="gl-field"><span>${l}</span><span class="gl-num"><input type="number" value="${v}" min="0" data-design-data> ${u}</span><small>${d}</small></label>`).join('')}</div><div class="set-actions">${C.btn('保存', { pri: true, toast: '已保存。下次分析素材时按新的数量看' })}${C.btn('恢复默认', { toast: '恢复成 3 张、8 张、60 件、15 件、60 分钟' })}</div></section>`;
  }
  const EDITORS = [['OpenChatCut', '0.2.16', '', '可用'], ['OpenFilm', '0.1.5', '', '可用'], ['ChatCut Desktop 还没连上本机', '', '还没连上本机。在 ChatCut 里开启本机连接后，点「重新检查」。', '没连上'], ['剪映', '11.0.0', '', '可用'], ['Kdenlive', '26.04', '', '可用']];
  reg('set-model', {
    group: '全局', name: '设置 · 模型', nav: 'settings',
    states: [['ok', '都配好了'], ['missing', '还没登记看图模型']],
    title: '设置与诊断', sub: '本机配置与可选连接',
    render: s => setShell('set-model', modelMain(s === 'missing')),
  });
  reg('set-editors', {
    group: '全局', name: '设置 · 剪辑软件（沿用现状）', nav: 'settings',
    title: '设置与诊断', sub: '本机配置与可选连接',
    render: () => setShell('set-editors', `<h3>剪辑软件</h3><p>每件作品出草稿时，用你给它选的剪辑软件，没选过的默认用 Kdenlive。选了 ChatCut 但没连上时，不会悄悄换成别的，会在工作台提醒你。</p><ul class="dx-list" data-design-id="SET-EDITORS">${EDITORS.map(([n, v, note, st]) => `<li><div><b>${n}${v ? ` · <span data-design-data>${v}</span>` : ''}</b>${note ? `<small>${note}</small>` : ''}</div><div class="dx-end"><span class="dx-val ${st === '可用' ? '' : 'muted'}">${st}</span></div></li>`).join('')}</ul><div class="set-actions">${C.btn('重新检查', { toast: '重新检查每个剪辑软件装没装、连没连上' })}</div>`),
  });
  reg('set-upstream', {
    group: '全局', name: '设置 · 上游账号', nav: 'settings',
    title: '设置与诊断', sub: '本机配置与可选连接',
    render: () => setShell('set-upstream', `<h3>上游账号</h3><p>上游中台是 MediaClaw 的网页端。不连也能用本机的整理、挑镜头、配乐卡点和出草稿。</p>
      <div class="loc-empty" data-design-id="SET-UPSTREAM-OFF"><div><b>还没连上上游中台</b><small>在网页上授权以后，把配对意图粘贴回来。本机不存令牌明文；解除配对后，本机的作品和素材都不受影响。</small></div><div class="actions">${C.btn('粘贴配对意图', { toast: '粘贴在网页上拿到的配对意图' })}${C.btn('去网页授权', { pri: true, toast: '在浏览器里打开 MediaClaw 的授权页' })}</div></div>
      <section class="set-sec" data-design-id="SET-UPSTREAM-GAINS"><h4>连上以后多出来的</h4><p>这几样只在上游中台里做，本机做不了。</p><ul class="dx-list">${[['直出的配音', '按口播稿生成配音，回到「字幕与声音」那一步'], ['直出的英文字幕', '按切好的中文字幕逐条翻译'], ['网页上派给这台电脑的任务', '在网页上点「在 Mac 上做」，这台电脑接着做'], ['成片回传', '检查通过的低清成片传回 MediaClaw，原片和高清成片留在本机']].map(([b, sm]) => `<li><span class="dx-tile">${GI.cloud}</span><div><b>${b}</b><small>${sm}</small></div></li>`).join('')}</ul></section>`),
  });

  // ================= 素材整理（作品侧页） =================
  const TIDY_TABS = [['additions', '补充素材', 12], ['pending', '待处理', 6], ['bursts', '连拍与相似', '4 组'], ['uses', '用途', 12]];
  const tidyTabs = s => `<div class="full gl-subtabs" data-design-id="TIDY-TABS"><div class="tabs">${TIDY_TABS.map(([k, t, n]) => `<button aria-pressed="${s === k}" data-go="tidy" data-s="${k}">${t}<i data-design-data>${n}</i></button>`).join('')}</div></div>`;
  const addCard = (s, file, why, scene, unknown) => `<div class="gl-add" data-design-id="TIDY-ADD">${th(s)}<div><b class="mono" data-design-data>${esc(file)}</b><small data-design-data>${esc(why)}</small><span class="gl-select ${unknown ? 'gl-select--empty' : ''}" data-design-data>${unknown ? '选场景…' : esc(scene)} ▾</span></div></div>`;
  function tidyAdditions() {
    const sports = [['IMG_4512.MOV', '同一条跑道，起跑前的准备'], ['IMG_4515.MOV', '看台视角，和已有镜头同一位置'], ['IMG_4519.HEIC', '计时屏特写，能看到成绩'], ['IMG_4521.MOV', '弯道上的几个人在跑'], ['IMG_4526.HEIC', '终点线旁的观众']];
    const travel = [['IMG_4478.MOV', '高铁站进站口，和「路上」同一天'], ['IMG_4480.HEIC', '车厢里拍的，去学校的路上']];
    return C.attn({ title: `1 条没合并成：${D('IMG_4510.MOV')}`, text: '文件读不出来，判断不了放哪个场景。它还在补充素材里，没有动。', actions: C.btn('在访达中显示', { toast: '在访达里打开这个文件' }) + C.btn('移到待处理', { go: 'tidy', s: 'pending' }), id: 'TIDY-ADD-FAIL' }) +
      C.statusline(`<b>${D(3)} 条原始格式已经自动进了待处理：</b>${D(2)} 段全景原片、${D(1)} 段 Log 视频。`, C.btn('去待处理', { go: 'tidy', s: 'pending', cls: 'btn--sm' }), 'TIDY-ADD-AUTO') +
      `<section class="pnl full" data-design-id="TIDY-ADD-GROUP"><div class="pnl-h"><div><h3>AI 建议放进「校运会」<span>${D(sports.length)} 条</span></h3><p>都是 10/24 下午在操场拍的，画面里是同一条跑道。</p></div>${C.btn('这一组按建议放', { cls: 'btn--sm', toast: '这 5 条标成「校运会」，点底部确认后合并' })}</div><div class="pnl-b gl-adds">${sports.map(([f, w], k) => addCard(inScene('sports-meet', k * 3 + 5), f, w, '校运会')).join('')}</div></section>
      <section class="pnl full" data-design-id="TIDY-ADD-GROUP"><div class="pnl-h"><div><h3>AI 建议放进「路上」<span>${D(travel.length)} 条</span></h3><p>拍摄时间在去学校的路上，和「路上」里的镜头接得上。</p></div>${C.btn('这一组按建议放', { cls: 'btn--sm', toast: '这 2 条标成「路上」，点底部确认后合并' })}</div><div class="pnl-b gl-adds">${travel.map(([f, w], k) => addCard(inScene('travel', k * 7 + 20), f, w, '路上')).join('')}</div></section>
      <section class="pnl full" data-design-id="TIDY-ADD-UNKNOWN"><div class="pnl-h"><div><h3>没认出场景<span>${D(1)} 条</span></h3><p>只拍到人群，看不出在哪，你选一个场景。</p></div></div><div class="pnl-b gl-adds">${addCard(inScene('travel', 3), 'IMG_4531.MOV', '只拍到人群，没有能认出地点的东西', '', true)}</div></section>
      <div class="pnl full gl-bottombar" data-design-id="TIDY-ADD-CONFIRM"><p>确认后 ${D(7)} 条按场景合并，文件名加「补充」编号；没选场景的 ${D(1)} 条留在这里。</p><div class="actions">${C.btn('确认 7 条', { pri: true, toast: '7 条合并进对应场景的文件夹，挑镜头时会一起看' })}</div></div>`;
  }
  function tidyPending() {
    const rows = [
      ['防抖', 'sports-meet', 13, '手持跟跑.MOV', '校运会', '跟着跑的时候抖得厉害，剪之前先防抖。', false],
      ['转码', 'sports-meet', 8, 'VID_20260514_全景_01.insv', '校运会', '全景原片，要先在 Insta360 里导出平面视频。', true],
      ['转码', 'sports-meet', 11, 'VID_20260514_全景_02.insv', '校运会', '全景原片，要先在 Insta360 里导出平面视频。', true],
      ['转码', 'travel', 30, '夜景延时_Log.MOV', '路上', 'Log 画面，先还原颜色再用。', true],
      ['修复', 'travel/raw-pending', 0, '广州白云机场窗外_模糊待选.mp4', '路上', '画面发虚，打算用 Wink 修一下。', false],
      ['补齐', 'selfie-moments', 9, 'IMG_4436.HEIC', '自拍', '实况照片只有照片，同名的视频没拷过来。', false],
    ];
    return `<section class="pnl full" data-design-id="TIDY-PENDING"><ul class="rows">${rows.map(([kind, sc, n, f, scene, why, auto]) => `<li><span class="gl-th gl-th--row">${shotImg(inScene(sc, n))}</span><div><b><span class="mono" data-design-data>${esc(f)}</span> · ${scene}</b><small data-design-data>${esc(why)}</small></div><span class="end"><i class="tag ${kind === '修复' ? 'tag--warn' : ''}">${kind}</i>${auto ? '<i class="tag">自动进来的</i>' : ''}${C.btn('处理好了', { cls: 'btn--sm', toast: `${f} 回到「${scene}」里` })}</span></li>`).join('')}</ul></section>`;
  }
  function tidyBursts() {
    const groups = [
      ['号码布镜前自拍', '24 张', '号码布镜前自拍', [3, 6, 15], '号码布完整，手机没有挡住脸。'],
      ['起跑准备（看台视角）', '18 张', '看台视角补充', [4, 5, 9], '所有人都蹲好了，起跑线完整在画面里。'],
      ['终点冲刺', '30 张', '终点冲刺', [5, 10, 15], '冲在最前面的人离镜头最近，没有被观众挡住。'],
      ['校园人像自拍', '20 张', '人像自拍视频_近景', [2, 6, 12], '表情最自然，身后的树没有糊。'],
    ];
    return groups.map(([name, n, src, [a, b, c], why]) => {
      const fr = framesOf(src, 9);
      return `<section class="pnl full" data-design-id="TIDY-BURST"><div class="pnl-h"><div><h3>${name}<span>${D(n)}</span></h3><p>出彩 ${D(a)} · 动作略不同 ${D(b)} · 近乎一样 ${D(c)}</p></div><div class="actions">${C.btn('按建议分', { cls: 'btn--sm', pri: true, toast: `出彩的 ${a} 张进场景和精选，动作不同的 ${b} 张留在场景里当补充，近乎一样的 ${c} 张整组原始保留` })}${C.btn('整组原始保留', { cls: 'btn--sm', toast: '整组放进原始保留：不进手机、不进素材库' })}${C.btn('自己挑', { cls: 'btn--sm', toast: '打开这一组，一张张定' })}</div></div><div class="pnl-b"><div class="gl-burst">${fr.map((f, k) => `<span class="gl-th ${k === 0 ? 'gl-rep' : ''}">${img(f)}${k === 0 ? '<i class="gl-rep-tag">AI 挑的代表</i>' : ''}</span>`).join('')}<span class="gl-th gl-more"><span>+${D(parseInt(n, 10) - fr.length)}</span></span></div><div class="verdict"><small>为什么是这张</small><p data-design-data>${why}</p></div></div></section>`;
    }).join('') + `<p class="howto full">近乎一样的照片不会进可清理文件。想留就整组原始保留：不进手机、不进素材库，冷归档时跟着作品走。</p>`;
  }
  function tidyUses() {
    const col = (name, n, desc, picks, extra = '', id = 'TIDY-USE') => `<section class="pnl gl-use" data-design-id="${id}"><div class="pnl-h"><h3>${name}<span>${D(n)}</span></h3>${extra}</div><div class="pnl-b"><p class="gl-usedesc">${desc}</p><div class="gl-usegrid">${picks.map(i => th(sel(i))).join('')}</div></div></section>`;
    const pendingCol = `<section class="pnl gl-use" data-design-id="TIDY-USE-PENDING"><div class="pnl-h"><h3>手机精选<span>${D(3)}</span></h3>${C.st('3 条等你确认', 'wait')}</div><div class="pnl-b"><p class="gl-usedesc">AI 建议放进手机常用：复制一份进 iCloud 照片准备区。</p><div class="gl-usepend">${[16, 7, 12].map(i => `<div class="gl-pend">${th(sel(i))}<span class="actions"><button class="btn btn--sm" data-toast="确认放进手机精选">要</button><button class="btn btn--sm" data-toast="不放进手机">不要</button></span></div>`).join('')}</div></div></section>`;
    return `<div class="gl-uses full">${col('可复用镜头', 6, '别的作品也能用。素材库只登记一张卡片，原件留在作品里。', [2, 1, 16, 11, 22, 18], C.link('去素材库', { go: 'library' }))}${col('封面候选', 2, '复制一份进 iCloud 照片准备区的封面候选。', [1, 7])}${col('纪念', 1, '超出这件作品本身的人生节点，另外登记到素材库的纪念。', [26])}${pendingCol}</div><p class="howto full">同一条素材可以同时有几种用途，所以各栏加起来比素材条数多。</p>`;
  }
  const TIDY_HEAD = {
    additions: ['12 条补充素材，等你确认放哪个场景', '10/24 从整理台放进来的。原始格式（全景原片、Log）自动进待处理；其余由 AI 按画面和拍摄时间建议场景，可以整组确认。'],
    pending: ['6 条待处理，每条都写了原因', '知道放哪个场景，但要先处理才能剪；「看起来一般」不算原因。处理好以后点「处理好了」，它回到场景里。'],
    bursts: ['4 组连拍和相似照片', 'AI 在每组里挑了代表，其余按你定：出彩的进场景和精选，动作不同的留在场景里当补充，近乎一样但想留的整组原始保留。'],
    uses: ['用途：哪些素材以后还要用', '精选副本放进 iCloud 照片准备区，素材库只登记卡片，原件一直留在作品里。'],
  };
  reg('tidy', {
    group: '作品侧页', name: '素材整理', nav: 'projects', piece: { tab: 'tidy' },
    states: [['additions', '补充素材 12 条'], ['pending', '待处理 6 条'], ['bursts', '连拍与相似 4 组'], ['uses', '用途']],
    actions: () => playBtn,
    render: s => C.head({ eyebrow: '素材整理', title: TIDY_HEAD[s][0], lede: TIDY_HEAD[s][1], id: 'TIDY-HEAD' }) + tidyTabs(s) + ({ additions: tidyAdditions, pending: tidyPending, bursts: tidyBursts, uses: tidyUses }[s])(),
  });

  // ================= 保存与归档（作品侧页） =================
  // 归档按作品算（R225 C1）。「副本核对通过」「已冷归档」分开显示（C9）；条件没齐不出删除按钮。
  const STAGES = [['活动期', '还在剪、还在发'], ['发布冷却期', '发布后约一个月，阿里云盘镜像好'], ['冷归档期', '原始素材移出 Mac，移动硬盘留完整包'], ['恢复期', '要用时拷回 Mac，原归档不直接改']];
  const ARCH = {
    active: {
      piece: PIECE.vlog.title, project: PIECE.vlog.project, date: PIECE.vlog.date, stage: 0,
      head: ['还在剪，先不用归档', '归档按作品算。发布满约一个月、两份副本都核对通过、写好索引卡、做过恢复演练以后，才能把原始素材移出 Mac。'],
      status: [['副本核对：1 份通过，1 份还没拷', 'off'], ['冷归档：还没做', 'off']],
      copies: [['cloud', '阿里云盘', '单向镜像 · 整件作品', '1,284 个文件 · 41.6 GB', '10月20日核对通过', 'ok', ''], ['drive', '移动硬盘「T7-归档-01」', '冷归档 · 整件作品', '', '还没拷', 'off', C.btn('拷过去', { cls: 'btn--sm', toast: '把整件作品拷到 T7-归档-01，拷完读回来核对' })]],
      conds: [['发布满约一个月', 'todo', '还没发布'], ['阿里云盘镜像核对通过', 'ok', '10月20日'], ['移动硬盘完整包核对通过', 'todo', '还没拷'], ['索引卡写好', 'todo', '冷归档时写'], ['恢复演练通过', 'todo', '拷完以后做']],
      free: '条件都齐了以后，可以腾出 Mac 上约 41.6 GB。条件没齐之前，这里不会出现删除按钮。',
    },
    cooling: {
      piece: '第一视角体验清华毕业典礼', project: '2026年清华毕业典礼内容创作', date: '2026/6/25', stage: 1,
      head: ['发布冷却期：移动硬盘副本没核对通过', '补拷以后再核对一次。两份副本都通过、做过恢复演练，才能冷归档。'],
      attn: true,
      status: [['副本核对：1 份通过，1 份没通过', 'wait'], ['冷归档：还没做', 'off']],
      copies: [['cloud', '阿里云盘', '单向镜像 · 整件作品', '412 个文件 · 18.9 GB', '10月21日核对通过', 'ok', ''], ['drive', '移动硬盘「T7-归档-01」', '冷归档 · 整件作品', '409 / 412 个文件', '10月22日核对：少了 3 个', 'bad', '']],
      conds: [['发布满约一个月', 'ok', '已发布 41 天'], ['阿里云盘镜像核对通过', 'ok', '10月21日'], ['移动硬盘完整包核对通过', 'fail', '少了 3 个文件'], ['索引卡写好', 'ok', '10月22日'], ['恢复演练通过', 'todo', '补拷以后再做']],
      free: '补齐以后可以腾出 Mac 上约 18.9 GB。条件没齐之前，这里不会出现删除按钮。',
    },
    ready: {
      piece: '400米比赛 · 第一视角', project: PIECE.vlog.project, date: '2026/5/14', stage: 1,
      head: ['条件都齐了，可以冷归档', '两份副本都核对通过，索引卡写好了，恢复演练也做过。冷归档会把原始素材移出 Mac，移动硬盘里留完整包。'],
      status: [['副本核对：两份都通过', 'ok'], ['冷归档：还没做', 'off']],
      copies: [['cloud', '阿里云盘', '单向镜像 · 整件作品', '1,031 个文件 · 38.2 GB', '10月23日核对通过', 'ok', ''], ['drive', '移动硬盘「T7-归档-01」', '冷归档 · 整件作品', '1,031 个文件 · 38.2 GB', '10月23日核对通过', 'ok', '']],
      conds: [['发布满约一个月', 'ok', '已发布 36 天'], ['阿里云盘镜像核对通过', 'ok', '10月23日'], ['移动硬盘完整包核对通过', 'ok', '10月23日'], ['索引卡写好', 'ok', '在素材文件夹的项目归档索引里'], ['恢复演练通过', 'ok', '10月24日 · 随机拷回 20 个都能打开']],
      free: '',
    },
  };
  function archivePage(s) {
    const a = ARCH[s];
    const stages = `<ol class="gl-stages full" data-design-id="ARCH-STAGES">${STAGES.map(([t, d], i) => `<li class="${i < a.stage ? 'done' : ''} ${i === a.stage ? 'cur' : ''} ${i === 3 ? 'gl-restore' : ''}" ${i === a.stage ? 'aria-current="step"' : ''}><b>${i < a.stage ? '✓' : i + 1}</b><span><strong>${t}</strong><small>${d}</small></span></li>`).join('')}</ol>`;
    const status = `<div class="gl-astatus full" data-design-id="ARCH-STATUS">${a.status.map(([t, k]) => (k === 'off' ? C.st(t, 'off') : k === 'wait' ? C.st(t, 'wait') : C.st(t))).join('')}</div>`;
    const attn = a.attn ? C.attn({ title: '移动硬盘「T7-归档-01」上少了 3 个文件', text: '10月22日读回核对时发现：output/v1 里有 3 个成片不在硬盘上。补拷以后会再核对一次；在那之前这件作品不能冷归档。', actions: C.btn('补拷这 3 个', { pri: true, toast: '把少的 3 个文件补拷到 T7-归档-01，再读回来核对' }) + C.btn('看是哪 3 个', { toast: '列出 output/v1 里不在硬盘上的 3 个文件' }), id: 'ARCH-MISSING' }) : '';
    const copies = `<section class="pnl" data-design-id="ARCH-COPIES"><div class="pnl-h"><h3>副本</h3>${C.link('管理去处', { toast: '去处在「设置与诊断 › 存放位置 › 归档去处」里登记' })}</div><ul class="rows">${a.copies.map(([ic, name, role, size, check, st, act]) => `<li><span class="dx-tile">${GI[ic]}</span><div><b data-design-data>${esc(name)}</b><small>${role}${size ? ` · <span data-design-data>${esc(size)}</span>` : ''}</small></div><span class="end">${st === 'ok' ? C.st(check) : st === 'bad' ? C.st(check, 'bad') : C.st(check, 'off')}${act}</span></li>`).join('')}</ul><div class="pnl-f"><p>副本核对通过只说明那一份是完整的；冷归档要两份都通过，再移走 Mac 上的原始素材。</p></div></section>`;
    const conds = `<section class="pnl" data-design-id="ARCH-CONDS"><div class="pnl-h"><h3>冷归档前还差什么</h3><span class="gl-condn" data-design-data>${a.conds.filter(c => c[1] === 'ok').length} / ${a.conds.length}</span></div><div class="pnl-b"><ul class="chk gl-conds">${a.conds.map(([t, k, v]) => `<li class="${k === 'fail' ? 'fail' : k === 'todo' ? 'gl-todo' : ''}">${t}<span data-design-data>${esc(v)}</span></li>`).join('')}</ul></div><div class="pnl-f gl-keep"><p>Mac 上会一直留着：索引卡、素材库卡片、精选副本、成片。移走的只有原始素材。</p></div></section>`;
    const free = a.free ? `<p class="howto full" data-design-id="ARCH-FREE">${a.free}</p>` : `<div class="gl-ready full" data-design-id="ARCH-READY"><div><strong>腾出 Mac 上的 ${D('38.2 GB')}</strong><p>先列出要从 Mac 移走的 ${D('1,031')} 个原始文件，以及它们在两份副本里的位置；你核对后再点一次，才移到系统废纸篓。</p></div>${C.btn('腾出 38.2 GB…', { pri: true, toast: '打开冷归档计划：逐项列出要移走的文件和两份副本里的位置' })}</div>`;
    return C.head({ eyebrow: '保存与归档', title: a.head[0], lede: a.head[1], id: 'ARCH-HEAD' }) + status + stages + attn + `<div class="gl-arch full">${copies}${conds}</div>` + free;
  }
  reg('archive', {
    group: '作品侧页', name: '保存与归档', nav: 'projects', piece: { tab: 'archive' },
    states: [['active', '活动期 · 硬盘还没拷'], ['cooling', '冷却期 · 副本少了文件'], ['ready', '条件都齐了']],
    crumb: s => `<button data-go="projects">项目</button>·${D(ARCH[s].project)}`,
    title: s => D(ARCH[s].piece),
    sub: s => D(ARCH[s].date),
    actions: s => (s === 'active' ? playBtn : '<button class="btn btn--play" data-toast="打开已出的成片">看已出的成片</button>'),
    render: archivePage,
  });
})();
