#!/usr/bin/env python3
"""Generate the bounded real-media audio fixture without editing its sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess

from runtime_paths import local_media_root
from edl_contract import normalise_edl
from edit_backends.kdenlive_render import generate_from_edl
from edit_backends import handoff_pack
from render_preview import build_plan, execute_plan
from video_candidate import preview_video


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run(command, log):
    with log.open('wb') as output:
        subprocess.run(command, stdout=output, stderr=output, check=True,
                       env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})


def generate(fixture_path, destination):
    spec = json.loads(fixture_path.read_text())
    root = local_media_root()
    work = root / spec['work']
    destination.mkdir(parents=True, exist_ok=False)
    mirror = destination / 'sources'
    sources = {str(Path(spec['work']) / c['path']) for c in spec['clips']}
    sources.update(m['path'] for m in spec['music'])
    originals = []
    bed = str(Path(spec['work']) / spec['bed']['path'])
    for ref in sorted(sources):
        source = (root / ref).resolve()
        assert source.is_relative_to(root) and source.is_file()
        target = mirror / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        originals.append({'source': ref, 'sha256': digest(source)})
        if ref == bed:
            # Both consumers receive one identical, explicitly selected stream.
            run(['ffmpeg', '-nostdin', '-hide_banner', '-v', 'error', '-n', '-i', str(source),
                 '-map', '0:v:0', '-map', f"0:{spec['bed']['stream_index']}", '-c', 'copy',
                 '-map_metadata', '-1', str(target)], destination / 'bed-stream-selection.log')
        else:
            os.link(source, target)
    write(destination / 'source-hashes.json', originals)
    frozen = ['scripts/audio_plan.py', 'scripts/edl_contract.py', 'schemas/edit-decision-list.schema.json',
              'studio/server.py', 'studio/static/review-view.js', 'studio/static/review-common.js',
              'music-analysis.registry.json']
    write(destination / 'protected-hashes.json', {p: digest(Path(p)) for p in frozen})
    baseline = {p.relative_to(work).as_posix(): digest(p) for p in work.iterdir() if p.is_file()}
    baseline['creative-store'] = digest(Path.home() / '.photo-content-os/studio/creative-projects.json')
    write(destination / 'work-before.json', baseline)
    beat_maps = []
    for music in spec['music']:
        path = Path.home() / '.photo-content-os/r223/beat-maps' / (music['id'] + '.json')
        document = json.loads(path.read_text())
        assert all(a < b for a, b in zip(document['beats'], document['beats'][1:]))
        assert all(t in document['beats'] for t in document['downbeats'])
        beat_maps.append({'path': str(path), 'sha256': digest(path), 'beats': document['beats'],
                          'downbeats': document['downbeats']})
    assert round(spec['music'][0]['source_start_sec'] + 8, 3) in beat_maps[0]['beats']
    assert spec['music'][1]['source_start_sec'] > 8
    assert spec['music'][1]['source_start_sec'] in beat_maps[1]['downbeats']
    write(destination / 'beat-inputs.json', beat_maps)
    transcript = json.loads((work / spec['speech']['transcript']).read_text())
    assert any(s['start_sec'] <= 1 and s['end_sec'] >= 5 for s in transcript['segments'])
    write(destination / 'speech-input.json', {'path': spec['work'] + '/' + spec['speech']['transcript'],
          'sha256': digest(work / spec['speech']['transcript']), 'precision': spec['speech']['precision'],
          'current_transcript_precision': transcript['precision'],
          'basis': '交接 7 批准的 chunk 区间 0.350–21.835 秒与源 1–5 秒相交；不用后来新增的逐字时间',
          'human_checked': False, 'selected_intersection_source_sec': [1, 5],
          'selected_intersection_timeline_sec': [14, 18]})
    clips = []
    for slot, row in enumerate(spec['clips'], 1):
        clip = {'slot': slot, 'time_range': f"{row['start']}-{row['end']}",
                'source_file': str(Path(spec['work']) / row['path']), 'source_start_sec': row['source_start'],
                'purpose': '声音专项测试', 'visual_need': '兰大六镜测试', 'caption': f'声音测试 · 第 {slot} 镜',
                'edit_note': '独立测试版，未经过人工验收'}
        clip.update({k: v for k, v in row.items() if k.startswith('audio_')})
        clips.append(clip)
    music = [{k: v for k, v in m.items() if k not in ('id', 'path')} | {'source': m['path']}
             for m in spec['music']]
    music[1]['duck_regions'] = [{'start_sec': 14, 'end_sec': 18,
                               'gain': 10 ** (-12 / 20), 'ramp_sec': .2}]
    edl = normalise_edl({'project_id': spec['project_id'], 'project_revision': spec['project_revision'],
           'source_script_used': True, 'generation_model': 'R227-approved-real-fixture',
           'generation_reasoning': '阶段 A 六镜方案、R223 拍点导出、chunk 说话区间；尚未人工听校',
           'clips': clips, 'missing_materials': [], 'music': music,
           'audio_beds': [{k: v for k, v in spec['bed'].items() if k not in ('path', 'stream_index')} |
                          {'source': bed, 'fade_in_sec': .03, 'fade_out_sec': .03,
                           'note': '原片流索引 1（AAC 双声道）；预备副本仅含此音频流；三镜连续铺底'}]})
    edl_path = destination / '06_edit_decision_list.json'
    write(edl_path, edl)
    storyboard = destination / '05_storyboard.md'
    storyboard.write_text('# 兰大声音专项独立测试版\n\n22 秒、六镜；不改变原作品阶段。说话区间来自 chunk ASR，未人工听校。\n')
    generate_from_edl(edl_path=edl_path, output_dir=destination / 'kdenlive', media_root=mirror,
                      project_id=spec['project_id'], project_revision=spec['project_revision'])
    handoff_pack.generate(project_id=spec['project_id'], project_revision=spec['project_revision'],
                          edl_path=edl_path, storyboard_path=storyboard, output_root=destination / 'handoff',
                          materials_path=mirror, revision_basis_path=None)
    handoff_pack.validate(destination / 'handoff/1/manifest.json')
    plan = build_plan(edl, project=mirror, output=destination / 'mixed.mp4', width=854, height=480)
    # Bound decoder concurrency on laptops with multiple 4K inputs.
    command = plan['command']
    command[5:5] = ['-filter_complex_threads', '1']
    command[-1:-1] = ['-threads', '2']
    write(destination / 'preview-plan.json', plan)
    execute_plan(plan)
    preview = preview_video(destination / 'mixed.mp4', destination / 'preview.mp4')
    write(destination / 'preview-artifact.json', preview)
    for item in originals:
        assert digest(root / item['source']) == item['sha256']


def register(fixture_path, destination):
    spec = json.loads(fixture_path.read_text())
    root = local_media_root()
    work = root / spec['work']
    version = work / 'output' / spec['version']
    version.mkdir(parents=True, exist_ok=True)
    preview_path = version / 'preview.mp4'
    assert not preview_path.exists(), 'Never overwrite an existing preview'
    shutil.copyfile(destination / 'preview.mp4', preview_path)
    run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-ss', '14.5', '-i', str(destination / 'preview.mp4'),
         '-frames:v', '1', str(destination / 'poster.jpg')], destination / 'poster.log')
    evidence = Path.home() / '.photo-content-os/evidence'
    write(version / 'preview.json', {'schema_version': 'local_preview_v1', 'project_id': spec['project_id'],
          'name': '兰大声音专项测试（未人工验收）',
          'preview_ref': (destination / 'preview.mp4').relative_to(evidence).as_posix(),
          'work_output': preview_path.relative_to(work).as_posix(),
          'sha256': digest(destination / 'preview.mp4'),
          'poster_ref': (destination / 'poster.jpg').relative_to(evidence).as_posix(),
          'poster_sha256': digest(destination / 'poster.jpg')})
    write(version / 'test-version.json', {'authority': str(destination / '06_edit_decision_list.json'),
          'kdenlive_project': str(destination / 'kdenlive/timeline.kdenlive'),
          'handoff_manifest': str(destination / 'handoff/1/manifest.json'),
          'stage_unchanged': True, 'human_acceptance': 'pending',
          'cleanup': '用户验收后删除整个 output/vR227-audio-test 测试版目录'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True, help='本机实测配置文件')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    destination = args.output.expanduser().resolve()
    if args.register_only:
        register(args.fixture, destination)
    else:
        generate(args.fixture, destination)
