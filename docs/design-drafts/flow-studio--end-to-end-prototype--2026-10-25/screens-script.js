// 按脚本做视频：1 写稿 → 2 分镜 → 3 对稿剪辑（口播）/ 逐镜动画（直出）→ 4 字幕与声音 → 5 出片检查。见 SPEC.md 第 1–4 节。
// 依据：写稿的区块、锁定、版本、回滚、只改选中段落、下游「要更新」—— studio/project_store.py、studio/ai_patch.py；
//       分镜按稿配素材、缺的画面单列 —— scripts/generate_storyboard_edl.py（missing_materials）；
//       口播对稿剪辑的对齐率、漏说、重说和静音、复核、动画位置、六项检查 —— studio/static/handoff.js；
//       直出逐镜渲染、只重试失败那一镜 —— docs/video-pipeline-pf2.md；双语字幕 —— docs/direct-video-bilingual-subtitles.md。
// 画面里的数字和句子是设计数据（D() 标出），不是正式结果。
(function () {
  'use strict';
  const { reg, C, ctx } = PCOS;
  const { esc, D, img, SHOTS, ICON } = ctx;

  // ---------- 小工具 ----------
  const hashS = () => new URLSearchParams(location.hash.slice(1)).get('s');
  const mmss = t => { t = Math.max(0, Math.round(t)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); };
  const sec1 = t => (Math.round(t * 10) / 10).toFixed(1);
  // 按场景取第 n 个镜头（设计数据），读不到时返回 null，img() 会画灰块
  const byScene = (scene, n) => { const xs = SHOTS.filter(s => s.scene === scene && s.status !== 'unused' && s.status !== 'rejected'); return xs.length ? xs[n % xs.length] : null; };
  const pic = s => img(ctx.frameOf(s), s ? s.reason : '');
  const lockIc = `<span class="sc-ic" aria-hidden="true">${ICON.lock}</span>`;
  const sparkIc = `<span class="sc-ic" aria-hidden="true">${ICON.sparkle}</span>`;

  // ---------- 两件作品的设计数据 ----------
  const L = {
    spoken: {
      brief: [['平台', '抖音'], ['时长', '约 1 分 30 秒'], ['要记住的那一句', '状态是做出来的，不是等出来的。'], ['给谁看', '断更了、想回来的创作者']],
      ver: 5,
      blocks: [
        { t: '我断更了整整一年。今天不道歉，只拆四句我对自己说过的话。', lock: true },
        { t: '第一句：「等我想清楚再发。」可是想清楚这件事，从来不会自己发生。' },
        { t: '第二句：「发了也没人看。」我翻了后台，断更前最后十条，平均播放八百多。' },
        { t: '第三句：「别人做得比我好。」这句是真的，但它和我发不发，没有关系。' },
        { t: '第四句：「再等等，等状态好一点。」状态是做出来的，不是等出来的。' },
        { t: '所以从今天起，每周一条。做得不好，也先发出来。' },
      ],
      instr: '口语一点，第二段加一个具体例子',
      after: {
        1: '第一句：「等我想清楚再发。」去年三月我写好一条，改了十一遍，最后也没发。想清楚这件事，从来不会自己发生。',
        2: '第二句：「发了也没人看。」我回去翻了后台：断更前最后十条，平均每条也有八百多人看。',
      },
      why: '按你说的改：第 2 段加了一个例子，第 3 段把「平均播放」换成说出口的说法。没选的段落没动。',
      check: '第 2 段的例子是 AI 写的（去年三月、改了十一遍）。采用前确认这是你的真事，不是就改成你自己的经历。',
      versions: [['第 5 版', '你改了结尾', '10/25 21:40'], ['第 4 版', 'AI 改了第 4 段，你采用了', '10/25 21:12'], ['第 3 版', '你锁定了开场', '10/24 22:05'], ['第 2 版', '把粘贴的草稿分成 6 段', '10/24 21:58']],
      dur: '约 1:28',
      affected: '第 4、5、6 镜',
    },
    direct: {
      brief: [['平台', '视频号'], ['时长', '约 1 分钟'], ['要记住的那一句', '平均速度不是速度的平均。'], ['给谁看', '初二学生']],
      ver: 3,
      blocks: [
        { t: '平均速度不是速度的平均。', lock: true },
        { t: '小明去学校，前一半路程每秒 2 米，后一半每秒 6 米。很多人脱口而出：平均 4 米每秒。' },
        { t: '错了。平均速度等于总路程除以总时间。' },
        { t: '设全程 1200 米：前 600 米用 300 秒，后 600 米用 100 秒，一共 400 秒。' },
        { t: '1200 除以 400，平均速度是每秒 3 米，不是 4 米。' },
        { t: '慢的那段花的时间多，所以它说了算。' },
      ],
      instr: '说得更口语，像在跟同学讲',
      after: {
        1: '小明上学，前一半路走着去，每秒 2 米；后一半骑车，每秒 6 米。你是不是想说：平均 4 米每秒？',
        2: '不对。平均速度，要拿总路程，除以总时间。',
      },
      why: '按你说的改：第 2 段换成问句、加了「走着去」「骑车」两个动作，第 3 段拆成短句好念。没选的段落没动。',
      check: '「走着去」「骑车」是 AI 加的情节，分镜第 2 镜的路线图要跟着改。',
      versions: [['第 3 版', '你改了第 5 段的数字', '10/23 16:20'], ['第 2 版', 'AI 改了第 6 段，你采用了', '10/23 15:48'], ['第 1 版', '从上游中台带过来的口播稿', '10/23 15:30']],
      dur: '约 1:02',
      affected: '第 2、3 镜',
    },
  };
  const lineOf = () => (ctx.line === 'direct' ? 'direct' : 'spoken');
  // 还没做到的步骤写中性的话，不预告后面的结果
  const LATER = [null, null, '等分镜配好', '等画面', '还没出片'];

  // ================= 1 写稿 =================
  const lineSwitch = state => `<div class="row sc-line" data-design-id="S1-LINE"><span class="muted">拍法</span><div class="tabs" role="group" aria-label="拍法">${[['spoken', '口播（你出镜说）'], ['direct', '直出（不出镜：配音加动画）']].map(([k, label]) => `<button aria-pressed="${lineOf() === k}" data-go="s1" data-s="${state}" data-line="${k}">${label}</button>`).join('')}</div></div>`;

  const briefRow = (d, empty) => empty
    ? `<section class="pnl sc-brief" data-design-id="S1-BRIEF"><div class="sc-brief-empty"><b>选题说明</b><span>还没写。先写一句「要让人记住的话」，AI 改稿时会照着它。</span>${C.btn('写选题说明', { cls: 'btn--sm', toast: '展开选题说明：平台、时长、要记住的那一句、给谁看' })}</div></section>`
    : `<section class="pnl sc-brief" data-design-id="S1-BRIEF"><div class="sc-brief-h"><b>选题说明</b>${C.link('展开修改', { toast: '展开选题说明。改了它，口播稿、分镜都会标「要更新」' })}</div><dl>${d.brief.map(([k, v]) => `<div><dt>${k}</dt><dd data-design-data>${esc(v)}</dd></div>`).join('')}</dl></section>`;

  function blockRow(b, i, o) {
    const selected = o.selected && o.selected.includes(i);
    const changed = o.diff && o.diff[i] != null;
    const fresh = o.fresh && o.fresh.includes(i);
    const text = changed
      ? `<div class="sc-diff"><del data-design-data>${esc(b.t)}</del><ins data-design-data>${esc(o.diff[i])}</ins></div>`
      : `<p data-design-data>${esc(b.t)}</p>${fresh ? '<small class="sc-fresh">第 6 版刚采用的 AI 改法</small>' : ''}`;
    return `<li class="sc-blk ${selected ? 'is-sel' : ''} ${b.lock ? 'is-lock' : ''}" data-design-id="S1-BLOCK"><label class="sc-check"><input type="checkbox" ${selected ? 'checked' : ''} ${b.lock ? 'disabled' : ''} aria-label="选中第 ${i + 1} 段"></label><span class="sc-no">${i + 1}</span><div class="sc-txt">${text}</div><button class="sc-lock ${b.lock ? 'on' : ''}" aria-label="${b.lock ? '已锁定，点一下解锁' : '锁定这一段'}" data-toast="${b.lock ? '解锁后你和 AI 才能改这一段' : '锁定后 AI 改不了这一段，你自己改也要先解锁'}">${ICON.lock}</button></li>`;
  }

  function editor(d, state) {
    if (state === 'blank') {
      return `<section class="pnl sc-editor" data-design-id="S1-EDITOR"><div class="pnl-h"><h3>口播稿</h3><p>空一行算一段</p></div><div class="sc-paste"><p>把口播稿粘贴进来，或者直接写。</p><small>粘贴后按空行分段，每段都能单独锁定、单独让 AI 改。AI 只改你选中的段落，不替你从头写。</small><div class="actions">${C.btn('从剪贴板粘贴', { pri: true, toast: '读剪贴板里的文字，按空行分段' })}${C.btn('从上游中台带过来', { toast: '上游中台没连上：连上后可以把那边写好的口播稿带过来' })}</div></div></section>`;
    }
    const v = state === 'adopted' ? d.ver + 1 : d.ver;
    const blocks = state === 'adopted' ? d.blocks.map((b, i) => (d.after[i] ? { ...b, t: d.after[i] } : b)) : d.blocks;
    const sel = [1, 2];
    const tool = state === 'ai-proposal'
      ? `<div class="sc-tool" data-design-id="S1-AI-TOOL"><span class="chip chip--ac">已选 2 段</span><div class="sc-instr"><span class="muted">让 AI 怎么改</span><b data-design-data>${esc(d.instr)}</b></div>${C.link('换个说法再改', { toast: '改要求后重新生成，只动第 2、3 段' })}</div>
         <div class="sc-proposal" data-design-id="S1-AI-PROPOSAL">${sparkIc}<div><p data-design-data>${esc(d.why)}</p><p class="sc-warnline" data-design-data>${esc(d.check)}</p></div><div class="actions">${C.btn('不要', { toast: '已放弃这次改法，口播稿还是第 ' + d.ver + ' 版' })}${C.btn('采用这次改法', { pri: true, go: 's1', s: 'adopted' })}</div></div>`
      : `<div class="sc-tool sc-tool--done" data-design-id="S1-SAVED"><span class="chip">第 ${v} 版已保存</span><span class="muted">采用了 AI 对第 2、3 段的改法。旧版本都留着。</span>${C.link('退回第 ' + d.ver + ' 版', { toast: '回到第 ' + d.ver + ' 版会存成第 ' + (v + 1) + ' 版，不删任何历史' })}</div>`;
    return `<section class="pnl sc-editor" data-design-id="S1-EDITOR"><div class="pnl-h"><h3>口播稿<span class="sc-meta" data-design-data>第 ${v} 版 · 6 段 · ${esc(d.dur)}</span></h3><p>锁定的段落 AI 改不了</p></div>${tool}<ol class="sc-blocks">${blocks.map((b, i) => blockRow(b, i, state === 'ai-proposal' ? { selected: sel, diff: d.after } : { fresh: [1, 2] })).join('')}</ol></section>`;
  }

  function s1Rail(d, state) {
    if (state === 'blank') return `<aside class="stack">${C.statusline('写下第一段以后，这里记下每一版，随时能看差别、退回。')}</aside>`;
    const v = state === 'adopted' ? d.ver + 1 : d.ver;
    const versions = (state === 'adopted' ? [[`第 ${v} 版`, '采用了 AI 对第 2、3 段的改法', '10/25 21:52']].concat(d.versions) : d.versions);
    const ver = `<section class="pnl" data-design-id="S1-VERSIONS"><div class="pnl-h"><h3>版本</h3><p>退回会存成新的一版</p></div><ul class="rows sc-vers">${versions.map(([name, what, when], i) => `<li><div><b>${name}${i === 0 ? ' · 现在' : ''}<span class="sc-when" data-design-data>${esc(when)}</span></b><small data-design-data>${esc(what)}</small></div>${i === 0 ? '' : `<div class="end">${C.link('看差别', { toast: '左右对照：' + name + ' 和现在这一版' })}${C.link('回到这一版', { toast: '回到' + name + '会存成新的一版，旧版本都留着' })}</div>`}</li>`).join('')}</ul></section>`;
    const items = [['分镜', state === 'adopted' ? `${d.affected}要按新稿更新` : `${d.affected}会标「要更新」`], ['剪辑方案', '跟着分镜一起更新'], ['成片', '已出的版本保留，标成按旧稿做的']];
    const down = `<section class="pnl" data-design-id="S1-DOWNSTREAM"><div class="pnl-h"><h3>${state === 'adopted' ? '口播稿改了，这些要更新' : '采用以后会影响'}</h3></div><ul class="rows">${items.map(([k, v], i) => `<li><div><b>${k}</b><small data-design-data>${esc(v)}</small></div>${i === 0 && state === 'adopted' ? `<div class="end">${C.st('要更新', 'wait')}</div>` : ''}</li>`).join('')}</ul>${state === 'adopted' ? `<div class="pnl-f"><p>分镜按新稿重配以后，这里的提示自动消失。</p>${C.btn('去分镜', { pri: true, go: 's2', s: 'stale' })}</div>` : ''}</section>`;
    return `<aside class="stack">${ver}${down}</aside>`;
  }

  reg('s1', {
    group: '按脚本做视频', name: '1 写稿', nav: 'projects', piece: { tab: 'script', step: 1 },
    states: [['ai-proposal', '选了两段让 AI 改'], ['blank', '空白稿'], ['adopted', '采用以后']],
    flow: s => (s === 'blank'
      ? { notes: ['还没写', '等稿子写好', '等分镜', '等画面', '还没出片'], done: [false, false, false, false, false] }
      : s === 'adopted' ? { notes: [`口播稿第 ${L[lineOf()].ver + 1} 版`, `${staleSet[lineOf()].length} 镜要更新`, ...LATER.slice(2)], warn: [1] }
        : { notes: [null, lineOf() === 'direct' ? '7 镜 · 缺 1 镜' : null, ...LATER.slice(2)] }),
    render: s => {
      const d = L[lineOf()];
      const head = {
        'ai-proposal': ['AI 改好了第 2、3 段，等你决定', `只改你选中的段落，第 1 段锁着不动。看一遍改法，合适就采用，存成第 ${d.ver + 1} 版。`],
        blank: ['先把口播稿写下来', '这件作品还没有口播稿。写好以后才能排分镜。'],
        adopted: [`口播稿第 ${d.ver + 1} 版已保存`, `分镜里有 ${staleSet[lineOf()].length} 镜是按旧稿配的，要按新稿更新。`],
      }[s];
      return C.head({ eyebrow: '第 1 步 · 写稿', title: head[0], lede: head[1], actions: lineSwitch(s), id: 'S1-HEAD' })
        + `<div class="full">${briefRow(d, s === 'blank')}</div>`
        + `<div class="cols"><div class="stack">${editor(d, s)}</div>${s1Rail(d, s)}</div>`;
    },
  });

  // ================= 2 分镜 =================
  const SB = {
    spoken: [
      { say: '我断更了整整一年。', type: '口播原片', shot: () => byScene('selfie-moments', 1), dur: 4.2 },
      { say: '今天不道歉，只拆四句我对自己说过的话。', type: '讲解动画', anim: '四句话卡片', dur: 5.1 },
      { say: '第一句：「等我想清楚再发。」', type: '素材', shot: () => byScene('travel', 2), dur: 3.6, why: '人站在通道里停住、往前看，对上「想清楚再走」的犹豫。' },
      { say: '可是想清楚这件事，从来不会自己发生。', miss: '素材里没有你在写稿、改稿的画面', dur: 4.8, stale: '去年三月我写好一条，改了十一遍，最后也没发。' },
      { say: '第二句：「发了也没人看。」', type: '口播原片', shot: () => byScene('selfie-moments', 4), dur: 3.0, stale: '第二句：「发了也没人看。」我回去翻了后台：' },
      { say: '我翻了后台，断更前最后十条，平均播放八百多。', type: '讲解动画', anim: '十条播放量柱状图', dur: 6.4, stale: '断更前最后十条，平均每条也有八百多人看。' },
      { say: '第三句：「别人做得比我好。」这句是真的，', miss: '刷手机的 2 段都糊了，体检没通过', dur: 4.4 },
      { say: '第四句：状态是做出来的，不是等出来的。', type: '素材', shot: () => byScene('sports-meet', 1), dur: 5.6, why: '跑道上冲刺的动作，对上「做出来」。' },
      { say: '所以从今天起，每周一条。做得不好，也先发出来。', type: '口播原片', shot: () => byScene('selfie-moments', 5), dur: 4.0 },
    ],
    direct: [
      { say: '平均速度不是速度的平均。', type: '讲解动画', anim: '标题卡', dur: 4.0 },
      { say: '小明去学校，前一半路程每秒 2 米，后一半每秒 6 米。', type: '讲解动画', anim: '上学路线图：两段两种颜色', dur: 7.2, stale: '小明上学，前一半路走着去，每秒 2 米；后一半骑车，每秒 6 米。' },
      { say: '很多人脱口而出：平均 4 米每秒。错了。', type: '讲解动画', anim: '「4 米每秒」被划掉', dur: 4.8, stale: '你是不是想说：平均 4 米每秒？不对。' },
      { say: '平均速度等于总路程除以总时间。', type: '讲解动画', anim: '公式卡', dur: 4.4 },
      { say: '设全程 1200 米：前 600 米用 300 秒，后 600 米用 100 秒。', type: '讲解动画', anim: '两段用时对比条', dur: 8.6 },
      { say: '1200 除以 400，平均速度是每秒 3 米，不是 4 米。', miss: '画面要求还空着：这一镜要画什么，还没定', dur: 6.0 },
      { say: '慢的那段花的时间多，所以它说了算。', type: '讲解动画', anim: '时间轴：慢的一段占四分之三', dur: 6.0 },
    ],
  };
  const typeChip = r => (r.miss ? '' : `<span class="tag">${r.type}</span>`);
  const staleSet = { spoken: [3, 4, 5], direct: [1, 2] };

  function sbPicture(r, line) {
    if (r.miss) return `<div class="sc-pic sc-pic--miss" aria-hidden="true"><span>?</span></div>`;
    if (r.anim) return `<div class="sc-pic sc-pic--anim"><span data-design-data>${esc(r.anim)}</span></div>`;
    return `<div class="sc-pic">${pic(r.shot && r.shot())}</div>`;
  }

  function sbTable(line, state, focus) {
    const rows = SB[line];
    const stale = state === 'stale' ? staleSet[line] : [];
    return `<section class="pnl" data-design-id="S2-TABLE"><div class="pnl-h"><h3>分镜<span class="sc-meta" data-design-data>${rows.length} 镜 · 约 ${mmss(rows.reduce((a, r) => a + r.dur, 0))}</span></h3><p>字幕照这一镜说的话出</p></div>
      <div class="sc-sb" role="table" aria-label="分镜">
        <div class="sc-sb-row sc-sb-head" role="row"><span>镜</span><span>这一镜说的话</span><span>画面</span><span>时长</span><span>状态</span></div>
        ${rows.map((r, i) => {
          const isStale = stale.includes(i);
          const st = isStale ? C.st('要更新', 'wait') : r.miss ? C.st('缺画面', 'wait') : C.st('配上了');
          const say = isStale && r.stale ? `<del data-design-data>${esc(r.say)}</del><ins data-design-data>${esc(r.stale)}</ins>` : `<p data-design-data>${esc(r.say)}</p>`;
          const sub = r.miss ? `<small class="sc-miss" data-design-data>AI 没配上：${esc(r.miss)}</small>` : r.why ? `<small data-design-data>AI：${esc(r.why)}</small>` : r.anim ? `<small>讲解动画 · 在上游中台写好确认</small>` : `<small>口播原片 · 按稿对上的那一段</small>`;
          return `<button class="sc-sb-row ${i === focus ? 'is-cur' : ''} ${r.miss ? 'is-miss' : ''} ${isStale ? 'is-stale' : ''}" role="row" data-toast="选中第 ${i + 1} 镜，右边看它配了什么、为什么" data-design-id="S2-ROW"><span class="sc-n">${String(i + 1).padStart(2, '0')}</span><span class="sc-say">${say}${sub}</span><span class="sc-picc">${sbPicture(r, line)}${typeChip(r)}</span><span class="mono sc-dur" data-design-data>${sec1(r.dur)} 秒</span><span>${st}</span></button>`;
        }).join('')}
      </div></section>`;
  }

  function sbRail(line, state, focus) {
    const r = SB[line][focus];
    if (state === 'stale') {
      return `<aside class="stack"><section class="pnl" data-design-id="S2-RAIL"><div class="pnl-h"><h3>第 ${focus + 1} 镜 · 要更新</h3></div><div class="pnl-b stack"><div class="sc-cmp"><small>按第 ${L[line].ver} 版配的</small><p data-design-data>${esc(r.say)}</p></div><div class="sc-cmp sc-cmp--new"><small>第 ${L[line].ver + 1} 版说的</small><p data-design-data>${esc(r.stale)}</p></div><p class="muted sc-p">重配时 AI 按新的话重新找画面，给你看理由；你确认之前，现在的画面不会被换掉。</p></div></section></aside>`;
    }
    const cands = line === 'spoken'
      ? [byScene('selfie-moments', 2), byScene('travel', 4), byScene('travel', 0)]
      : [];
    const why = ['在拍东西，但不是在写稿', '有人在走，看不出犹豫', '空镜，和这句话没关系'];
    const body = line === 'spoken'
      ? `<p class="muted sc-p">AI 找了最接近的 3 个，都不够好：</p><ul class="sc-cands">${cands.map((s, i) => `<li><span class="sc-thumb">${pic(s)}</span><div><small>AI 看到的</small><p data-design-data>${esc(s ? s.reason : '读不到这个镜头的描述')}</p><small class="sc-miss" data-design-data>对不上：${why[i]}</small></div></li>`).join('')}</ul>`
      : `<p class="muted sc-p">AI 按这句口播拟了一个画面要求。你定了以后，下一步 AI 才按它写这一镜的动画代码：</p><div class="sc-cmp sc-cmp--new"><small>AI 拟的画面要求</small><p data-design-data>「1200 ÷ 400 =」先出现，「3」跳到停住，下面一行小字「米每秒，不是 4」。整镜只让「3」这一个数动。</p></div>`;
    const acts = line === 'spoken'
      ? `${C.btn('去素材库找', { pri: true, go: 'library', s: 'pick' })}${C.btn('改成讲解动画', { toast: '第 4 镜改成讲解动画：到逐镜动画那一步由 AI 写代码' })}${C.btn('写进待拍清单', { toast: '已写进待拍清单：拍一段你在电脑前改稿的画面' })}`
      : `${C.btn('用这个画面要求', { pri: true, toast: '第 6 镜的画面要求定了；下一步 AI 按它写动画代码' })}${C.btn('我自己写', { toast: '在这一行的「画面」里写这一镜要画什么' })}`;
    return `<aside class="stack"><section class="pnl" data-design-id="S2-RAIL"><div class="pnl-h"><h3>第 ${focus + 1} 镜 · 缺画面</h3></div><div class="pnl-b stack"><p class="sc-say-big" data-design-data>「${esc(r.say)}」</p>${body}</div><div class="pnl-f sc-acts">${acts}</div></section></aside>`;
  }

  reg('s2', {
    group: '按脚本做视频', name: '2 分镜', nav: 'projects', piece: { tab: 'script', step: 2 },
    states: [['partial', '缺画面'], ['stale', '稿子改了，要更新']],
    flow: s => (s === 'stale'
      ? { notes: [`口播稿第 ${L[lineOf()].ver + 1} 版`, `${staleSet[lineOf()].length} 镜要更新`, ...LATER.slice(2)], warn: [1] }
      : { notes: [null, lineOf() === 'direct' ? '7 镜 · 缺 1 镜' : null, ...LATER.slice(2)], warn: [1] }),
    render: s => {
      const line = lineOf();
      const rows = SB[line];
      const miss = rows.map((r, i) => [r, i]).filter(([r]) => r.miss);
      const focus = s === 'stale' ? staleSet[line][0] : miss[0][1];
      const n = rows.length - miss.length;
      let head, attn;
      if (s === 'stale') {
        const ids = staleSet[line].map(i => i + 1).join('、');
        head = C.head({ eyebrow: '第 2 步 · 分镜', title: `口播稿改了，第 ${ids} 镜要更新`, lede: `这 ${staleSet[line].length} 镜的话和画面还是按第 ${L[line].ver} 版配的。其余 ${rows.length - staleSet[line].length} 镜没受影响。`, id: 'S2-HEAD' });
        attn = C.attn({ title: `第 ${ids} 镜按旧稿配的`, text: `口播稿第 ${L[line].ver + 1} 版（10/25 21:52）改了第 2、3 段。重配只动这 ${staleSet[line].length} 镜，配好以后你确认了才替换。`, actions: C.btn('先看稿子差别', { go: 's1', s: 'adopted' }) + C.btn(`按新稿重配这 ${staleSet[line].length} 镜`, { pri: true, toast: 'AI 正在按新稿给这几镜重找画面' }), id: 'S2-STALE' });
      } else {
        head = C.head({ eyebrow: '第 2 步 · 分镜', title: `${rows.length} 镜里 ${n} 镜配上了画面，缺 ${miss.length} 镜`, lede: line === 'spoken' ? 'AI 按口播稿一句句去素材里找画面，每一镜写了为什么选它。找不到的不硬凑，单独列出来等你定。' : '直出的每一镜是一段讲解动画：这一步定每镜说什么、画面要表达什么；下一步 AI 按这个写动画代码。画面要求还空着的镜单独列出来。', actions: C.btn('下一步：' + (line === 'direct' ? '逐镜动画' : '对稿剪辑'), { go: line === 'direct' ? 's3d' : 's3' }), id: 'S2-HEAD' });
        attn = C.attn({ title: `还缺 ${miss.length} 个画面：第 ${miss.map(([, i]) => i + 1).join('、')} 镜`, text: line === 'spoken' ? `AI 在素材里没找到对得上的画面，没有硬凑。右边是第 ${miss[0][1] + 1} 镜最接近的几个，和你能怎么补。` : `这一镜还没写画面要求，AI 没法写它的动画代码。可以自己写一句，也可以用 AI 按这句口播拟的，你改了再定。`, actions: C.btn(`先补第 ${miss[0][1] + 1} 镜`, { toast: `已选中第 ${miss[0][1] + 1} 镜，右边选怎么补` }), id: 'S2-MISSING' });
      }
      return head + attn + `<div class="cols"><div class="stack">${sbTable(line, s, focus)}</div>${sbRail(line, s, focus)}</div>`;
    },
  });

  // ================= 3 对稿剪辑（口播） =================
  const SRC = 192; // 原片 3:12
  const CUTS = [[14, 19, 're', '我断更了，呃，我断更了整整一年。'], [27, 30, 'si', ''], [52, 58, 're', '等我想清楚——等我想清楚再发。'], [66, 69, 'si', ''], [88, 96, 're', '断更前最后十条，最后十条的平均……'], [104, 108, 'si', ''], [133, 141, 're', '它和我发不发，没，没有关系。'], [160, 164, 'si', '']];
  const REVIEW = [
    [41, 47, '这个我之前在直播里也提过一次，就是那个……', '稿子里没有这句，听起来是跑题，建议剪掉。', 'cut'],
    [76, 80, '（笑）对，就是这么回事。', '语气词，可以留着当停顿。', 'keep'],
    [117, 124, '其实还有第五句，但是今天先不说。', '稿子里没有第五句，留着会让人等下文。', 'cut'],
    [176, 181, '好，那就这样，拜拜。', '在结尾那句之后，留不留看你习惯。', 'keep'],
  ];
  const ANIMS = [[9, '四句话卡片', '「只拆四句我对自己说过的话」'], [62, '十条播放量柱状图', '「平均播放八百多」']];
  const SEGS = [0, 12, 60, 100, 130, 165];
  const pct = t => (100 * t / SRC).toFixed(2);

  function wave(silences) {
    const n = 180; let bars = '';
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) * SRC / n;
      const quiet = silences.some(([a, b]) => t >= a && t <= b);
      const h = quiet ? 2 : 8 + Math.abs(Math.sin(i * 0.73) * 14 + Math.sin(i * 0.29) * 10 + Math.sin(i * 1.9) * 5);
      bars += `<rect x="${(i * 1000 / n).toFixed(1)}" y="${(30 - h / 2).toFixed(1)}" width="3.2" height="${h.toFixed(1)}" rx="1"/>`;
    }
    return `<svg class="sc-wave" viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true">${bars}</svg>`;
  }

  function timeline(state) {
    const marks = CUTS.map(([a, b, k]) => `<i class="sc-mk sc-mk--${k}" style="left:${pct(a)}%;width:${pct(b - a)}%" title="${k === 're' ? '重说' : '静音'} ${mmss(a)}–${mmss(b)}"></i>`).join('')
      + REVIEW.map(([a, b, , , dec]) => (state === 'clean' ? (dec === 'cut' ? `<i class="sc-mk sc-mk--re" style="left:${pct(a)}%;width:${pct(b - a)}%"></i>` : '') : `<i class="sc-mk sc-mk--rv" style="left:${pct(a)}%;width:${pct(b - a)}%" title="只复核 ${mmss(a)}–${mmss(b)}"></i>`)).join('')
      + ANIMS.map(([t, name]) => `<i class="sc-mk sc-mk--an" style="left:${pct(t)}%" title="动画 ${name}"><b>${name}</b></i>`).join('');
    const segs = SEGS.map((a, i) => `<i style="left:${pct(a)}%;width:${pct((SEGS[i + 1] || SRC) - a)}%">第 ${i + 1} 段</i>`).join('');
    const ticks = [0, 30, 60, 90, 120, 150, 180].map(t => `<i style="left:${pct(t)}%">${mmss(t)}</i>`).join('');
    return `<section class="pnl" data-design-id="S3-TIMELINE"><div class="pnl-h"><h3>建议位置<span class="sc-meta" data-design-data>原片 3:12</span></h3><p>红色是重说，灰色是静音，虚线框只复核，竖线是动画位置</p></div><div class="pnl-b sc-tl"><div class="sc-track"><span>口播稿</span><div class="sc-lane sc-segs">${segs}</div></div><div class="sc-track"><span>原片</span><div class="sc-lane sc-wavelane">${wave(CUTS.filter(c => c[2] === 'si'))}${marks}</div></div><div class="sc-track sc-ruler"><span></span><div class="sc-lane">${ticks}</div></div></div></section>`;
  }

  function reviewList(state) {
    const left = state === 'clean' ? 0 : REVIEW.length;
    return `<section class="pnl" data-design-id="S3-REVIEW"><div class="pnl-h"><h3>稿子外的话<span class="sc-meta" data-design-data data-left>${left ? `还有 ${left} 处要你定` : '都定好了'}</span></h3><p>AI 只给建议，留不留你定</p></div><ul class="rows sc-sugs">${REVIEW.map(([a, b, words, why, dec], i) => `<li data-design-id="S3-REVIEW-ROW"><code class="sc-tc">${mmss(a)}–${mmss(b)}</code><div><p data-design-data>「${esc(words)}」</p><small data-design-data>AI：${esc(why)}</small></div><span class="mono sc-len">${sec1(b - a)} 秒</span><div class="end">${C.btn('听一下', { cls: 'btn--sm', toast: `从 ${mmss(a - 2)} 开始放，前后各多放 2 秒` })}<div class="seg sc-seg2" role="group" aria-label="第 ${i + 1} 处"><button aria-pressed="${state === 'clean' && dec === 'cut'}" data-dec="cut">剪掉</button><button aria-pressed="${state === 'clean' && dec === 'keep'}" data-dec="keep">留着</button></div></div></li>`).join('')}</ul></section>`;
  }

  function autoList() {
    const shown = CUTS.filter(c => c[2] === 're').slice(0, 3);
    return `<section class="pnl" data-design-id="S3-AUTO"><div class="pnl-h"><h3>已按稿剪好<span class="sc-meta" data-design-data>8 处 · 共 0:41</span></h3><p>重说只留一遍，长静音剪掉</p></div><ul class="rows sc-sugs">${shown.map(([a, b, , words]) => `<li><code class="sc-tc">${mmss(a)}–${mmss(b)}</code><div><p data-design-data>「${esc(words)}」</p><small>重说（按稿） · 留后一遍</small></div><span class="mono sc-len">${sec1(b - a)} 秒</span><div class="end">${C.btn('撤回', { cls: 'btn--sm', toast: '这一处不剪了，原片这一段留着' })}</div></li>`).join('')}<li class="sc-more"><div><small>另 5 处：1 处重说、4 处静音</small></div><div class="end">${C.link('展开', { toast: '展开其余 5 处' })}</div></li></ul></section>`;
  }

  function animList() {
    return `<section class="pnl" data-design-id="S3-ANIMS"><div class="pnl-h"><h3>叠讲解动画<span>2 处</span></h3><p>出草稿时叠在对应台词上</p></div><ul class="rows">${ANIMS.map(([t, name, on], i) => `<li class="sc-ovgo" data-go="s3" data-s="overlay"><code class="sc-tc">${mmss(t)}</code><div><b data-design-data>${esc(name)}</b><small data-design-data>叠在${esc(on)}上 · ${i ? '比台词长 2.3 秒' : '放得下'}</small></div><span class="end">${C.btn('放哪、多长', { cls: 'btn--sm', go: 's3', s: 'overlay' })}</span></li>`).join('')}</ul></section>`;
  }

  function s3Rail(state) {
    const s = byScene('selfie-moments', 4);
    return `<aside class="stack"><section class="pnl sc-player" data-design-id="S3-PLAYER"><div class="sc-frame sc-frame--sm">${pic(s)}<i class="sc-anim-tag">动画 · 十条播放量柱状图</i><p class="sc-cap">我翻了后台，断更前最后十条，</p></div><div class="pnl-b"><div class="kv"><span>此刻</span><strong data-design-data>1:02 · 第 3 段</strong></div><div class="kv"><span>原片</span><strong data-design-data>1:02–1:09</strong></div><div class="kv"><span>预计剪后</span><strong data-design-data>${state === 'clean' ? '2:18' : '2:31'}</strong></div><div class="rail-foot">${C.btn('播放剪后的样子', { pri: true, toast: '按现在的剪点从头播，跳过要剪的部分' })}</div></div></section></aside>`;
  }

  // ================= 3 对稿剪辑 · 讲解动画放哪（口播） =================
  // 依据：上游 MediaClaw CreationVideoPanel 的 teach-overlay（三种叠法：右侧小窗 / 全屏切过去 / 左右分屏；
  //       动画比台词长时：加速到台词长度，或让 AI 改短，改短出候选、确认后才替换并只重渲这一段）。
  // 动画是 AI 写的一段 HTML 动画代码（window.seekFrame），预览里直接跑这段代码。
  const OV_LAYOUTS = [['pip', '右侧小窗', '口播画面不动，动画放在右侧小窗'], ['full', '全屏切过去', '这几秒整屏换成动画，口播声音不断'], ['split', '左右分屏', '左边口播，右边动画']];
  const OV = [
    { t: 9, name: '四句话卡片', on: '「只拆四句我对自己说过的话」', anim: 3.6, line: 3.8, layout: 'full' },
    { t: 62, name: '十条播放量柱状图', on: '「平均播放八百多」', anim: 6.4, line: 4.1, layout: 'pip' },
  ];
  // 这段是 AI 写的动画代码本身（设计数据）：十根柱子依次长出来，最后画平均线、数字跳到 812 停住
  const barCode = (D, grow) => `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1000px;height:1000px;overflow:hidden;background:#F3F0E8;color:#1C2A30;font-family:"STHeiti","Heiti SC","PingFang SC",sans-serif}
.t{position:absolute;left:60px;top:52px;font-size:60px}
.bars{position:absolute;left:60px;right:60px;top:200px;height:560px;display:flex;align-items:flex-end;gap:22px}
.bars i{flex:1;height:0;background:#1E5E6A;border-radius:10px 10px 0 0}
.avg{position:absolute;left:46px;right:46px;border-top:7px dashed #D8552A;opacity:0}
.num{position:absolute;right:60px;font-size:92px;color:#D8552A;opacity:0}
.src{position:absolute;left:60px;bottom:48px;font-size:32px;color:#52616A}
</style></head><body>
<div class="t">断更前最后十条</div>
<div class="bars" id="bars"></div><div class="avg" id="avg"></div><div class="num" id="num"></div>
<div class="src">数据：我的抖音后台</div>
<script>
const D = ${D};
const GROW = ${grow};
const V = [640, 1210, 530, 980, 720, 1430, 590, 810, 660, 540];
const AVG = 812, MAX = 1500;
const bars = document.getElementById('bars');
V.forEach(() => bars.appendChild(document.createElement('i')));
const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
window.seekFrame = (frame, fps) => {
  const t = frame / fps;
  [...bars.children].forEach((b, i) => { b.style.height = 560 * V[i] / MAX * ease((t - i * GROW / V.length) / 0.6) + 'px'; });
  const y = 760 - 560 * AVG / MAX;
  const avg = document.getElementById('avg'), num = document.getElementById('num');
  avg.style.top = y + 'px'; avg.style.opacity = ease((t - GROW) / 0.4);
  num.style.top = (y - 124) + 'px'; num.style.opacity = ease((t - GROW) / 0.3);
  num.textContent = '平均 ' + Math.round(AVG * ease((t - GROW) / 1.2));
};
window.seekFrame(0, 30);
<\/script></body></html>`;
  const OV_NOW = { D: 6.4, code: barCode(6.4, 4.0) };
  const OV_AI = { D: 4.0, code: barCode(4.0, 2.0) };
  const ovFrame = (code, D, cls = '') => `<div class="sc-ovanim ${cls}" data-ov-d="${D}"><iframe class="sc-ovif" srcdoc="${esc(code)}" title="讲解动画预览" tabindex="-1"></iframe></div>`;
  const codeBlock = (code, id) => `<details class="sc-code" data-design-id="${id}"><summary>看代码 <span class="sc-meta" data-design-data>${code.length.toLocaleString()} 字符 · 上限 100,000</span></summary><pre><code>${esc(code)}</code></pre></details>`;
  let ovLayout = 'pip';

  function ovList(sel) {
    return `<section class="pnl" data-design-id="S3-OV-LIST"><div class="pnl-h"><h3>讲解动画<span>2 段</span></h3><p>AI 按分镜写的动画代码，在本机逐帧渲染</p></div><ul class="rows">${OV.map((a, i) => {
      const long = a.anim > a.line;
      return `<li class="sc-ovrow ${i === sel ? 'is-sel' : ''}" data-design-id="S3-OV-ROW"><code class="sc-tc">${mmss(a.t)}</code><div><b data-design-data>${esc(a.name)}</b><small data-design-data>叠在${esc(a.on)}上 · ${OV_LAYOUTS.find(l => l[0] === (i === sel ? ovLayout : a.layout))[1]}</small></div><span class="end">${long ? C.st(`比台词长 ${sec1(a.anim - a.line)} 秒`, 'wait') : C.st('放得下')}</span></li>`;
    }).join('')}</ul></section>`;
  }
  // 台词和动画两条长度对比：按这一段的秒数画，不按全片
  function ovBars(a, D) {
    const max = Math.max(D, a.line) + 0.6;
    const w = v => (100 * v / max).toFixed(1);
    return `<div class="sc-ovbars" data-design-id="S3-OV-BARS"><div><span>这句台词</span><div class="sc-ovlane"><i class="sc-ovline" style="width:${w(a.line)}%"><b data-design-data>${sec1(a.line)} 秒</b></i></div></div><div><span>动画</span><div class="sc-ovlane"><i class="sc-ovanimbar ${D > a.line ? 'is-long' : ''}" style="width:${w(D)}%"><b data-design-data>${sec1(D)} 秒</b></i>${D > a.line ? `<i class="sc-ovover" style="left:${w(a.line)}%;width:${w(D - a.line)}%"></i>` : ''}</div></div><p class="sc-ovnext" data-design-data>后一句「第三句：别人做得比我好。」从 1:06 开始</p></div>`;
  }
  function ovLayouts() {
    const s = byScene('selfie-moments', 4);
    return `<div class="sc-ovlayouts" role="radiogroup" aria-label="十条播放量柱状图怎么叠" data-design-id="S3-OV-LAYOUTS">${OV_LAYOUTS.map(([k, t, d]) => `<button role="radio" aria-checked="${ovLayout === k}" data-ovlayout="${k}"><span class="sc-ovthumb sc-ovthumb--${k}">${pic(s)}<i></i></span><b>${t}</b><small>${d}</small></button>`).join('')}</div>`;
  }
  function ovStage(code, D, label) {
    const s = byScene('selfie-moments', 4);
    return `<div class="sc-ovstage-wrap"><div class="sc-ovstage" data-layout="${ovLayout}" data-design-id="S3-OV-STAGE">${pic(s)}${ovFrame(code, D)}<p class="sc-cap">我翻了后台，断更前最后十条，</p></div><small class="sc-ovlabel">${label}</small></div>`;
  }
  function ovScrub(D) {
    const frames = Math.round(D * 30);
    return `<div class="sc-ovscrub" data-design-id="S3-OV-SCRUB"><button class="btn btn--sm" data-ovplay>播放</button><input type="range" min="0" max="1000" value="${Math.round(1000 * 3.2 / D)}" aria-label="拖动看每一帧" data-ovscrub data-base="${D}"><span class="mono" data-ovtime data-design-data>3.2 / ${sec1(D)} 秒</span></div><small class="sc-ovhint">按${D === OV_NOW.D ? '' : '候选的'}动画代码逐帧画出来，和本机渲染用的是同一段代码。共 ${frames} 帧。</small>`;
  }

  function overlayView(s) {
    const a = OV[1];
    const ai = s === 'overlay-ai';
    const head = C.head({ eyebrow: '第 3 步 · 对稿剪辑 · 讲解动画', title: ai ? '十条播放量柱状图：AI 改短的候选，等你确认' : '2 段讲解动画放到口播的哪里', lede: '动画是 AI 按分镜写的代码，在本机逐帧渲染。这里只定动画放哪、多长；叠加精修在剪辑软件里做。', actions: C.btn('回到剪辑建议', { go: 's3', s: 'review' }), id: 'S3-OV-HEAD' });
    const attn = ai
      ? C.attn({ title: '候选 · 待确认：动画改到 4.0 秒', text: 'AI 只改了这段动画的代码：十根柱子 2 秒长完，平均数 1.2 秒跳到 812 停住，最后 0.8 秒停在完整画面上。口播、另一段动画和剪辑建议都不动。确认后只重渲这一段。', actions: C.btn('不要', { go: 's3', s: 'overlay', toast: '候选丢掉了，还是原来 6.4 秒的动画' }) + C.btn('采用', { pri: true, go: 's3', s: 'overlay', toast: '已采用：这段动画按 4.0 秒重新渲染，其余不动' }), id: 'S3-OV-CANDIDATE' })
      : C.attn({ title: `动画 ${sec1(a.anim)} 秒，这句台词只有 ${sec1(a.line)} 秒`, text: '叠上去会多出 2.3 秒，盖住下一句「第三句」的开头。选一种：加速到台词长度（不改代码，整段放快 1.56 倍）；或让 AI 改短（改代码，出一个候选，你看过再定）。', actions: C.btn('加速到台词长度', { toast: '这段动画按 1.56 倍速放，正好 4.1 秒；代码不变' }) + C.btn('让 AI 改短', { pri: true, go: 's3', s: 'overlay-ai' }), id: 'S3-OV-LONG' });
    const detail = `<section class="pnl" data-design-id="S3-OV-DETAIL"><div class="pnl-h"><h3>${D(a.name)}<span class="sc-meta" data-design-data>1:02 · 叠在${esc(a.on)}上</span></h3><p>${ai ? '左边是现在，右边是候选' : '怎么叠'}</p></div><div class="pnl-b stack">${ai ? `<div class="sc-ovcmp">${ovStage(OV_NOW.code, OV_NOW.D, '现在 · 6.4 秒')}${ovStage(OV_AI.code, OV_AI.D, '候选 · 4.0 秒')}</div>${ovScrub(OV_AI.D)}${ovBars(a, OV_AI.D)}` : `${ovLayouts()}${ovBars(a, a.anim)}`}</div></section>`;
    const diff = ai ? `<section class="pnl" data-design-id="S3-OV-DIFF"><div class="pnl-h"><h3>AI 改了哪几行</h3><p>只动了时长和长柱子的速度</p></div><div class="pnl-b"><pre class="sc-diff"><code><i class="del">- const D = 6.4;</i><i class="add">+ const D = 4.0;</i><i class="del">- const GROW = 4;</i><i class="add">+ const GROW = 2;</i></code></pre>${codeBlock(OV_AI.code, 'S3-OV-CODE')}</div></section>` : '';
    const rail = ai ? '' : `<aside class="stack"><section class="pnl sc-player" data-design-id="S3-OV-PREVIEW"><div class="pnl-h"><h3>预览</h3><p data-ovlayout-name>${OV_LAYOUTS.find(l => l[0] === ovLayout)[1]}</p></div><div class="pnl-b stack">${ovStage(OV_NOW.code, OV_NOW.D, '叠在口播 1:02 上')}${ovScrub(OV_NOW.D)}${codeBlock(OV_NOW.code, 'S3-OV-CODE')}</div></section></aside>`;
    return head + attn + (ai ? `<div class="full stack">${detail}${diff}</div>` : `<div class="cols"><div class="stack">${ovList(1)}${detail}</div>${rail}</div>`);
  }

  // 把预览里的动画代码按当前进度画出来；iframe 按容器宽度缩放（脚本里设置，不写内联样式）
  function ovBind(root) {
    const range = root.querySelector('[data-ovscrub]');
    const timeEl = root.querySelector('[data-ovtime]');
    const baseD = range ? +range.dataset.base : OV_NOW.D;
    const fit = () => root.querySelectorAll('.sc-ovanim').forEach(box => { const f = box.querySelector('iframe'); if (f) f.style.transform = `scale(${box.clientWidth / 1000})`; });
    // 一条进度控制所有预览：按同一时刻对比，各自超过自己的时长就停在最后一帧
    const draw = () => {
      const t = (range ? range.value / 1000 : 0.5) * baseD;
      root.querySelectorAll('.sc-ovanim').forEach(box => {
        const f = box.querySelector('iframe');
        try { f.contentWindow.seekFrame(Math.round(Math.min(t, +box.dataset.ovD) * 30), 30); } catch (e) { /* 还没加载完，load 时再画 */ }
      });
      if (timeEl) timeEl.textContent = `${sec1(t)} / ${sec1(baseD)} 秒`;
    };
    root.querySelectorAll('.sc-ovanim iframe').forEach(f => f.addEventListener('load', () => { fit(); draw(); }));
    if (range) range.addEventListener('input', draw);
    const play = root.querySelector('[data-ovplay]');
    let timer = null;
    if (play) play.addEventListener('click', () => {
      if (timer) { clearInterval(timer); timer = null; play.textContent = '播放'; return; }
      if (+range.value >= 1000) range.value = 0;
      play.textContent = '暂停';
      timer = setInterval(() => {
        range.value = Math.min(1000, +range.value + 1000 / (baseD * 30)); draw();
        if (+range.value >= 1000 || !document.body.contains(play)) { clearInterval(timer); timer = null; play.textContent = '播放'; }
      }, 1000 / 30);
    });
    root.querySelectorAll('[data-ovlayout]').forEach(b => b.addEventListener('click', () => {
      ovLayout = b.dataset.ovlayout;
      const name = OV_LAYOUTS.find(l => l[0] === ovLayout)[1];
      root.querySelectorAll('[data-ovlayout]').forEach(x => x.setAttribute('aria-checked', String(x === b)));
      root.querySelectorAll('.sc-ovstage').forEach(st => { st.dataset.layout = ovLayout; });
      const nm = root.querySelector('[data-ovlayout-name]'); if (nm) nm.textContent = name;
      const row = root.querySelector('.sc-ovrow.is-sel small'); if (row) row.textContent = row.textContent.replace(/· [^·]+$/, '· ' + name);
      requestAnimationFrame(() => { fit(); draw(); });
    }));
    fit();
  }

  reg('s3', {
    group: '按脚本做视频', name: '3 对稿剪辑（口播）', nav: 'projects', piece: { tab: 'script', step: 3 }, line: 'spoken',
    states: [['review', '漏说 1 句、4 处要你定'], ['clean', '全部对上'], ['overlay', '讲解动画放哪'], ['overlay-ai', 'AI 改短的候选']],
    flow: s => (s === 'clean' ? { notes: [null, '9 镜 · 都配上了', '12 处都处理好了', ...LATER.slice(3)] } : { notes: [null, '9 镜 · 都配上了', '4 处要你定', ...LATER.slice(3)], warn: [2] }),
    render: s => {
      if (s === 'overlay' || s === 'overlay-ai') return overlayView(s);
      const facts = [['原片', '3:12 · 1080×1920'], ['对齐', '按第 5 版口播稿 · 对齐率 ' + (s === 'clean' ? '100%' : '96.4%')], ['剪辑建议', s === 'clean' ? '12 处 · 都处理好了' : '12 处 · 自动剪 8 · 复核 4'], ['预计剪后', s === 'clean' ? '2:18' : '2:31']];
      const head = s === 'clean'
        ? C.head({ eyebrow: '第 3 步 · 对稿剪辑', title: '稿子每一句都对上了，12 处都处理好了', lede: '8 处重说和静音按稿剪掉，稿子外的 4 处你定了 2 处剪、2 处留。叠动画的 2 处在出草稿时一起放上。', actions: C.btn('下一步：字幕与声音', { pri: true, go: 's4', s: 'spoken' }), id: 'S3-HEAD' })
        : C.head({ eyebrow: '第 3 步 · 对稿剪辑', title: '8 处已按稿剪好，4 处等你定', lede: '本机把原片转写成字，和口播稿一句句对上。重说和长静音按稿剪掉；稿子外的话留不留由你定。', actions: C.btn('下一步：字幕与声音', { go: 's4', s: 'spoken' }), id: 'S3-HEAD' });
      const miss = s === 'clean' ? C.note('口播稿 6 段、19 句都在原片里找到了。', 'S3-ALL-FOUND') : C.attn({ title: '漏说 1 句：「状态是做出来的，不是等出来的。」', text: '口播稿第 5 段这句在原片里没找到，不生成剪点。这句也是选题说明里「要记住的那一句」。核对稿件，或补录这一句后再检查。', actions: C.btn('改稿删掉这句', { go: 's1', s: 'ai-proposal' }) + C.btn('补录后重新检查', { pri: true, toast: '把补录的那段放进素材文件夹，再点这里重新对稿' }), id: 'S3-MISSING' });
      return head + miss
        + `<div class="sc-facts full" data-design-id="S3-FACTS">${facts.map(([k, v]) => `<div><small>${k}</small><b data-design-data>${esc(v)}</b></div>`).join('')}</div>`
        + `<div class="full">${timeline(s)}</div>`
        + `<div class="cols"><div class="stack">${reviewList(s)}${autoList()}${animList()}</div>${s3Rail(s)}</div>`;
    },
    after: (root, s) => {
      if (s === 'overlay' || s === 'overlay-ai') { ovBind(root); return; }
      root.querySelectorAll('.sc-seg2').forEach(g => g.addEventListener('click', e => {
        const b = e.target.closest('button'); if (!b) return;
        g.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        const left = [...root.querySelectorAll('.sc-seg2')].filter(x => !x.querySelector('[aria-pressed="true"]')).length;
        const tag = root.querySelector('[data-left]'); if (tag) tag.textContent = left ? `还有 ${left} 处要你定` : '都定好了';
      }));
    },
  });

  // 3 逐镜动画（直出）在 screens-code.js：AI 写代码的工作台。

  // ================= 4 字幕与声音 =================
  // 直出：中文按每行 14 字、最多两行切；英文逐条跟在中文下方，放不下就报出来，不截断
  const CUES_D = [
    [1, 0, 48, '平均速度不是速度的平均。', 'Average speed isn\'t the average of speeds.'],
    [2, 48, 150, '小明去学校，前一半路程', 'Xiao Ming walks to school: the first half'],
    [3, 150, 264, '每秒 2 米，后一半每秒 6 米。', 'at 2 m/s, the second half at 6 m/s.'],
    [4, 264, 330, '很多人脱口而出：', 'Many people blurt out:'],
    [5, 330, 408, '平均 4 米每秒。错了。', '"4 m/s on average." Wrong.'],
    ['6–11', 408, 798, '', ''],
    [12, 798, 870, '1200 除以 400，', '1,200 divided by 400'],
    [13, 870, 978, '平均速度是每秒 3 米，不是 4 米。', 'the average speed is 3 m/s, not 4.'],
    [14, 978, 1158, '慢的那段花的时间多，\n所以它说了算。', 'The slow part takes up more of the time, so it has the bigger say in the overall average.'],
  ];
  const CUES_S = [
    [1, '0:00.4', '0:03.1', '我断更了整整一年。'],
    [2, '0:03.1', '0:06.8', '今天不道歉，\n只拆四句我对自己说过的话。'],
    [3, '0:07.2', '0:09.9', '第一句：「等我想清楚再发。」'],
    [4, '0:10.3', '0:13.6', '可是想清楚这件事，\n从来不会自己发生。'],
    [5, '0:14.0', '0:16.2', '第二句：「发了也没人看。」'],
    ['6–46', '0:16.2', '2:31.0', ''],
  ];
  const br = t => esc(t).replace(/\n/g, '<br>');

  function cueTable(kind, state) {
    if (kind === 'spoken') {
      return `<section class="pnl" data-design-id="S4-CUES"><div class="pnl-h"><h3>字幕<span class="sc-meta" data-design-data>46 条 · 中文</span></h3><p>本机转写，按逐字时间对齐</p></div><div class="sc-cues sc-cues--zh" role="table"><div class="sc-cue sc-cue-head" role="row"><span>#</span><span>时间</span><span>中文</span><span></span></div>${CUES_S.map(([n, a, b, zh]) => (zh ? `<div class="sc-cue" role="row"><span class="mono">${n}</span><span class="mono muted">${a}–${b}</span><span data-design-data>${br(zh)}</span><span>${C.st('放得下')}</span></div>` : `<div class="sc-cue sc-cue-fold" role="row"><span class="mono">${n}</span><span class="mono muted">${a}–${b}</span><span class="muted">都放得下 · ${C.link('展开', { toast: '展开第 6–46 条' })}</span><span></span></div>`)).join('')}</div></section>`;
    }
    const off = state === 'upstream-off';
    return `<section class="pnl" data-design-id="S4-CUES"><div class="pnl-h"><h3>字幕<span class="sc-meta" data-design-data>14 条 · ${off ? '中文（英文等上游）' : '中英双语'} · 30 帧/秒</span></h3><p>改了中文切分或切镜点，要重新翻译</p></div><div class="sc-cues" role="table"><div class="sc-cue sc-cue-head" role="row"><span>#</span><span>帧</span><span>中文</span><span>${off ? '英文（上游中台连上以后逐条补上）' : '英文'}</span><span></span></div>${CUES_D.map(([n, a, b, zh, en]) => {
      if (!zh) return `<div class="sc-cue sc-cue-fold" role="row"><span class="mono">${n}</span><span class="mono muted">${a}–${b}</span><span class="muted sc-span2">${off ? '中文都放得下' : '中英都放得下'} · ${C.link('展开', { toast: `展开第 ${n} 条` })}</span><span></span></div>`;
      const bad = !off && n === 14;
      return `<div class="sc-cue ${bad ? 'is-bad' : ''}" role="row"><span class="mono">${n}</span><span class="mono muted">${a}–${b}</span><span data-design-data>${br(zh)}</span><span class="sc-en" data-design-data>${off ? '' : esc(en)}</span><span>${off ? '' : bad ? C.st('放不下', 'bad') : C.st('放得下')}</span></div>`;
    }).join('')}</div></section>`;
  }

  function sound(kind, state) {
    const rows = kind === 'spoken'
      ? [['口播原声', '剪后 2:31 · 按对稿剪辑的剪点', C.st('就绪')], ['背景音乐', '没加', C.btn('从音乐库选', { cls: 'btn--sm', go: 'music' })]]
      : state === 'upstream-off'
        ? [['配音', '在上游中台生成，连上以后自动取回', C.st('等上游', 'wait')], ['背景音乐', '没加', C.btn('从音乐库选', { cls: 'btn--sm', go: 'music' })]]
        : [['配音', '来自上游中台 · 0:39 · 时长不变', C.st('就绪')], ['背景音乐', '没加', C.btn('从音乐库选', { cls: 'btn--sm', go: 'music' })]];
    return `<section class="pnl" data-design-id="S4-SOUND"><div class="pnl-h"><h3>声音</h3></div><ul class="rows">${rows.map(([k, v, end]) => `<li><div><b>${k}</b><small data-design-data>${esc(v)}</small></div><div class="end">${end}</div></li>`).join('')}</ul></section>`;
  }

  function preview(kind, state) {
    if (kind === 'spoken') {
      return `<section class="pnl sc-player" data-design-id="S4-PREVIEW"><div class="sc-frame">${pic(byScene('selfie-moments', 1))}<div class="sc-safe"><p class="sc-zh">我断更了整整一年。</p></div></div><div class="pnl-b">${style([['中文', '每行最多 14 字，最多两行'], ['位置', '底部 20% 安全区'], ['底框', '黑色 75% 不透明']])}</div></section>`;
    }
    const bad = state === 'en-too-long';
    return `<section class="pnl sc-player" data-design-id="S4-PREVIEW"><div class="sc-frame sc-frame--anim"><div class="sc-anim-art"><span>慢</span><i></i><span>快</span><small>时间轴：慢的一段占四分之三</small></div><div class="sc-safe ${bad ? 'is-bad' : ''}"><p class="sc-zh">慢的那段花的时间多，<br>所以它说了算。</p>${state === 'upstream-off' ? '' : `<p class="sc-en2">The slow part takes up more of the time, so it has the bigger say in the overall average.</p>`}${bad ? '<em>第 3 行放不下</em>' : ''}</div></div><div class="pnl-b">${style([['中文', '每行最多 14 字，最多两行'], ['英文', '中文字号的 58%，最小 45%，最多两行'], ['位置', '中英共用一个底框，底部 20% 安全区']])}</div></section>`;
  }
  const style = rows => rows.map(([k, v]) => `<div class="kv"><span>${k}</span><strong>${v}</strong></div>`).join('');

  reg('s4', {
    group: '按脚本做视频', name: '4 字幕与声音', nav: 'projects', piece: { tab: 'script', step: 4 },
    states: [['en-too-long', '直出：1 条英文放不下'], ['upstream-off', '直出：上游没连上'], ['spoken', '口播：中文字幕']],
    // 没写状态、又是从口播过来的，就画口播；点了直出的状态，顶栏换成直出那件作品
    crumb: s => { if (hashS() || ctx.line !== 'spoken') ctx.line = s === 'spoken' ? 'spoken' : 'direct'; return undefined; },
    flow: s => {
      const k = !hashS() && ctx.line === 'spoken' ? 'spoken' : s;
      return k === 'spoken' ? { notes: [null, '9 镜 · 都配上了', '12 处都处理好了', '中文字幕 46 条', '还没出片'] }
        : k === 'upstream-off' ? { notes: [null, '7 镜 · 都配上了', '有配音才能渲染', '等上游给配音', '还没出片'], done: [true, true, false, false, false], warn: [3] }
          : { notes: [null, '7 镜 · 都配上了', '7 镜都渲染好了', '1 条英文放不下', '还没出片'], warn: [3] };
    },
    render: s => {
      const k = !hashS() && ctx.line === 'spoken' ? 'spoken' : s;
      let head, attn = '';
      if (k === 'spoken') {
        head = C.head({ eyebrow: '第 4 步 · 字幕与声音', title: '中文字幕 46 条，按原片切好了', lede: '字幕来自本机转写，时间按逐字时间对上剪后的口播。改字不会动原片。', actions: C.btn('下载字幕文件', { toast: '导出字幕文件，给剪辑软件用' }) + C.btn('下一步：出片检查', { pri: true, go: 's5' }), id: 'S4-HEAD' });
      } else if (k === 'upstream-off') {
        head = C.head({ eyebrow: '第 4 步 · 字幕与声音', title: '中文字幕切好了，配音和英文还没到', lede: '直出的配音和英文翻译在上游中台生成。中文字幕已经按口播稿切成 14 条。', actions: C.btn('下一步：出片检查', { disabled: true }), id: 'S4-HEAD' });
        attn = C.attn({ title: '上游中台没连上：配音和英文字幕拿不到', text: '连上以后自动取回配音，再按这 14 条中文逐条要英文。没有配音不能出片。', actions: C.btn('去连接', { pri: true, go: 'set-upstream' }), id: 'S4-UPSTREAM' });
      } else {
        head = C.head({ eyebrow: '第 4 步 · 字幕与声音', title: '14 条字幕里，第 14 条英文放不下', lede: '中文每行最多 14 字、最多两行；英文跟在中文下方，一条中文配一条完整的英文。放不下就报出来，不截断译文。', actions: C.btn('下一步：出片检查', { disabled: true }), id: 'S4-HEAD' });
        attn = C.attn({ title: '第 14 条英文放不下：缩到最小字号还要三行', text: '「慢的那段花的时间多，所以它说了算。」的英文太长。这一条要在上游中台重新翻译得短一些；其余 13 条不用动。', actions: C.btn('回上游重新翻译这一条', { pri: true, toast: '已把第 14 条发回上游中台重新翻译' }), id: 'S4-TOO-LONG' });
      }
      const kind = k === 'spoken' ? 'spoken' : 'direct';
      return head + attn + `<div class="cols"><div class="stack">${cueTable(kind, k)}${sound(kind, k)}</div><aside class="stack">${preview(kind, k)}</aside></div>`;
    },
  });

  // ================= 5 出片检查 =================
  // 直出：本机逐帧渲染出两版，对比检查。口播：交给剪辑软件精修，导出的成片收回来检查。
  const EDITORS = [['Kdenlive', '出一份能直接打开的时间线，在 Kdenlive 里精修', true], ['剪映', '不出工程，给剪点清单，照着在剪映里剪', false], ['OpenChatCut', '开源的网页剪辑工具，装在本仓库里', false]];
  const WILL_CHECK = [['能完整播放', '从头到尾解码一遍'], ['音画同步', '音画差不超过 0.04 秒'], ['帧数和时长一致', '和剪后的时间线对上'], ['原片没有被改动', '原片指纹和导入时一样'], ['字幕', '46 条都在画面里，时间不乱'], ['黑帧', '没有意外的黑屏']];
  const s5Kind = s => (!hashS() && ctx.line === 'spoken' ? 'spoken-waiting' : s);

  function editorRow() {
    return `<section class="pnl" data-design-id="S5-EDITORS"><div class="pnl-h"><h3>出片方式</h3><p>只改这件作品</p></div><div class="sc-editors">${EDITORS.map(([name, line, cur]) => `<button class="sc-editor-opt" ${cur ? 'aria-current="true"' : ''} data-toast="${cur ? '这件作品现在用 ' + name : '换成 ' + name + '：草稿要重新出一次'}"><header><b>${name}</b>${cur ? C.st('现在用', 'run') : ''}</header><small>${line}</small></button>`).join('')}</div></section>`;
  }

  function spokenWaiting() {
    const head = C.head({ eyebrow: '第 5 步 · 出片检查', title: '草稿已经交给 Kdenlive，改完把成片拖回来', lede: 'Kdenlive 里是按对稿剪辑排好的时间线：8 处重说和静音已剪、2 处讲解动画已叠、46 条字幕已放。你在里面精修、导出 MP4，再拖回这里检查。', actions: C.btn('打开剪点清单', { toast: '打开剪点清单：每一处剪点的时间码和做法' }) + C.btn('在 Kdenlive 里打开', { pri: true, toast: '在 Kdenlive 里打开这件作品的时间线' }), id: 'S5-HEAD' });
    const will = `<section class="pnl" data-design-id="S5-WILL-CHECK"><div class="pnl-h"><h3>收回以后查这 6 项</h3><p>都通过才算一版</p></div><ul class="sc-will">${WILL_CHECK.map(([k, v]) => `<li><b>${k}</b><small>${v}</small></li>`).join('')}</ul></section>`;
    return head + `<div class="full stack">${editorRow()}${C.drop({ editor: 'Kdenlive' })}${will}</div>`
      + C.statusline('还没出片。收回的成片通过检查以后，才能记录发布。', '', 'S5-PUBLISH');
  }

  function spokenFailed() {
    const head = C.head({ eyebrow: '第 5 步 · 出片检查', title: 'v1 检查没通过，先别用', lede: '原片和剪后的时间线都没动。在 Kdenlive 里改好、重新导出，再收回来查一遍。', id: 'S5-HEAD' });
    const attn = C.attn({ tone: 'cut', title: 'v1 有 2 项没通过：音画同步、字幕', text: '音画差超出允许范围；有一条字幕跑出了画面。具体数值在下面这一版里。', actions: C.btn('重新收回', { pri: true, toast: '打开系统的选择文件窗口，选改好的成片' }), id: 'S5-FAILED' });
    const shot = byScene('selfie-moments', 1);
    const v1 = C.cand({ v: 'v1', editor: 'Kdenlive', dur: '2:31', frames: '4530', status: 'fail', poster: ctx.frameOf(shot), note: '10/26 10:42 收回', checks: [['能完整播放', 'ok', ''], ['音画同步', 'fail', '实测 0.12 秒 · 允许 0.04 秒'], ['帧数和时长一致', 'ok', '4530 帧'], ['原片没有被改动', 'ok', ''], ['字幕', 'fail', '第 31 条超出画面'], ['黑帧', 'ok', '没有']], actions: C.btn('看第 31 条', { cls: 'btn--sm', toast: '跳到 1:58，第 31 条字幕折成了三行，压出底部安全区' }) + C.btn('听哪里不同步', { cls: 'btn--sm', toast: '从 0:52 开始放：声音比画面晚 0.12 秒' }) });
    return head + attn
      + C.statusline('出片方式：<b>Kdenlive</b> · 出一份能直接打开的时间线，在 Kdenlive 里精修', C.link('换', { toast: '出片方式：Kdenlive、剪映（剪点清单）、OpenChatCut' }), 'S5-METHOD')
      + `<div class="cands full sc-cands2" data-design-id="S5-CANDIDATES">${v1}</div>`
      + C.statusline('还没出片。收回的成片通过检查以后，才能记录发布。', '', 'S5-PUBLISH');
  }

  function directCompare() {
    const head = C.head({ eyebrow: '第 5 步 · 出片检查', title: '两版成片：v2 通过检查，v1 不能用', lede: '成片在本机逐帧渲染、合成配音和字幕，再查能不能完整播放、音画、帧数、原片、字幕和黑帧。通过的才算一版。', id: 'S5-HEAD' });
    const method = C.statusline('出片方式：<b>本机逐帧渲染</b> · 按确认过的动画代码逐帧画，再合成配音和字幕', C.link('换', { toast: '出片方式：本机逐帧渲染（直出默认）、Kdenlive 合成（口播原片叠动画时用）' }), 'S5-METHOD');
    const v1 = C.cand({ v: 'v1', editor: '本机逐帧渲染', dur: '0:39', frames: '1158', status: 'fail', note: '第 5 镜补图前', checks: [['能完整播放', 'ok', ''], ['音画同步', 'fail', '实测 0.21 秒 · 允许 0.04 秒'], ['帧数和时长一致', 'ok', '3990 帧'], ['原片没有被改动', 'ok', ''], ['字幕', 'ok', '14 条'], ['黑帧', 'ok', '没有']], actions: C.btn('听哪里不同步', { cls: 'btn--sm', toast: '从第 5 镜开始放：配音比画面晚 0.21 秒' }) });
    const v2 = C.cand({ v: 'v2', editor: '本机逐帧渲染', dur: '0:39', frames: '1158', status: 'pass', current: true, note: '第 5 镜补图后', checks: [['能完整播放', 'ok', ''], ['音画同步', 'ok', '0.01 秒'], ['帧数和时长一致', 'ok', '3990 帧'], ['原片没有被改动', 'ok', ''], ['字幕', 'ok', '14 条'], ['黑帧', 'ok', '没有']], actions: C.btn('播放', { cls: 'btn--sm', toast: '播放 v2' }) });
    return head + method
      + `<div class="cands full sc-cands2 sc-direct" data-design-id="S5-CANDIDATES">${v1}${v2}</div>`
      + C.statusline('回传上游：上游中台连上以后，自动回传通过检查的 v2 低清版（短边 480，不超过 20 MB）。', C.btn('去连接', { cls: 'btn--sm', go: 'set-upstream' }), 'S5-UPLOAD')
      + C.statusline('还没发布。发布以后记一下平台和链接，3 天后提醒你看数据、写一句复盘。', C.btn('记录发布', { cls: 'btn--sm', toast: '填平台、发布时间和链接' }), 'S5-PUBLISH');
  }

  reg('s5', {
    group: '按脚本做视频', name: '5 出片检查', nav: 'projects', piece: { tab: 'script', step: 5 },
    states: [['compare', '直出：v1 没通过、v2 通过'], ['spoken-waiting', '口播：等收回成片'], ['spoken-failed', '口播：检查没通过']],
    // 没写状态、又是从口播过来的，就画口播；点了哪种状态，顶栏换成那件作品
    crumb: s => { if (hashS() || ctx.line !== 'spoken') ctx.line = s.startsWith('spoken') ? 'spoken' : 'direct'; return undefined; },
    flow: s => {
      const k = s5Kind(s);
      if (k === 'compare') return { notes: [null, '7 镜 · 都配上了', '7 镜都渲染好了', '中英字幕 14 条', 'v2 通过检查'], done: [true, true, true, true, false] };
      return { notes: [null, '9 镜 · 都配上了', '12 处都处理好了', '中文字幕 46 条', k === 'spoken-failed' ? 'v1 检查没通过' : '等收回成片'], done: [true, true, true, true, false], warn: k === 'spoken-failed' ? [4] : [] };
    },
    actions: s => (s5Kind(s) === 'compare' ? C.btn('在访达中显示 v2', { toast: '在访达里选中 v2 成片' }) : ''),
    render: s => {
      const k = s5Kind(s);
      return k === 'spoken-waiting' ? spokenWaiting() : k === 'spoken-failed' ? spokenFailed() : directCompare();
    },
    after: root => {
      root.querySelectorAll('.sc-direct .cand .poster').forEach(p => {
        const t = document.createElement('div'); t.className = 'sc-ptitle'; t.innerHTML = '<b>平均速度</b><small>不是速度的平均</small>'; p.appendChild(t);
      });
    },
  });
})();
