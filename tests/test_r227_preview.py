"""FFmpeg-generated audio markers and the identity-bound Studio preview path."""
import json
import math
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from edl_contract import normalise_edl, write_edl
from render_preview import PreviewError, build_plan, execute_plan
from video_candidate import preview_video
from studio.video_workflow import VideoWorkflow

RATE = 48000


def run(*args):
    return subprocess.run([str(a) for a in args], capture_output=True, check=True).stdout


def tone(path, frequency, duration=10, *, video=False):
    args = ['ffmpeg', '-v', 'error', '-y']
    if video:
        args += ['-f', 'lavfi', '-i', f'color=c=blue:s=160x90:r=30:d={duration}']
    args += ['-f', 'lavfi', '-i', f'sine=frequency={frequency}:sample_rate={RATE}:duration={duration}']
    args += ['-c:a', 'pcm_s16le']
    if video:
        args += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p']
    run(*args, path)


def edl():
    clip = dict(slot=1, time_range='0-4', source_start_sec=1, source_file='a.mov',
                purpose='测试', visual_need='测试', caption='测试', edit_note='测试', audio_mute=True)
    return normalise_edl(dict(source_script_used=True, generation_model='fixture', generation_reasoning='high',
                             clips=[clip, dict(clip, slot=2, time_range='4-8', source_file='b.mov', audio_mute=False, audio_lead_sec=.5)],
                             audio_beds=[dict(source='bed.wav', source_start_sec=1, timeline_start_sec=0, timeline_end_sec=8, volume=.2)],
                             music=[dict(source='one.wav', timeline_start_sec=0, timeline_end_sec=6, volume=.7, fade_out_sec=1,
                                         duck_regions=[dict(start_sec=2, end_sec=3, gain=10**(-12/20), ramp_sec=.25)]),
                                    dict(source='two.wav', source_start_sec=1, timeline_start_sec=5, timeline_end_sec=8, volume=.7, fade_in_sec=1)]))


def pcm(path):
    return np.frombuffer(run('ffmpeg', '-v', 'error', '-i', path, '-map', '0:a:0', '-ac', '1', '-ar', RATE,
                             '-f', 'f64le', '-'), dtype='<f8')


def amplitude(samples, frequency, start, end):
    a, b = round(start*RATE), round(end*RATE)
    t = np.arange(a, b) / RATE
    return 2 * abs(np.sum(samples[a:b] * np.exp(-2j*np.pi*frequency*t))) / (b-a)


@pytest.fixture(scope='module')
def rendered(tmp_path_factory):
    root = tmp_path_factory.mktemp('r227-preview')
    for name, frequency, video in [('a.mov', 300, True), ('b.mov', 900, True), ('bed.wav', 150, False), ('one.wav', 1700, False), ('two.wav', 2300, False)]:
        tone(root/name, frequency, video=video)
    output = root/'mixed.mov'
    plan = build_plan(edl(), project=root, output=output, width=160, height=90)
    # Inspect the filter output before AAC introduces codec-window ringing.
    command = plan['command']
    command[command.index('-c:a')+1] = 'pcm_s16le'
    execute_plan(plan)
    return root, plan, output, pcm(output)


def test_plan_consumes_validated_audio_and_disables_normalization(rendered):
    root, plan, _, _ = rendered
    assert plan['audio_plan']['source_validation'] == 'passed'
    graph = plan['command'][plan['command'].index('-filter_complex')+1]
    assert 'normalize=0' in graph
    assert all(name in graph for name in ('atrim=', 'asetpts=', 'adelay=', 'afade=', 'volume=', 'amix='))
    assert plan['audio_plan']['muted_slots'] == [1]
    assert '-t' in plan['command']


def test_lead_duck_crossfade_bed_and_duration(rendered):
    root, _, output, samples = rendered
    assert len(samples) == 8*RATE
    bins = [(t/1000, amplitude(samples, 900, t/1000, (t+10)/1000)) for t in range(3400, 4050, 10)]
    first = next(t for t, value in bins if value > .02)
    assert abs(first - 3.5) <= .04
    before = amplitude(samples, 1700, 1, 1.5)
    during = amplitude(samples, 1700, 2.25, 2.75)
    after = amplitude(samples, 1700, 3.5, 3.9)
    duck = 20*math.log10(during / ((before+after)/2))
    assert -13 <= duck <= -11
    # Every 20 ms around the crossfade contains music, including both at 5.5 s.
    levels = [math.hypot(amplitude(samples, 1700, t, t+.02), amplitude(samples, 2300, t, t+.02)) for t in np.arange(4.9, 6.1, .02)]
    assert min(levels) > .04
    bed = [amplitude(samples, 150, t, t+.1) for t in (3.8, 3.95, 4.1)]
    assert max(bed)/min(bed) < 1.1
    assert amplitude(samples, 300, 1, 1.5) < .001
    measured = dict(lead_onset_sec=first, duck_db=duck, crossfade_min_amplitude=min(levels), bed_amplitudes=bed,
                    pcm_duration_sec=len(samples)/RATE)
    (root/'measurements.json').write_text(json.dumps(measured, indent=2))
    print(json.dumps(measured))


def test_sample_accurate_30ms_fade(tmp_path):
    # A constant signal exposes the actual sample envelope without FFT/window error.
    run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=160x90:r=30:d=2',
        '-f', 'lavfi', '-i', 'aevalsrc=0.25:s=48000:d=2', '-c:v', 'libx264', '-c:a', 'pcm_s16le', tmp_path/'dc.mov')
    raw = edl()
    raw['clips'] = [dict(raw['clips'][0], source_file='dc.mov', candidate_files=['dc.mov'], source_start_sec=0, time_range='0-1', audio_mute=False),
                    dict(raw['clips'][0], slot=2, source_file='dc.mov', candidate_files=['dc.mov'], source_start_sec=1, time_range='1-2', audio_mute=False)]
    raw.pop('audio_beds'); raw.pop('music')
    plan = build_plan(normalise_edl(raw), project=tmp_path, output=tmp_path/'dc-out.mov', width=160, height=90)
    plan['command'][plan['command'].index('-c:a')+1] = 'pcm_s16le'
    execute_plan(plan)
    samples = pcm(tmp_path/'dc-out.mov')
    plateau = np.median(samples[2000:4000])
    for start in (0, RATE):
        actual = samples[start:start+1440]/plateau
        assert np.max(abs(actual - np.arange(1440)/1440)) < .001
    assert abs(samples[RATE]) < .0001
    step = float(np.max(abs(np.diff(samples[RATE-1440:RATE+1441]))))
    assert step < .001
    print(json.dumps(dict(pcm_fade_samples=1440, pcm_fade_ms=30, pcm_max_sample_step=step)))


def test_low_resolution_keeps_the_mix(rendered):
    root, _, output, _ = rendered
    preview_video(output, root/'preview.mp4')
    samples = pcm(root/'preview.mp4')
    duck = 20*math.log10(amplitude(samples, 1700, 2.25, 2.75)/amplitude(samples, 1700, 1, 1.5))
    assert -13 <= duck <= -11
    assert amplitude(samples, 900, 3.6, 3.8) > .04
    assert abs(len(samples)/RATE-8) < .04


def test_pending_plan_never_executes(tmp_path):
    plan = build_plan(edl(), project=tmp_path, output=tmp_path/'out.mp4', require_sources=False)
    assert plan['audio_plan']['source_validation'] == 'pending'
    with pytest.raises(PreviewError, match='audio_source_info_required'):
        execute_plan(plan)


def test_unreadable_source_is_not_silence(tmp_path):
    (tmp_path/'a.mov').write_bytes(b'broken')
    raw = edl(); raw['clips'] = raw['clips'][:1]; raw.pop('audio_beds'); raw.pop('music')
    with pytest.raises(Exception, match='audio_probe_failed'):
        build_plan(raw, project=tmp_path, output=tmp_path/'out.mp4')


def test_source_escape_in_music_is_rejected(rendered):
    root, _, _, _ = rendered
    raw = edl(); raw['music'][0]['source'] = '../outside.wav'
    with pytest.raises(PreviewError, match='escapes'):
        build_plan(raw, project=root, output=root/'invalid.mp4')


def test_candidate_preview_remixes_native_video(rendered):
    from video_candidate import mixed_edl_preview
    root, _, video, _ = rendered
    mixed_edl_preview(video, root/'remixed.mp4', edl=edl(), project=root)
    samples = pcm(root/'remixed.mp4')
    # Remapping must discard the input mix, rather than double it.
    assert .07 < amplitude(samples, 1700, 1, 1.5) < .10
    assert -13 < 20*math.log10(amplitude(samples, 1700, 2.25, 2.75)/amplitude(samples, 1700, 1, 1.5)) < -11


def test_candidate_rejects_different_timeline_duration(rendered):
    from video_candidate import mixed_edl_preview
    root, _, video, _ = rendered
    raw = edl(); raw['clips'][-1]['time_range'] = '4-9'
    with pytest.raises(Exception, match='audio_preview_duration_mismatch'):
        mixed_edl_preview(video, root/'bad.mp4', edl=raw, project=root)


def test_studio_edl_requires_current_project_and_revision(tmp_path):
    workflow = VideoWorkflow(Mock())
    identity = dict(photoProjectId='p', photoProjectRevision=2)
    ctx = dict(root=tmp_path, identity=identity)
    assert workflow._preview_edl(ctx) is None
    raw = edl(); raw.update(project_id='p', project_revision=2)
    write_edl(tmp_path/'06_edit_decision_list.json', raw)
    assert workflow._preview_edl(ctx) == raw
    for identity_change in (dict(project_id='q'), dict(project_revision=1), dict(project_revision=True)):
        write_edl(tmp_path/'06_edit_decision_list.json', {**raw, **identity_change})
        with pytest.raises(Exception, match='版本'):
            workflow._preview_edl(ctx)


def test_studio_render_to_actual_preview_ref(rendered, tmp_path, monkeypatch):
    """Only the editor export is synthetic; candidate/mix/registry/HTTP are real."""
    import shutil
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from studio.project_store import ProjectStore
    from studio.server import StudioApplication
    from media import file_sha256
    root, _, video, _ = rendered
    # Exercise the supported pre-captioned native-export branch without relying
    # on this host's optional FFmpeg drawtext build.
    from PIL import Image, ImageDraw, ImageFont
    caption = Image.new('RGBA', (160, 90))
    draw = ImageDraw.Draw(caption)
    font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 12)
    draw.rectangle((60, 68, 100, 88), fill=(0, 0, 0, 220))
    draw.text((68, 70), '测试', fill='white', font=font)
    caption.save(tmp_path/'caption.png')
    baked = tmp_path/'native-captioned.mov'
    run('ffmpeg', '-v', 'error', '-y', '-i', video, '-i', tmp_path/'caption.png', '-filter_complex',
        "[0:v][1:v]overlay=enable='between(t,0.1,7.9)'[v]", '-map', '[v]', '-map', '0:a:0',
        '-c:v', 'libx264', '-c:a', 'copy', baked)
    video = baked
    for name in ('a.mov', 'b.mov', 'bed.wav', 'one.wav', 'two.wav'):
        shutil.copy2(root/name, tmp_path/name)
    app = StudioApplication(ProjectStore(tmp_path/'state'))
    project = app.store.create_project(title='合成音频验证', local_workspace=str(tmp_path))
    pid = project['id']
    identity = dict(jobId='r227_audio', photoProjectId=pid, photoProjectRevision=1)
    raw = edl(); raw.update(project_id=pid, project_revision=1)
    write_edl(tmp_path/'06_edit_decision_list.json', raw)
    (tmp_path/'video.json').write_text(json.dumps(dict(scope='video_handoff_v1', identity=identity, shots=[], animations=[])))
    binding = tmp_path/'binding.json'
    binding.write_text(json.dumps(dict(identity=dict(project_id=pid, project_revision=1, job_id=identity['jobId']),
                                      project_root=str(tmp_path), creative_store=str(app.store.path), source_refs=['a.mov'], steps=[])))
    for name, value in dict(LOCAL_MEDIA_ROOT=str(tmp_path), PHOTO_STUDIO_VIDEO_WORKSPACE=str(tmp_path),
                            PHOTO_STUDIO_VIDEO_BINDING=str(binding)).items():
        monkeypatch.setenv(name, value)
    workflow = app.video_workflow
    from edit_backends.registry import describe_backends
    workflow.probes = [dict(r, probe={}) for r in describe_backends()]
    ctx = workflow.context(pid)
    (ctx['run']/'native-suggest.json').write_text(json.dumps(dict(duration=10, precision='word', suggestions=[])))
    ctx = workflow.context(pid)
    subs = tmp_path/'subtitles.srt'
    subs.write_text('1\n00:00:00,100 --> 00:00:07,900\n测试\n')
    manifest = tmp_path/'native-manifest.json'
    manifest.write_text(json.dumps(dict(output=dict(path=str(video), sha256=file_sha256(video)),
                                       inputs=[], subtitle_burned_in=True, subtitle_bottom_ratio=.8, fps=30, time_map=[dict(source_start=1, source_end=9)],
                                       executed_cuts=[dict(kind='manual', startSeconds=0, endSeconds=1),
                                                      dict(kind='manual', startSeconds=9, endSeconds=10)], subtitles=str(subs))))
    native = dict(status='candidate', output=str(video), manifest=str(manifest), frames=240)
    adapter = Mock(); adapter.render.return_value = native
    session = workflow._session(ctx)
    with patch('studio.video_workflow.get_backend', return_value=adapter):
        workflow.render(ctx, session, {})
    assert session['public']['state'] == 'refine', session['public']
    payload = json.loads((ctx['run']/'studio-candidate.json').read_text())
    candidate = payload['candidate']
    path = workflow.preview(pid, candidate['publicCandidateId'])
    assert path == (tmp_path/payload['preview_ref']).resolve()
    rows = workflow.public_candidates(pid, ctx)
    row = next(r for r in rows if r.get('previewUrl'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.handler())
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}' + row['previewUrl']) as response:
            assert response.read() == path.read_bytes()
    finally:
        server.shutdown(); server.server_close(); worker.join()
    samples = pcm(path)
    assert abs(len(samples)/RATE-8) < .04
    assert amplitude(samples, 900, 3.6, 3.8) > .04
    duck = 20*math.log10(amplitude(samples, 1700, 2.25, 2.75)/amplitude(samples, 1700, 1, 1.5))
    assert -13 <= duck <= -11
    print(json.dumps(dict(studio_preview_duck_db=duck, studio_preview_duration_sec=len(samples)/RATE)))
    stale = dict(ctx, identity=dict(identity, photoProjectRevision=2))
    with patch.object(workflow, 'context', return_value=stale):
        with pytest.raises(Exception, match='不可用'):
            workflow.preview(pid, candidate['publicCandidateId'])
    raw['music'][0]['volume'] = .6
    write_edl(tmp_path/'06_edit_decision_list.json', raw)
    assert workflow.public_candidates(pid, ctx)[0]['previewUrl'] is None
    with pytest.raises(Exception, match='重新生成预览'):
        workflow.preview(pid, candidate['publicCandidateId'])


def test_tail_and_looped_product_envelopes(rendered, tmp_path):
    from audio_plan import gain_at
    root, _, _, _ = rendered
    raw = edl(); raw.pop('audio_beds'); raw.pop('music')
    raw['clips'][0].update(audio_mute=False, audio_tail_sec=.5)
    raw['clips'][1].update(audio_mute=True)
    plan = build_plan(raw, project=root, output=tmp_path/'tail.mov', width=160, height=90)
    plan['command'][plan['command'].index('-c:a')+1] = 'pcm_s16le'
    execute_plan(plan)
    samples = pcm(tmp_path/'tail.mov')
    assert amplitude(samples, 300, 4.1, 4.3) > .1
    assert amplitude(samples, 300, 4.6, 4.8) < .001

    run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'aevalsrc=0.25:s=48000:d=2', tmp_path/'dc.wav')
    import shutil
    shutil.copy2(root/'a.mov', tmp_path/'a.mov')
    raw['clips'] = [dict(raw['clips'][0], audio_mute=True, audio_tail_sec=0, time_range='0-4')]
    raw['music'] = [dict(source='dc.wav', source_start_sec=1, timeline_start_sec=0, timeline_end_sec=4, loop=True,
                         volume=.5, fade_in_sec=.5, fade_out_sec=.5,
                         duck_regions=[dict(start_sec=.25, end_sec=3.75, gain=.25, ramp_sec=.25)])]
    plan = build_plan(normalise_edl(raw), project=tmp_path, output=tmp_path/'product.mov', width=160, height=90)
    plan['command'][plan['command'].index('-c:a')+1] = 'pcm_s16le'
    execute_plan(plan)
    samples = pcm(tmp_path/'product.mov')
    for time in (.1, .2, .35, .45, .9, 1.01, 1.02, 1.5, 2.01, 2.02, 3.6, 3.8, 3.9):
        expected = .25 * sum(gain_at(segment, time) for segment in plan['audio_plan']['segments'])
        assert abs(samples[round(time*RATE)] - expected) < .0001


def test_silent_source_still_has_bounded_silent_mix(tmp_path):
    run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=160x90:r=30:d=1', '-an', tmp_path/'silent.mov')
    raw = edl(); raw['clips'] = [dict(raw['clips'][0], source_file='silent.mov', source_start_sec=0, time_range='0-1')]
    raw.pop('audio_beds'); raw.pop('music')
    plan = build_plan(raw, project=tmp_path, output=tmp_path/'silent-out.mov', width=160, height=90)
    plan['command'][plan['command'].index('-c:a')+1] = 'pcm_s16le'
    execute_plan(plan)
    samples = pcm(tmp_path/'silent-out.mov')
    assert len(samples) == RATE and max(abs(samples)) == 0
