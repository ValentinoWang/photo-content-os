// 直出第 3 步「逐镜动画」：AI 写每一镜的动画代码 → 预览 → 检查 → 改 → 确认 → 只重渲改过的镜。
// 依据：上游 MediaClaw 的 CreationVideoPanel（direct-board、AI 改短、改成不用素材图、候选待确认），
// 本机渲染器 scripts/video_render（seekFrame、逐帧、只重渲失败或改过的镜），
// direct-video-shots 技能的检查项（动画比配音长、读不完、画面停住、口播里没有的数字、渲染硬规则）。
// 预览里跑的是真代码：每一镜是一段带 window.seekFrame 的 HTML，拖动帧滑块就是在逐帧调用它。
(function () {
  'use strict';
  const { reg, C, ctx } = PCOS;
  const { esc, D } = ctx;
  const FPS = 30;

  // ---------- 全片设计（AI 写代码前先定，7 镜都照这个） ----------
  const LOOK = { bg: '#0F1B22', ink: '#E8EEF0', main: '#4FB3BD', acc: '#F2B33D', mute: '#7C8D96', faint: '#2A3A42' };
  const BASE_CSS = `html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:${LOOK.bg};color:${LOOK.ink};font-family:"PingFang SC","Heiti SC",sans-serif}
*{box-sizing:border-box}.hd{position:absolute;left:72px;right:72px;top:92px;display:flex;justify-content:space-between;font-size:40px;color:${LOOK.mute}}
.dots{position:absolute;left:72px;right:72px;top:160px;display:flex;gap:12px}.dots i{flex:1;height:8px;border-radius:4px;background:${LOOK.faint}}.dots i.on{background:${LOOK.main}}
.abs{position:absolute}.big{font-size:132px;font-weight:600;letter-spacing:2px}.mid{font-size:72px}.lab{font-size:44px;color:${LOOK.mute}}.acc{color:${LOOK.acc}}.main{color:${LOOK.main}}`;
  const header = (n, kicker) => `<div data-role="header"><div class="hd"><span>${kicker}</span><span>${String(n).padStart(2, '0')} / 07</span></div><div class="dots">${[1, 2, 3, 4, 5, 6, 7].map(i => `<i class="${i <= n ? 'on' : ''}"></i>`).join('')}</div></div>`;
  const ease = 'const e=x=>x<0?0:x>1?1:1-Math.pow(1-x,3);';
  const page = (n, kicker, D, body, script) => `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
${BASE_CSS}
</style></head>
<body>
${header(n, kicker)}
${body}
<script>
const D = ${D};
${ease}
window.seekFrame = (frame, fps) => {
  const t = frame / fps;
${script}
};
</script>
</body></html>`;

  // ---------- 7 镜的代码（设计数据：按 direct-video-shots 的规矩写的真代码） ----------
  const SHOT_CODE = {
    // 01 原稿：按字数估的 2.4 秒写，标题 1.2 秒才开始出现 —— 配音实测只有 1.6 秒
    '1a': page(1, '平均速度', 2.4,
      `<div class="abs big" id="a" style="left:72px;top:560px">平均速度</div>
<div class="abs big acc" id="ne" style="left:72px;top:760px">≠</div>
<div class="abs big" id="b" style="left:240px;top:760px">速度的平均</div>
<div class="abs lab" id="q" style="left:72px;top:1060px">它们不是一回事</div>`,
      `  const a = document.getElementById('a'), ne = document.getElementById('ne'), b = document.getElementById('b'), q = document.getElementById('q');
  a.style.opacity = e((t - 0.4) / 0.5);
  b.style.opacity = e((t - 1.2) / 0.5);
  ne.style.transform = 'scale(' + (0.4 + 0.6 * e((t - 1.6) / 0.3)) + ')';
  ne.style.opacity = e((t - 1.6) / 0.3);
  q.style.opacity = e((t - 1.9) / 0.4);`),
    // 01 AI 改短后的候选：标题第 0 帧就在，主动作「≠」在 0.2–0.8 秒做完
    '1b': page(1, '平均速度', 1.6,
      `<div class="abs big" id="a" style="left:72px;top:560px">平均速度</div>
<div class="abs big acc" id="ne" style="left:72px;top:760px">≠</div>
<div class="abs big" id="b" style="left:240px;top:760px">速度的平均</div>`,
      `  const ne = document.getElementById('ne'), b = document.getElementById('b');
  b.style.opacity = 0.35 + 0.65 * e(t / 0.3);
  ne.style.transform = 'scale(' + (0.4 + 0.6 * e((t - 0.2) / 0.6)) + ')';
  ne.style.opacity = e((t - 0.2) / 0.4);`),
    2: page(2, '小明上学', 7.2,
      `<svg class="abs" style="left:72px;top:700px" width="936" height="420" viewBox="0 0 936 420">
  <line x1="40" y1="200" x2="468" y2="200" stroke="${LOOK.mute}" stroke-width="18" stroke-linecap="round" id="s1" stroke-dasharray="428" stroke-dashoffset="428"/>
  <line x1="468" y1="200" x2="896" y2="200" stroke="${LOOK.main}" stroke-width="18" stroke-linecap="round" id="s2" stroke-dasharray="428" stroke-dashoffset="428"/>
  <circle id="me" cx="40" cy="200" r="30" fill="${LOOK.ink}"/>
  <text x="254" y="120" font-size="52" fill="${LOOK.mute}" text-anchor="middle" id="l1" opacity="0">每秒 2 米</text>
  <text x="682" y="120" font-size="52" fill="${LOOK.main}" text-anchor="middle" id="l2" opacity="0">每秒 6 米</text>
  <text x="40" y="300" font-size="44" fill="${LOOK.mute}">家</text><text x="896" y="300" font-size="44" fill="${LOOK.mute}" text-anchor="end">学校</text>
</svg>`,
      `  const s1 = document.getElementById('s1'), s2 = document.getElementById('s2'), me = document.getElementById('me');
  s1.setAttribute('stroke-dashoffset', 428 * (1 - e((t - 0.6) / 2.0)));
  document.getElementById('l1').setAttribute('opacity', e((t - 0.8) / 0.5));
  s2.setAttribute('stroke-dashoffset', 428 * (1 - e((t - 3.4) / 1.0)));
  document.getElementById('l2').setAttribute('opacity', e((t - 3.6) / 0.5));
  me.setAttribute('cx', 40 + 428 * e((t - 0.6) / 2.0) + 428 * e((t - 3.4) / 1.0));`),
    3: page(3, '常见答案', 4.8,
      `<div class="abs big" id="ans" style="left:72px;top:700px">4 米每秒</div>
<div class="abs" id="cut" style="left:72px;top:800px;height:14px;width:0;background:${LOOK.acc}"></div>
<div class="abs mid acc" id="no" style="left:72px;top:960px">错了</div>`,
      `  document.getElementById('ans').style.opacity = e((t - 1.5) / 0.3);
  document.getElementById('cut').style.width = (640 * e((t - 2.1) / 0.4)) + 'px';
  document.getElementById('no').style.opacity = e((t - 2.6) / 0.4);`),
    4: page(4, '定义', 4.4,
      `<div class="abs mid" style="left:72px;top:620px" id="l">平均速度</div>
<div class="abs mid main" style="left:72px;top:760px" id="eq">= 总路程</div>
<div class="abs" style="left:72px;top:880px;height:8px;width:600px;background:${LOOK.ink}" id="bar"></div>
<div class="abs mid main" style="left:150px;top:920px" id="den">总时间</div>`,
      `  document.getElementById('eq').style.opacity = e((t - 0.5) / 0.5);
  document.getElementById('bar').style.transform = 'scaleX(' + e((t - 1.4) / 0.4) + ')';
  document.getElementById('bar').style.transformOrigin = 'left';
  document.getElementById('den').style.opacity = e((t - 1.9) / 0.5);`),
    5: page(5, '设全程 1200 米', 8.6,
      `<div class="abs lab" style="left:72px;top:560px">前 600 米</div>
<div class="abs" id="b1" style="left:72px;top:630px;height:96px;width:0;background:${LOOK.mute};border-radius:12px"></div>
<div class="abs mid" id="t1" style="left:72px;top:750px;opacity:0">300 秒 · 5 分钟</div>
<div class="abs lab" style="left:72px;top:940px">后 600 米</div>
<div class="abs" id="b2" style="left:72px;top:1010px;height:96px;width:0;background:${LOOK.main};border-radius:12px"></div>
<div class="abs mid" id="t2" style="left:72px;top:1130px;opacity:0">100 秒</div>`,
      `  document.getElementById('b1').style.width = (900 * e((t - 0.8) / 1.6)) + 'px';
  document.getElementById('t1').style.opacity = e((t - 2.2) / 0.5);
  document.getElementById('b2').style.width = (300 * e((t - 4.6) / 0.8)) + 'px';
  document.getElementById('t2').style.opacity = e((t - 5.2) / 0.5);`),
    6: page(6, '算一下', 6.0,
      `<div class="abs mid" style="left:72px;top:620px" id="f">1200 ÷ 400 =</div>
<div class="abs big acc" style="left:72px;top:760px;font-size:300px;font-variant-numeric:tabular-nums" id="n">0</div>
<div class="abs lab" style="left:72px;top:1140px">米每秒，不是 4</div>`,
      `  document.getElementById('f').style.opacity = e(t / 0.4);
  document.getElementById('n').textContent = Math.min(3, Math.floor(3 * e((t - 0.6) / 1.4) + 0.0001));`),
    7: page(7, '谁说了算', 6.0,
      `<div class="abs lab" style="left:72px;top:600px">总共 400 秒</div>
<div class="abs" style="left:72px;top:680px;width:936px;height:120px;background:${LOOK.faint};border-radius:14px"></div>
<div class="abs" id="slow" style="left:72px;top:680px;height:120px;width:0;background:${LOOK.acc};border-radius:14px 0 0 14px"></div>
<div class="abs" id="fast" style="left:774px;top:680px;height:120px;width:0;background:${LOOK.main};border-radius:0 14px 14px 0"></div>
<div class="abs mid acc" id="say" style="left:72px;top:880px;opacity:0">慢的一段占四分之三</div>`,
      `  document.getElementById('slow').style.width = (702 * e((t - 0.5) / 1.4)) + 'px';
  document.getElementById('fast').style.width = (234 * e((t - 2.0) / 0.6)) + 'px';
  document.getElementById('say').style.opacity = e((t - 2.8) / 0.5);`),
  };
  const codeOf = (n, cand) => SHOT_CODE[n === 1 ? (cand ? '1b' : '1a') : n];

  // ---------- 7 镜：口播、按字数估的时长、配音实测时长 ----------
  const SHOTS = [
    { n: 1, say: '平均速度不是速度的平均。', anim: '标题卡', est: 2.4, real: 1.6, act: '「≠」从小到大落在两行字中间' },
    { n: 2, say: '小明去学校，前一半路程每秒 2 米，后一半每秒 6 米。', anim: '上学路线图', est: 4.7, real: 7.2, act: '路线分两段画出来，人跟着走' },
    { n: 3, say: '很多人脱口而出：平均 4 米每秒。错了。', anim: '「4 米每秒」被划掉', est: 3.5, real: 4.8, act: '一条线划掉「4 米每秒」' },
    { n: 4, say: '平均速度等于总路程除以总时间。', anim: '公式卡', est: 2.9, real: 4.4, act: '公式一项项拼出来' },
    { n: 5, say: '设全程 1200 米：前 600 米用 300 秒，后 600 米用 100 秒。', anim: '两段用时对比条', est: 5.9, real: 8.6, act: '两根时间条先后长出来' },
    { n: 6, say: '1200 除以 400，平均速度是每秒 3 米，不是 4 米。', anim: '1200 ÷ 400 = 3', est: 4.5, real: 6.0, act: '「3」跳到停住' },
    { n: 7, say: '慢的那段花的时间多，所以它说了算。', anim: '时间轴：慢的一段占四分之三', est: 3.3, real: 6.0, act: '时间条里慢的一段先铺满四分之三' },
  ];

  // ---------- 检查（两组：能不能渲染 / 看起来对不对） ----------
  const HARD = ['画布 1080×1920，页眉标好了', '不读网络和外部文件', '不用定时器和随机数', '字幕带（画面最下面五分之一）里没放字', '代码不超过 10 万字'];
  const LOOKS = {
    1: [['fail', 1.6, '动画比配音长', '按字数估的是 2.4 秒，配音实测只有 1.6 秒。「≠」1.6 秒才开始出来，切镜时还没出完，观众只看到两行字。']],
    3: [['warn', 1.5, '一行字读不完', '「4 米每秒」在 1.5 秒出现、2.1 秒就被划掉，在屏上 0.6 秒；按每字 0.2 秒加 0.5 秒算，读完要 1.3 秒。']],
    5: [['warn', 2.2, '口播里没说过的数', '画面写「5 分钟」，口播只说「300 秒」。数一样，但观众要换算一次。']],
    6: [['warn', 2.0, '画面停住太久', '「3」在 2.0 秒停住以后到 6.0 秒都没有变化，停了 4 秒。要是故意停在答案上，标成停顿就不再提醒。']],
  };
  const lvl = n => (LOOKS[n] || []).some(x => x[0] === 'fail') ? 'fail' : (LOOKS[n] || []).length ? 'warn' : 'ok';

  // ---------- 状态 ----------
  // review 主状态：7 镜写好、配音也出来了，检查出 1 镜必须改、3 处提醒
  // code 看代码 · candidate AI 改短候选 · writing AI 正在写 · render-failed 渲染失败 · done 全部渲染好
  const STATES = [['review', '1 镜必须改'], ['code', '看这一镜的代码'], ['candidate', 'AI 改短的候选'], ['writing', 'AI 正在写'], ['render-failed', '第 5 镜渲染失败'], ['done', '全部渲染好']];
  const ui = { sel: 1, tab: 'check', subs: true, frame: null };
  const shotStatus = (s, n) => {
    if (s === 'writing') return n <= 4 ? 'written' : n === 5 ? 'writing' : 'wait';
    if (s === 'done') return 'rendered';
    if (s === 'render-failed') return n === 5 ? 'render-fail' : n === 6 ? 'rendering' : 'rendered';
    if (s === 'candidate' && n === 1) return 'cand';
    return lvl(n) === 'ok' ? 'ok' : lvl(n);
  };
  const STATUS_TXT = { fail: ['必须改', 'bad'], warn: ['有提醒', 'wait'], ok: ['检查通过', ''], cand: ['候选 · 待确认', 'run'], written: ['写好了', ''], writing: ['正在写…', 'run'], wait: ['等着写', 'off'], rendered: ['渲染好了', ''], 'render-fail': ['没渲染成', 'bad'], rendering: ['渲染中 108 / 180 帧', 'run'] };

  // ---------- 预览（iframe 里跑真代码，父页面用 postMessage 让它跳到某一帧） ----------
  const bridge = `<script>addEventListener('message',e=>{if(e.data&&e.data.seek!=null)window.seekFrame(e.data.seek,${FPS});});<\/script>`;
  const srcdoc = code => esc(code.replace('</body>', bridge + '</body>'));
  const stage = (code, id, w, frame, subs, extra = '') => `<div class="cd-stage" style="width:${w}px;height:${Math.round(w * 16 / 9)}px" data-design-id="CODE-PREVIEW">
    <iframe class="cd-frame" data-frame="${frame}" data-stage="${id}" srcdoc="${srcdoc(code)}" style="transform:scale(${w / 1080})" title="第 ${id} 镜预览" tabindex="-1"></iframe>
    ${subs ? `<div class="cd-subband" aria-hidden="true"><span>字幕带</span></div>` : ''}${extra}</div>`;

  // 帧滑块：画出动画长度、配音结束的位置，超出配音的那段标成「会被切掉」
  function scrubber(sh, s, cand) {
    const animD = sh.n === 1 ? (cand ? 1.6 : 2.4) : sh.real;
    const total = Math.max(animD, sh.real);
    const frames = Math.round(total * FPS);
    const f = ui.frame == null ? Math.round(Math.min(animD, sh.real) * 0.85 * FPS) : Math.min(ui.frame, frames);
    const cutPct = sh.real < animD ? (sh.real / total) * 100 : null;
    return `<div class="cd-scrub" data-design-id="CODE-SCRUB">
      <div class="cd-scrub-row">${C.btn('▶', { cls: 'btn--sm cd-play' })}<input type="range" min="0" max="${frames}" value="${f}" data-scrub aria-label="拖到第几帧"><span class="mono" data-readout>${(f / FPS).toFixed(2)} 秒 · 第 ${f} 帧</span></div>
      <div class="cd-lanes"><div class="cd-lane"><span>动画</span><span class="cd-track"><i class="cd-bar" style="width:${(animD / total) * 100}%"></i>${cutPct != null ? `<i class="cd-cutoff" style="left:${cutPct}%;width:${100 - cutPct}%"><b>会被切掉</b></i>` : ''}</span></div><div class="cd-lane"><span>配音</span><span class="cd-track"><i class="cd-bar cd-bar--voice" style="width:${(sh.real / total) * 100}%"></i></span></div></div>
    </div>`;
  }

  // ---------- 右侧：检查 / 代码 / 画面设计 / 版本 ----------
  const TABS = [['check', '检查'], ['code', '代码'], ['plan', '这一镜的画面设计'], ['vers', '版本']];
  function checkTab(sh, s) {
    const items = s === 'candidate' && sh.n === 1 ? [] : (LOOKS[sh.n] || []);
    const looks = items.length ? items.map(([k, t, title, text]) => `<li class="cd-chk cd-chk--${k}" data-design-id="CODE-CHECK-ITEM"><header><b>${title}</b><span class="mono">t = ${t.toFixed(1)} 秒</span></header><p data-design-data>${text}</p>${k === 'fail' ? `<div class="actions">${C.btn('跳到这一帧', { cls: 'btn--sm', toast: '滑块跳到 1.6 秒：配音在这里结束' })}${C.btn('改口播，把这句说长一点', { cls: 'btn--sm', go: 's1' })}</div>` : `<div class="actions">${C.btn('跳到这一帧', { cls: 'btn--sm', toast: `滑块跳到 ${t.toFixed(1)} 秒` })}${C.btn(sh.n === 6 ? '是故意停住的' : '没关系，不改', { cls: 'btn--sm', toast: '这条提醒记下了，不再提' })}</div>`}</li>`).join('')
      : `<li class="cd-chk cd-chk--ok"><header><b>没有发现问题</b></header><p>时长、读不读得完、停住多久、画面上的数都对过了。</p></li>`;
    return `<div class="cd-group"><h4>能不能渲染 <span class="cd-ok">${HARD.length} / ${HARD.length} 通过</span></h4><ul class="cd-hard">${HARD.map(h => `<li>${h}</li>`).join('')}</ul></div>
      <div class="cd-group"><h4>看起来对不对 ${items.length ? `<span class="${lvl(sh.n) === 'fail' ? 'cd-bad' : 'cd-warn'}">${items.length} 条</span>` : '<span class="cd-ok">通过</span>'}</h4><ul class="cd-chks">${looks}</ul></div>
      <div class="cd-ask" data-design-id="CODE-ASK"><label for="cd-ask-in">按你的意见改这一镜</label><div class="row"><input id="cd-ask-in" placeholder="例：t=1.2 秒 · 第二行 · 字太小 → 放大到和第一行一样 · 颜色不动"><button class="btn" data-toast="AI 只改第 ${String(sh.n).padStart(2, '0')} 镜，改好给你一个候选，确认后才替换">让 AI 改</button></div><small>一条一行：什么时候 · 哪里 · 什么问题 → 怎么改 · 哪些不动。AI 只改这一镜，改好是候选，你确认了才替换。</small></div>`;
  }
  // 代码高亮：只分注释、字符串、数字三种颜色，问题行整行标出
  function highlight(code, hot = [], added = []) {
    return code.split('\n').map((line, i) => {
      let h = esc(line)
        .replace(/(\/\/.*$)/, '<i class="cm">$1</i>')
        .replace(/(&#39;[^&]*?&#39;|&quot;[^&]*?&quot;)/g, '<i class="sq">$1</i>')
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '<i class="nu">$1</i>');
      const cls = hot.some(r => r.test(line)) ? ' class="hot"' : added.some(r => r.test(line)) ? ' class="add"' : '';
      return `<span${cls}><em>${i + 1}</em>${h || ' '}</span>`;
    }).join('');
  }
  function codeTab(sh, s) {
    const cand = s === 'candidate' && sh.n === 1;
    const code = codeOf(sh.n, cand);
    const hot = sh.n === 1 && !cand ? [/const D = 2\.4/, /t - 1\.[26]\)/] : [];
    const added = cand ? [/const D = 1\.6/, /t \/ 0\.3/, /t - 0\.2\)/] : [];
    const meta = `<div class="cd-codemeta" data-design-id="CODE-META"><span data-design-data>${code.length.toLocaleString()} 字 · 上限 100,000</span><span>${cand ? 'AI 改短的候选 · 还没确认' : s === 'review' || s === 'code' ? '写好了 · 还没确认' : '已确认 · 渲染前核对没变过'}</span>${C.btn('复制', { cls: 'btn--sm', toast: '代码已复制' })}${C.btn('在编辑器里打开', { cls: 'btn--sm', toast: '用本机默认编辑器打开这一镜的代码；改完回来会重新检查' })}</div>`;
    const diff = cand ? `<div class="cd-diff" data-design-id="CODE-DIFF"><b>AI 改了什么</b><ul><li><s>const D = 2.4</s> → <span>const D = 1.6</span>：按配音实测时长</li><li>「速度的平均」第 0 帧就在，不再等 1.2 秒才淡入</li><li>「≠」改在 0.2–0.8 秒落下，配音结束前 0.8 秒做完</li><li>删掉「它们不是一回事」这一行：1.6 秒里读不完，下一镜会讲</li></ul></div>` : '';
    return meta + diff + `<pre class="cd-code" data-design-id="CODE-SOURCE" tabindex="0">${highlight(code, hot, added)}</pre>`;
  }
  function planTab(sh) {
    return `<dl class="cd-plan" data-design-id="CODE-PLAN"><div><dt>这一镜说的话</dt><dd data-design-data>${esc(sh.say)}</dd></div><div><dt>唯一的主动作</dt><dd data-design-data>${esc(sh.act)}</dd></div><div><dt>观众读到什么</dt><dd data-design-data>${esc(sh.anim)}</dd></div><div><dt>时长</dt><dd><span data-design-data>按字数估 ${sh.est.toFixed(1)} 秒 · 配音实测 ${sh.real.toFixed(1)} 秒</span></dd></div><div><dt>怎么交给下一镜</dt><dd data-design-data>${sh.n === 7 ? '停在「慢的一段占四分之三」上，到结尾至少停 1 秒' : '最后一帧停在完整画面上，下一镜第 0 帧就有主画面'}</dd></div></dl>`;
  }
  function versTab(sh, s) {
    const rows = sh.n === 1
      ? [[s === 'candidate' ? '候选 · AI 改短' : null, '按配音实测 1.6 秒重排', '10/25 21:52'], ['第 2 版 · 现在', '你说「≠ 要更大」，AI 改的', '10/25 21:40'], ['第 1 版', 'AI 按分镜第一次写', '10/25 21:31']].filter(r => r[0])
      : [['第 1 版 · 现在', 'AI 按分镜第一次写', '10/25 21:31']];
    return `<ul class="rows cd-vers" data-design-id="CODE-VERSIONS">${rows.map(([v, why, when], i) => `<li><div><b>${v}</b><small data-design-data>${why} · ${when}</small></div><div class="end">${i ? C.btn('和现在比', { cls: 'btn--sm', toast: '左右两边同时播，代码按行对比' }) + C.btn('回到这一版', { cls: 'btn--sm', toast: '回到这一版要重新确认' }) : ''}</div></li>`).join('')}</ul>`;
  }

  // ---------- 左侧镜头列表 ----------
  function shotList(s) {
    return `<ol class="cd-list" data-design-id="CODE-SHOTS">${SHOTS.map(sh => {
      const st = shotStatus(s, sh.n), [txt, kind] = STATUS_TXT[st];
      const thumb = st === 'wait' || st === 'writing' ? `<span class="cd-thumb cd-thumb--empty">${st === 'writing' ? '写' : ''}</span>` : `<span class="cd-thumb">${stage(codeOf(sh.n, s === 'candidate'), sh.n, 54, Math.round(sh.real * 0.8 * FPS), false)}</span>`;
      return `<li><button class="cd-item ${ui.sel === sh.n && s !== 'done' ? 'is-sel' : ''}" data-shot="${sh.n}" aria-current="${ui.sel === sh.n && s !== 'done'}">${thumb}<span class="cd-item-b"><span class="row"><b class="mono">${String(sh.n).padStart(2, '0')}</b><span class="mono muted" data-design-data>${(s === 'writing' ? sh.est : sh.real).toFixed(1)} 秒</span></span><small data-design-data>${esc(sh.anim)}</small>${C.st(txt, kind)}</span></button></li>`;
    }).join('')}</ol>`;
  }

  // ---------- 全片设计（一行，可展开） ----------
  const lookStrip = () => `<section class="pnl full cd-look" data-design-id="CODE-LOOK"><div class="cd-look-row"><b>全片设计</b><span class="cd-sw"><i style="background:${LOOK.bg}"></i>底色</span><span class="cd-sw"><i style="background:${LOOK.main}"></i>主色 · 图形</span><span class="cd-sw"><i style="background:${LOOK.acc}"></i>强调色 · 只标结论</span><span class="muted">字号 132 / 72 / 44 · 一镜一个主动作，次要动作晚 0.15 秒</span><span class="muted">不用：光晕霓虹、紫蓝渐变、三卡并排、全部同时淡入</span>${C.link('看完整设计', { toast: '展开 AI 写代码前定下的全片设计：外观、主要图形、动作规矩、每镜一行、禁用清单' })}</div></section>`;

  // ---------- 配音时间轴：每镜估算和实测 ----------
  function voiceLane(s) {
    const len = sh => (s === 'writing' ? sh.est : sh.real);
    const tot = SHOTS.reduce((a, x) => a + len(x), 0);
    let acc = 0;
    const segs = SHOTS.map(sh => { const l = acc / tot * 100, w = len(sh) / tot * 100; acc += len(sh); const over = sh.n === 1 && (s === 'review' || s === 'code'); return `<i class="cd-seg ${over ? 'is-over' : ''} ${ui.sel === sh.n && s !== 'done' ? 'is-sel' : ''}" style="left:${l}%;width:${w}%"><b>${String(sh.n).padStart(2, '0')}</b>${over ? '<em>动画比配音长 0.8 秒</em>' : ''}</i>`; }).join('');
    return `<section class="pnl full" data-design-id="CODE-VOICE"><div class="pnl-h"><h3>配音和每一镜<span>${s === 'writing' ? '配音还没合成 · 先按字数估' : `配音 ${ctx.mmss(tot)} · 每镜按实测时长排`}</span></h3><p>${s === 'writing' ? '按字数估时长（字数 ÷ 5.1）；配音合成后按每句实测时长重排' : '配音读得比估算快的镜，动画要跟着改短'}</p></div><div class="pnl-b"><div class="cd-voice">${segs}</div></div></section>`;
  }

  // ---------- 页头和提醒 ----------
  function headOf(s) {
    const H = (title, lede, actions) => C.head({ eyebrow: '第 3 步 · 逐镜动画', title, lede, actions, id: 'CODE-HEAD' });
    if (s === 'writing') return H('AI 正在写第 5 镜的动画代码', '先定了全片设计，再按分镜一镜一镜写。每一镜是一段动画代码，写好就能在这里预览和检查；你确认以后才会渲染。', C.btn('停下来', { toast: '停在第 5 镜；写好的 4 镜留着' }));
    if (s === 'done') return H('7 镜都渲染好了', '每一镜按你确认过的代码在本机逐帧画出来。改了哪一镜，只重渲那一镜。', C.btn('看全片拼图', { toast: '7 镜关键帧拼成一张图，相邻两镜的切点并排看' }) + C.btn('下一步：字幕与声音', { pri: true, go: 's4', s: 'en-too-long' }));
    if (s === 'render-failed') return H('6 镜渲染好了，第 5 镜没渲染成', '每一镜按确认过的代码在本机逐帧画。重试只重渲失败的那一镜，配音不再收费。', C.btn('下一步：字幕与声音', { disabled: true }));
    if (s === 'candidate') return H('第 01 镜：AI 改短了一版，等你看', '只改了第 01 镜的出现时机，口播、配音和其他 6 镜都不动。采用以后要确认，确认了只重渲这一镜。', '');
    return H('AI 写好了 7 镜动画代码，1 镜必须改', '每一镜是一段动画代码，在本机逐帧渲染成画面。先在这里看预览和检查，确认的镜才渲染；改了哪一镜，只重渲那一镜。', C.btn('确认第 02–07 镜并渲染', { toast: '第 02–07 镜确认，开始渲染；第 01 镜改好再确认' }));
  }
  function attnOf(s) {
    if (s === 'review' || s === 'code') return C.attn({ tone: 'cut', title: '第 01 镜动画比配音长，切镜时「≠」还没出来', text: '这一镜按字数估了 2.4 秒，配音实测只有 1.6 秒。可以让 AI 按 1.6 秒改短这一镜的动画，或回去把这句口播说长一点。', actions: C.btn('让 AI 按 1.6 秒改短', { pri: true, go: 's3d', s: 'candidate' }), id: 'CODE-MUSTFIX' });
    if (s === 'candidate') return '';
    if (s === 'render-failed') return C.attn({ tone: 'cut', title: '第 5 镜没渲染成：代码第 3 行要读的「成绩表.jpg」不在这一镜里', text: '本机渲染只读这一镜确认过的素材。可以补上这张图，或让 AI 改成不用这张图、直接画出来。', actions: C.btn('补上这张图', { toast: '从这件作品的素材里选「成绩表.jpg」加进第 5 镜' }) + C.btn('让 AI 改成不用这张图', { pri: true, toast: 'AI 重写第 5 镜：数字直接画出来，不读图；改好是候选，确认后只重渲这一镜' }), id: 'CODE-RENDERFAIL' });
    return '';
  }

  // ---------- 中间 + 右侧：选中的这一镜 ----------
  function detail(s) {
    const sh = SHOTS[ui.sel - 1];
    const st = shotStatus(s, sh.n);
    if (st === 'wait') return `<section class="pnl cd-detail cd-detail--empty" data-design-id="CODE-DETAIL"><div class="pnl-b"><b>第 ${String(sh.n).padStart(2, '0')} 镜还没开始写</b><p class="muted">AI 写完第 5 镜就写它。按字数估 ${sh.est.toFixed(1)} 秒，主动作：${esc(sh.act)}。</p></div></section>`;
    if (st === 'writing') {
      const code = codeOf(5).split('\n').slice(0, 24).join('\n');
      return `<section class="pnl cd-detail" data-design-id="CODE-DETAIL"><div class="pnl-h"><h3>第 05 镜 · 两段用时对比条<span>正在写</span></h3><p>先写主动作：两根时间条先后长出来</p></div><div class="pnl-b"><pre class="cd-code cd-code--live" data-design-id="CODE-STREAM">${highlight(code)}<span class="cd-caret"></span></pre></div></section>`;
    }
    const cand = s === 'candidate' && sh.n === 1;
    const subs = ui.subs;
    const preview = cand
      ? `<div class="cd-pair"><figure>${stage(codeOf(1, false), '1-now', 210, Math.round(1.5 * FPS), subs)}<figcaption>现在 · 2.4 秒</figcaption></figure><figure>${stage(codeOf(1, true), '1-cand', 210, Math.round(1.5 * FPS), subs)}<figcaption class="cd-cand-cap">候选 · 1.6 秒</figcaption></figure></div>`
      : stage(codeOf(sh.n, false), sh.n, 270, null, subs);
    const tab = s === 'code' && ui.tab === 'check' ? 'code' : ui.tab;
    const body = { check: checkTab, code: codeTab, plan: planTab, vers: versTab }[tab](sh, s);
    const candBar = cand ? `<div class="cd-candbar" data-design-id="CODE-CANDIDATE"><p>采用以后第 01 镜换成这一版，还要你确认一次；确认了只重渲这一镜。</p><div class="actions">${C.btn('不要', { go: 's3d', s: 'review' })}${C.btn('按我的意见再改', { toast: '在下面写一条意见，AI 在候选上接着改' })}${C.btn('采用这一版', { pri: true, go: 's3d', s: 'review', toast: '第 01 镜换成候选，等你确认' })}</div></div>` : '';
    return `<section class="pnl cd-detail" data-design-id="CODE-DETAIL"><div class="pnl-h"><h3>第 ${String(sh.n).padStart(2, '0')} 镜 · ${D(sh.anim)}</h3><p data-design-data>${esc(sh.say)}</p></div>
      <div class="cd-detail-b"><div class="cd-preview">${preview}${scrubber(sh, s, cand)}<label class="cd-toggle"><input type="checkbox" data-subs ${subs ? 'checked' : ''}> 显示字幕带</label></div>
      <div class="cd-side">${candBar}<div class="cd-tabs" role="tablist">${TABS.map(([k, label]) => `<button role="tab" data-tab="${k}" aria-selected="${tab === k}">${label}</button>`).join('')}</div><div class="cd-tabbody">${body}</div></div></div></section>`;
  }

  // ---------- 全部渲染好：海报一排 + 切点对比 ----------
  function film(s) {
    if (s !== 'done' && s !== 'render-failed') return '';
    return `<section class="pnl full" data-design-id="CODE-FILM"><div class="pnl-h"><h3>渲染好的画面<span>每镜一张关键帧</span></h3>${s === 'done' ? C.link('看切点对比', { toast: '相邻两镜：前一镜最后 0.2 秒和后一镜开头 0.2 秒并排' }) : ''}</div><div class="pnl-b cd-film">${SHOTS.map(sh => { const st = shotStatus(s, sh.n); return `<figure class="${st === 'render-fail' ? 'is-fail' : ''}">${st === 'render-fail' ? '<span class="cd-thumb cd-thumb--empty">没有画面</span>' : stage(codeOf(sh.n, true), 'f' + sh.n, 96, Math.round(sh.real * 0.9 * FPS), false)}<figcaption><b class="mono">${String(sh.n).padStart(2, '0')}</b> ${C.st(...STATUS_TXT[st])}</figcaption></figure>`; }).join('')}</div></section>`;
  }

  reg('s3d', {
    group: '按脚本做视频', name: '3 逐镜动画（直出）· AI 写代码', nav: 'projects', piece: { tab: 'script', step: 3 }, line: 'direct',
    states: STATES,
    flow: s => (s === 'done'
      ? { notes: [null, '7 镜 · 都配上了', '7 镜都渲染好了', '1 条英文放不下', '还没出片'] }
      : s === 'writing' ? { notes: [null, '7 镜 · 都配上了', 'AI 在写第 5 镜', '等动画', '还没出片'] }
        : { notes: [null, '7 镜 · 都配上了', s === 'render-failed' ? '第 5 镜没渲染成' : '第 01 镜必须改', '等动画渲染好', '还没出片'], warn: [2] }),
    render: s => {
      if (s === 'candidate' || s === 'review') { ui.sel = 1; }
      if (s === 'writing' && ![5].includes(ui.sel)) ui.sel = 5;
      if (s === 'render-failed') ui.sel = 5;
      if (s === 'code') { ui.sel = 1; ui.tab = 'code'; } else if (ui.tab === 'code' && s === 'review') ui.tab = 'check';
      ui.frame = null;
      return headOf(s) + attnOf(s) + lookStrip()
        + `<div class="cd-work full">${shotList(s)}<div class="cd-main">${s === 'done' ? '' : detail(s)}${film(s)}</div></div>`
        + voiceLane(s);
    },
    after: (root, s) => {
      const post = (ifr, f) => { try { ifr.contentWindow.postMessage({ seek: f }, '*'); } catch (e) { /* 预览跳帧失败不影响页面 */ } };
      const seekAll = () => root.querySelectorAll('iframe.cd-frame').forEach(ifr => {
        const f = ifr.dataset.frame === 'null' ? null : +ifr.dataset.frame;
        const go = () => post(ifr, f == null ? Math.round(+(root.querySelector('[data-scrub]')?.value || 30)) : f);
        ifr.addEventListener('load', go); go();
      });
      seekAll();
      const scrub = root.querySelector('[data-scrub]');
      const readout = root.querySelector('[data-readout]');
      const main = () => [...root.querySelectorAll('.cd-preview iframe.cd-frame')];
      const setFrame = f => { ui.frame = f; if (scrub) scrub.value = f; if (readout) readout.textContent = `${(f / FPS).toFixed(2)} 秒 · 第 ${f} 帧`; main().forEach(ifr => post(ifr, f)); };
      scrub?.addEventListener('input', () => setFrame(+scrub.value));
      let timer = null;
      root.querySelector('.cd-play')?.addEventListener('click', e => {
        const b = e.currentTarget;
        if (timer) { clearInterval(timer); timer = null; b.textContent = '▶'; return; }
        b.textContent = '❚❚';
        let f = +scrub.value >= +scrub.max ? 0 : +scrub.value;
        timer = setInterval(() => { f += 1; if (f > +scrub.max) { clearInterval(timer); timer = null; b.textContent = '▶'; return; } setFrame(f); }, 1000 / FPS);
      });
      root.querySelectorAll('[data-shot]').forEach(b => b.addEventListener('click', () => { ui.sel = +b.dataset.shot; rerender(root, s); }));
      root.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => { ui.tab = b.dataset.tab; rerender(root, s, true); }));
      root.querySelector('[data-subs]')?.addEventListener('change', e => { ui.subs = e.target.checked; rerender(root, s, true); });
    },
  });
  // 局部重画：保留步骤条和页头，只换工作区
  function rerender(root, s, keepFrame) {
    const keep = keepFrame ? ui.frame : null;
    const work = root.querySelector('.cd-work');
    const tmp = document.createElement('div');
    tmp.innerHTML = `<div class="cd-work full">${shotList(s)}<div class="cd-main">${s === 'done' ? '' : detail(s)}${film(s)}</div></div>`;
    work.replaceWith(tmp.firstElementChild);
    const voice = root.querySelector('[data-design-id="CODE-VOICE"]');
    const tmp2 = document.createElement('div'); tmp2.innerHTML = voiceLane(s); voice.replaceWith(tmp2.firstElementChild);
    ui.frame = keep;
    PCOS.screens.s3d.after(root, s);
    if (keep != null) { const sc = root.querySelector('[data-scrub]'); if (sc) { sc.value = keep; sc.dispatchEvent(new Event('input')); } }
  }
})();
