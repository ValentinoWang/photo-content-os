"""Regression boundaries: measured failures, SA review-only, explicit dispatch."""
from pathlib import Path
from unittest.mock import Mock, patch
import json
import pytest
from studio.video_workflow import candidate_failed, _replace_ops
from edit_backends.execution import render
import unittest
import test_ps_studio_handoff as fixture_module


@pytest.mark.parametrize('checks,failed', [({'avSync':'fail','avOffsetSeconds':.4,'avOffsetLimitSeconds':.1},True),({'playable':'fail'},True),({'avSync':'pass'},False),([{'status':'failed','details':{'offset':.4}}],True)])
def test_candidate_failure_is_not_green(checks,failed):
    assert candidate_failed({'checks':checks}) is failed


def test_dispatch_never_precreates_adapter_output_or_falls_back(tmp_path):
    adapter=Mock()
    def fail(**kw):
        assert not kw['output_dir'].exists()
        raise ValueError('openfilm_export_unavailable')
    adapter.render.side_effect=fail
    with patch('edit_backends.execution.get_backend',return_value=adapter) as get:
        result=render(backend_id='openfilm',output_dir=tmp_path/'output',source=tmp_path/'source')
    get.assert_called_once_with('openfilm')
    assert result['status']=='failed' and result['editor_backend']=='openfilm'
    assert json.loads((tmp_path/'output/editor-failure.json').read_text())['reason']=='openfilm_export_unavailable'
    adapter.close.assert_called_once()


def test_native_replace_creates_tracks_after_remove():
    before={'tracks':[{'clips':[{'id':'talk'}]},{'clips':[{'id':'overlay'}]}]}
    after={'tracks':[{'clips':[{'id':'a','src':'source'},{'id':'b','src':'source'}]},{'clips':[{'id':'c','src':'animation'}]}]}
    ops=_replace_ops(before,after)
    assert ops[2]['newTrack']==0 and ops[3]['track']==0 and ops[4]['newTrack']==1


class WorkflowBoundaryTests(unittest.TestCase):
    setUp = fixture_module.StudioHandoffTests.setUp
    write = staticmethod(fixture_module.StudioHandoffTests.write)
    projection = fixture_module.StudioHandoffTests.projection
    def test_failed_candidate_projects_measured_values(self):
        c={'identity':self.identity,'status':'check_failed','checks':{'playable':'pass','avSync':'fail','avOffsetSeconds':.4,'avOffsetLimitSeconds':.1}}
        self.write(self.run/'handoff_manifest.json',{'candidate':c})
        p=self.projection()
        assert p['state']=='check-failed'
        assert p['candidate']['checks']['avOffsetSeconds']==.4

    def test_script_alignment_and_review_survive_projection(self):
        a={'mode':'script','script_version':3,'alignment_rate':.9,'missing_sentences':[{'text':'漏说'}]}
        self.write(self.run/'native-suggest.json',{'duration':10,'precision':'word','script_alignment':a,'suggestions':[{'type':'review','start':1,'end':2,'basis':'script','auto_cut_allowed':False}]})
        p=self.projection()
        assert p['scriptAlignment']==a
        assert p['suggestions'][0]['type']=='review'
        assert p['suggestions'][0]['automatic'] is False

    def test_identity_and_revision_required_for_every_command(self):
        ctx=self.app.video_workflow.context(self.project['id'])
        for payload in ({'identity':{**self.identity,'jobId':'other'},'expectedRevision':1},{'identity':self.identity,'expectedRevision':9},{'identity':self.identity,'expectedRevision':True},{'identity':{**self.identity,'photoProjectRevision':True},'expectedRevision':1}):
            with pytest.raises(Exception,match='作品交接已变化'):
                self.app.video_workflow.assert_identity(ctx,payload)

    def test_guide_choice_does_not_change_stage(self):
        old=self.app.store.get_project(self.project['id'])
        self.app.video_editor_choice(self.project['id'],{'editor':'otio_kdenlive','method':'guide','revision':1})
        assert self.projection()['state']=='guide'
        assert self.app.store.get_project(self.project['id'])==old

    def test_return_upload_rejects_empty_before_creating_files(self):
        with pytest.raises(Exception,match='成片大小无效'):
            self.app.video_workflow.receive(self.project['id'],None,0,{'identity':self.identity,'expectedRevision':1})
        assert not list(self.run.glob('returned-*'))
