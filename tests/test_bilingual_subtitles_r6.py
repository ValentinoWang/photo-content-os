"""Bilingual captions share one safe backplate and preserve frame-cut coverage."""
import copy,json,tempfile,unittest
from pathlib import Path
import pytest
from _support import load_script
s=load_script('video_subtitles','bilingual_subtitles_r6')

def descriptor(english='A modest test can reveal an unexpected answer.'):
 text='先记录预期，然后用一次小尝试检验，再逐条对照真实结果。'
 d={'script':text,'narration':{'sentenceTimings':[{'text':text,'startSeconds':0,'endSeconds':4}]},'shots':[{'shot':{'endSeconds':2}},{'shot':{'endSeconds':4}}]}
 if english is not None:d['narration']['sentenceTimings'][0]['englishText']=english
 return d

def check_bilingual_style_has_shared_safe_box_and_darker_english():
 style=s.bilingual_layout(['中文字幕第一行','中文字幕第二行'],'A small test.',1080,1920)
 assert .55<=style['englishFontSize']/style['fontSize']<=.60
 assert style['boxTop']>=1536 and style['boxTop']+style['boxHeight']<=1920
 assert style['englishTop']>style['chineseTop'] and style['sharedBackplate']
 def luminance(v):
  x=v/255;return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
 assert (luminance(207)+.05)/(luminance(64)+.05)>=4.5
 assert style['englishColor']=='0xcfcfcf'

def check_long_english_shrinks_then_wraps_at_most_two_lines_without_loss():
 en='A careful observation records the expectation before the action and compares it with the actual outcome afterward.'
 x=s.bilingual_layout(['中文字幕'],en,1080,1920)
 assert x['englishFontSize']<=round(x['fontSize']*.58)
 assert 1<=len(x['englishLines'])<=2
 assert ' '.join(x['englishLines'])==en
 assert all(s.caption_text_width(line,x['englishFontSize'])<=x['maxTextWidth'] for line in x['englishLines'])
 with pytest.raises(Exception,match='photo_subtitle_english_too_long'):s.bilingual_layout(['中文'],'word '*1000,1080,1920)

def check_cuts_continue_both_languages_and_cover_every_spoken_frame():
 d=descriptor();before=copy.deepcopy(d);cues=s.build_subtitle_cues(d,fps=30,total_frames=120)
 assert d==before and all(c.get('englishText') for c in cues)
 assert ' '.join(c['englishText'] for c in cues)==d['narration']['sentenceTimings'][0]['englishText']
 for frame in range(119):assert sum(c['startFrame']<=frame<c['endFrame'] for c in cues)==1
 assert all(not(c['startFrame']<60<c['endFrame']) for c in cues)
 assert next(c for c in cues if c['startFrame']<=60<c['endFrame'])['startFrame']==60

def check_absent_english_keeps_single_layer_and_sidecar_is_readable(tmp_path):
 path=tmp_path/'caption.srt';cues=s.write_direct_subtitles(descriptor(None),path,fps=30,total_frames=120)
 assert all('englishText' not in c for c in cues)
 s.write_direct_subtitles(descriptor(),path,fps=30,total_frames=120)
 data=json.loads(path.with_suffix('.frames.json').read_text())
 assert all(c['englishText'] for c in data['cues'])
 assert 'A modest test' in path.read_text()

def check_real_burn_contains_two_layers_in_one_safe_backplate(tmp_path):
 import shutil,subprocess
 if not shutil.which('ffmpeg'):(_ for _ in ()).throw(unittest.SkipTest('FFmpeg required'))
 video=tmp_path/'source.mp4';out=tmp_path/'out.mp4';sub=tmp_path/'sub.srt'
 subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=white:s=1080x1920:r=30:d=0.5','-f','lavfi','-i','anullsrc=r=8000:cl=mono','-shortest','-c:v','libx264','-threads','1','-preset','ultrafast','-c:a','aac',str(video)],check=True,capture_output=True)
 d={'script':'准备好了再出发。','narration':{'sentenceTimings':[{'text':'准备好了再出发。','englishText':'Get ready, then begin.','startSeconds':0,'endSeconds':.5}]},'shots':[{'shot':{'endSeconds':.5}}]}
 s.write_direct_subtitles(d,sub,fps=30,total_frames=15);s.burn_subtitles(video,sub,out)
 from PIL import Image
 import io
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-vf','select=eq(n\\,3)','-frames:v','1','-f','image2pipe','-vcodec','png','-'])
 image=Image.open(io.BytesIO(raw)).convert('RGB');layout=json.loads(out.with_suffix('.subtitle-style.json').read_text())['bilingualLayouts'][0]
 assert layout['boxTop']>=1536 and layout['boxTop']+layout['boxHeight']<=1920
 # Actual decoded English glyphs are grey on the same dark rectangle as Chinese.
 en=image.crop((72,layout['englishTop'],1008,layout['englishTop']+layout['englishFontSize']+3));pixels=list(en.getdata());assert sum(150<min(p)<230 for p in pixels)>50
 assert min(image.getpixel((540,layout['boxTop']+2)))<100


class BilingualCaptionTests(unittest.TestCase):
 def test_style_and_contrast(self):check_bilingual_style_has_shared_safe_box_and_darker_english()
 def test_english_wrapping(self):check_long_english_shrinks_then_wraps_at_most_two_lines_without_loss()
 def test_cut_continuation(self):check_cuts_continue_both_languages_and_cover_every_spoken_frame()
 def test_single_layer_and_readback(self):
  with tempfile.TemporaryDirectory() as directory:check_absent_english_keeps_single_layer_and_sidecar_is_readable(Path(directory))
 def test_real_two_layer_burn(self):
  with tempfile.TemporaryDirectory() as directory:check_real_burn_contains_two_layers_in_one_safe_backplate(Path(directory))
