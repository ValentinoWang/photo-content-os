"""One remaining anonymous SSR request. Never rerun or reset the ledger."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'scripts'))
from music_library.cache import CachedHTTP,read_json,write_json,request_cache_key
from music_library.errors import MusicError
from music_library.library import MusicLibrary
from music_library.links import parse_link
from music_library.network import MusicOpener
from music_library.platforms import PlatformAdapter
from music_library.douyin_share import IPHONE_SAFARI
OUT=Path(__file__).resolve().parent
lib=MusicLibrary()
ledger_path=lib.root/'.request-grants/R210-phase2f.json'
ledger=read_json(ledger_path,'本轮请求账本')
assert sum(r['node']=='douyin:share-note' for r in ledger['requests'])==1
for file,digest in ledger['repair']['source_sha256'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest
assert hashlib.sha256((OUT/'focused-initial.log').read_bytes()).hexdigest()==ledger['repair']['proof_sha256']
cache=lib.root/'.http-cache/R210-phase2f'
assert not cache.exists(),'Run cache already exists; refuse another smoke'
class Adapter(PlatformAdapter):
    resolved=None
    def resolve(self,link):
        result=super().resolve(link);self.resolved=result;return result
class Opener:
    proxy=''
    def __init__(self):self.transport=MusicOpener(proxy='')
    def open(self,request,timeout):
        assert not request.has_header('Cookie')
        if request.full_url=='https://www.iesdouyin.com/share/note/7694712348003151717/':
            name='douyin:share-note';assert request.get_header('User-agent')==IPHONE_SAFARI
        elif adapter.resolved and request.full_url==adapter.resolved['url'].replace('http://','https://',1):
            name='douyin:audio'
        else:raise MusicError('不在本轮授权节点范围内，未联网')
        count=sum(r['node']==name for r in ledger['requests'])
        if count>=2 or (name=='douyin:audio' and count>=1):raise MusicError('节点额度不足，未联网')
        row={'node':name,'number':count+1,'method':request.get_method(),'route':'direct','cookie_present':False,
             'user_agent':'iPhone Safari' if name.endswith('share-note') else 'default','follow_redirects':False if name.endswith('share-note') else None,
             'cache_key':request_cache_key(request.full_url,request.data),'state':'claimed'}
        ledger['requests'].append(row);write_json(ledger_path,ledger)
        try:
            response=self.transport.open(request,timeout);row.update(state='response',status=response.code);return response
        except BaseException as exc:row.update(state='failed',exception_type=type(exc).__name__);raise
        finally:write_json(ledger_path,ledger)
http=CachedHTTP(cache,opener=Opener())
adapter=Adapter(lib.root/'.http-cache',http=http)
lib.adapter=adapter
text='8.79 复制打开抖音，看看【歪头美啦的图文作品】开智的小曲。# vibe知识大赏 # ai小曲 https://v.douyin.com/iSj4d8_TFGA/ qre:/ m@Q.KW :9pm 04/26'
link=parse_link(text);attempt=lib.root/'.attempts'/(hashlib.sha256(link.key.encode()).hexdigest()+'.json')
archive=lib.root/'.attempt-history/R210-phase2f';archive.mkdir(parents=True)
if attempt.exists():attempt.rename(archive/attempt.name)
result={}
try:
    status,track=lib.import_link(text)
    result.update(status=status,title=track['title'],duration_seconds=track['duration_seconds'],expected_duration=adapter.resolved['expected_duration'],file_sha256=track['file_sha256'])
    audio=lib.root/track['file_sha256']/track['audio_file']
    probe=subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_name,sample_rate,duration:format=duration','-of','json',str(audio)],capture_output=True,text=True,check=True,timeout=60)
    result['ffprobe']=json.loads(probe.stdout)
    decoded=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-err_detect','explode','-i',str(audio),'-map','0:a:0','-f','null','-'],capture_output=True,timeout=300)
    result['full_decode_exit_code']=decoded.returncode;assert decoded.returncode==0
    assert abs(track['duration_seconds']-adapter.resolved['expected_duration'])<=2
    before=http.network_calls;repeat,_=lib.import_link(text)
    result['repeat']={'status':repeat,'requests':http.network_calls-before,'tunnel_starts':0}
except MusicError as exc:result.update(status='failed',reason=str(exc),failure=getattr(exc,'diagnostic',None))
finally:
    http.opener.transport.session.close()
    result.update(network_requests=http.network_calls,tunnel_starts=0,requests=[r for r in ledger['requests'] if r.get('inherited_from') is None and r['node'] in ('douyin:share-note','douyin:audio')])
    write_json(OUT/'real-import-results.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
