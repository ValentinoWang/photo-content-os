"""Stage 2e smoke. Counts are cumulative, claimed before send, never reset.

Run IDs are exclusive. A second request requires a recorded offline repair/test.
Use --refresh-node only after that repair; old response files are never deleted.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
from music_library.cache import read_json, write_json, request_cache_key
from music_library.errors import MusicError
from music_library.library import MusicLibrary
from music_library.links import parse_link
from music_library.platforms import PlatformAdapter
from music_library.network import MusicOpener
from music_library.egress import read_target
import music_library.egress as egress

cli=argparse.ArgumentParser()
cli.add_argument('--run', type=int, required=True)
cli.add_argument('--platforms', nargs='+', choices=['netease','qishui','douyin'], default=['netease','qishui','douyin'])
cli.add_argument('--seed-run', type=int)
cli.add_argument('--refresh-node', action='append', default=[])
args=cli.parse_args()
OUT=Path(__file__).resolve().parent
library=MusicLibrary()
ledger_path=library.root/'.request-grants/R210-phase2e.json'
ledger=read_json(ledger_path,'阶段 2e 请求账本')
assert read_target(), 'External SSH egress config required'
marker=ledger_path.with_name(f'R210-phase2e-run-{args.run}.json')
with os.fdopen(os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:
    json.dump({'run':args.run,'platforms':args.platforms},f)
cache_base=library.root/'.http-cache/R210-phase2e'
for platform in args.platforms:
    target=cache_base/platform/f'run-{args.run}'
    if target.exists(): raise MusicError('本轮缓存已存在，拒绝覆盖')
    if args.seed_run:
        seed=cache_base/platform/f'run-{args.seed_run}'
        # Original cache remains untouched; seed a fresh partition with unaffected responses only.
        excluded={row['cache_key'] for row in ledger['requests'] if row['node'] in args.refresh_node}
        skip={key+suffix for key in excluded for suffix in ('.json','.body')}
        shutil.copytree(seed,target,ignore=lambda directory,names: [name for name in names if name in skip])
    else:
        target.mkdir(parents=True,mode=0o700)

history=PlatformAdapter(library.root/'.http-cache')
tunnels=[]
original_tunnel=egress.SSHTunnel
class AuditedTunnel(original_tunnel):
    def __init__(self,*a,**k):
        super().__init__(*a,**k);tunnels.append(self)
egress.SSHTunnel=AuditedTunnel
class Adapter(PlatformAdapter):
    current_platform=None
    resolved=None
    @contextmanager
    def import_context(self,platform):
        self.current_platform=platform
        self.cache_root=cache_base/platform/f'run-{args.run}'
        from music_library.cache import CachedHTTP
        self.http=CachedHTTP(self.cache_root,opener=MusicOpener(proxy=''))
        self.engine=None
        with super().import_context(platform): yield
    def cached_identity(self,link): return history.cached_identity(link)
    def resolve(self,link):
        result=super().resolve(link)
        self.resolved={key:result.get(key) for key in ('title','artist','platform_id','expected_duration')}
        return result
adapter=Adapter(cache_base)
library.adapter=adapter
original_open=MusicOpener.open

def guarded_open(transport,request,timeout):
    platform=adapter.current_platform
    part=urlsplit(request.full_url)
    route='ssh-egress' if transport.proxy else 'direct'
    if (platform in ('netease','qishui')) != bool(transport.proxy): raise MusicError('出口路由不符，拒绝联网')
    node=None
    if platform=='netease' and part.hostname=='interface3.music.163.com':
        node={'/api/v3/song/detail':'detail','/eapi/song/enhance/player/url/v1':'player'}.get(part.path)
    elif platform=='qishui' and part.hostname=='music.douyin.com' and part.path=='/qishui/share/track': node='page'
    elif platform=='douyin' and part.hostname=='ttwid.bytedance.com' and part.path=='/ttwid/union/register/': node='anonymous-registration'
    elif platform=='douyin' and part.hostname=='www.douyin.com' and part.path=='/aweme/v1/web/aweme/detail/': node='detail'
    elif part.hostname and part.hostname.endswith(('.music.126.net','.douyinvod.com','.byteimg.com','.douyinpic.com')): node='audio'
    if not node: raise MusicError('出现范围外节点，未请求')
    name=platform+':'+node
    used=sum(row['node']==name for row in ledger['requests'])
    if used>=2: raise MusicError('该节点已用满两次，禁止第三次请求')
    if used:
        repairs=[r for r in ledger['repairs'] if r['node']==name and r['consumed_at_repair']==used]
        if not repairs: raise MusicError('第二次请求缺少离线修复和回归证据，未请求')
        repair=repairs[-1]
        source=ROOT/repair.get('source','scripts/music_library/network.py')
        proof=OUT/repair['tests']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=repair['source_sha256'] or hashlib.sha256(proof.read_bytes()).hexdigest()!=repair['tests_sha256']:
            raise MusicError('离线修复或测试摘要已变化，未请求')
        for related, digest in repair.get('related_sources', {}).items():
            if hashlib.sha256((ROOT/related).read_bytes()).hexdigest()!=digest:
                raise MusicError('相关修复源码已变化，未请求')
    headers={k.lower():v for k,v in request.header_items()}
    content_type=headers.get('content-type') or ('application/x-www-form-urlencoded' if request.data is not None else None)
    shape={'header_names':sorted(set(headers)|({'content-type'} if content_type else set())),
           'content_type':content_type,'body_bytes':len(request.data or b''),'cookie_present':'cookie' in headers}
    row={'node':name,'number':used+1,'run':args.run,'method':request.get_method(),'route':route,'host':part.hostname,
         'path':part.path,'cache_key':request_cache_key(request.full_url,request.data),'state':'claimed','request_structure':shape}
    ledger['requests'].append(row);write_json(ledger_path,ledger)
    print(name,used+1,route,'claimed',flush=True)
    try:
        response=original_open(transport,request,timeout)
        row.update(state='response',status=response.code)
        return response
    except BaseException as exc:
        row.update(state='failed',exception_type=type(exc).__name__)
        raise
    finally: write_json(ledger_path,ledger)
MusicOpener.open=guarded_open
inputs={
'netease':'分享Rich Edwards/Emelie的单曲《Turn Back Time》https://163cn.tv/bi1PoHIY (@网易云音乐)',
'qishui':'《Fever Pitch》@汽水音乐 https://qishui.douyin.com/s/iXGDYc11/',
'douyin':'8.79 复制打开抖音，看看【歪头美啦的图文作品】开智的小曲。# vibe知识大赏 # ai小曲 https://v.douyin.com/iSj4d8_TFGA/ qre:/ m@Q.KW :9pm 04/26'}
results=[]
try:
    for platform in args.platforms:
        text=inputs[platform];link=parse_link(text)
        path=library.root/'.attempts'/(hashlib.sha256(link.key.encode()).hexdigest()+'.json')
        if path.exists() and read_json(path,'历史记录').get('state')!='complete':
            archive=library.root/f'.attempt-history/R210-phase2e/run-{args.run}'
            archive.mkdir(parents=True,exist_ok=True)
            dest=archive/path.name
            if dest.exists(): raise MusicError('归档已存在，拒绝覆盖')
            path.rename(dest)
        adapter.resolved=None
        before=len(ledger['requests'])
        row={'platform':platform}
        try:
            status,track=library.import_link(text)
            row.update(status=status,title=track['title'],artist=track['artist'],file_sha256=track['file_sha256'],
                       duration_seconds=track['duration_seconds'],resolved=adapter.resolved,license_status=track['license_status'])
            audio=library.root/track['file_sha256']/track['audio_file']
            probe=subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries',
                'stream=codec_name,sample_rate,duration:format=duration','-of','json',str(audio)],capture_output=True,text=True,check=True,timeout=60)
            row['ffprobe']=json.loads(probe.stdout)
            decode=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-err_detect','explode','-i',str(audio),
                '-map','0:a:0','-f','null','-'],capture_output=True,timeout=300)
            row['full_decode_exit_code']=decode.returncode
            assert decode.returncode==0
            if adapter.resolved:
                assert abs(track['duration_seconds']-adapter.resolved['expected_duration'])<=2
            count,starts=len(ledger['requests']),sum(t.starts for t in tunnels)
            repeat,_=library.import_link(text)
            row['repeat']={'status':repeat,'network_requests':len(ledger['requests'])-count,'tunnel_starts':sum(t.starts for t in tunnels)-starts}
            assert repeat=='已在库里' and row['repeat']['network_requests']==row['repeat']['tunnel_starts']==0
        except MusicError as exc:
            row.update(status='failed',reason=str(exc),failure=getattr(exc,'diagnostic',None),resolved=adapter.resolved)
        except Exception as exc:
            row.update(status='failed',reason='本地验证失败，需离线排查',exception_type=type(exc).__name__,resolved=adapter.resolved)
        row['new_requests']=len(ledger['requests'])-before
        results.append(row)
        print(platform,row['status'],row.get('reason',row.get('title')),flush=True)
finally:
    for tunnel in tunnels:tunnel.close()
    MusicOpener.open=original_open;egress.SSHTunnel=original_tunnel
    counts={name:sum(row['node']==name for row in ledger['requests']) for name in sorted({r['node'] for r in ledger['requests']})}
    summary={'run':args.run,'results':results,'cumulative_counts':counts,'requests':[{**r,'path':'[media path redacted]'} if r['node'].endswith(':audio') else r for r in ledger['requests']],
        'tunnels':[{'pid':t.process.pid if t.process else None,'starts':t.starts,'closed':t.process is None or t.process.poll() is not None} for t in tunnels],
        'library':[{'title':t['title'],'platform':t['platform'],'file_sha256':t['file_sha256'],'duration_seconds':t['duration_seconds']} for t in library.list_tracks()]}
    write_json(OUT/f'run-{args.run}-results.json',summary)
