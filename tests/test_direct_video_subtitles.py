"""Speech source, legibility and exact-frame regressions for direct candidates."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _support import load_script
candidate = load_script('video_candidate', 'direct_subtitle_candidate')


class SubtitleSourceTests(unittest.TestCase):
    def test_direct_projection_uses_spoken_sentences_not_storyboard_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source.wav'; video = root / 'native.mp4'
            source.touch(); video.touch()
            descriptor = {
                'script': '口播第一句。口播第二句。',
                'narration': {'sentenceTimings': [
                    {'text': '口播第一句。', 'startSeconds': 0, 'endSeconds': 1},
                    {'text': '口播第二句。', 'startSeconds': 1, 'endSeconds': 2}]},
                'shots': [{'shot': {'startSeconds': 0, 'endSeconds': 2}, 'subtitle': '这只是画面要点'}]}
            metadata = {'streams': [{'codec_type': 'video', 'duration': '2', 'avg_frame_rate': '30/1'}], 'format': {'duration': '2'}}
            captured = []
            class StopAfterSource(Exception):
                pass
            def observe(_video, subtitles, _output):
                captured.append(subtitles.read_text()); raise StopAfterSource()
            with patch.object(candidate, 'probe_media', return_value=metadata), \
                 patch.object(candidate, 'review_module') as review, \
                 patch.object(candidate, 'burn_subtitles', side_effect=observe):
                review.return_value.check_output_video.return_value = {'checks': [{'check': 'subtitles', 'status': 'passed'}]}
                with self.assertRaises(StopAfterSource):
                    candidate.project_candidate(native={'status': 'completed', 'candidate': str(video), 'checks': {'frames': 60}},
                        descriptor=descriptor, source=source, original_hashes={source: '0'*64}, output_dir=root/'return', workspace=root)
            self.assertIn('口播第一句。', captured[0]); self.assertIn('口播第二句。', captured[0])
            self.assertNotIn('画面要点', captured[0])
            self.assertEqual(len(candidate.review_module().read_srt_cues(root/'return/subtitles.srt')), 2)


@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for rendered subtitle evidence')
class RenderedSubtitleTests(unittest.TestCase):
    def run_ffmpeg(self, *args):
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', *args], check=True, capture_output=True, timeout=180)

    def frames(self, video, indices):
        expr = '+'.join(f'eq(n,{n})' for n in indices)
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video), '-vf', f"select='{expr}'", '-fps_mode', 'vfr', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
        info = candidate.probe_media(video); stream = next(s for s in info['streams'] if s['codec_type']=='video')
        size = stream['width'] * stream['height'] * 3
        self.assertEqual(len(raw), len(indices)*size)
        return [raw[i*size:(i+1)*size] for i in range(len(indices))], stream['width'], stream['height']

    def test_real_cut_first_frames_80166667_and_122866667(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source.mp4'; output=root/'captioned.mp4'; subtitles=root/'subtitles.srt'
            self.run_ffmpeg('-f','lavfi','-i','color=white:s=320x568:r=30:d=123', '-f','lavfi','-i','anullsrc=r=8000:cl=mono',
                '-shortest','-c:v','libx264','-threads','1','-preset','ultrafast','-c:a','aac',str(source))
            subtitles.write_text('1\n00:00:00,000 --> 00:01:20,167\n上一镜的字幕还没有结束\n\n2\n00:01:20,167 --> 00:02:02,867\n本镜字幕\n\n3\n00:02:02,867 --> 00:02:03,000\n最后一镜的字幕\n')
            candidate.burn_subtitles(source, subtitles, output)
            frames,w,h=self.frames(output,[2404,2405,2406,3685,3686,3687])
            for cut,before,first,next_frame in [(80.166667,frames[0],frames[1],frames[2]),(122.866667,frames[3],frames[4],frames[5])]:
                a=first[int(h*.8)*w*3:]; b=next_frame[int(h*.8)*w*3:]
                error=sum(abs(x-y) for x,y in zip(a,b))/len(a)
                with self.subTest(cut=cut):
                    self.assertLess(error, .25, f'{cut}: previous cue remains on first frame; mean difference={error}')
                    previous=before[int(h*.8)*w*3:]
                    changed=sum(abs(x-y) for x,y in zip(previous,a))/len(a)
                    self.assertGreater(changed,1,f'{cut}: caption must change on the first frame, not remain blank or old')

    def test_white_text_has_a_dark_backplate_on_white_and_black(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source.mp4'; output=root/'captioned.mp4'; subtitles=root/'subtitles.srt'
            self.run_ffmpeg('-f','lavfi','-i','color=white:s=1080x1920:r=30:d=0.2',
                '-f','lavfi','-i','color=black:s=1080x1920:r=30:d=0.2', '-f','lavfi','-i','anullsrc=r=8000:cl=mono',
                '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map','[v]','-map','2:a','-t','0.4',
                '-c:v','libx264','-threads','1','-preset','ultrafast','-c:a','aac',str(source))
            subtitles.write_text('1\n00:00:00,000 --> 00:00:00,400\n一二三四五六七八九十一二三四\n甲乙丙丁戊己庚辛壬癸甲乙丙丁\n')
            candidate.burn_subtitles(source, subtitles, output)
            frames,w,h=self.frames(output,[2,8])
            from PIL import Image
            light=Image.frombytes('RGB',(w,h),frames[0]); dark=Image.frombytes('RGB',(w,h),frames[1])
            # A real filled rectangle has dark corners, unlike a glyph's thin outline.
            points=[(x,y) for y in range(1536,h) for x in range(w) if max(light.getpixel((x,y)))<110]
            self.assertTrue(points)
            xs,ys=zip(*points); left,right,top,bottom=min(xs),max(xs),min(ys),max(ys)
            self.assertGreaterEqual(left,72); self.assertLess(right,w-72)
            self.assertGreaterEqual(top,1536); self.assertLess(bottom,1920)
            corners=[light.getpixel((x,y)) for x in [left+5,right-5] for y in [top+5,bottom-5]]
            self.assertTrue(all(max(c)<110 for c in corners), f'no filled dark box: {corners}')
            self.assertLessEqual(max(light.getpixel((540,top+5))),100)
            self.assertGreater(max(max(dark.getpixel((x,y))) for y in range(top,bottom+1) for x in range(left,right+1)),240)


class CaptionPlanningTests(unittest.TestCase):
    def planner(self):
        from video_subtitles import build_subtitle_cues
        return build_subtitle_cues

    def test_long_spoken_sentence_splits_at_comma_proportionally_and_wraps(self):
        text='我担心的事情其实并没有真的发生过，先把担心写下来再回头逐条对照实际结果。'
        descriptor={'script':text,'narration':{'sentenceTimings':[{'text':text,'startSeconds':0,'endSeconds':12}]},
                    'shots':[{'shot':{'startSeconds':0,'endSeconds':12},'subtitle':'画面要点不烧录'}]}
        cues=self.planner()(descriptor, fps=30, total_frames=360)
        self.assertEqual(''.join(c['text'] for c in cues),text)
        self.assertGreater(len(cues),1); self.assertTrue(cues[0]['text'].endswith('，'))
        self.assertTrue(all(len(c['text'])<=28 and len(c['lines'])<=2 and all(len(line)<=14 for line in c['lines']) for c in cues))
        self.assertEqual(cues[0]['endFrame'],round(360*len(cues[0]['text'])/len(text)))
        self.assertEqual(cues[-1]['endFrame'],359)

    def test_no_timings_keeps_storyboard_text_and_invalid_supplied_timings_do_not_fallback(self):
        descriptor={'narration':None,'shots':[{'shot':{'startSeconds':0,'endSeconds':1},'subtitle':'保留原分镜字幕'}]}
        self.assertEqual(self.planner()(descriptor,fps=30,total_frames=30)[0]['text'],'保留原分镜字幕')
        descriptor['narration']={'sentenceTimings':[{'text':'不能忽略的坏时序','startSeconds':float('nan'),'endSeconds':1}]}
        with self.assertRaises(candidate.ProductContractError):self.planner()(descriptor,fps=30,total_frames=30)

    def test_cues_obey_all_cut_frames_and_never_extend_past_final_frame(self):
        cuts=[0,18,37.2,57.1333333333,80.166667,102.4,122.866667,142.5333333333]
        descriptor={'script':'原话。'*7,'narration':{'sentenceTimings':[{'text':'原话。','startSeconds':a,'endSeconds':b} for a,b in zip(cuts,cuts[1:])]},
                    'shots':[{'shot':{'startSeconds':a,'endSeconds':b},'subtitle':'不使用'} for a,b in zip(cuts,cuts[1:])]}
        cues=self.planner()(descriptor,fps=30,total_frames=4276)
        for i,cut in enumerate(cuts[1:-1]):
            frame=round(cut*30); self.assertLessEqual(cues[i]['endFrame'],frame)
            active=[n for n,c in enumerate(cues) if c['startFrame']<=frame<c['endFrame']]
            self.assertEqual(active,[i+1])
        self.assertLessEqual(cues[-1]['endFrame'],4275)

    def test_style_locks_contrast_geometry_and_font_size(self):
        from video_subtitles import subtitle_style
        style=subtitle_style(1080,1920)
        self.assertGreaterEqual(style['boxOpacity'],.55); self.assertGreaterEqual(style['fontSize'],60); self.assertLessEqual(style['fontSize'],64)
        self.assertEqual(style['maxLineChars'],14);self.assertEqual(style['maxLines'],2);self.assertGreaterEqual(style['sideMargin'],72)
        composite=1-style['boxOpacity'];linear=composite/12.92 if composite<=.04045 else ((composite+.055)/1.055)**2.4
        self.assertGreaterEqual(1.05/(linear+.05),4.5)

if __name__=='__main__':unittest.main()
