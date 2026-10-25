#!/usr/bin/env python3
"""从 R276 的可交互稿 direct.html 生成 R277 的 revise.html：上面的步骤条、全片设计、七镜胶片原样沿用，
只换掉选中一镜后的详情（DV-REWRITE 一带），并加一页「画面问题记录」。

用法（仓库根目录）：python3 docs/tasks/R277-shot-visual-revision/design/build_revise.py
R276 的稿改了以后重跑一遍即可；替换不上会报错，不会悄悄生成半成品。
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / 'R276-direct-video-opus/design/direct.html'
EXTRA = (HERE / 'revise-extra.js').read_text(encoding='utf-8')
RV_LINE = "const RV_STATES=[['review','第 02 镜：画面上标出 Opus 看出的 3 处'],['select','点了画面上的「约 25%」'],['picked','选好 3 处改法，补了一句'],['rewriting2','正在重写第 02 镜'],['compare','重写好了：第 1 版和第 2 版'],['kept-prev','退回第 1 版'],['saved','第 01 镜存为样例'],['review-failed','Opus 没看成画面'],['log','画面问题记录']];"
CSS = (HERE / 'revise-extra.css').read_text(encoding='utf-8')
s = SRC.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f'R276 的稿变了，找不到（或不止一处）：{old[:60]!r}，出现 {n} 次')
    s = s.replace(old, new)


rep('href="base.css"', 'href="../../R276-direct-video-opus/design/base.css"')
rep('src="shots-data.js"', 'src="../../R276-direct-video-opus/design/shots-data.js"')
rep('</style>', CSS + '\n</style>')
rep('// ---------- 页面 ----------', EXTRA + '\n// ---------- 页面 ----------')
# 状态：本稿只有「七镜都写好」之后的改画面流程
rep("const STATES=[['empty'", "const STATES_R276=[['empty'")
rep("let st=(new URLSearchParams", RV_LINE + "\nconst STATES=RV_STATES;\nlet st=(new URLSearchParams")
# 胶片上第 02 镜在重写时显示「正在重写」
rep("  if(st==='rewriting') return i===2?['rewriting']:['rendered'];", "  if(st==='rewriting') return i===2?['rewriting']:['rendered'];\n  if(rv==='rewriting2') return i===1?['rewriting']:['rendered'];")
# 详情换成本稿的；「七镜都写好」的页头多一个「画面问题记录」入口
rep("+designRow()+film()+detail();\n  else if(st==='composing')", "+designRow()+film()+(rv?detail2():detail());\n  else if(st==='composing')")
rep("C.btn('上传配音…',{toast:'选择一个 WAV 文件；上传后按配音实测每镜时长'})", "C.btn('画面问题记录',{cls:'rv-go-log'})+C.btn('上传配音…',{toast:'选择一个 WAV 文件；上传后按配音实测每镜时长'})")
rep("  $('#screen').innerHTML=ptabs()+flow()+body;\n  bind();", "  if(rv==='log') body=logPage();\n  $('#screen').innerHTML=(rv==='log'?'':ptabs()+flow())+body;\n  bind(); bind2();")
rep("function go(){const q=new URLSearchParams(location.hash.slice(1));st=q.get('s')||'empty';if(!STATES.some(([k])=>k===st))st='empty';if(playing){clearInterval(playing);playing=null;}sel=st==='failed-shot'?4:st==='rewriting'?2:0;render();mock();}",
    "function go(){const q=new URLSearchParams(location.hash.slice(1));rv=q.get('s')||'review';if(!STATES.some(([k])=>k===rv))rv='review';st='ready';if(playing){clearInterval(playing);playing=null;}sel=rv==='saved'?0:1;rvReset();render();mock();}")
(HERE / 'revise.html').write_text(s, encoding='utf-8')
print('写出', HERE / 'revise.html')
