"""Audio contract, derived plan and handoff boundaries; no editor runtime required."""
import copy
import csv
import hashlib
import importlib
import json
from pathlib import Path
import sys
import wave
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from edl_contract import EDLContractError, normalise_edl, write_edl
from edit_backends import handoff_pack
from studio.edl_bridge import EDLBridgeError, read_edl_bridge

FIXTURES = ROOT / "tests/fixtures/r227-audio-legacy"
FIELDS = ("audio_lead_sec", "audio_tail_sec", "audio_mute", "audio_fade_in_sec", "audio_fade_out_sec")


def document():
    raw = json.loads((FIXTURES / "v1.input.json").read_text())
    first = raw["clips"][0]
    first["source_file"] = "scene.wav"
    first["source_start_sec"] = 2
    raw["clips"] += [dict(first, slot=2, time_range="4-8"), dict(first, slot=3, time_range="8-12")]
    return raw


def requested():
    raw = document()
    raw["clips"][0]["audio_mute"] = True
    raw["clips"][1].update(audio_lead_sec=.5, audio_tail_sec=.5, audio_fade_in_sec=.1, audio_fade_out_sec=.2, volume=.8)
    raw["audio_beds"] = [dict(source="bed.wav", source_start_sec=1, timeline_start_sec=0, timeline_end_sec=12, volume=.4, fade_in_sec=.1, fade_out_sec=.1, note="同地现场声")]
    raw["music"] = [dict(source="one.wav", timeline_start_sec=0, timeline_end_sec=8, volume=.5, fade_out_sec=2, duck_to=.1,
                         duck_regions=[dict(start_sec=2, end_sec=4, gain=.251, ramp_sec=.5)]),
                    dict(source="two.wav", timeline_start_sec=6, timeline_end_sec=12, source_start_sec=3, fade_in_sec=2)]
    return raw


def compile_plan(raw=None, **kwargs):
    module = importlib.import_module("creative.audio_plan")
    return module.compile_audio_plan(normalise_edl(raw or requested()), **kwargs)


@pytest.mark.parametrize("name", ["v1", "v2", "audio-object", "duck-loop", "music-precision"])
def test_legacy_bytes_frozen(name, tmp_path):
    expected = (FIXTURES / f"{name}.expected.json").read_bytes()
    freeze = json.loads((FIXTURES / "freeze.json").read_text())
    assert hashlib.sha256(expected).hexdigest() == freeze["cases"][name]
    target = tmp_path / "output.json"
    write_edl(target, normalise_edl(json.loads((FIXTURES / f"{name}.input.json").read_text())))
    assert target.read_bytes() == expected


def test_contract_schema_and_read_only_bridge(tmp_path):
    normalized = normalise_edl(requested())
    assert normalized["clips"][0]["audio_mute"] is True
    for field in FIELDS:
        clip = normalized["clips"][0 if field == "audio_mute" else 1]
        assert field in clip
    assert normalized["audio_beds"][0]["note"] == "同地现场声"
    assert normalized["music"][0]["duck_regions"][0]["ramp_sec"] == .5
    schema = json.loads((ROOT / "schemas/edit-decision-list.schema.json").read_text())
    assert set(FIELDS) <= schema["properties"]["clips"]["items"]["properties"].keys()
    assert "audio_beds" in schema["properties"]
    Draft202012Validator(schema).validate(normalized)
    source = tmp_path / "06_edit_decision_list.json"
    write_edl(source, normalized)
    before = source.read_bytes()
    assert read_edl_bridge(tmp_path)["content"] == normalized
    assert source.read_bytes() == before
    broken = copy.deepcopy(normalized)
    broken["clips"][1]["audio_mute"] = "false"
    source.write_text(json.dumps(broken))
    assert not Draft202012Validator(schema).is_valid(broken)
    with pytest.raises(EDLBridgeError):
        read_edl_bridge(tmp_path)


def test_explicit_zero_stays_present_and_selects_v2():
    raw = document()
    raw["clips"][1].update({key: False if key == "audio_mute" else 0 for key in FIELDS})
    normalized = normalise_edl(raw)
    assert normalized["schema_version"] == "edit_decision_list_v2"
    assert set(FIELDS) <= normalized["clips"][1].keys()
    assert not set(FIELDS) & normalized["clips"][0].keys()
    module = importlib.import_module("creative.audio_plan")
    assert module.audio_operations({**raw, "clips": [], "music": []}) == []


@pytest.mark.parametrize("field,value", [("audio_mute", "false"), ("audio_mute", 0), ("audio_lead_sec", True), ("audio_tail_sec", -1), ("audio_fade_in_sec", float("nan")), ("audio_fade_out_sec", float("inf")), ("audio_lead_sec", .0001), ("audio_mute", None), ("audio_tail_sec", None)])
def test_invalid_clip_audio(field, value):
    raw = document()
    raw["clips"][1][field] = value
    with pytest.raises(EDLContractError):
        normalise_edl(raw)


@pytest.mark.parametrize("change", ["first_lead", "last_tail", "neighbor", "source_handle", "fade", "speed", "bed_bounds", "duck_ramp", "duck_bounds", "duck_overlap", "audio_tracks", "bed_field", "overlay"])
def test_audio_relational_validation(change):
    raw = requested()
    if change == "first_lead": raw["clips"][0]["audio_lead_sec"] = .5
    if change == "last_tail": raw["clips"][2]["audio_tail_sec"] = .5
    if change == "neighbor": raw["clips"][1]["audio_lead_sec"] = 4.001
    if change == "source_handle": raw["clips"][1]["source_start_sec"] = .1
    if change == "fade": raw["clips"][1]["audio_fade_in_sec"] = 2.501
    if change == "speed": raw["clips"][2]["speed"] = 2
    if change == "bed_bounds": raw["audio_beds"][0]["timeline_end_sec"] = 13
    if change == "duck_ramp": del raw["music"][0]["duck_regions"][0]["ramp_sec"]
    if change == "duck_bounds": raw["music"][0]["duck_regions"][0]["start_sec"] = .1
    if change == "duck_overlap": raw["music"][0]["duck_regions"] *= 2
    if change == "audio_tracks": raw["audio"] = {"tracks": []}
    if change == "bed_field": del raw["audio_beds"][0]["source_start_sec"]
    if change == "overlay": raw["clips"][1]["layer"] = "overlay"
    with pytest.raises(EDLContractError): normalise_edl(raw)


@pytest.mark.parametrize("section,field,value", [
    ("audio_beds", "timeline_start_sec", -1), ("audio_beds", "timeline_end_sec", 0),
    ("audio_beds", "source_start_sec", .00001), ("audio_beds", "volume", 2.01),
    ("audio_beds", "volume", True), ("audio_beds", "fade_in_sec", 6.001),
    ("audio_beds", "fade_out_sec", None), ("duck_regions", "gain", -1),
    ("duck_regions", "gain", 1.001), ("duck_regions", "gain", True),
    ("duck_regions", "ramp_sec", None), ("duck_regions", "end_sec", 2),
    ("duck_regions", "ramp_sec", .00001), ("duck_regions", "start_sec", float("inf")),
])
def test_invalid_beds_and_ducks(section, field, value):
    raw = requested()
    target = raw["audio_beds"][0] if section == "audio_beds" else raw["music"][0]["duck_regions"][0]
    target[field] = value
    with pytest.raises(EDLContractError): normalise_edl(raw)


def test_plan_offsets_mute_bed_duck_crossfade_and_lanes():
    raw = requested()
    before = copy.deepcopy(raw)
    plan = compile_plan(raw)
    assert raw == before
    assert plan["authority"] == "derived_from_edl"
    assert plan["source_validation"] == "pending"
    assert plan["muted_slots"] == [1]
    segments = {s["id"]: s for s in plan["segments"]}
    clip = segments["clip:2"]
    assert [clip[k] for k in ("timeline_start_sec", "timeline_end_sec", "source_start_sec", "source_end_sec")] == [3.5, 8.5, 1.5, 6.5]
    assert segments["music:0"]["physical_track"] != segments["music:1"]["physical_track"]
    assert segments["clip:2"]["physical_track"] != segments["clip:3"]["physical_track"]
    module = importlib.import_module("creative.audio_plan")
    gain = module.gain_at
    assert gain(segments["music:0"], 3) == pytest.approx(.5 * .251)
    assert gain(segments["music:0"], 1.5) == pytest.approx(.5)
    assert gain(segments["music:0"], 4.5) == pytest.approx(.5)
    assert gain(segments["music:0"], 7) == pytest.approx(.25)
    assert gain(segments["music:1"], 7) == pytest.approx(.5)
    for t in (3.999, 4, 4.001, 7.999, 8, 8.001):
        assert gain(segments["bed:0"], t) == pytest.approx(.4)
    for a in plan["segments"]:
        for b in plan["segments"]:
            if a is not b and max(a["timeline_start_sec"], b["timeline_start_sec"]) < min(a["timeline_end_sec"], b["timeline_end_sec"]):
                assert a["physical_track"] != b["physical_track"]


def test_fade_and_duck_multiply_and_empty_regions_override_legacy():
    raw = requested()
    raw["music"][0].update(fade_in_sec=4, duck_regions=[dict(start_sec=1, end_sec=2, gain=.25, ramp_sec=.5)])
    song = next(s for s in compile_plan(raw)["segments"] if s["id"] == "music:0")
    gain = importlib.import_module("creative.audio_plan").gain_at
    assert gain(song, 1.5) == pytest.approx(.5 * (1.5 / 4) * .25)
    raw["music"][0]["duck_regions"] = []
    song = next(s for s in compile_plan(raw)["segments"] if s["id"] == "music:0")
    assert gain(song, 1.5) == pytest.approx(.5 * (1.5 / 4))


def test_cut_edges_exact_30ms_and_short_sound():
    plan = compile_plan(document())
    module = importlib.import_module("creative.audio_plan")
    first = plan["segments"][0]
    assert first["fade_in_sec"] == first["fade_out_sec"] == .03
    assert module.gain_at(first, 0) == 0
    assert module.gain_at(first, .015) == pytest.approx(.5)
    assert module.gain_at(first, .03) == 1
    assert module.gain_at(first, 3.985) == pytest.approx(.5)
    assert module.gain_at(first, 4) == 0
    raw = document()
    raw["clips"] = [dict(raw["clips"][0], time_range="0-.040")]
    # The canonical range parser requires a leading zero.
    raw["clips"][0]["time_range"] = "0-0.040"
    short = compile_plan(raw)["segments"][0]
    assert short["fade_in_sec"] == short["fade_out_sec"] == .02


def test_source_preflight_and_legacy_duck_never_guesses():
    info = {name: {"duration_sec": 30, "has_audio": True} for name in ("scene.wav", "bed.wav", "one.wav", "two.wav")}
    assert compile_plan(source_info=info)["source_validation"] == "passed"
    info["scene.wav"]["duration_sec"] = 6
    with pytest.raises(EDLContractError, match="audio_source_range"): compile_plan(source_info=info)
    info["scene.wav"] = {"duration_sec": 30, "has_audio": False}
    with pytest.raises(EDLContractError, match="audio_stream_missing"): compile_plan(source_info=info)
    raw = requested()
    del raw["music"][0]["duck_regions"]
    with pytest.raises(EDLContractError, match="audio_speech_regions_required"): compile_plan(raw)
    plan = compile_plan(raw, speech_regions=[{"start_sec": 2, "end_sec": 4, "ramp_sec": .5}])
    assert importlib.import_module("creative.audio_plan").gain_at(next(s for s in plan["segments"] if s["id"] == "music:0"), 3) == pytest.approx(.1)


def test_music_loop_explicit_and_source_checked():
    raw = document()
    raw["music"] = [dict(source="short.wav", timeline_start_sec=0, timeline_end_sec=12, source_start_sec=1)]
    info = {"scene.wav": {"duration_sec": 20, "has_audio": True}, "short.wav": {"duration_sec": 4, "has_audio": True}}
    with pytest.raises(EDLContractError, match="audio_source_range"): compile_plan(raw, source_info=info)
    raw["music"][0]["loop"] = True
    plan = compile_plan(raw, source_info=info)
    music = [s for s in plan["segments"] if s["kind"] == "music"]
    assert sum(s["timeline_end_sec"] - s["timeline_start_sec"] for s in music) == 12
    assert all(s["source_end_sec"] <= 4 for s in music)
    for bad in (0, -1, float("nan"), float("inf"), True):
        info["short.wav"]["duration_sec"] = bad
        with pytest.raises(EDLContractError, match="audio_source_info_required"):
            compile_plan(raw, source_info=info)


def test_silent_default_clip_is_omitted_but_requested_bed_fails():
    raw = document()
    info = {"scene.wav": {"duration_sec": 20, "has_audio": False}}
    assert compile_plan(raw, source_info=info)["segments"] == []
    raw["audio_beds"] = [dict(source="scene.wav", source_start_sec=0, timeline_start_sec=0, timeline_end_sec=12)]
    with pytest.raises(EDLContractError, match="audio_stream_missing"):
        compile_plan(raw, source_info=info)


def make_pack(tmp_path):
    for name in ("scene.wav", "bed.wav", "one.wav", "two.wav"):
        with wave.open(str(tmp_path / name), "wb") as sound:
            sound.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            sound.writeframes(b"\0\0" * 8000 * 30)
    edl_path = tmp_path / "edl.json"
    edl_path.write_text(json.dumps(requested()))
    storyboard = tmp_path / "storyboard.md"
    storyboard.write_text("镜头说明")
    result = handoff_pack.generate(project_id="fixture", project_revision=1, edl_path=edl_path, storyboard_path=storyboard,
                                   output_root=tmp_path / "packs", materials_path=tmp_path, revision_basis_path=None)
    return Path(result["manifest"])


def test_handoff_all_audio_and_tamper_recomputed_checksums(tmp_path):
    path = make_pack(tmp_path)
    manifest = json.loads(path.read_text())
    assert manifest["audio_plan"]["source_validation"] == "passed"
    assert len(manifest["audio_plan"]["segments"]) == 5
    assert len(manifest["audio_beds"]) == len(manifest["music"]) - 1 == 1
    with (path.parent / "clips.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert json.loads(rows[1]["audio_plan"])[0]["timeline_start_sec"] == 3.5
    assert json.loads(rows[0]["audio_mute"]) is True
    assert json.loads(rows[0]["audio_beds"]) == manifest["audio_beds"]
    assert json.loads(rows[0]["music"]) == manifest["music"]
    note_path = path.parent / "剪辑交接说明.md"
    note = note_path.read_text()
    for text in ("声音先进", "声音晚出", "静音", "铺底", "压低", "换歌", "3.500", "8.500", "0.030", "尚未核实"):
        assert text in note
    assert handoff_pack.validate(path)["status"] == "passed"
    # A self-consistent manifest/CSV rewrite must still fail against the source EDL.
    manifest["audio_plan"]["segments"][0]["timeline_start_sec"] = 0
    path.write_text(json.dumps(manifest))
    with pytest.raises(handoff_pack.HandoffError, match="声音|音频"): handoff_pack.validate(path)
    manifest["audio_plan"]["segments"][0]["timeline_start_sec"] = 3.5
    note_path.write_text(note.replace("声音先进", "删掉处理"))
    manifest["artifact_checksums"]["handoff_note"] = hashlib.sha256(note_path.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(handoff_pack.HandoffError): handoff_pack.validate(path)


@pytest.mark.parametrize("tamper", ["csv_beds", "csv_music", "csv_mute", "drop_plan", "bed_manifest", "music_manifest", "source_bytes"])
def test_handoff_rejects_audio_omission_and_source_drift(tmp_path, tamper):
    path = make_pack(tmp_path)
    manifest = json.loads(path.read_text())
    csv_path = path.parent / "clips.csv"
    if tamper.startswith("csv_"):
        with csv_path.open() as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        field = {"csv_beds": "audio_beds", "csv_music": "music", "csv_mute": "audio_mute"}[tamper]
        rows[0][field] = ""
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        manifest["artifact_checksums"]["clips_csv"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if tamper == "drop_plan": del manifest["audio_plan"]
    if tamper == "bed_manifest": manifest["audio_beds"] = []
    if tamper == "music_manifest": manifest["music"] = []
    if tamper == "source_bytes":
        with (tmp_path / "bed.wav").open("r+b") as handle:
            handle.seek(50)
            handle.write(b"\1\1")
    path.write_text(json.dumps(manifest))
    with pytest.raises(handoff_pack.HandoffError): handoff_pack.validate(path)


def test_handoff_probe_failure_does_not_create_pack(tmp_path):
    path = make_pack(tmp_path)
    (tmp_path / "bed.wav").write_bytes(b"unreadable")
    edl_path = tmp_path / "edl.json"
    with pytest.raises(handoff_pack.HandoffError, match="探测失败"):
        handoff_pack.generate(project_id="fixture", project_revision=2, edl_path=edl_path,
                              storyboard_path=tmp_path / "storyboard.md", output_root=path.parent.parent,
                              materials_path=tmp_path, revision_basis_path=None)
    assert not (path.parent.parent / "2").exists()


@pytest.mark.parametrize("backend", ["openfilm", "openchatcut"])
@pytest.mark.parametrize("payload", [{"clips": [{"audio_mute": False}]}, {"audio_beds": []}, {"music": [{"duck_regions": []}]}])
def test_unsupported_backends_refuse_before_runtime(tmp_path, backend, payload):
    adapter = importlib.import_module(f"edit_backends.{backend}_adapter").Backend()
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": [], **payload}))
    with patch.object(adapter, "probe", side_effect=AssertionError("runtime must not start")):
        if backend == "openfilm":
            from edit_backends.interface import BackendError
            with pytest.raises(BackendError, match="audio_request_unsupported"):
                adapter.render(source=tmp_path / "source.mp4", suggestions_path=suggestions, output_dir=tmp_path / "candidate")
            result = json.loads((tmp_path / "candidate/render-result.json").read_text())
        else:
            result = adapter.render(source=tmp_path / "source.mp4", suggestions_path=suggestions, output_dir=tmp_path / "candidate")
    assert result["status"] == "failed"
    assert "audio_request_unsupported" in result["reason"]


def test_chatcut_unverified_handoff_and_diagnostics(tmp_path):
    from edit_backends.editors.chatcut_adapter import Backend
    from edit_backends.editors.chatcut_handoff import prepare_package, execute_handoff
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": [], **requested()}))
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic")
    subtitles = tmp_path / "subtitles.srt"
    subtitles.write_text("synthetic")
    package = tmp_path / "chatcut"
    result = prepare_package(source=source, subtitles=subtitles, animations=[], suggestions=suggestions, output_dir=package, project_id="fixture", project_revision=1)
    assert result["audio_operations"]
    assert all(item["message"] == "这项声音处理尚未核实" for item in result["audio_operations"])
    assert "这项声音处理尚未核实" in Backend().describe()["capability_notes"]["audio_operations"]
    with patch("edit_backends.editors.chatcut_handoff.LocalMcpSession", side_effect=AssertionError("no live tools")):
        executed = execute_handoff(package, live=True, session_factory=lambda: pytest.fail("no live tools"))
    assert executed["status"] == "audio_unverified"
    assert executed["audio_operations"] == result["audio_operations"]
