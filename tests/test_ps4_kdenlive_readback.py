"""Actual saved MLT and returned bytes are independent evidence inputs."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import xml.etree.ElementTree as ET

import pytest
from unittest.mock import patch
from edit_backends.kdenlive_adapter import Backend
from edit_backends.kdenlive_render import build_timeline, write_json, timeline_tractor
from edit_backends.interface import BackendError
import unittest


def movie(path, duration=4):
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=0x25516b:s=288x512:r=30:d={duration}',
                    '-f','lavfi','-i',f'sine=frequency=660:duration={duration}', '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(path)],check=True)


def saved_project(root, pid='ps4', revision=1):
    source=root/'source.mp4';movie(source)
    subs=root/'source.srt';subs.write_text('1\n00:00:00,000 --> 00:00:04,000\n合成口播\n')
    suggestions={'precision':'word','suggestions':[{'type':'repetition','start':.8,'end':1.2,'auto_cut_allowed':True}]}
    sugg=root/'suggestions.json';write_json(sugg,suggestions)
    directory=root/'kdenlive';directory.mkdir()
    plan=build_timeline(source=source,suggestions=suggestions,subtitles=subs,animations=[],output_dir=directory,project_id=pid,project_revision=revision)
    from edit_backends.kdenlive_render import sha256_file
    plan['inputs'].append({'path':str(sugg),'sha256':sha256_file(sugg),'role':'edit_suggestions'})
    write_json(directory/'render-plan.json',plan)
    write_json(directory/'render-result.json',{'status':'candidate','editor_backend':'otio_kdenlive','project_id':pid,'project_revision':revision})
    return source,directory,plan


def test_saved_xml_changes_win_over_original_plan(tmp_path):
    _,directory,original=saved_project(tmp_path)
    backend=Backend();first=backend.read_back(project_dir=directory)
    assert first['time_map']==original['time_map']
    project=directory/'timeline.kdenlive';tree=ET.parse(project)
    # Person restored three frames in the first clip, then saved the XML.
    entry=tree.getroot().find("playlist[@id='playlist0']/entry")
    entry.set('out','26')
    timeline_tractor(tree.getroot()).set('out','110')
    tree.write(project,encoding='unicode')
    changed=backend.read_back(project_dir=directory)
    assert changed['engine_revision']!=first['engine_revision']
    assert changed['frames']==111 and changed['time_map'][0]['source_end']==.9
    assert changed['executed_cuts']==[{'kind':'retake','startSeconds':.9,'endSeconds':1.2}]
    assert json.loads((directory/'render-plan.json').read_text())==original


def test_readback_rejects_changed_source_and_unapproved_resource(tmp_path):
    source,directory,_=saved_project(tmp_path)
    project=directory/'timeline.kdenlive';tree=ET.parse(project)
    producer=tree.getroot().find("producer[@id='producer0']/property[@name='resource']")
    if producer is None:producer=next(p for p in tree.getroot().findall("producer/property[@name='resource']") if p.text==str(source))
    producer.text='/unapproved/other.mp4';tree.write(project,encoding='unicode')
    with pytest.raises(BackendError,match='unapproved'):Backend().read_back(project_dir=directory)
