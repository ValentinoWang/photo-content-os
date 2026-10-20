"""A2 negative cases: foreground quality, soft warnings and reviewed image defects."""
import json
import os
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import select_shots as selector
from shot_quality import frame_metrics
from llm_common import generate_text_with_codex_cli


def row():
    r=selector.empty_row('S0123456789','video','scene/clip.mp4',0,3)
    r['metrics'].update(blur_variance=150,overexposed_fraction=.3,underexposed_fraction=0,
                        shake_high_frequency=.012,tracking_fraction=.5)
    return r


def test_soft_findings_are_not_hard_rejections():
    r=row();selector.apply_quality(r,1000,selector.DEFAULT_CONFIG)
    assert r['rejection_reasons']==[]
    assert {'blur','overexposed','shake'}<=set(r['quality_flags'])
    assert r['quality_penalty']>0


def test_only_extreme_shake_and_short_shots_are_hard_rejected():
    r=row();r['metrics']['shake_high_frequency']=.03;r['duration_sec']=.5
    selector.apply_quality(r,1000,selector.DEFAULT_CONFIG)
    assert {'extreme_shake','too_short'}<=set(r['rejection_reasons'])


def test_subject_tiles_do_not_penalize_plain_background():
    frame=np.full((640,640,3),127,np.uint8)
    patch=np.indices((160,160)).sum(axis=0)//4%2*255
    frame[160:320,160:320]=patch[...,None]
    metrics=frame_metrics(frame,selector.DEFAULT_CONFIG)
    assert len(metrics['tile_variances'])==16
    assert metrics['blur_variance']>metrics['whole_frame_variance']*4
    blurred=frame_metrics(cv2.GaussianBlur(frame,(0,0),12),selector.DEFAULT_CONFIG)
    assert blurred['blur_variance']<metrics['blur_variance']*.1


def test_all_soft_candidates_appear_in_paged_sheets(tmp_path):
    from PIL import Image
    Image.new('RGB',(30,30),'red').save(tmp_path/'frame.jpg')
    rows=[]
    for i in range(10):
        r=row();r.update(id=f'S{i:010d}',frames=['frame.jpg'],status='usable',total_score=5,
                          quality_flags=['shake'],quality_penalty=.2)
        rows.append(r)
    out=tmp_path/'out';(out/'sheets').mkdir(parents=True)
    sheets=selector.make_sheets(rows,tmp_path,out,selector.DEFAULT_CONFIG)
    assert {identifier for s in sheets for identifier in s['ids']}=={r['id'] for r in rows}


def test_visual_defect_flags_are_required_strict_booleans():
    value={'decisions':[{'id':'S1','decision':'精选','reason':'画面有文字'}]}
    with pytest.raises(ValueError):selector.validate_model_answer(value,{'S1'})
    value['decisions'][0].update(has_title_or_sticker='false',has_watermark=False,has_occlusion=False)
    with pytest.raises(ValueError):selector.validate_model_answer(value,{'S1'})


@pytest.mark.parametrize('flag',['has_title_or_sticker','has_watermark','has_occlusion'])
def test_flagged_images_cannot_be_selected(flag):
    r=row();r.update(status='usable',quality_flags=[],quality_penalty=0)
    answer={'id':r['id'],'decision':'精选','reason':'清晰人物',
            'has_title_or_sticker':False,'has_watermark':False,'has_occlusion':False}
    answer[flag]=True
    selector.apply_model_decision(r,answer)
    assert r['status']!='selected' and r['visual_flags'][flag]
    assert '标记' in r['model_reason']
    assert {'has_title_or_sticker':'标题或贴纸字','has_watermark':'水印','has_occlusion':'手指或物体遮挡'}[flag] in r['model_reason']


def test_prompt_binds_context_and_visible_only_reasoning(tmp_path):
    r=row()
    prompt=selector.selection_prompt(tmp_path,[r])
    assert '只描述画面' in prompt and '据文件名' in prompt
    assert '不推断场所功能' in prompt and '运动和身体类镜头优先' in prompt
    assert 'scene/clip.mp4' in prompt
    assert '不得把同组其他镜头' in prompt
    (tmp_path/'readme.md').write_text('账号人设：短跑运动员\n剪辑目标：记录训练\n')
    assert '短跑运动员' in selector.selection_prompt(tmp_path,[r])


def test_codex_env_python_uses_running_runtime(tmp_path,monkeypatch):
    wrapper=tmp_path/'codex'
    wrapper.write_text('#!/usr/bin/env python3\nimport sys,tomllib,json\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index("-o")+1]).write_text(json.dumps({"prefix":sys.prefix}))\n')
    wrapper.chmod(0o755)
    old=tmp_path/'old';old.mkdir()
    (old/'python3').write_text('#!/bin/sh\nexit 99\n');(old/'python3').chmod(0o755)
    monkeypatch.setenv('PATH',str(old)+os.pathsep+os.environ['PATH'])
    monkeypatch.setenv('OPENCLAW_CODEX_BIN',str(wrapper))
    answer=generate_text_with_codex_cli(system_prompt='test',user_prompt='test')
    assert json.loads(answer)['prefix']==sys.prefix


def test_one_white_sample_does_not_reject_other_visible_frames():
    r=row()
    r['frame_measurements']=[{'status':'ok','blur_variance':500.,
        'overexposed_fraction':fraction,'underexposed_fraction':0.} for fraction in [1.,.1,.1]]
    selector.aggregate_frames(r)
    selector.apply_quality(r,1000,selector.DEFAULT_CONFIG)
    assert 'all_white' not in r['rejection_reasons']
    assert 'overexposed' in r['quality_flags']


def test_reviewed_duplicate_remains_usable_as_an_alternative():
    r=row();r['duplicate_of']='Sother'
    answer={'id':r['id'],'decision':'可用','reason':'人物和号码布清楚',
            'has_title_or_sticker':False,'has_watermark':False,'has_occlusion':False}
    selector.apply_model_decision(r,answer)
    assert r['status']=='usable'
    answer['decision']='精选'
    selector.apply_model_decision(r,answer)
    assert r['status']=='usable'  # Only the group representative may be selected.


def test_sheets_include_corner_details_for_small_defects(tmp_path):
    from PIL import Image
    Image.new('RGB',(640,360),'white').save(tmp_path/'frame.jpg')
    r=row();r.update(frames=['frame.jpg']*3,status='usable',total_score=5)
    out=tmp_path/'out';(out/'sheets').mkdir(parents=True)
    sheet=selector.make_sheets([r],tmp_path,out,selector.DEFAULT_CONFIG)[0]
    assert len(sheet['detail_paths'])==3
    for relative in sheet['detail_paths']:
        with Image.open(tmp_path/relative) as image:
            assert image.width==1024 and image.height>150


def test_prompt_preserves_clear_body_and_partially_obscured_alternatives(tmp_path):
    prompt=selector.selection_prompt(tmp_path,[row()])
    assert '重复本身不能作为不用的理由' in prompt
    assert '脸部局部被手机或闪光遮住' in prompt
    assert '四角放大图' in prompt
