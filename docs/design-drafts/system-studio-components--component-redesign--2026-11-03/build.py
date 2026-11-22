#!/usr/bin/env python3
"""把 origin/main 的真实页面包成 live/before 和 live/after；after 只多组件和下面的替换。"""
import re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).parent; SRC=Path(sys.argv[1]); OUT=ROOT/'live'
shutil.rmtree(OUT,ignore_errors=True)
# 打包工具按正则找 import，会把字符串里的 xx-import' 当成模块；只在稿子副本里转义，产品代码不动
def rel(t): return re.sub(r"""\bimport(?=["'])""",r"impor\\x74",_rel(t))
def _rel(t): return re.sub(r"""(from\s*['"]|import\(['"]|href="|src=")/(?=[\w-]+\.(?:js|css)\b)""",r'\1./',t)
for name in ('before','after'):
    d=OUT/name; shutil.copytree(SRC,d)
    for f in list(d.glob('*.js'))+[d/'index.html']: f.write_text(rel(f.read_text()))
    h=(d/'index.html').read_text()
    h=h.replace('<link rel="stylesheet" href="./styles.css">','<script src="../mock.js"></script>\n<link rel="stylesheet" href="./styles.css">')
    h=h.replace('@import','@import')
    (d/'index.html').write_text(h)
    s=d/'styles.css'; s.write_text(re.sub(r"@import url\([^)]*\);\n?",'',s.read_text()))
shutil.copy(ROOT/'src/mock.js',OUT/'mock.js')
A=OUT/'after'; shutil.copy(ROOT/'src/components.js',A); shutil.copy(ROOT/'src/components.css',A)
h=(A/'index.html').read_text(); (A/'index.html').write_text(h.replace('</head>','<link rel="stylesheet" href="./components.css">\n</head>'))
v=A/'review-view.js'; t=v.read_text()
def sub(old,new):
    global t
    if t.count(old)!=1: sys.exit(f'替换点不是恰好一处（{t.count(old)}）：{old[:70]}')
    t=t.replace(old,new)
sub("import {mediaSummary,","import {statusBadge,factStrip,stepEmpty,statTiles,stageTrack,mediaMeta} from './components.js';\nimport {mediaSummary,")
sub("const chip=status?`<span class=\"chip\">${status}</span>`:'';","const chip='';")
sub("<small>${[withProject?D(group?.title):'',p.date?D(p.date):'',`<span>${media(p)}</span>`].filter(Boolean).join(' · ')}</small>${p.cover||(!chip&&!play)?'':`<div class=\"chips\">${chip}${play}</div>`}</div></article>`",
    "${stageTrack(p)}<small>${[withProject?`<span>${D(group?.title)}</span>`:'',p.date?`<span>${D(p.date)}</span>`:'',mediaMeta(p)].filter(Boolean).join('')}</small>${p.cover||(!chip&&!play)?'':`<div class=\"chips\">${chip}${play}</div>`}</div></article>`")
sub("`<div class=\"cap-row\"><i class=\"dot ${['可用','装在本仓库里，可用','Codex 可用','经广州服务器，可用'].includes(value)?'dot--ok':''}\"></i><div>${name}<small>${value}</small></div></div>`",
    "`<div class=\"cap-row\"><span>${name}</span>${statusBadge(/可用/.test(value)?'可用':value)}</div>`")
sub("<div class=\"empty\" data-design-id=\"R208-INBOX-empty\"><h2>没有要整理的新素材</h2><p>从手机或相机导入的照片和视频，会按拍摄时间和地点自动分成一批批放在这里，你决定每一批放进哪个项目。太短、损坏、完全重复的会列出来让你勾选删除。原文件不会被改动。</p><div class=\"facts\"><span>已整理进项目的作品<b data-design-data>${catalog.pieces.length}</b>件</span><span>视频<b data-design-data>${catalog.pieces.reduce((a,p)=>a+p.videos,0)}</b>段</span><span>照片<b data-design-data>${catalog.pieces.reduce((a,p)=>a+p.photos,0)}</b>张</span></div><div class=\"actions\">${button('导入照片和视频','data-new',true)}${button('去看项目','data-go=\"projects\"')}</div></div>",
    "${stepEmpty('没有要整理的新素材',[['inbox','导入','手机或相机'],['split','自动分批','按时间和地点'],['folder','你定去处','放进哪个项目']],statTiles([[catalog.pieces.length,'件','作品'],[catalog.pieces.reduce((a,p)=>a+p.videos,0),'段','视频'],[catalog.pieces.reduce((a,p)=>a+p.photos,0),'张','照片']])+factStrip([['lock','原文件不动'],['star','太短、损坏、重复的由你勾选删']]),button('导入照片和视频','data-new',true)+button('去看项目','data-go=\"projects\"'))}")
sub("function row(title,note='',value='') {return `<div class=\"setrow\"><div><strong>${title}</strong>${note?`<small>${note}</small>`:''}</div><span class=\"val\">${value}</span></div>`;}",
    "function row(title,note='',value='') {const plain=value.replace(/<[^>]+>/g,'');const known=['可用','没连上','已连接','未连接','已配置','没配置','已登录','没登录','暂不支持'].includes(plain);return `<div class=\"setrow\"><div><strong>${title}</strong>${note?`<small>${note}</small>`:''}</div><span class=\"val\">${known?statusBadge(plain):value}</span></div>`;}")
sub("<p>素材、成片、音乐都在本机这个文件夹里，不上传。</p>${row('素材根',`${D(catalog.groups.length)} 个项目 · ${D(catalog.pieces.length)} 件作品`)}${row('音乐库','',`${D((await api('/api/review/music')).tracks.length)} 首`)}${row('素材库','',`${D(state.assetStatistics?.asset_count||0)} 项`)}",
    "${factStrip([['lock','都在本机'],['one','不上传']])}${statTiles([[catalog.groups.length,'个','项目'],[catalog.pieces.length,'件','作品'],[(await api('/api/review/music')).tracks.length,'首','音乐库'],[state.assetStatistics?.asset_count||0,'项','素材库']])}")
sub("<p>写脚本、挑镜头时看图都用这里的模型。密钥只存本机。</p>","${factStrip([['scissors','写脚本、挑镜头都用'],['lock','密钥只存本机']])}")
sub("<p>连上后能在网页中台看任务进度。不连也不影响本机创作。</p>","${factStrip([['link','连上能看任务进度'],['one','不连也能创作']])}")
sub("<p>只在你粘贴链接时下载那一首，不批量抓取。</p>","${factStrip([['down','粘贴链接，下那一首'],['one','不批量抓取']])}")
sub("<p>出草稿时 ChatCut 连上就用 ChatCut，否则用剪映。没连上的不会被悄悄换掉，会在工作台提醒你。</p>","${factStrip([['route','优先 ChatCut，没连上用剪映'],['bell','换了会在工作台提醒']])}")
sub("<div class=\"empty\" data-design-id=\"R208-LIBRARY-empty\"><h2>素材库还是空的</h2><p>在作品的「挑镜头」里选中一个镜头，点「收进素材库」，它就会出现在这里，别的作品也能直接用。</p><div class=\"actions\">${button('去看项目','data-go=\"projects\"',true)}${button('登记素材','data-register-asset')}</div></div>",
    "${stepEmpty('素材库还是空的',[['scissors','挑镜头','在作品里选中'],['star','收进素材库','点一下就行'],['repeat','到处复用','别的作品直接用']],'',button('去看项目','data-go=\"projects\"',true)+button('登记素材','data-register-asset'))}")
v.write_text(t); print('built')
