// R278 设计稿共用：数据、各块的画法、放大浮层、可点演示。index.html（给用户看）和 spec.html（给 Codex）都用。
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D=v=>`<span data-design-data>${esc(v)}</span>`;
const mmss=t=>{t=Math.max(0,Math.round(t));return Math.floor(t/60)+':'+String(t%60).padStart(2,'0')};
const SCRIPT=["清华AI体育博主，断更一年。会写代码，会练体能，就是发不出一条视频。后来我看到一项研究：容易焦虑的人担心的事，百分之九十一没有发生。拦着我的，是脑子里的四句话。今天一句一句，对一对研究。","第一句：发出去，会被人看低。断了这么久，大家肯定都注意到了。有个经典实验：让学生穿件尴尬的衣服走进教室。穿的人估计，大约一半的人会注意到。实际只有四分之一左右。别人的注意，远比我们以为的少。没有人在等我宣布回归。","第二句：担心的事，一定会发生。开头那个数就来自这里：把每天的担心记下来，事后逐条对照。大约百分之九十一，没有发生。所以发之前，我先写一行：我担心什么。过两天再补一行：实际怎样。不写下来，就永远不知道它没应验。","第三句：还没做到最好，再改改。西蒙提过一个说法，叫满意化：够好就停，不用非找到最好。有本书叫《艺术与恐惧》，讲过一个陶艺课的故事。一组按数量打分，一组按质量打分。最好的作品，反而出自数量组。所以我先写下几条标准，满足了就发。","第四句：反正都断了，再断几天也一样。这叫破戒效应。有研究跟踪了九十多个人，发现偶尔漏掉一次，对养成没有实质影响。养成的中位数是六十六天，快的十八天，慢的两百五十四天。断了，今天接上就行。我只给自己一条规矩：不连着断两次。","这些道理，我早就懂。可懂了，身体还是怕。旧的预测只在出错时才会改，而不发，它就永远不会错。所以我把动作写成一句：如果晚饭后坐到桌前，就打开草稿箱，发最早剪好的那一条。九十四项研究汇总下来，这样写的人明显更容易做到。","发布是训练课，不是比赛。发出来的七十分，比没发的九十五分有用。你也有一件存了很久的东西吧？今天写两行字。一行写：如果什么时候，我就做哪个小动作。一行写：我最担心会发生什么。过两天，回来对一对。"];
const sec=t=>Math.round([...t].length/5.1*10)/10;
const TOTAL=mmss(SCRIPT.reduce((a,t)=>a+sec(t),0));
const TITLE='断更一年，我拆了四句话';
// 中台「断更一年，我拆了四句话」的分镜（上游 storyboard.json 真数据）；画面图是上游代码渲染每镜的最后一帧
const HAND=[{"d": "清华AI体育博主，断更一年。会写代码，会练体能，就是发不出一条视频。后来我看到一项研究：容易焦虑的人担心的事，百分之九十一没有发生。拦着我的，是脑子里的四句话。今天一句一句，对一对研究。", "v": "浅米色底，封面即完整画面：大字身份「清华 AI 体育博主」、珊瑚色「断更一年」、珊瑚色巨大「91%」配「担心的事 没有发生」和限定「一项研究 · 容易焦虑的人」；三张反差卡「会写代码 ✓」「会练体能 ✓」「发视频 0 条」；最后出现四句话四个标签", "sub": "清华 AI 体育博主，断更一年 / 容易焦虑的人担心的事，91% 没有发生", "cam": "固定竖屏，封面直接成立；反差卡逐张浮现，91% 下划线随口播画出，四个标签依次出现", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 16.1}, {"d": "第一句：发出去，会被人看低。断了这么久，大家肯定都注意到了。有个经典实验：让学生穿件尴尬的衣服走进教室。穿的人估计，大约一半的人会注意到。实际只有四分之一左右。别人的注意，远比我们以为的少。没有人在等我宣布回归。", "v": "大号白卡柱状图：珊瑚色「穿的人估计 约 50%」和深青色「实际注意到 约 25%」两根柱子", "sub": "穿的人估计：约 50% 注意到 / 实际：约 25%", "cam": "固定竖屏，两根柱子按口播先后升起，结论条最后滑入", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 19.0}, {"d": "第二句：担心的事，一定会发生。开头那个数就来自这里：把每天的担心记下来，事后逐条对照。大约百分之九十一，没有发生。所以发之前，我先写一行：我担心什么。过两天再补一行：实际怎样。不写下来，就永远不知道它没应验。", "v": "10×10 的方格逐个亮成珊瑚色代表担心，随后 91 格褪成灰色，只剩 9 格；右侧大字 91%；下方两张卡「发之前：我担心什么」「两天后：实际怎样」", "sub": "91% 的担心没有发生 / 发之前写担心，两天后写实际", "cam": "固定竖屏，方格逐行填满再成片褪灰，两张卡依次出现", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 18.2}, {"d": "第三句：还没做到最好，再改改。西蒙提过一个说法，叫满意化：够好就停，不用非找到最好。有本书叫《艺术与恐惧》，讲过一个陶艺课的故事。一组按数量打分，一组按质量打分。最好的作品，反而出自数量组。所以我先写下几条标准，满足了就发。", "v": "进度条停在「够好 · 发」，虚线圈出远处的「最好？」；陶艺课两组对比：数量组两排小陶罐，其中一只珊瑚色，质量组只有一只灰陶罐；底部四条打勾的完成标准", "sub": "够好就停 / 最好的作品出自数量组（书中故事）", "cam": "固定竖屏，进度条推进停在够好，陶罐逐个摆出，清单逐条打勾", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 19.4}, {"d": "第四句：反正都断了，再断几天也一样。这叫破戒效应。有研究跟踪了九十多个人，发现偶尔漏掉一次，对养成没有实质影响。养成的中位数是六十六天，快的十八天，慢的两百五十四天。断了，今天接上就行。我只给自己一条规矩：不连着断两次。", "v": "大号习惯曲线从第 0 天升起后趋平，「漏一次」的空心点后曲线照常上升；66 天中位数虚线；18–254 天的浅青色区间标「因人而异」，254 天注明外推估计；底部八个圆点只空一个，配「不连断两次」", "sub": "漏一次，没有实质影响 / 中位数 66 天，因人而异 18–254 天", "cam": "固定竖屏，曲线从左往右画出，区间展开，圆点逐个点亮", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 19.6}, {"d": "这些道理，我早就懂。可懂了，身体还是怕。旧的预测只在出错时才会改，而不发，它就永远不会错。所以我把动作写成一句：如果晚饭后坐到桌前，就打开草稿箱，发最早剪好的那一条。九十四项研究汇总下来，这样写的人明显更容易做到。", "v": "大号三节点循环图「预测：会被看低 → 不发 → 永远不会错」，箭头绕回起点，中间写「越躲越信」；下方两张卡「如果 晚饭后坐到桌前」「就 打开草稿箱 发最早那条」", "sub": "不发，预测就永远不会错 / 如果……就……", "cam": "固定竖屏，循环箭头逐段画出，两张卡先后出现", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 19.2}, {"d": "发布是训练课，不是比赛。发出来的七十分，比没发的九十五分有用。你也有一件存了很久的东西吧？今天写两行字。一行写：如果什么时候，我就做哪个小动作。一行写：我最担心会发生什么。过两天，回来对一对。", "v": "标题「发布是训练课，不是比赛」；两条横条：深青色实心「发出来的 70 分」，灰色虚线「没发的 95 分 · 没人看得到」；问句之后出现两张留空的填空卡「一行写计划」「一行写担心」", "sub": "发布是训练课，不是比赛 / 今天写两行字", "cam": "固定竖屏，实心条填充，填空卡依次出现，结尾停在完整画面", "aud": "百炼 Cherry 配音，无背景音乐", "sec": 16.9}];
const HAND_META={rev:3,at:'10 月 26 日 14:02',voice:'百炼 Cherry',dur:mmss(HAND.reduce((a,r)=>a+r.sec,0))};
const NEWER={rev:4,at:'10 月 26 日 15:10'};
// 这台电脑上三次真实生成的全片设计（新到旧）
const STYLES=[
 {id:'0e18',title:TITLE,time:'10 月 26 日 01:51',cur:true,img:'img/style-0e18.jpg',pal:['#14171A','#4FB3A9','#FF8A3D','#9AA3AB'],type:'168 / 72 / 44',sum:'每拍只动一个主角，数字跳完就停，橙色只给结论',nots:['第二种强调色','光晕霓虹粒子','三卡并排','同时淡入','整句口播上屏','饼图仪表盘'],rule:'每拍只有一个主动作随口播句级时序出现，次要动作幅度为主动作的50–70%并晚150毫秒开始；数字跳动1.4秒后停住；橙色只在结论落定时出现一次，之后画面静止不再动字。',ban:['第二个彩色强调色：橙色只标结论，关键词强调只用更亮的中性色或加大字号','光晕、霓虹、粒子、紫蓝渐变、毛玻璃卡片','三卡并排、KPI网格、一屏要点列表、圆圈里放图标','所有元素同时淡入或全部从下往上滑入，字在被读时仍在移动','把口播原句整句写上画面，或在底部 y≥1536 放文字和关键图形','饼图、仪表盘、图例，以及未标「示意图，非原始数据」的示意数据']},
 {id:'0d6e',title:TITLE,time:'10 月 26 日 01:26',img:'img/style-0d6e.jpg',pal:['#15171B','#5FB8C2','#FF7A3D','#9AA0A8'],type:'200 / 72 / 44',sum:'每镜一个主动作，配角晚半拍，字落定就不动',nots:['光晕霓虹','米白纸衬线','第二种强调色','KPI 网格','整句口播上屏','数字同时跳'],rule:'每镜只有一个主动作随口播句级时序推进，次要动作幅度为主动作的50–70%并晚150毫秒起步，其余元素静止，文字落定后不再移动。',ban:['光晕、霓虹、粒子、紫蓝渐变、毛玻璃卡片等AI露馅装饰','米白纸底、衬线大标题、「01/02」编号与胶囊标签','第二种彩色强调；橙色以外的颜色标结论','饼图、仪表盘、KPI网格、三卡并排、一屏要点列表','画面文字照抄口播原句，或在y≥1536放文字与关键图形','同屏多个数字同时跳动，或元素全部同时淡入、从下往上滑入']},
 {id:'7719',title:TITLE,time:'10 月 26 日 01:20',img:'img/style-7719.jpg',pal:['#F1F3F2','#1E2A32','#E2572B','#5D6870'],type:'200 / 64 / 44',sum:'每镜一个主动作，图解跟口播长出来，数字跳完就停',nots:['暗底漂浮元素','紫蓝渐变','米白纸衬线','三卡并排','同时淡入','第二种彩色'],rule:'每镜只有一个主动作，次要动作的幅度为主动作的50–70%，并晚150毫秒开始；图解随口播逐段生长，数字跳动1.4秒后停住。',ban:['暗底漂浮小元素、光晕、霓虹、粒子','紫蓝渐变、网格渐变、毛玻璃卡片','米白纸底配衬线大标题、斜体强调词、01/02编号、胶囊标签','三卡并排、KPI网格、圆圈图标、一屏要点列表','全部元素同时淡入或统一从下往上滑入','除强调橙外引入第二种彩色']},
];
// 从头定的样张（用浅色那套真实设计当示例）
const LIBX=id=>LIB.find(x=>x.id===id)||LIB[0];
// 样张还没画的风格：只用它的三种颜色画一块占位，不放字
const phTile=x=>`<span class="lib-ph" style="--bg:${x.pal[0]};--pc:${x.pal[1]};--ac:${x.pal[2]}" aria-hidden="true"></span>`;
const DRAFT={...STYLES[2],palDeep:['#F1F3F2','#121B21','#E2572B','#5D6870']};
const DESC='浅米色底，深青做主色，结论只用橙色。\n字的感觉：标题要粗，数字特别大。\n画面怎么动：每句只动一个东西，动完就停。\n不要什么：渐变、一屏堆很多卡片。';
const TABS=`<nav class="ptabs" role="tablist" data-design-id="DV-TABS"><button role="tab" aria-selected="false">按素材剪 vlog</button><button role="tab" aria-selected="false">按脚本做视频</button><button role="tab" aria-selected="true">脚本直出</button></nav>`;
const btn=(t,attrs='',pri=false)=>`<button class="btn${pri?' btn--pri':''}" ${attrs}>${t}</button>`;
const head=(title,lede='',actions='',one=false)=>`<div class="stephead full" data-design-id="DV-HEAD"><div><p class="eyebrow">脚本直出</p><h2>${title}</h2>${lede?`<p${one?' data-max-lines="1"':''}>${lede}</p>`:''}</div><div class="actions">${actions}</div></div>`;
const cell=(cls,mark,title,note,extra='',tag='div',attrs='')=>`<${tag} class="fstep ${cls}" ${attrs}><b>${mark}</b><span><strong>${title}</strong>${note.startsWith('=')?`<small>${esc(note.slice(1))}</small>`:`<small data-design-data>${esc(note)}</small>`}</span>${extra}</${tag}>`;
const ENTRY=`<em class="dv-step-edit" data-design-id="DV-RESCRIPT-ENTRY">改分镜脚本</em>`;
const LOCK=t=>`<em class="dv-step-lock" data-design-id="DV-RESCRIPT-LOCKED">${t}</em>`;
const nav=c=>`<nav class="flow full" aria-label="这件作品的步骤" data-design-id="DV-STEPS">${c}</nav>`;
const S1=`7 镜 · 约 ${TOTAL}`;
const STEPS={
 entry:nav(cell('done dv-fstep-btn','✓','分镜脚本',S1,ENTRY,'button','data-rescript aria-label="改分镜脚本"')+cell('done','✓','Opus 写每一镜','7 镜都写好了')+cell('done','✓','成片','无声预览 · 2:23')),
 writing:nav(cell('done','✓','分镜脚本',S1,LOCK('写完才能改'))+cell('cur','2','Opus 写每一镜','3 / 7 镜写好','','div','aria-current="step"')+cell('','3','成片','还没合成')),
 composing:nav(cell('done','✓','分镜脚本',S1,LOCK('合成完才能改'))+cell('done','✓','Opus 写每一镜','7 镜都写好了')+cell('cur','3','成片','正在合成','','div','aria-current="step"')),
 designing:nav(cell('done','✓','分镜脚本',S1,LOCK('写完才能改'))+cell('cur','2','Opus 写每一镜','正在定全片设计','','div','aria-current="step"')+cell('','3','成片','还没合成')),
 rescript:nav(cell('cur','1','分镜脚本',S1,'','div','aria-current="step"')+cell('','2','Opus 写每一镜','=生成后从头写')+cell('','3','成片','=生成后重新合成')),
 first:nav(cell('cur','1','分镜脚本',S1,'','div','aria-current="step"')+cell('','2','Opus 写每一镜','等分镜脚本')+cell('','3','成片','还没合成')),
 firstHand:nav(cell('cur','1','分镜脚本',`7 镜 · ${HAND_META.dur}`,'','div','aria-current="step"')+cell('','2','Opus 写每一镜','等分镜脚本')+cell('','3','成片','还没合成')),
 firstEmpty:nav(cell('cur','1','分镜脚本','还没粘贴','','div','aria-current="step"')+cell('','2','Opus 写每一镜','等分镜脚本')+cell('','3','成片','还没合成')),
};
const HEADS={
 entry:head('无声预览出来了',D('从点「生成」到出片用了 11:52。上传配音以后按配音重排时长，再合成带声成片。'),'<button class="btn rv-go-log">画面问题记录</button>'+btn('上传配音…')+btn('重新合成')),
 writing:head(D('Opus 写好了 3 镜，正在写第 04、05、06 镜'),D('写好一镜就渲染一镜。第 06 镜自查没过，正在自动重写一次。')),
 composing:head('正在合成无声预览','七镜画面逐帧拼起来，再检查一遍。'),
 designing:head('Opus 正在按你的话改全片设计','定好以后七镜三镜一组同时写。可以离开这一页，回来接着看进度。'),
 rescript:head('改分镜脚本，重新生成','点「生成」后 Opus 从头写每一镜，配音要重新上传。现在这条留在本机，页面只显示新的那条。',btn('回到现在这条','data-rescript-back'),true),
 firstHand:head(D('分镜脚本共 7 镜，可以生成了'),'中台交过来的分镜和配音都已带上。检查一下，改完就能生成。'),
 firstEmpty:head('把分镜脚本直接做成视频','粘贴分镜脚本，Opus 给每一镜写一段动画代码，在这台电脑上逐帧渲染成画面，再合成一条竖屏成片。不用素材，也不用剪辑软件。'),
 first:head(D('分镜脚本共 7 镜，可以生成了'),'检查一下分镜：一格是一镜。时长先按字数估，上传配音后按实测。'),
};
const sw=pal=>`<span class="dv-style-sw">${pal.map(c=>`<i style="--swatch:${c}"></i>`).join('')}</span>`;
const pal4=pal=>`<div class="dv-sw-pal">${['背景','主色','强调色','中性'].map((n,i)=>`<span class="dv-sw"><i style="--swatch:${pal[i]}"></i>${n}</span>`).join('')}</div>`;
const metaOf=(s,pal,title,extra='')=>`<div class="dv-sw-meta"><h4>${title}</h4>${extra}${pal4(pal)}<dl><div><dt>字号</dt><dd data-design-data>${s.type}</dd></div><div><dt>动作规矩</dt><dd data-design-data>${esc(s.sum)}</dd></div><div><dt>不用</dt><dd><span class="dv-nots">${s.nots.map(b=>`<span data-design-data>${esc(b)}</span>`).join('')}</span></dd></div></dl></div>`;
const HINTS=['底色和主色','强调色','字的感觉','画面怎么动','参考什么','不要什么'];
function styleWide(o){
 const segs=`<div class="seg" role="radiogroup" aria-label="视频风格怎么定"><button role="radio" data-mode="base" aria-checked="${o.mode==='base'}" aria-pressed="${o.mode==='base'}" ${o.none&&o.nolib?'disabled':''}>选现成的风格</button><button role="radio" data-mode="new" aria-checked="${o.mode==='new'}" aria-pressed="${o.mode==='new'}">从头定风格</button></div>`;
 let edit='',prev='';
 if(o.mode==='base'){
  const s=o.base;
  const card=x=>`<button class="dv-sw-card" data-style="${x.id}" aria-pressed="${!!s&&x.id===s.id}">${x.img?`<img src="${x.img}" alt="">`:phTile(x)}<span><b data-design-data>${esc(x.lib?x.name:x.title)}</b>${x.lib?'':`<small data-design-data>${x.cur&&o.rescript?'这条 · ':''}${x.time}</small>`}${sw(x.pal)}</span></button>`;
  edit=(o.none?'<p class="dv-sw-none">这台电脑上还没有做过的成片，先从风格库里挑一个。</p>':`<label class="dv-sw-label">这台电脑上做过的</label><div class="dv-sw-cards" data-design-id="DV-STYLE-CARDS">${STYLES.map(card).join('')}</div>`)
   +(o.lib?`<label class="dv-sw-label">风格库<span>样张都是同一段台词</span></label><div class="dv-sw-cards" data-design-id="DV-STYLE-LIB">${LIB.map(card).join('')}</div>`:'')+`<label class="dv-sw-label">在这个风格上改哪里<span>（可不填）</span></label><textarea rows="3" data-adjust placeholder="例：强调色换成暖黄，其余不动；数字再大一些">${esc(o.adjust||'')}</textarea>`;
  prev=!s?`<div class="dv-sw-empty"><b>还没选风格</b><span>在左边选一个</span></div><div class="dv-sw-meta"><p class="muted">选好以后这里放它的样张，和色板、字号、动作规矩、不用的套路。</p></div>`
   :s.lib&&!s.clip?`<div><div class="dv-poster">${phTile(s)}</div><p class="dv-sw-cap">样张 · 同一段台词</p></div>${metaOf(s,s.pal,`风格库 · ${esc(s.name)}`)}`
   :s.lib?`<div><div class="dv-poster"><video src="${s.clip}" poster="${s.img}" muted loop playsinline preload="metadata" aria-hidden="true"></video></div><p class="dv-sw-cap">样张 · 同一段台词</p></div>${metaOf(s,s.pal,`风格库 · ${esc(s.name)}`)}`
   :`<div><div class="dv-poster"><img src="${s.img}" alt=""></div><p class="dv-sw-cap">首镜关键帧</p></div>${metaOf(s,s.pal,D(`${s.cur&&o.rescript?'这条 · ':''}${s.time}`))}`;
 } else {
  const t=(o.text||'').trim(),dr=o.draft;
  edit=`${o.none?'<p class="dv-sw-none">还没有可以沿用的成片</p>':''}<label class="dv-sw-label">风格说明<span>越具体越好</span></label><textarea rows="6" data-desc ${dr==='drafting'||dr==='revising'?'disabled':''} placeholder="例：浅米色底，深青做主色，结论只用橙色。标题要粗，数字特别大。每句只动一个东西，动完就停。不要渐变，不要一屏堆很多卡片。">${esc(o.text||'')}</textarea><div class="dv-sw-hints"><span>可以照这几项写：</span>${HINTS.map(h=>`<button class="pill" data-hint="${h}">${h}</button>`).join('')}</div>`;
  if(dr==='ready'||dr==='revising')edit+=`<label class="dv-sw-label">再改一句<span>（可不填）</span></label><textarea rows="3" data-revise ${dr==='revising'?'disabled':''} placeholder="例：主色再深一点，标题再大一号">${esc(o.revise||'')}</textarea><div class="dv-sw-acts">${btn('改','data-revise-go'+((o.revise||'').trim()&&dr==='ready'?'':' disabled'))}</div>`;
  else if(dr!=='accepted')edit+=`<div class="dv-sw-acts">${btn('先定风格','data-draft'+(t&&!o.nolines&&!dr?'':' disabled'))}<p>${o.nolines?'先粘贴分镜脚本：样张就是第 01 镜。':'Opus 先定全片设计，再把第 01 镜写出来当样张，约 2–3 分钟。'}</p></div>`;
  if(!dr)prev=`<div class="dv-sw-empty"><b>样张会出现在这里</b><span>先写出第 01 镜</span></div><div class="dv-sw-meta"><p class="muted">定好以后这里显示色板、字号、动作规矩和不用的套路。</p></div>`;
  else if(dr==='drafting'||dr==='revising')prev=`<div class="dv-poster"><div class="dv-veil dv-veil--writing"><b>${dr==='drafting'?'正在定风格':'正在改样张'}</b><span class="mono" data-design-data>已用 0:42</span></div></div><div class="dv-sw-meta"><p class="muted">${dr==='drafting'?'先定全片设计，再把第 01 镜写出来当样张，约 2–3 分钟。':`按你的话改：${D(o.revise||'')}`}</p></div>`;
  else if(dr==='failed')prev=`<div class="dv-sw-empty"><b>没定成</b></div><div class="dv-sw-meta"><p class="dv-sw-fail">没定成：样张写了两次都没过自查。</p><div class="dv-sw-acts">${btn('重试','data-draft')}</div></div>`;
  else {const pal=o.revised?DRAFT.palDeep:DRAFT.pal;const acc=dr==='accepted';prev=`<div><div class="dv-poster"><img src="${DRAFT.img}" alt=""></div><p class="dv-sw-cap">样张 · 第 01 镜</p></div>${metaOf(DRAFT,pal,acc?'刚定好的风格':'样张出来了',acc?'<span class="dv-sw-used">已选用</span>':'')}`;
   prev+=``;
   prev=prev.replace('</dl></div>',`</dl><div class="dv-sw-acts">${acc?btn('重新定','data-redo'):btn('就用这个','data-accept')}${acc?'':'<p>满意了点「就用这个」，才能生成。</p>'}</div></div>`);}
 }
 return `<section class="dv-style-wide" data-design-id="DV-STYLE"><header class="dv-sw-head"><div><h3>视频风格</h3><p>Opus 在这个风格上写每一镜。先定好风格，才能生成。</p></div>${segs}</header><div class="dv-sw-body"><div class="dv-sw-edit" data-design-id="DV-STYLE-EDIT">${edit}</div><div class="dv-sw-preview" data-design-id="DV-STYLE-PREVIEW">${prev}</div></div></section>`;
}
function how(o){
 const first=o.mode==='base'?(!o.base?['先在下面选一个风格','选好就能生成']:(o.adjust||'').trim()?['Opus 先按你写的改全片设计','约 1 分钟']:['全片设计沿用选中的风格','不用等']):o.draft==='accepted'?['全片设计用刚定好的风格，第 01 镜直接用样张','不用等']:['先在下面定好风格、看过样张','点「先定风格」，约 2–3 分钟'];
 return `<div class="dv-opt" data-design-id="DV-HOW"><h4>点「生成」以后</h4><ol class="dv-how"><li><b>1</b><span>${first[0]}<small>${first[1]}</small></span></li><li><b>2</b><span>每一镜写一段动画代码，三镜同时写；写完自查，不过关的自动重写一次<small>每镜约 1–3 分钟</small></span></li><li><b>3</b><span>写好一镜就在本机逐帧渲染一镜，页面上马上能看<small>可以离开这一页，不会中断</small></span></li></ol></div>`;
}
const VOICE=`<div class="dv-opt" data-design-id="DV-VOICE"><h4>配音（可以之后再加）</h4><p>没有配音先出无声预览。上传配音以后，按配音实测每一镜的时长，动画比配音长的镜会自动改短。</p><div class="row"><button class="btn rv-go-log">画面问题记录</button><button class="btn">上传配音…</button></div></div>`;
const VOICE_HAND=`<div class="dv-opt" data-design-id="DV-VOICE"><h4>配音（从中台带过来）</h4><p><span data-design-data>${HAND_META.voice} · ${HAND_META.dur}</span>。生成时按这条配音实测每一镜的时长，动画比配音长的镜会自动改短。</p><div class="row"><button class="btn rv-go-log">画面问题记录</button><button class="btn">换一个配音…</button></div></div>`;
const opts=o=>`<aside class="dv-opts">${how(o)}${o.src==='handoff'?VOICE_HAND:VOICE}</aside>`;
const canGen=o=>hasLines(o)&&(o.mode==='base'?!!o.base:o.draft==='accepted');
function genbar(o){
 let txt,need=false;
 if(o.mode==='base'){const s=o.base,adj=(o.adjust||'').trim()?`，改：${esc(o.adjust.trim())}`:'';if(!s){txt='风格还没选：在下面选一个现成的风格，或者从头定';need=true;}else txt=s.lib?`风格：风格库「${esc(s.name)}」${adj}`:`风格：沿用「${esc(s.title)}」${s.time}${adj}`;}
 else if(o.draft==='accepted')txt='风格：刚定好的风格（从头定）';
 else {txt='风格还没定好：先点「先定风格」，满意了点「就用这个」';need=true;}
 if(!hasLines(o)){txt='分镜脚本还空着：先在上面粘贴或导入';need=true;}
 return `<div class="dv-genbar" data-design-id="DV-GENBAR"><p class="${need?'need':''}" data-design-data>${txt}</p><div class="actions">${btn('生成','data-generate'+(canGen(o)?'':' disabled'),true)}</div></div>`;
}
const PH='把台词粘贴进来，每一行会变成一镜。例如：&#10;清华 AI 体育博主，断更一年。会写代码，会练体能，就是发不出一条视频。&#10;第一句：发出去，会被人看低。';
const blank=d=>({d,v:'',sub:'',cam:'',aud:'',img:null});
const rowsOf=o=>o.rows||(o.src==='handoff'?HAND.map((r,i)=>({...r,img:{src:`img/hand-0${i+1}.jpg`,tag:'代码渲染'}})):SCRIPT.map((d,i)=>({...blank(d),img:o.rescript?{src:`img/job-0${i+1}.jpg`,clip:`img/job-0${i+1}.mp4`}:null})));
const hasLines=o=>rowsOf(o).some(r=>r.d.trim());
const timed=o=>o.src==='handoff'&&o.timed!==false;
const zoomHtml=(n,t,src,clip,stat)=>`<div class="sb-zoom${stat?' sb-zoom--static':''}" role="dialog" aria-label="第 ${n} 镜画面" data-design-id="DV-SB-ZOOM"><header><b data-design-data>第 ${n} 镜</b><span data-design-data>${t}</span><button type="button" class="link" data-zoom-close>关闭</button></header>${clip?`<video src="${clip}" poster="${src}" muted loop playsinline preload="metadata"></video>`:`<img src="${src}" alt="">`}</div>`;
function sbTimes(R,o){let t=0;return R.map(r=>{const a=t;t+=timed(o)?r.sec:r.d.trim()?sec(r.d):0;return [a,t];});}
function form(o={}){
 const R=rowsOf(o),L=R.filter(r=>r.d.trim()),nn=i=>String(i+1).padStart(2,'0'),T=sbTimes(R,o),tot=mmss(T.length?T[T.length-1][1]:0);
 const cell=(r,i,f,name)=>`<textarea rows="1" data-row="${i}" data-f="${f}" aria-label="第 ${nn(i)} 镜${name}" placeholder="${f==='v'?'写这一镜画什么（可不填）':'—'}"${r[f]?' data-design-data':''}>${esc(r[f])}</textarea>`;
 const tt=i=>R[i].d.trim()?mmss(T[i][0])+'–'+mmss(T[i][1]):'—';
 const pic=(r,i)=>r.img?`<button type="button" class="sb-pic" data-design-id="DV-SB-PIC" aria-label="放大第 ${nn(i)} 镜画面" data-n="${nn(i)}" data-t="${tt(i)}" data-src="${r.img.src}"${r.img.clip?` data-clip="${r.img.clip}"`:''}>${r.img.clip?`<video src="${r.img.clip}" poster="${r.img.src}" muted loop playsinline preload="metadata" aria-hidden="true"></video>`:`<img src="${r.img.src}" alt="">`}</button>`:`<div class="sb-pic sb-none" data-design-id="DV-SB-PIC">还没有画面</div>`;
 const rows=R.slice(0,o.limit||R.length).map((r,i)=>`<tr data-design-id="DV-SB-ROW"><td class="sb-t"><b data-design-data>${nn(i)}</b><span data-design-data>${r.d.trim()?mmss(T[i][0])+'–'+mmss(T[i][1]):'—'}</span></td><td class="sb-vc"><div class="sb-v">${pic(r,i)}<div class="sb-vt">${r.img&&r.img.tag?`<em class="sb-tag" data-design-data>${r.img.tag}</em>`:''}${cell(r,i,'v','画面')}</div></div>${o.zoom===i&&r.img?zoomHtml(nn(i),tt(i),r.img.src,r.img.clip,true):''}</td><td>${cell(r,i,'d','台词')}</td><td>${cell(r,i,'sub','字幕 / 花字')}</td><td>${cell(r,i,'cam','景别 · 运镜')}</td><td>${cell(r,i,'aud','音乐 / 音效')}</td></tr>`).join('');
 const src=o.src==='handoff'?`<p class="dv-sb-src" data-design-id="DV-SB-SOURCE"><span data-design-data>从中台交过来：「${TITLE}」第 ${HAND_META.rev} 版 · ${HAND_META.at} · 带配音（${HAND_META.voice} · ${HAND_META.dur}）。</span><span>在这里改只存在本机，不会改中台的分镜。</span></p>`
  :o.newer?`<p class="dv-sb-src" data-design-id="DV-SB-SOURCE"><span data-design-data>中台又交过来新的分镜：第 ${NEWER.rev} 版 · ${NEWER.at}。</span><button class="link" data-take-handoff>换成中台这版</button></p>`:'';
 const body=L.length||o.rows&&o.rows.length?`<div class="dv-sb-wrap"><table class="dv-sb" data-design-id="DV-SB-TABLE"><colgroup><col class="c-t"><col class="c-v"><col class="c-d"><col class="c-sub"><col class="c-cam"><col class="c-aud"></colgroup><thead><tr><th>镜头</th><th>画面</th><th>台词</th><th>字幕 / 花字</th><th>景别 · 运镜</th><th>音乐 / 音效<small>暂不进成片</small></th></tr></thead><tbody>${rows}${o.limit&&R.length>o.limit?`<tr class="sb-more"><td colspan="6">还有 ${R.length-o.limit} 镜，同上</td></tr>`:''}</tbody></table></div>`
  :`<div class="dv-sb-empty"><textarea data-row="0" data-f="d" aria-label="台词" placeholder="${PH}"></textarea></div>`;
 const note=L.length?`<span data-design-data>台词里按回车拆成两镜，台词开头按退格并到上一镜 · 时长${timed(o)?'按中台的配音':'按台词每秒 5.1 字估'}</span>`:'还没有分镜脚本。可以粘贴台词、导入分镜文件，或从中台交过来。';
 return `<section class="dv-form" data-design-id="DV-SCRIPT"><header><div><h3>分镜脚本</h3><span class="dv-script-sub" data-max-lines="1">每镜写台词，就是配音要念的话；画面、字幕、景别 · 运镜不写，由 Opus 定。</span></div>${L.length?`<span data-design-data>${L.length} 镜 · ${timed(o)?'':'约 '}${tot}</span>`:''}</header>${src}${body}<footer><p aria-live="polite">${note}</p><div class="actions">${btn('导入分镜文件')}</div></footer></section>`;
}
const growAll=root=>root.querySelectorAll('.dv-sb textarea').forEach(t=>{t.style.height='auto';t.style.height=t.scrollHeight+2+'px';});
const still=matchMedia('(prefers-reduced-motion: reduce)');
const clipSeen=new IntersectionObserver(es=>es.forEach(e=>{const v=e.target;if(e.isIntersecting&&!still.matches)v.play().catch(()=>{});else v.pause();}));
const playClips=root=>root.querySelectorAll('.sb-pic video,.sb-zoom video,.dv-poster video,.lib-grid video').forEach(v=>{if(still.matches&&v.closest('.sb-zoom'))v.controls=true;v.addEventListener('error',()=>{const i=new Image();i.src=v.poster;i.alt='';v.replaceWith(i);},{once:true});clipSeen.observe(v);});
function designRow(src){
 const s=src==='library'?LIBX('flat'):STYLES[0];
 return `<div class="dv-design" data-design-id="DV-DESIGN"><b>全片设计</b><span class="dv-design-src" data-design-data>${src==='library'?`用风格库「${esc(s.name)}」的风格`:src==='adjusted'?`在「${TITLE}」的风格上改过`:`沿用「${TITLE}」的风格`}</span>${[['背景',0],['主色',1],['强调色',2],['中性',3]].map(([n,i])=>`<span class="dv-sw"><i style="background:${i===2&&src==='adjusted'?'#E8B04A':s.pal[i]}"></i>${n}</span>`).join('')}${D('字号 '+s.type)}<p class="dv-design-line"><em>动作规矩</em><span data-design-data>${esc(s.sum)}</span></p><p class="dv-design-line"><em>不用</em><span class="dv-nots">${s.nots.map(b=>`<span data-design-data>${esc(b)}</span>`).join('')}</span></p></div>`;
}
const PENDING=`<div class="dv-design dv-design--pending" data-design-id="DV-DESIGN"><b>全片设计</b><span data-design-data>在「${TITLE}」的风格上改：强调色换成暖黄，其余不动。改好以后七镜都照它写。</span></div>`;
const mk=(st,name,html,on)=>on?html.replace(/^<(\w+) /,`<$1 data-design-state="${st}-${name}" `):html;
function frame(st,o={},on=true){
 const wrap=inner=>`<div class="frame"><img src="img/light-topbar.png" alt=""><div class="main"><section id="review-screen" class="review-screen single dv-direct">${TABS}${inner}</section></div>`;
 const blk=(name,html)=>`<div class="dv-body">${mk(st,name,html,on)}</div>`;
 if(st==='entry')return wrap(blk('steps',STEPS.entry)+blk('head',HEADS.entry))+`<img src="img/light-done-below.png" alt=""></div>`;
 if(st==='writing'||st==='composing')return wrap(blk('steps',STEPS[st])+blk('head',HEADS[st]))+`</div>`;
 if(st==='designing')return wrap(blk('steps',STEPS.designing)+blk('head',HEADS.designing)+blk('design',PENDING))+`</div>`;
 if(st==='inherited'||st==='adjusted'||st==='library')return wrap(blk('steps',STEPS.writing)+blk('head',HEADS.writing)+blk('design',designRow(st)))+`</div>`;
 const which=st==='first-empty'?'firstEmpty':st==='first-handoff'?'firstHand':st.startsWith('first')?'first':'rescript';
 return wrap(blk('steps',STEPS[which])+blk('head',HEADS[which])+`<div class="dv-body"><div class="dv-start" data-design-id="DV-START">${mk(st,'script',form(o),on)}${mk(st,'style',styleWide(o),on)}${mk(st,'opts',opts(o),on)}${mk(st,'gen',genbar(o),on)}</div></div>`)+`</div>`;
}
const B0={mode:'base',base:STYLES[0],rescript:true};
const STATES=[
 ['entry','生成过 · 「分镜脚本」那一格可点'],
 ['writing','正在写 · 入口灰掉（页头以下同现在，未画）'],
 ['composing','正在合成 · 入口灰掉（页头以下同现在，未画）'],
 ['rescript','改分镜脚本 · 默认沿用这条的风格',B0],
 ['rescript-zoom','改分镜脚本 · 点第 02 镜的画面，放大播放',{...B0,zoom:1}],
 ['rescript-adjust','改分镜脚本 · 沿用这条，写了改哪里',{...B0,adjust:'强调色换成暖黄，其余不动'}],
 ['rescript-newer','R282 · 改分镜脚本 · 中台又交过来新的版本',{...B0,newer:true}],
 ['rescript-other','改分镜脚本 · 换成另一条成片的风格',{...B0,base:STYLES[2]}],
 ['first-empty','第一次 · 分镜脚本还空着（「生成」灰）',{mode:'base',base:STYLES[0],rows:[],nolines:true}],
 ['first','第一次 · 只粘贴了台词（画面这些没写，由 Opus 定）· 默认沿用最近一条成片的风格',{mode:'base',base:STYLES[0]}],
 ['first-handoff','R282 · 第一次 · 中台交过来的分镜（六列都有、带画面图和配音）',{mode:'base',base:STYLES[0],src:'handoff'}],
 ['first-new','从头定 · 还没写说明（「先定风格」「生成」都灰）',{mode:'new'}],
 ['first-new-text','从头定 · 写好说明，可以「先定风格」',{mode:'new',text:DESC}],
 ['first-new-drafting','从头定 · Opus 正在定风格、写样张',{mode:'new',text:DESC,draft:'drafting'}],
 ['first-new-ready','从头定 · 样张出来了（还没「就用这个」，「生成」灰）',{mode:'new',text:DESC,draft:'ready',revise:'主色再深一点，标题再大一号'}],
 ['first-new-revising','从头定 · 按「再改一句」改样张',{mode:'new',text:DESC,draft:'revising',revise:'主色再深一点，标题再大一号'}],
 ['first-new-accepted','从头定 · 点了「就用这个」，可以生成',{mode:'new',text:DESC,draft:'accepted',revised:true}],
 ['first-new-failed','从头定 · 样张没定成',{mode:'new',text:DESC,draft:'failed'}],
 ['first-none-r278','这台电脑上还没有做过的成片（R278 单独上线时：只能从头定）',{mode:'new',none:true,nolib:true}],
 ['first-lib','R283 · 第一次 · 选了风格库里的「扁平插画」',{mode:'base',base:LIBX('flat'),lib:true}],
 ['first-none','R283 · 这台电脑上还没有做过的成片：只有风格库，还没选（「生成」灰）',{mode:'base',base:null,none:true,lib:true}],
 ['designing','沿用并改 · Opus 正在改全片设计（页头以下同现在，未画）'],
 ['inherited','沿用不改 · 直接写镜，全片设计写来源（页头以下同现在，未画）'],
 ['adjusted','沿用并改 · 改好以后的全片设计（页头以下同现在，未画）'],
 ['library','R283 · 用风格库的风格 · 全片设计写来源（页头以下同现在，未画）'],
];
const shrink=html=>`<div class="dv-direct cmp-fit"><div class="cmp-scale">${html}</div></div>`;
const fitCmps=()=>document.querySelectorAll('.cmp-fit').forEach(b=>{const k=Math.min(1,b.clientWidth/1182),s=b.firstElementChild;s.style.transform=`scale(${k})`;b.style.height=Math.ceil(s.offsetHeight*k)+'px';});
let zoomEl=null,zoomFrom=null;
function closeZoom(back=true){if(!zoomEl)return;zoomEl.remove();zoomEl=null;if(back&&zoomFrom)zoomFrom.focus({preventScroll:true});zoomFrom=null;}
function openZoom(b){closeZoom(false);const d=b.dataset,w=document.createElement('div');w.innerHTML=zoomHtml(d.n,d.t,d.src,d.clip);zoomEl=w.firstElementChild;document.body.append(zoomEl);const r=b.getBoundingClientRect();zoomEl.style.left=Math.min(r.right+8,innerWidth-zoomEl.offsetWidth-8)+'px';zoomEl.style.top=Math.max(8,Math.min(r.top-8,innerHeight-zoomEl.offsetHeight-8))+'px';zoomFrom=b;playClips(zoomEl);zoomEl.querySelector('[data-zoom-close]').focus({preventScroll:true});}
document.addEventListener('click',e=>{const b=e.target.closest('button.sb-pic');if(b){openZoom(b);return;}if(zoomEl&&(e.target.closest('[data-zoom-close]')||!zoomEl.contains(e.target)))closeZoom();});
addEventListener('keydown',e=>{if(e.key==='Escape')closeZoom();});
addEventListener('scroll',()=>closeZoom(false),{passive:true});
// 可点演示
let demo={view:'entry',o:{...B0,adjust:'',text:'',revise:''}};
let timer=null;
function toast(t){const el=document.createElement('div');el.className='toast';el.textContent=t;document.body.append(el);setTimeout(()=>el.remove(),2600);}
function keep(sel,fn){const box=document.querySelector('[data-demo]');const el=box.querySelector(sel);const pos=el?el.selectionStart:0;fn();renderDemo();const n=box.querySelector(sel);if(n){n.focus();n.setSelectionRange(pos,pos);}}
function reFocus(i,pos,f='d'){const t=document.querySelector(`[data-demo] [data-row="${i}"][data-f="${f}"]`);if(t){t.focus({preventScroll:true});t.setSelectionRange(pos,pos);}}
function renderDemo(){
 const box=document.querySelector('[data-demo]');
 box.innerHTML=demo.view==='entry'?frame('entry',{},false):frame('rescript',demo.o,false);
 growAll(box);playClips(box);
 const on=(sel,ev,fn)=>box.querySelectorAll(sel).forEach(el=>el.addEventListener(ev,fn));
 on('[data-rescript]','click',()=>{demo.view='rescript';demo.o={...B0,adjust:'',text:'',revise:''};demo.o.rows=rowsOf(demo.o);renderDemo();reFocus(0,0);});
 const L=()=>demo.o.rows||(demo.o.rows=rowsOf(demo.o));
 const J=(...xs)=>xs.filter(x=>(x||'').trim()).join('；');
 const TA='.dv-sb textarea,.dv-sb-empty textarea';
 on(TA,'input',e=>{const t=e.target,i=+t.dataset.row,f=t.dataset.f,p=t.selectionStart,A=L();A[i]=A[i]||blank('');A[i][f]=t.value;if(f==='d')demo.o.timed=false;renderDemo();reFocus(i,p,f);});
 on('.dv-sb textarea[data-f="d"]','keydown',e=>{const t=e.target,i=+t.dataset.row,p=t.selectionStart,q=t.selectionEnd,A=L(),r=A[i];
  if(e.key==='Enter'&&!e.isComposing&&e.keyCode!==229){e.preventDefault();A.splice(i,1,{...r,d:t.value.slice(0,p).trimEnd()},blank(t.value.slice(q).trimStart()));demo.o.timed=false;renderDemo();reFocus(i+1,0);}
  else if(e.key==='Backspace'&&p===0&&q===0&&i>0){e.preventDefault();const pr=A[i-1];A.splice(i-1,2,{d:pr.d+t.value,v:J(pr.v,r.v),sub:J(pr.sub,r.sub),cam:J(pr.cam,r.cam),aud:J(pr.aud,r.aud),img:pr.img||r.img});demo.o.timed=false;renderDemo();reFocus(i-1,pr.d.length);}});
 on('textarea[data-f="d"]','paste',e=>{const x=e.clipboardData.getData('text');if(!/\n/.test(x))return;e.preventDefault();const t=e.target,i=+t.dataset.row,A=L(),r=A[i]||blank('');const parts=(t.value.slice(0,t.selectionStart)+x+t.value.slice(t.selectionEnd)).split(/\r?\n/).map(y=>y.trim()).filter(Boolean);A.splice(i,1,...parts.map((d,j)=>j?blank(d):{...r,d}));demo.o.timed=false;renderDemo();const j=i+parts.length-1;reFocus(j,(A[j]||{d:''}).d.length);});
 on('[data-take-handoff]','click',()=>{demo.o.src='handoff';demo.o.newer=false;demo.o.timed=true;demo.o.rows=rowsOf({src:'handoff'});renderDemo();});
 on('[data-rescript-back]','click',()=>{demo.view='entry';renderDemo();});
 on('[data-mode]','click',e=>{demo.o.mode=e.currentTarget.dataset.mode;renderDemo();});
 on('[data-style]','click',e=>{demo.o.base=[...STYLES,...LIB].find(s=>s.id===e.currentTarget.dataset.style);renderDemo();});
 on('[data-adjust]','input',e=>keep('[data-adjust]',()=>demo.o.adjust=e.target.value));
 on('[data-desc]','input',e=>keep('[data-desc]',()=>demo.o.text=e.target.value));
 on('[data-revise]','input',e=>keep('[data-revise]',()=>demo.o.revise=e.target.value));
 on('[data-hint]','click',e=>{const h=e.currentTarget.dataset.hint;demo.o.text=((demo.o.text||'').replace(/\s+$/,'')+(demo.o.text?'\n':'')+h+'：');renderDemo();const t=box.querySelector('[data-desc]');t.focus();t.setSelectionRange(t.value.length,t.value.length);});
 on('[data-draft]','click',()=>{demo.o.draft='drafting';demo.o.revised=false;renderDemo();clearTimeout(timer);timer=setTimeout(()=>{demo.o.draft='ready';renderDemo();},1800);});
 on('[data-revise-go]','click',()=>{demo.o.draft='revising';renderDemo();clearTimeout(timer);timer=setTimeout(()=>{demo.o.draft='ready';demo.o.revised=true;renderDemo();},1800);});
 on('[data-accept]','click',()=>{demo.o.draft='accepted';renderDemo();});
 on('[data-redo]','click',()=>{demo.o.draft=undefined;demo.o.revise='';renderDemo();});
 on('[data-generate]','click',()=>toast(demo.o.mode==='new'?'新建一次生成：全片设计用刚定好的风格，第 01 镜直接用样张':(demo.o.adjust||'').trim()?'新建一次生成：Opus 先按你写的改全片设计，再写每一镜':'新建一次生成：直接沿用这套全片设计开始写每一镜'));
}
