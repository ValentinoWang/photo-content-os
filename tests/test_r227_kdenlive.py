"""Kdenlive audio graph and real MLT acoustics on generated, non-private media."""
import array
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from edit_backends.editors import kdenlive_render as renderer
from edit_backends.editors.kdenlive_adapter import Backend
from edit_backends.editors.kdenlive_readback import read_project
from edit_backends.editors.otio_kdenlive import require_otio, timeline_tractor
from edit_backends.editors import otio_kdenlive
from edit_backends.interface import BackendError


def run(command, *, log=None, timeout=120):
    result = subprocess.run(command, capture_output=True, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}, timeout=timeout)
    if log:
        log.write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, (result.stdout + result.stderr).decode(errors="replace")[-3000:]
    return result.stdout


def make_media(path, audio, *, video=False):
    command = ["ffmpeg", "-v", "error", "-y"]
    if video:
        command += ["-f", "lavfi", "-i", "color=blue:s=160x90:r=30:d=12"]
    command += ["-f", "lavfi", "-i", audio]
    if video:
        command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest"]
    run([*command, "-c:a", "pcm_s16le", str(path)])


def edl(media):
    def clip(slot, start, end, source):
        return dict(slot=slot, time_range=f"{start:.3f}-{end:.3f}", source_start_sec=1,
                    source_file=str(media / source), purpose="合成验证", visual_need="合成画面", caption="测试字幕", edit_note="验证声音")
    clips = [clip(1, 0, 3, "a.mkv"), clip(2, 3, 6, "b.mkv"), clip(3, 6, 9, "a.mkv")]
    clips[1].update(audio_lead_sec=.5, audio_tail_sec=.5)
    clips[2]["audio_mute"] = True
    return dict(doc_type="edit_decision_list", source_script_used=True, generation_model="synthetic-fixture",
                generation_reasoning="deterministic test", project_id="r227-k", project_revision=1, clips=clips, missing_materials=[],
                audio_beds=[dict(source=str(media / "bed.wav"), source_start_sec=1, timeline_start_sec=0, timeline_end_sec=9, volume=.2)],
                music=[dict(source=str(media / "one.wav"), source_start_sec=1, timeline_start_sec=0, timeline_end_sec=6, volume=.5, fade_out_sec=2,
                            duck_regions=[dict(start_sec=3.5, end_sec=4.5, gain=10**(-12/20), ramp_sec=.5)]),
                       dict(source=str(media / "two.wav"), source_start_sec=1, timeline_start_sec=4, timeline_end_sec=9, volume=.5, fade_in_sec=2)])


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    value = os.environ.get("R227_K_EVIDENCE")
    root = Path(value).expanduser() if value else tmp_path_factory.mktemp("r227-k")
    root.mkdir(parents=True, exist_ok=True)
    for name, frequency in (("a.mkv", 440), ("b.mkv", 880), ("bed.wav", 220), ("one.wav", 1000), ("two.wav", 1500)):
        make_media(root / name, f"sine=frequency={frequency}:sample_rate=48000:duration=12", video=name.endswith("mkv"))
    for name, amplitude in (("positive.mkv", .2), ("negative.mkv", -.2)):
        make_media(root / name, f"aevalsrc={amplitude}:s=48000:d=12", video=True)
    return root


@pytest.fixture(scope="module")
def project(media):
    source = media / "edl.json"
    source.write_text(json.dumps(edl(media), ensure_ascii=False))
    destination = media / "project"
    result = Backend().generate_from_edl(edl_path=source, output_dir=destination, media_root=media,
                                         project_id="r227-k", project_revision=1)
    return destination, result


def render_pcm(project, destination):
    assert renderer.melt_executable(), "Real MLT required for R227-K acoustics"
    command = [renderer.melt_executable(), str(project), "-consumer", f"avformat:{destination}",
               "f=wav", "vn=1", "acodec=pcm_s16le", "ar=48000", "channels=1", "real_time=-1", "threads=2"]
    run(command, log=destination.with_suffix(".log"))
    with wave.open(str(destination)) as sound:
        assert sound.getframerate() == 48000
        samples = array.array("h", sound.readframes(sound.getnframes()))
    return [value / 32768 for value in samples]


def amplitude(samples, frequency, start, duration=.2):
    first, count = round(start * 48000), round(duration * 48000)
    values = samples[first:first + count]
    assert len(values) == count
    sine = sum(value * math.sin(2 * math.pi * frequency * i / 48000) for i, value in enumerate(values))
    cosine = sum(value * math.cos(2 * math.pi * frequency * i / 48000) for i, value in enumerate(values))
    return 2 * math.hypot(sine, cosine) / count


def props(element):
    return {item.get("name"): item.text for item in element.findall("property")}


def test_edl_entry_and_otio_audio_physical_tracks(project):
    directory, result = project
    assert result["status"] == "done"
    plan = json.loads((directory / "render-plan.json").read_text())["audio_plan"]
    assert plan["source_validation"] == "passed"
    assert plan["muted_slots"] == [3]
    timeline = require_otio().adapters.read_from_file(str(directory / "timeline.otio"))
    audio = [track for track in timeline.tracks if track.kind == "Audio"]
    assert len(audio) == plan["physical_track_count"]
    segments = [item for track in audio for item in track if item.__class__.__name__ == "Clip"]
    assert len(segments) == 5
    b = next(item for item in segments if item.metadata["content_os"]["audio_segment"]["id"] == "clip:2")
    assert b.source_range.start_time.to_seconds() == .5
    assert b.source_range.duration.to_seconds() == 4
    root = ET.parse(directory / "timeline.kdenlive").getroot()
    seq = timeline_tractor(root)
    assert len([t for t in seq.findall("transition") if props(t).get("mlt_service") == "mix"]) == len(audio)
    assert all(props(t).get("sum") == "1" for t in seq.findall("transition") if props(t).get("mlt_service") == "mix")
    for track in root.findall("tractor"):
        if track.get("id", "").startswith("track"):
            expected = "video" if props(track).get("kdenlive:audio_track") == "1" else "audio"
            assert all(t.get("hide") == expected for t in track.findall("track"))


def test_real_mlt_lead_duck_crossfade_and_continuous_bed(project, media):
    directory, _ = project
    samples = render_pcm(directory / "timeline.kdenlive", media / "mixed.wav")
    before = amplitude(samples, 880, 2.2)
    early = amplitude(samples, 880, 2.65)
    stable = amplitude(samples, 880, 3.05)
    assert before < stable * .01
    assert early > stable * .9
    onset = next(t / 1000 for t in range(2420, 2581, 5) if amplitude(samples, 880, t / 1000, .025) > stable * .15)
    assert abs(onset - 2.5) <= .04
    duck_db = 20 * math.log10(amplitude(samples, 1000, 3.7) / amplitude(samples, 1000, 1.0))
    assert -13 <= duck_db <= -11
    assert amplitude(samples, 1000, 5.0) > .005
    assert amplitude(samples, 1500, 5.0) > .005
    assert amplitude(samples, 1500, 5.7) > amplitude(samples, 1500, 4.1) * 3
    crossing = [math.hypot(amplitude(samples, 1000, t, .05), amplitude(samples, 1500, t, .05)) for t in (4, 4.5, 5, 5.5, 5.9, 6)]
    assert min(crossing) > .01
    baseline = amplitude(samples, 220, 1.0)
    bed_db = [20 * math.log10(amplitude(samples, 220, t) / baseline) for t in (2.9, 5.9)]
    assert max(abs(value) for value in bed_db) < .5
    assert len(samples) == 9 * 48000
    # A muted video source must not reappear through the video lane.
    assert amplitude(samples, 440, 6.8) < .0005
    measurements = dict(onset_sec=onset, lead_sec=3-onset, duck_db=duck_db, bed_cut_db=bed_db,
                        crossfade_min_amplitude=min(crossing), duration_sec=len(samples)/48000)
    (media / "acoustics.json").write_text(json.dumps(measurements, indent=2))


def test_readback_audio_is_saved_graph_not_cached_plan(project, media):
    directory, _ = project
    result = read_project(directory)
    assert result["audio_matches_plan"] is True
    assert len(result["audio_segments"]) == 5
    b = next(item for item in result["audio_segments"] if item["id"] == "clip:2")
    assert b["timeline_start_sec"] == 2.5
    assert b["source_start_sec"] == .5
    assert b["timeline_end_sec"] == 6.5
    raw = (directory / "timeline.kdenlive").read_bytes()
    root = ET.fromstring(raw)
    volume = next(f for f in root.findall("producer/filter") if props(f).get("mlt_service") == "volume")
    volume.find("property[@name='level']").text = "0=-24"
    try:
        (directory / "timeline.kdenlive").write_text(ET.tostring(root, encoding="unicode"))
        changed = read_project(directory)
        assert changed["engine_revision"] != result["engine_revision"]
        assert changed["audio_matches_plan"] is False
        assert changed["audio_mismatches"]
        assert changed["audio_segments"] != result["audio_segments"]
    finally:
        (directory / "timeline.kdenlive").write_bytes(raw)


@pytest.mark.parametrize("change", ["source", "position", "mix", "mix_trim", "mute", "filter", "disabled"])
def test_readback_detects_audio_graph_changes(project, change):
    directory, _ = project
    path = directory / "timeline.kdenlive"
    original = path.read_bytes()
    root = ET.fromstring(original)
    audio_playlist = next(p for p in root.findall("playlist") if props(p).get("kdenlive:audio_track") == "1" and p.find("entry") is not None)
    entry = audio_playlist.find("entry")
    producer = root.find(f"producer[@id='{entry.get('producer')}']")
    if change == "source": producer.find("property[@name='resource']").text = "/unapproved/audio.wav"
    if change == "position": audio_playlist.insert(0, ET.Element("blank", {"length": "1"}))
    if change == "mix": next(t for t in timeline_tractor(root).findall("transition") if props(t).get("mlt_service") == "mix").find("property[@name='sum']").text = "0"
    if change == "mix_trim": next(t for t in timeline_tractor(root).findall("transition") if props(t).get("mlt_service") == "mix").set("out", "1")
    if change == "mute":
        tractor = next(t for t in root.findall("tractor") if props(t).get("kdenlive:audio_track") == "1")
        tractor.find("track").set("hide", "both")
    if change == "filter": producer.find("filter/property[@name='mlt_service']").text = "unsupported_gain"
    if change == "disabled": ET.SubElement(producer.find("filter"), "property", {"name": "disable"}).text = "1"
    try:
        path.write_text(ET.tostring(root, encoding="unicode"))
        if change in ("source", "filter", "disabled"):
            with pytest.raises(BackendError): read_project(directory)
        else:
            assert read_project(directory)["audio_matches_plan"] is False
    finally:
        path.write_bytes(original)


def test_otio_validation_checks_audio_and_cli_entry(project, media):
    directory, _ = project
    args = SimpleNamespace(project_id="r227-k", project_revision=1, otio=directory / "timeline.otio",
                           kdenlive=directory / "timeline.kdenlive", result_output=directory / "validation.json")
    # Only the app reopen is substituted here; the graph and real MLT acoustics
    # are tested separately. This is not evidence of a GUI reopen.
    with patch.object(otio_kdenlive, "kdenlive_executable", return_value="fixture-app"), patch.object(otio_kdenlive, "probe_kdenlive_version", return_value="fixture"), patch.object(otio_kdenlive, "probe_kdenlive_reopen"):
        assert otio_kdenlive.validate(args) == 0
    destination = media / "cli-project"
    run([sys.executable, str(ROOT / "scripts/edit_backends/editors/otio_kdenlive.py"), "generate-edl", "--edl", str(media / "edl.json"),
         "--project-id", "r227-k", "--project-revision", "1", "--output-dir", str(destination), "--media-root", str(media)])
    assert read_project(destination)["audio_matches_plan"] is True
    storyboard = media / "storyboard.md"; storyboard.write_text("合成分镜")
    software = str(ROOT / "scripts/edit_backends/editors/otio_kdenlive.py")
    common = [sys.executable, software]
    handoff = media / "otio-route"
    run([*common, "generate-otio", "--project-id", "r227-k", "--project-revision", "1", "--edl", str(media / "edl.json"),
         "--storyboard", str(storyboard), "--output-root", str(handoff)])
    run([*common, "generate-kdenlive", "--project-id", "r227-k", "--project-revision", "1", "--otio", str(handoff / "1/timeline.otio"),
         "--output-root", str(handoff)])
    from edit_backends.editors.kdenlive_readback import audio_graph_differences
    root = ET.parse(handoff / "1/timeline.kdenlive").getroot()
    audio_plan = json.loads((handoff / "1/manifest.json").read_text())["audio_plan"]
    assert audio_graph_differences(root, handoff / "1", audio_plan)[1] == []
    with pytest.raises(ValueError, match="already_exists"):
        Backend().generate_from_edl(edl_path=media / "edl.json", output_dir=destination, media_root=media, project_id="r227-k", project_revision=1)


@pytest.mark.parametrize("change", ["speed", "source_handle", "duck_to", "identity"])
def test_edl_preflight_blocks_without_output_or_fallback(media, change):
    raw = copy.deepcopy(edl(media))
    if change == "speed": raw["clips"][1]["speed"] = 2
    if change == "source_handle": raw["clips"][1]["source_start_sec"] = .1
    if change == "duck_to":
        del raw["music"][0]["duck_regions"]
        raw["music"][0]["duck_to"] = .1
    if change == "identity": raw["project_revision"] = 2
    path = media / f"blocked-{change}.json"; path.write_text(json.dumps(raw))
    destination = media / f"blocked-{change}"
    before = hashlib.sha256((media / "b.mkv").read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        Backend().generate_from_edl(edl_path=path, output_dir=destination, media_root=media, project_id="r227-k", project_revision=1)
    assert not destination.exists()
    assert hashlib.sha256((media / "b.mkv").read_bytes()).hexdigest() == before


def test_real_cut_fade_is_one_frame_without_click(media):
    raw = edl(media)
    raw.pop("audio_beds"); raw.pop("music")
    raw["clips"] = [dict(raw["clips"][0], source_file=str(media / "positive.mkv"), time_range="0.000-2.000"),
                    dict(raw["clips"][0], slot=2, source_file=str(media / "negative.mkv"), time_range="2.000-4.000")]
    source = media / "cut-edl.json"; source.write_text(json.dumps(raw))
    directory = media / "cut-project"
    result = Backend().generate_from_edl(edl_path=source, output_dir=directory, media_root=media, project_id="r227-k", project_revision=1)
    assert result["audio_envelope_resolution_sec"] == pytest.approx(1 / 30)
    samples = render_pcm(directory / "timeline.kdenlive", media / "cut.wav")
    around = samples[round(1.9*48000):round(2.1*48000)]
    jump = max(abs(b-a) for a, b in zip(around, around[1:]))
    assert jump < .002
    # The first real sound cut ramps during one 1600-sample video frame.
    ramp = samples[:1600]
    assert abs(ramp[0]) < .001
    assert ramp[-1] > .19
    assert .08 < ramp[800] < .12
    (media / "cut-acoustics.json").write_text(json.dumps(dict(max_sample_jump=jump, fade_samples=1600, fade_ms=1000/30), indent=2))


def test_legacy_single_source_timeline_keeps_its_audio_route(media):
    destination = media / "legacy"; destination.mkdir()
    result = renderer.build_timeline(source=media / "a.mkv", suggestions={"suggestions": []}, subtitles=None,
                                     animations=[], output_dir=destination, project_id="legacy", project_revision=1)
    root = ET.parse(destination / "timeline.kdenlive").getroot()
    assert root.find("playlist[@id='audio_playlist']") is not None
    assert "audio_plan" not in result
    assert result["audio_tracks"] == 1


def test_gui_save_preserves_internal_mix_and_recognized_gain(project, media):
    """Replay the native editor's distinction between internal and user mixes."""
    directory, _ = project
    root = ET.parse(directory / "timeline.kdenlive").getroot()
    sequence = timeline_tractor(root)
    audio_producers = [p for p in root.findall('producer') if props(p).get('content_os:audio_segment_id')]
    assert len({props(p)['kdenlive:id'] for p in audio_producers}) == len(audio_producers)
    video_ids = {props(p)['kdenlive:id'] for p in root.findall('producer') if props(p).get('resource') and p not in audio_producers and props(p).get('kdenlive:id')}
    assert not video_ids.intersection(props(p)['kdenlive:id'] for p in audio_producers)
    for transition in sequence.findall("transition"):
        values = props(transition)
        if values.get("mlt_service") == "mix":
            assert values.get("internal_added") == "237", "GUI imports unmarked mixes as extra user compositions"
            assert values.get("accepts_blanks") == "1"
    for effect in root.findall("producer/filter"):
        if props(effect).get("mlt_service") == "volume":
            assert props(effect).get("kdenlive_id") == "volume"
            assert props(effect).get("kdenlive:ix") == "1", "Volume must belong to the editor's effect stack"
    # Kdenlive drops root custom properties and MLT's private processing cache.
    for prop in list(root.findall("property")):
        root.remove(prop)
    for node in root.iter():
        for prop in list(node.findall("property")):
            if prop.get("name", "").startswith("_"):
                node.remove(prop)
    simulated = media / "gui-saved.kdenlive"
    simulated.write_text(ET.tostring(root, encoding="unicode"))
    before = render_pcm(directory / "timeline.kdenlive", media / "save-before.wav")
    after = render_pcm(simulated, media / "save-after.wav")
    differences = []
    for offset in range(0, len(before), 4800):
        rms = lambda values: math.sqrt(sum(v*v for v in values) / len(values))
        differences.append(abs(20*math.log10(rms(before[offset:offset+4800])/rms(after[offset:offset+4800]))))
    assert max(differences) <= .5
    original = (directory / "timeline.kdenlive").read_bytes()
    try:
        (directory / "timeline.kdenlive").write_bytes(simulated.read_bytes())
        assert read_project(directory)["audio_matches_plan"] is True
    finally:
        (directory / "timeline.kdenlive").write_bytes(original)


@pytest.mark.parametrize('extension,codec', [('m4a', 'aac'), ('mp3', 'libmp3lame')])
def test_compressed_music_keeps_decoded_sample_origin(media, extension, codec):
    source = media / f'priming.{extension}'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
         r'aevalsrc=if(between(t\,2.04\,2.24)\,0.3*sin(2*PI*1000*t)\,0):s=44100:d=12',
         '-c:a', codec, str(source)])
    raw = edl(media)
    raw.pop('audio_beds')
    for clip in raw['clips']:
        clip.pop('audio_lead_sec', None); clip.pop('audio_tail_sec', None)
        clip['audio_mute'] = True
    raw['music'] = [dict(source=str(source), source_start_sec=1, timeline_start_sec=0,
                         timeline_end_sec=9, volume=1)]
    edl_path = media / f'priming-{extension}.json'
    edl_path.write_text(json.dumps(raw))
    destination = media / f'priming-{extension}'
    Backend().generate_from_edl(edl_path=edl_path, output_dir=destination, media_root=media,
                               project_id='r227-k', project_revision=1)
    samples = render_pcm(destination / 'timeline.kdenlive', media / f'priming-{extension}.wav')
    reference = run(['ffmpeg', '-v', 'error', '-i', str(source), '-af', 'atrim=start=1:end=10,asetpts=PTS-STARTPTS',
                     '-ac', '1', '-ar', '48000', '-f', 's16le', '-'])
    reference_samples = array.array('h', reference)
    actual_onset = next(i for i, value in enumerate(samples) if abs(value) > .03)
    expected_onset = next(i for i, value in enumerate(reference_samples) if abs(value/32768) > .03)
    assert abs(actual_onset-expected_onset)/48000 < .005, 'Decoder priming must not move a music beat'
    assert read_project(destination)['audio_matches_plan'] is True


def test_frame_clock_precision_matches_reported_52_second_project(tmp_path):
    """Exercise the EDL readback boundary without substituting its comparison."""
    from edit_backends.editors import kdenlive_readback as readback
    source = tmp_path / 'synthetic.wav'; source.write_bytes(b'synthetic audio identity')
    project_path = tmp_path / 'timeline.kdenlive'
    project_path.write_text('<mlt/>')
    root = ET.fromstring('<mlt><profile frame_rate_num="30" frame_rate_den="1"/>'
                         '<tractor id="sequence"><property name="content_os:timeline">1</property></tractor></mlt>')
    plan = dict(inputs=[dict(path=str(source), sha256=renderer.sha256_file(source), role='edl_media')],
                audio_plan={}, duration=52.066667)
    actual = [dict(source=str(source), timeline_end_sec=52.06)]
    # Only the graph traversal is substituted to supply the serialized clock value.
    with patch.object(readback, 'audio_graph_differences', return_value=(actual, [])):
        result = readback.read_edl_project(root, tmp_path, plan, dict(project_id='frame-clock', project_revision=1))
    assert result['audio_matches_plan'] is True
    actual[0]['timeline_end_sec'] = plan['duration'] + 1 / 30
    with patch.object(readback, 'audio_graph_differences', return_value=(actual, [])):
        result = readback.read_edl_project(root, tmp_path, plan, dict(project_id='frame-clock', project_revision=1))
    assert result['audio_matches_plan'] is False
    assert result['audio_mismatches'] == ['sequence:fps_or_duration']


def generic_clock_project(tmp_path, *, fps=30, count=1562, source_duration=52.06, extra_frame=False):
    """Small saved XML graph; media probing is isolated by its callers."""
    source = tmp_path / 'original.mp4'; source.write_bytes(b'synthetic source identity')
    subtitles = tmp_path / 'captions.srt'; subtitles.write_text('synthetic captions')
    suggestions = tmp_path / 'suggestions.json'; suggestions.write_text('{}')
    root = ET.Element('mlt')
    otio_kdenlive.xml_properties(root, {'kdenlive:docproperties.projectid':'frame-clock', 'content_os.project_revision':1})
    ET.SubElement(root, 'profile', {'frame_rate_num':str(fps), 'frame_rate_den':'1'})
    producer = ET.SubElement(root, 'producer', {'id':'original'})
    otio_kdenlive.xml_properties(producer, {'resource':str(source)})
    filt = ET.SubElement(producer, 'filter')
    otio_kdenlive.xml_properties(filt, {'mlt_service':'subtitle', 'resource':str(subtitles), 'geometry':'0/4%:0%x0%'})
    playlist = ET.SubElement(root, 'playlist', {'id':'clips'})
    ET.SubElement(playlist, 'entry', {'producer':'original', 'in':'0', 'out':str(count - 1)})
    sequence = ET.SubElement(root, 'tractor', {'id':'sequence', 'out':str(count - 1)})
    otio_kdenlive.xml_properties(sequence, {'content_os:timeline':1})
    ET.SubElement(sequence, 'track', {'producer':'clips'})
    inputs = [dict(path=str(p), role=role, sha256=renderer.sha256_file(p)) for p,role in
              [(source,'original_video'),(subtitles,'source_subtitles'),(suggestions,'edit_suggestions')]]
    plan = dict(inputs=inputs, executed_cuts=[], animation_placements=[])
    if extra_frame:
        animation = tmp_path / 'animation.mp4'; animation.write_bytes(b'synthetic animation identity')
        item = ET.SubElement(root, 'producer', {'id':'animation'})
        otio_kdenlive.xml_properties(item, {'resource':str(animation)})
        affine = ET.SubElement(item, 'filter')
        otio_kdenlive.xml_properties(affine, {'mlt_service':'affine','transition.rect':'0 0 160 90 1'})
        ET.SubElement(playlist, 'entry', {'producer':'animation', 'in':'0', 'out':'0'})
        sequence.set('out',str(count))
        inputs.append(dict(path=str(animation),role='teaching_animation',sha256=renderer.sha256_file(animation)))
        plan['animation_placements'] = [dict(animation_id='extra')]
    (tmp_path / 'timeline.kdenlive').write_text(ET.tostring(root, encoding='unicode'))
    (tmp_path / 'render-plan.json').write_text(json.dumps(plan))
    (tmp_path / 'render-result.json').write_text(json.dumps(dict(project_id='frame-clock',project_revision=1)))
    return dict(streams=[dict(codec_type='video',duration=str(source_duration))])


@pytest.mark.parametrize('fps,count,duration,valid', [
    (30,1562,52.06,True),
    (25,100,3.980000001,True),
    (25,100,3.98,False),  # Exactly half a frame is outside the allowed interval.
    (25,100,3.96,False),
    (60,240,3.99,False),  # Same seconds are over half a frame at this profile rate.
])
def test_generic_frame_clock_source_bounds(tmp_path, fps, count, duration, valid):
    from edit_backends.editors import kdenlive_readback as readback
    facts = generic_clock_project(tmp_path, fps=fps, count=count, source_duration=duration)
    with patch.object(readback, 'probe_media', return_value=facts):
        if valid:
            assert read_project(tmp_path)['frames'] == count
        else:
            with pytest.raises(BackendError, match='kdenlive_source_reorder_unsupported'):
                read_project(tmp_path)


def test_generic_frame_clock_rejects_one_frame_duration_mismatch(tmp_path):
    from edit_backends.editors import kdenlive_readback as readback
    facts = generic_clock_project(tmp_path, count=120, source_duration=4, extra_frame=True)
    with patch.object(readback, 'probe_media', return_value=facts):
        with pytest.raises(BackendError, match='kdenlive_project_duration_invalid'):
            read_project(tmp_path)


@pytest.mark.parametrize('field', ['timeline_start_sec','timeline_end_sec','source_start_sec','source_end_sec','initial_ramp_start_sec'])
@pytest.mark.parametrize('offset_frames,valid', [(.49,True),(.51,False),(1,False)])
def test_audio_frame_clock_positions(project, field, offset_frames, valid):
    from edit_backends.editors import kdenlive_readback as readback
    directory, _ = project
    root = ET.parse(directory / 'timeline.kdenlive').getroot()
    plan = json.loads((directory / 'render-plan.json').read_text())
    actual = readback.read_audio_graph(root, directory)
    actual[0][field] += offset_frames / 30
    with patch.object(readback, 'read_audio_graph', return_value=actual):
        _, mismatches = readback.audio_graph_differences(root, directory, plan['audio_plan'], plan.get('audio_sources'))
    assert (not mismatches) is valid
    if not valid:
        assert mismatches == [f"{actual[0]['id']}:{field}"]
