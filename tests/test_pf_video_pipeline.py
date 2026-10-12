from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from _support import load_script
adapter = load_script('openclaw_video_execution', 'pf_adapter', register=True)
from edit_backends import kdenlive_render as renderer
from openclaw_product_contract import ProductContractError, video_digest
from video_candidate import project_candidate, waveform_peaks, preview_video, cut_projection


def run(*args):
    return subprocess.run(args, capture_output=True, check=True).stdout


def descriptor():
    shots = [{'shot': {'shotId': '01', 'startSeconds': 0, 'endSeconds': 14}, 'visual': {'text': 'fixture', 'image': None},
              'dialogue': '口播夹具', 'subtitle': '测试字幕', 'camera': '全屏', 'audio': '配音', 'saveStatus': 'saved', 'failureCode': None}]
    identity = {'jobId': 'job_pf', 'publicTenantId': 'tenant_pf', 'publicContentId': 'content_pf', 'publicVariantId': 'variant_pf',
                'workRevision': 1, 'photoProjectId': 'project_pf', 'photoProjectRevision': 1, 'catalogDigest': 'sha256:'+'a'*64,
                'confirmationRef': 'confirm_pf', 'confirmedContentDigest': 'sha256:'+'b'*64}
    return {'identity': identity, 'shots': shots, 'animations': []}


@unittest.skipUnless(shutil.which('ffmpeg') and renderer.melt_executable(), 'FFmpeg and bundled melt required')
class FrameMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evidence = os.getenv('PF_FRAME_EVIDENCE_ROOT')
        cls.temporary = None if evidence else tempfile.TemporaryDirectory(prefix='pf-frame-')
        cls.root = Path(evidence) if evidence else Path(cls.temporary.name)
        cls.root.mkdir(parents=True, exist_ok=True)
        cls.source = cls.root / 'source.mp4'
        font = '/System/Library/Fonts/Supplemental/Arial.ttf'
        barcode = 'if(lt(Y,20)*lt(X,160),20+210*mod(floor(N/pow(2,floor(X/16))),2),70)'
        vf = f"format=rgb24,geq=r='{barcode}':g='{barcode}':b='{barcode}',drawtext=fontfile={font}:text='frame=%{{n}} t=%{{pts}}':x=170:y=2:fontsize=12:fontcolor=white"
        run('ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=30:d=20',
            '-f','lavfi','-i','sine=frequency=440:duration=20:sample_rate=48000','-vf',vf,
            '-c:v','libx264','-crf','12','-pix_fmt','yuv420p','-c:a','aac',str(cls.source))
        cls.suggestions = cls.root / 'suggestions.json'
        cls.suggestions.write_text(json.dumps({'precision': 'word', 'suggestions': [
            {'type': kind, 'start': a, 'end': b, 'auto_cut_allowed': True} for kind, a, b in [('silence',4,6),('repetition',8,10),('silence',12,14)]] + [{'type':'animation','animation_id':'lesson','start':11,'end':12}]}))
        cls.subtitles = cls.root / 'source.srt'
        cls.subtitles.write_text('1\n00:00:00,100 --> 00:00:19,900\n中文测试字幕\n')
        cls.animation = cls.root / 'animation.mov'
        run('ffmpeg','-v','error','-y','-f','lavfi','-i','color=red:s=160x90:r=30:d=1',
            '-vf',"format=rgba,geq=r=255:g=0:b=0:a='if(between(X,20,59)*between(Y,20,39),255,0)'",
            '-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le',str(cls.animation))
        cls.result = renderer.render(source=cls.source,suggestions_path=cls.suggestions,subtitles=cls.subtitles,
                                     animations=[{'path':str(cls.animation),'start':11,'end':12,'animation_id':'lesson',
                                                  'geometry':{'x':140,'y':30,'width':160,'height':90}}],output_dir=cls.root/'render')
    @classmethod
    def tearDownClass(cls):
        if cls.temporary: cls.temporary.cleanup()
    def test_every_frame_matches_retained_source_clock(self):
        def clocks(path):
            pixels = run('ffmpeg','-v','error','-i',str(path),'-vf','crop=160:2:0:8,format=gray','-f','rawvideo','-')
            return [sum((pixels[o+i*16+8]>128)<<i for i in range(10)) for o in range(0,len(pixels),320)]
        original = clocks(self.source)
        candidate = clocks(Path(self.result['output']))
        expected = original[:120]+original[180:240]+original[300:360]+original[420:600]
        self.assertEqual(len(candidate), 420)
        self.assertEqual(candidate, expected)
        self.assertEqual(candidate[210], original[330])
        self.assertEqual(candidate[330], original[510])
    def test_editable_document_structure_and_neutral_producers(self):
        root = ET.parse(self.root/'render/timeline.kdenlive').getroot()
        self.assertEqual(root.find("playlist[@id='main_bin']/property[@name='kdenlive:docproperties.version']").text,'1.1')
        self.assertEqual(len(root.findall("playlist[@id='playlist0']/entry")),4)
        self.assertTrue(root.find("tractor[@id='project_tractor']/track") is not None)
        self.assertTrue(all(p.get('in')=='0' for p in root.findall('producer') if p.get('id')!='black'))
    def test_alpha_and_geometry_have_exact_pixel_bounds(self):
        raw = run('ffmpeg','-v','error','-ss','7.2','-i',self.result['output'],'-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-')
        coords=[(i//3%320,i//3//320) for i in range(0,len(raw),3) if raw[i]>150 and raw[i+1]<70 and raw[i+2]<70]
        self.assertTrue(coords)
        xs,ys=zip(*coords)
        self.assertEqual((min(xs),max(xs),min(ys),max(ys)),(160,199,50,69))
    def test_projection_checks_preview_waveform_and_no_local_paths(self):
        desc=descriptor()
        desc['animations']=[{'animationId':'lesson','shotId':'01','requirement':'test','dialogue':'口播夹具',
            'dialogueStartSeconds':11,'dialogueEndSeconds':12,'suggestedStartSeconds':11,'durationSeconds':1,
            'layouts':['pip_right'],'selectedLayout':'pip_right','resolution':'unresolved'}]
        hashes={self.source:renderer.sha256_file(self.source)}
        payload=project_candidate(native=self.result,descriptor=desc,source=self.source,original_hashes=hashes,
                                  output_dir=self.root/'projection',workspace=self.root)
        candidate=payload['candidate']
        self.assertEqual(candidate['status'],'candidate')
        self.assertEqual(candidate['checks']['actualFrames'],420)
        self.assertEqual(candidate['sourceDurationSeconds'],20)
        self.assertEqual(candidate['removedSeconds'],6)
        self.assertEqual([c['kind'] for c in candidate['cuts']],['silence','retake','silence'])
        self.assertTrue(candidate['subtitleBurnedIn'])
        self.assertEqual(candidate['subtitleBottomRatio'],.8)
        self.assertTrue(1<=len(candidate['waveformPeaks'])<=400)
        self.assertTrue(all(0<=n<=1 for n in candidate['waveformPeaks']))
        self.assertNotIn(str(self.root),json.dumps(payload))
        self.assertNotIn('source.mp4',json.dumps(payload))
        self.assertLessEqual(candidate['preview']['artifact']['sizeBytes'],20_000_000)
        self.assertLessEqual(candidate['preview']['shortEdge'],480)
        self.assertLessEqual(candidate['preview']['longEdge'],854)
        self.assertEqual(candidate['candidateDigest'],video_digest({k:v for k,v in candidate.items() if k!='candidateDigest'}))
    def test_real_silence_envelope_has_no_simulated_peaks(self):
        silent=self.root/'silent.wav'
        run('ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=8000:cl=mono','-t','0.2',str(silent))
        self.assertTrue(all(v==0 for v in waveform_peaks(silent)))
    def test_changed_source_fails_projection(self):
        bad={self.source:'0'*64}
        desc=descriptor()
        desc['animations']=[{'animationId':'lesson','shotId':'01','requirement':'test','dialogue':'口播夹具','dialogueStartSeconds':11,'dialogueEndSeconds':12,'suggestedStartSeconds':11,'durationSeconds':1,'layouts':['pip_right'],'selectedLayout':'pip_right','resolution':'unresolved'}]
        payload=project_candidate(native=self.result,descriptor=desc,source=self.source,original_hashes=bad,
                                  output_dir=self.root/'bad-projection',workspace=self.root)
        self.assertEqual(payload['candidate']['status'],'check_failed')
        self.assertEqual(payload['candidate']['checks']['sourceUnchanged'],'fail')


class FrameGridProjectionTests(unittest.TestCase):
    def test_source_rate_conversion_does_not_invent_a_cut(self):
        plan={'fps':30,'time_map':[{'source_start':0,'source_end':10/30,'output_start':0}],'executed_cuts':[]}
        self.assertEqual(cut_projection(plan,21/60),[])
    def test_final_executed_cut_never_exceeds_real_source_duration(self):
        plan={'fps':30,'time_map':[{'source_start':0,'source_end':.4,'output_start':0}],
              'executed_cuts':[{'kind':'retake','startSeconds':.4,'endSeconds':14/30}]}
        self.assertEqual(cut_projection(plan,27/60),[{'kind':'retake','startSeconds':.4,'endSeconds':27/60}])


class PreviewAndBlackFrameTests(unittest.TestCase):
    def test_real_720p_preview_is_scaled_and_reencoded(self):
        with tempfile.TemporaryDirectory(prefix='pf-preview-') as directory:
            root=Path(directory);source=root/'source.mp4';preview=root/'preview.mp4'
            run('ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=1280x720:r=30:d=0.5',
                '-f','lavfi','-i','sine=duration=0.5:sample_rate=48000','-c:v','libx264','-c:a','aac','-pix_fmt','yuv420p',str(source))
            original=renderer.sha256_file(source)
            meta=preview_video(source,preview)
            self.assertEqual((meta['width'],meta['height']),(852,480))
            self.assertEqual(renderer.sha256_file(source),original)
            self.assertLessEqual(preview.stat().st_size,20_000_000)
    def test_real_60fps_source_projects_without_a_false_tail_cut(self):
        with tempfile.TemporaryDirectory(prefix='pf-rate-') as directory:
            root=Path(directory);source=root/'source.mp4'
            run('ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=60:d=0.35',
                '-f','lavfi','-i','sine=duration=0.35:sample_rate=48000','-c:v','libx264','-c:a','aac','-pix_fmt','yuv420p',str(source))
            (root/'suggestions.json').write_text(json.dumps({'precision':'word','suggestions':[]}))
            (root/'subtitles.srt').write_text('1\n00:00:00,010 --> 00:00:00,300\n测试字幕\n')
            native=renderer.render(source=source,suggestions_path=root/'suggestions.json',subtitles=root/'subtitles.srt',output_dir=root/'render')
            desc=descriptor();desc['shots'][0]['shot']['endSeconds']=.35
            payload=project_candidate(native=native,descriptor=desc,source=source,
                                      original_hashes={source:renderer.sha256_file(source)},output_dir=root/'return',workspace=root)
            self.assertEqual(payload['candidate']['status'],'candidate')
            self.assertEqual(payload['candidate']['cuts'],[])
            self.assertEqual(payload['candidate']['removedSeconds'],0)
            self.assertAlmostEqual(payload['candidate']['sourceDurationSeconds'],.35)

    def test_black_native_frames_fail_even_with_burned_subtitles(self):
        with tempfile.TemporaryDirectory(prefix='pf-black-') as directory:
            root=Path(directory);source=root/'source.mp4';native=root/'native.mp4'
            run('ffmpeg','-v','error','-y','-f','lavfi','-i','color=black:s=160x90:r=30:d=1',
                '-f','lavfi','-i','sine=duration=1:sample_rate=48000','-c:v','libx264','-c:a','aac','-pix_fmt','yuv420p',str(source))
            shutil.copyfile(source,native)
            desc=descriptor();desc['shots'][0]['shot']['endSeconds']=1
            payload=project_candidate(native={'status':'completed','candidate':str(native),'checks':{'frames':30}},
                                      descriptor=desc,source=source,original_hashes={source:renderer.sha256_file(source)},
                                      output_dir=root/'return',workspace=root)
            self.assertEqual(payload['candidate']['checks']['blackFrames'],'fail')
            self.assertEqual(payload['candidate']['status'],'check_failed')


class AnalysisForwardingTests(unittest.TestCase):
    def test_paid_provider_fails_before_any_local_work(self):
        for provider in ['fun_asr','dashscope','openai_api']:
            result=subprocess.run([str(adapter.PHOTO_PYTHON),str(adapter.SCRIPTS/'run_analyze_project.py'),'nonexistent',
                                   '--audio','--transcript-provider',provider],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('requires explicit --live',result.stderr)
            self.assertNotIn('+ ',result.stdout)
    def test_analysis_forwards_live_and_fun_asr_without_calling_provider(self):
        analysis=load_script('run_analyze_project','pf_analysis',register=True)
        commands=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(analysis.sys,'argv',['run_analyze_project',str(root),'--audio','--transcript-provider','fun_asr','--transcript-model','fun-asr','--live','--skip-llm']), patch.object(analysis,'project_path',return_value=root), patch.object(analysis,'run',side_effect=commands.append), patch.object(analysis,'apply_requested_tier'):
                self.assertEqual(analysis.main(),0)
        transcribe=next(c for c in commands if str(adapter.SCRIPTS/'transcribe_audio.py') in c)
        self.assertIn('--live',transcribe)
        self.assertEqual(transcribe[transcribe.index('--provider')+1],'fun_asr')
        self.assertEqual(transcribe[transcribe.index('--model')+1],'fun-asr')

    def test_registration_uses_desktop_without_guessed_tools(self):
        from studio.chatcut_mcp import PROBE_COMMAND
        self.assertEqual(PROBE_COMMAND,('codex','mcp','get','chatcut_desktop'))


if __name__=='__main__': unittest.main()
