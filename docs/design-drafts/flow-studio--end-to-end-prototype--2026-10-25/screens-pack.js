// 包装素材（作品侧页）：标题卡、数据图、下三分之一字条、章节卡这类 10 秒以内的短动画。
// 每一段是 AI 写的一段 HTML 动画代码（window.seekFrame），在本机逐帧渲染，导出成片或带透明通道的叠加层，你自己放进剪辑软件。
// 依据：docs/hyperframes-packaging-checks.md（验收项）、docs/editing-and-hyperframes.md（放哪、怎么进剪辑）、
//       scripts/video_render/README.md（渲染约定：seekFrame、固定字体、不读外部资源）。
// 预览里跑的就是下面这几段代码本身；数字和文字是设计数据（D() 标出），不是正式结果。
(function () {
  'use strict';
  const { reg, C, ctx } = PCOS;
  const { esc, D, img, SHOTS, SEL } = ctx;
  const s1 = t => (Math.round(t * 10) / 10).toFixed(1);
  const frameOf = s => ctx.frameOf(s);
  const find = word => SHOTS.find(s => (s.src || '').includes(word)) || null;
  const SHEET = find('成绩表');
  const START = SEL[0] || SHOTS[0] || null;
  const SPORT = SHOTS.find(s => s.scene === 'sports-meet' && s.status === 'selected') || SHOTS[0] || null;
  const FINISH = find('终点') || SPORT;

  // ---------- AI 写的三段代码（设计数据） ----------
  const HEAD = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="color-scheme" content="dark"><style>`;
  const EASE = 'const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);';
  // 片头标题卡（透明叠加层）：标题推出来以后一直停着，没有清场 —— 最后一帧不透明，检查没过
  const titleCode = `${HEAD}
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent;color:#fff;font-family:"STHeiti","Heiti SC","PingFang SC",sans-serif}
.box{position:absolute;left:0;right:0;top:600px;text-align:center}
.t{font-size:150px;letter-spacing:12px;text-shadow:0 6px 30px #0009}
.line{width:0;height:6px;background:#4FB3BD;margin:34px auto 0}
.s{font-size:54px;margin-top:26px;letter-spacing:8px;text-shadow:0 4px 18px #0009}
</style></head><body>
<div class="box"><div class="t" id="t">奔赴兰州</div><div class="line" id="l"></div><div class="s" id="s">2026 · 春 · 校运会</div></div>
<script>
const D = 3.0;
${EASE}
const $ = id => document.getElementById(id);
window.seekFrame = (frame, fps) => {
  const t = frame / fps;
  const a = ease(t / 0.5), b = ease((t - 0.2) / 0.5);
  $('t').style.opacity = a; $('t').style.transform = 'translateY(' + (1 - a) * 40 + 'px)';
  $('l').style.width = 360 * ease((t - 0.3) / 0.5) + 'px';
  $('s').style.opacity = b;
  // 推出来以后停在完整画面上，直到 D
};
window.seekFrame(0, 30);
<\/script></body></html>`;
  // 400 米成绩数据图（成片）：框和轴 → 参考线 → 今年的条长出来、数字跳到成绩停住 → 注释
  const chartCode = (me, last = 61.2) => `${HEAD}
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#0F1A1C;color:#F2F4F3;font-family:"STHeiti","Heiti SC","PingFang SC",sans-serif}
.k{position:absolute;left:84px;top:300px;font-size:52px;color:#9FB3B5}
.big{position:absolute;left:84px;top:380px;font-size:220px;line-height:1}
.big small{font-size:72px;margin-left:16px}
.frame{position:absolute;left:84px;right:84px;top:760px;height:420px;border-left:4px solid #3A4B4D;border-bottom:4px solid #3A4B4D;opacity:0}
.bar{position:absolute;left:88px;border-radius:0 12px 12px 0;width:0;overflow:hidden;white-space:nowrap}
.bar b{position:absolute;left:24px;font-size:42px;font-weight:400}
.ref{top:820px;height:84px;background:#3A4B4D}.ref b{top:18px}
.me{top:960px;height:120px;background:#4FB3BD;color:#071719}.me b{top:34px}
.note{position:absolute;top:1110px;font-size:48px;color:#F2C46B;opacity:0}
.src{position:absolute;left:84px;top:1250px;font-size:34px;color:#7D8C8E}
</style></head><body>
<div class="k">400 米决赛</div>
<div class="big"><span id="n">0.0</span><small>秒</small></div>
<div class="frame" id="frame"></div>
<div class="bar ref" id="ref"><b>去年 ${last} 秒</b></div>
<div class="bar me" id="me"><b>今年</b></div>
<div class="note" id="note">快了 ${s1(last - me)} 秒</div>
<div class="src">来源：校运会成绩表</div>
<script>
const D = 6.0;
const ME = ${me}, LAST = ${last}, FULL = 900;
${EASE}
const $ = id => document.getElementById(id);
window.seekFrame = (frame, fps) => {
  const t = frame / fps;
  $('frame').style.opacity = ease(t / 0.4);
  $('ref').style.width = FULL * ease((t - 0.4) / 0.4) + 'px';
  const k = ease((t - 0.8) / 1.4);
  $('me').style.width = FULL * ME / LAST * k + 'px';
  $('n').textContent = (ME * k).toFixed(1);
  $('note').style.left = (FULL * ME / LAST - 260) + 'px';
  $('note').style.opacity = ease((t - 2.2) / 0.4);
};
window.seekFrame(0, 30);
<\/script></body></html>`;
  // 下三分之一字条（透明叠加层）：滑进来、停住、滑出去，首末帧都是空的
  const lowerCode = `${HEAD}
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent;color:#fff;font-family:"STHeiti","Heiti SC","PingFang SC",sans-serif}
.bar{position:absolute;left:72px;top:1250px;height:150px;width:0;overflow:hidden;background:#0D1314e6;border-left:10px solid #4FB3BD;border-radius:0 14px 14px 0}
.bar b{position:absolute;left:44px;top:22px;font-size:56px;font-weight:400;white-space:nowrap}
.bar small{position:absolute;left:44px;top:92px;font-size:34px;color:#B0BEBF;white-space:nowrap}
</style></head><body>
<div class="bar" id="bar"><b id="t">兰州大学 · 春季校运会</b><small id="s">2026 年 5 月 14 日 · 榆中校区</small></div>
<script>
const D = 4.0;
${EASE}
const $ = id => document.getElementById(id);
window.seekFrame = (frame, fps) => {
  const t = frame / fps;
  const open = ease(t / 0.5) * (1 - ease((t - 3.4) / 0.5));
  $('bar').style.width = 780 * open + 'px';
  $('t').style.opacity = ease((t - 0.25) / 0.3) * (1 - ease((t - 3.3) / 0.3));
  $('s').style.opacity = ease((t - 0.4) / 0.3) * (1 - ease((t - 3.3) / 0.3));
};
window.seekFrame(0, 30);
<\/script></body></html>`;

  // ---------- 三段包装素材（review 状态） ----------
  const ITEMS = [
    {
      key: 'title', name: '片头标题卡', kind: '透明叠加层', D: 3.0, where: '叠在第 1 个镜头上 · 画面中间', bg: START, code: titleCode, at: 1,
      status: ['没过检查', 'bad'],
      checks: [['文字和来源一致', 'ok', '标题用作品名'], ['首末帧全透明', 'fail', '最后一帧还有字'], ['正常速度读得完', 'ok', '4 个字 · 停 2.3 秒'], ['一个主动作', 'ok', '标题从下往上推出']],
      issue: () => C.attn({ tone: 'cut', title: '最后一帧不是全透明', text: '标题推出来以后一直停着，没有清场。叠到第 1 个镜头上，切到第 2 个镜头时字会突然消失。拖到最后一帧，切到「只看透明部分」能看到。', actions: C.btn('我自己看', { cls: 'btn--sm', id: 'PACK-INSPECT' }).replace('<button ', '<button data-pk-inspect ') }),
      ai: '最后 0.5 秒把标题和横线一起淡出，最后一帧全透明', exportOk: false, exportWhy: '没过检查，不能导出',
    },
    {
      key: 'chart', name: '400 米成绩数据图', kind: '成片', D: 6.0, where: '接在第 18 个镜头（终点冲刺）后面', bg: null, code: chartCode(58.3), at: 0.55,
      status: ['要你核对', 'wait'],
      checks: [['数字和来源一致', 'unk', '58.3 · 来源写 58.8'], ['正常速度读得完', 'ok', '3 行 · 停 3.8 秒'], ['一个主动作', 'ok', '今年的条长出来'], ['数字跳动后停住', 'ok', '1.4 秒后停住'], ['图表按顺序出现', 'ok', '框和轴 → 参考线 → 数据 → 注释']],
      issue: () => `<div class="attention pk-issue" role="alert" data-design-id="PACK-SOURCE"><span class="pk-src">${img(frameOf(SHEET), '校运会成绩表')}</span><div><strong>数字和来源对不上：画面写 ${D('58.3')} 秒，成绩表照片里是 ${D('58.8')} 秒</strong><p>来源是这件作品里的「校运会成绩表」照片，第 3 行。改成 58.8 以后，「快了 2.9 秒」也会跟着变成「快了 2.4 秒」。</p></div><div class="actions">${C.btn('照片看错了，保留 58.3', { cls: 'btn--sm', toast: '保留 58.3 秒，来源一栏记下「按你核对的」' })}${C.btn('改成 58.8 秒', { cls: 'btn--sm', pri: true, toast: '数字改成 58.8 秒，注释改成「快了 2.4 秒」；只改数字，不用 AI' })}</div></div>`,
      ai: '', exportOk: false, exportWhy: '核对完数字才能导出',
    },
    {
      key: 'lower', name: '下三分之一字条', kind: '透明叠加层', D: 4.0, where: '叠在第 9 个镜头（进校运会）上 · 画面下方', bg: SPORT, code: lowerCode, at: 0.5,
      status: ['通过检查', ''],
      checks: [['文字和来源一致', 'ok', '日期、地点来自拍摄信息'], ['首末帧全透明', 'ok', '首帧、末帧都是空的'], ['正常速度读得完', 'ok', '2 行 · 停 2.8 秒'], ['一个主动作', 'ok', '字条从左滑进来']],
      issue: () => '', ai: '', exportOk: true,
    },
  ];

  const overlay = it => it.kind === '透明叠加层';
  // 预览台：9:16，透明叠加层叠在真实镜头上，可以切到棋盘格只看透明部分
  const stage = it => `<div class="pk-stage" data-bg="${overlay(it) ? 'photo' : 'none'}" data-design-id="PACK-STAGE">${overlay(it) ? img(frameOf(it.bg)) : ''}<div class="pk-anim" data-d="${it.D}"><iframe srcdoc="${esc(it.code)}" title="${esc(it.name)}预览" tabindex="-1"></iframe></div></div>`;
  const scrub = it => `<div class="pk-scrub" data-design-id="PACK-SCRUB"><input type="range" min="0" max="${Math.round(it.D * 30)}" value="${Math.round(it.D * 30 * it.at)}" aria-label="拖动看每一帧" data-pk-range><div class="pk-scrub-row"><button class="btn btn--sm" data-pk-play>播放</button><span class="mono" data-pk-time data-design-data>${s1(it.D * it.at)} / ${s1(it.D)} 秒</span></div></div>${overlay(it) ? `<div class="seg pk-bgseg" data-design-id="PACK-BG"><button aria-pressed="true" data-pk-bg="photo">叠在画面上</button><button aria-pressed="false" data-pk-bg="checker">只看透明部分</button></div>` : ''}`;
  const codeBox = it => `<details class="pk-code" data-design-id="PACK-CODE"><summary>看代码 <span data-design-data>${it.code.length.toLocaleString()} 字符</span></summary><pre><code>${esc(it.code)}</code></pre></details>`;
  const aiBox = it => `<div class="pk-ai" data-design-id="PACK-AI"><label for="pk-ai-${it.key}">要怎么改</label><textarea id="pk-ai-${it.key}" rows="2" placeholder="写一句要怎么改，例如：标题再大一点，停久一点">${esc(it.ai)}</textarea><button class="btn btn--sm ${it.ai ? 'btn--pri' : ''}" data-toast="AI 在改这段代码。改好出一个候选，你看过才替换">让 AI 改</button><small>只改这一段的代码；改好出一个候选，你看过才替换。</small></div>`;

  function card(it) {
    return `<section class="pnl full pk-card" data-pk-card data-design-id="PACK-ITEM"><div class="pk-grid"><div class="pk-left">${stage(it)}${scrub(it)}</div><div class="pk-mid"><header><div><h3>${D(it.name)}</h3><p data-design-data>${it.kind} · ${s1(it.D)} 秒 · ${esc(it.where)}</p></div>${C.st(it.status[0], it.status[1])}</header>${it.issue()}<h4>导出前的检查</h4>${C.checks(it.checks)}</div><div class="pk-right">${aiBox(it)}${codeBox(it)}<div class="pk-export">${C.btn('导出', { pri: it.exportOk, disabled: !it.exportOk, toast: `导出到这件作品的成片文件夹：${it.name}${overlay(it) ? '.mov（带透明通道）' : '.mp4'}` })}${it.exportOk ? `<small>导出成${overlay(it) ? '带透明通道的 MOV' : 'MP4'}，放进剪辑软件要你自己拖到时间线上。</small>` : `<small>${it.exportWhy}</small>`}</div></div></div></section>`;
  }

  function review() {
    return C.head({ eyebrow: '包装素材', title: '3 段包装素材，1 段没过检查，1 段要你核对数字', lede: '标题卡、数据图、字条这类 10 秒以内的短动画，由 AI 写代码，在本机逐帧渲染。过了检查才能导出到这件作品的成片文件夹，再由你放进剪辑软件。', actions: C.btn('组件库', { toast: '组件库在素材库 › 包装组件：做过、确认会复用的动画' }) + C.btn('新做一段', { pri: true, go: 'pack', s: 'new' }), id: 'PACK-HEAD' })
      + ITEMS.map(card).join('')
      + C.statusline('Kdenlive 草稿里不会自动加包装素材：导出以后，在剪辑软件里拖到对应镜头上。', '', 'PACK-NOTE');
  }

  // ---------- 新做一段 ----------
  const TYPES = [['标题卡', '片头、片名'], ['数据图', '一个数字或一组对比'], ['下三分之一字条', '地点、人名、时间'], ['章节卡', '段落之间的过渡'], ['信息卡', '一条要点'], ['角标', '固定在角落的小标识']];
  function fresh() {
    const pick = [SHEET, find('计时') || SPORT, FINISH].filter(Boolean);
    return C.head({ eyebrow: '包装素材 · 新做一段', title: '新做一段包装素材', lede: '一段只说一件事，10 秒以内。说清楚要说什么、数字从哪来，AI 先定画法再写代码，写完自动检查。', actions: C.btn('取消', { go: 'pack', s: 'review' }), id: 'PACK-NEW-HEAD' })
      + `<div class="cols"><div class="stack">
        <section class="pnl" data-design-id="PACK-NEW-TYPE"><div class="pnl-h"><h3>做哪一种</h3></div><div class="pnl-b pk-types" role="radiogroup" aria-label="包装素材的种类">${TYPES.map(([t, d], i) => `<button role="radio" aria-checked="${i === 1}" data-pk-radio><b>${t}</b><small>${d}</small></button>`).join('')}</div></section>
        <section class="pnl" data-design-id="PACK-NEW-SAY"><div class="pnl-h"><h3>这一段要说什么</h3><p>一句话就够</p></div><div class="pnl-b stack"><div class="pk-textarea" contenteditable="true" data-design-data>今年 400 米决赛跑了 58.8 秒，比去年快了 2.4 秒。</div><small>画面上的字是要点，不把这句话整句写上去。</small></div></section>
        <section class="pnl" data-design-id="PACK-NEW-SOURCE"><div class="pnl-h"><h3>数字从哪来</h3><p>画面上的数字都要有来源</p></div><div class="pnl-b stack"><div class="pk-srcpick" role="radiogroup" aria-label="选一张照片">${pick.map((s, i) => `<button role="radio" aria-checked="${i === 0}" data-pk-radio><span>${img(frameOf(s))}</span><small data-design-data>${esc(s && s.src ? s.src.split('/').pop().replace(/\.[^.]+$/, '') : '这件作品里的照片')}</small></button>`).join('')}</div><div class="kv"><span>AI 从照片里读出</span><strong data-design-data>今年 58.8 秒 · 第 3 行</strong></div><div class="kv"><span>去年的成绩</span><strong data-design-data>61.2 秒 · 你填的</strong></div>${C.link('不用照片，自己填数字', { toast: '改成手动填：今年、去年两个成绩' })}</div></section>
        <section class="pnl" data-design-id="PACK-NEW-OUT"><div class="pnl-h"><h3>出成什么、放在哪</h3></div><div class="pnl-b pk-out"><div class="seg pk-seg2" data-design-id="PACK-NEW-FORM"><button aria-pressed="true" data-pk-press>成片</button><button aria-pressed="false" data-pk-press>透明叠加层</button></div><div class="kv"><span>放在哪</span><strong data-design-data>接在第 18 个镜头（终点冲刺）后面</strong></div><div class="kv"><span>多长</span><strong data-design-data>6 秒 · 最多 10 秒</strong></div></div></section>
      </div><aside class="stack">
        <section class="pnl" data-design-id="PACK-NEW-LIB"><div class="pnl-h"><h3>先看组件库有没有能用的</h3></div><ul class="rows">${[['数字跳动卡', '用过 3 次 · 最近在「400米比赛 · 第一视角」'], ['横向对比条', '用过 1 次 · 两个数比大小']].map(([n, d]) => `<li><span class="pk-comp" aria-hidden="true"><i></i><i></i></span><div><b>${n}</b><small data-design-data>${d}</small></div><span class="end">${C.btn('用这个', { cls: 'btn--sm', toast: `套用「${n}」，换成这次的数字，不用 AI 重写` })}</span></li>`).join('')}</ul></section>
        <section class="pnl" data-design-id="PACK-NEW-GO"><div class="pnl-b stack"><p class="pk-p">没有合适的，就让 AI 写一段新的。读成绩表照片用看图模型（Codex）；写代码用 Claude Code，只发这句话和数字。</p>${C.btn('让 AI 写', { pri: true, go: 'pack', s: 'writing' })}</div></section>
      </aside></div>`;
  }

  // ---------- AI 正在写 ----------
  const STEPS = [['框和轴', 0, 0.4], ['参考线「去年 61.2 秒」', 0.4, 0.8], ['今年的条长出来，数字跳到 58.8 停住', 0.8, 2.2], ['注释「快了 2.4 秒」落在条尾', 2.2, 2.6]];
  function writing() {
    const code = chartCode(58.8).split('\n');
    const shown = code.slice(0, 26).join('\n');
    const pct = v => (100 * v / 6).toFixed(1);
    return C.head({ eyebrow: '包装素材 · AI 在写', title: 'AI 正在写「400 米成绩」数据图', lede: '先定画法，再写代码；写完自动检查，过了才能导出。可以离开这一页，写好会出现在包装素材里。', actions: C.btn('停下', { toast: '停下了。已经写的部分不保留，画法留着' }), id: 'PACK-WRITE-HEAD' })
      + `<section class="pnl full" data-design-id="PACK-PLAN"><div class="pnl-h"><h3>AI 先定的画法</h3><p>写代码前先写下来，你可以改</p></div><div class="pnl-b stack">
          <div class="kv"><span>唯一的主动作</span><strong>今年的条从 0 长到 58.8 秒的位置，停住</strong></div>
          <div class="pk-order" data-design-id="PACK-ORDER"><small>出现顺序 · 共 6 秒</small>${STEPS.map(([n, a, b], i) => `<div><span>${i + 1} ${n}</span><div class="pk-ol"><i style="left:${pct(a)}%;width:${pct(b - a)}%"></i></div><code>${s1(a)}–${s1(b)} 秒</code></div>`).join('')}<div><span>停在完整画面上</span><div class="pk-ol"><i class="hold" style="left:${pct(2.6)}%;width:${pct(3.4)}%"></i></div><code>2.6–6.0 秒</code></div></div>
          <div class="kv"><span>外观</span><strong class="pk-sw"><i style="background:#0F1A1C"></i>底色 <i style="background:#4FB3BD"></i>今年 <i style="background:#3A4B4D"></i>去年 <i style="background:#F2C46B"></i>注释</strong></div>
          <div class="kv"><span>不用</span><strong>图例、饼图、所有数字一起跳</strong></div>
        </div></section>
      <div class="cols"><div class="stack">
        <section class="pnl" data-design-id="PACK-STREAM"><div class="pnl-h"><h3>代码</h3><p data-design-data>写到第 26 行 · 大约还要 20 秒</p></div><div class="pnl-b"><pre class="pk-stream"><code>${esc(shown)}<i class="pk-caret"></i></code></pre></div></section>
      </div><aside class="stack">
        <section class="pnl" data-design-id="PACK-AFTER"><div class="pnl-h"><h3>写完会检查</h3></div><ul class="rows">${['数字和来源一致', '正常速度读得完', '一个主动作', '数字跳动后停住', '图表按顺序出现'].map(n => `<li><i class="dot"></i><div><small>${n}</small></div></li>`).join('')}</ul></section>
      </aside></div>`;
  }

  // ---------- 预览交互：拖动、播放、切换背景（缩放在脚本里设置，不写内联样式） ----------
  function bind(root) {
    root.querySelectorAll('[data-pk-card]').forEach(cardEl => {
      const box = cardEl.querySelector('.pk-anim'); const f = box && box.querySelector('iframe');
      const range = cardEl.querySelector('[data-pk-range]'); const time = cardEl.querySelector('[data-pk-time]');
      if (!box || !range) return;
      const d = +box.dataset.d;
      const fit = () => { f.style.transform = `scale(${box.clientWidth / 1080})`; };
      const draw = () => { try { f.contentWindow.seekFrame(+range.value, 30); } catch (e) { /* 还没加载完 */ } time.textContent = `${s1(range.value / 30)} / ${s1(d)} 秒`; };
      f.addEventListener('load', () => { fit(); draw(); });
      range.addEventListener('input', draw);
      const play = cardEl.querySelector('[data-pk-play]'); let timer = null;
      play.addEventListener('click', () => {
        if (timer) { clearInterval(timer); timer = null; play.textContent = '播放'; return; }
        if (+range.value >= +range.max) range.value = 0;
        play.textContent = '暂停';
        timer = setInterval(() => { range.value = +range.value + 1; draw(); if (+range.value >= +range.max || !document.body.contains(play)) { clearInterval(timer); timer = null; play.textContent = '播放'; } }, 1000 / 30);
      });
      const setBg = v => { cardEl.querySelector('.pk-stage').dataset.bg = v; cardEl.querySelectorAll('[data-pk-bg]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pkBg === v))); };
      cardEl.querySelectorAll('[data-pk-bg]').forEach(b => b.addEventListener('click', () => setBg(b.dataset.pkBg)));
      const inspect = cardEl.querySelector('[data-pk-inspect]');
      if (inspect) inspect.addEventListener('click', () => { range.value = range.max; draw(); setBg('checker'); });
      window.addEventListener('resize', fit);
      fit();
    });
    root.querySelectorAll('[role="radiogroup"]').forEach(g => g.addEventListener('click', e => { const b = e.target.closest('[data-pk-radio]'); if (!b) return; g.querySelectorAll('[data-pk-radio]').forEach(x => x.setAttribute('aria-checked', String(x === b))); }));
    root.querySelectorAll('.pk-seg2').forEach(g => g.addEventListener('click', e => { const b = e.target.closest('[data-pk-press]'); if (!b) return; g.querySelectorAll('[data-pk-press]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); }));
  }

  reg('pack', {
    group: '作品侧页', name: '包装素材', nav: 'projects', piece: { tab: 'pack' },
    states: [['review', '1 段没过检查'], ['new', '新做一段'], ['writing', 'AI 正在写']],
    actions: () => C.btn('看已出的成片 <span data-design-data>v1 · v2</span>', { cls: 'btn--play', toast: '打开已出的成片 v1、v2' }),
    render: s => (s === 'new' ? fresh() : s === 'writing' ? writing() : review()),
    after: root => bind(root),
  });
})();
