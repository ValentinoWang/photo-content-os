"""Saved editor gaps prove a cut even without an acoustic reason."""
import xml.etree.ElementTree as ET

from test_ps4_kdenlive_readback import saved_project
from edit_backends.kdenlive_adapter import Backend
from edit_backends.kdenlive_render import timeline_tractor


def test_personal_kdenlive_cut_uses_saved_boundaries(tmp_path):
    _, directory, _ = saved_project(tmp_path)
    project = directory / 'timeline.kdenlive'
    tree = ET.parse(project)
    # Trim the first three frames outside the automatic .8–1.2 recommendation.
    tree.getroot().find("playlist[@id='playlist0']/entry").set('in', '3')
    timeline_tractor(tree.getroot()).set('out', '104')
    tree.write(project, encoding='unicode')
    result = Backend().read_back(project_dir=directory)
    assert result['frames'] == 105
    assert result['executed_cuts'] == [
        {'kind': 'manual', 'startSeconds': 0., 'endSeconds': .1},
        {'kind': 'retake', 'startSeconds': .8, 'endSeconds': 1.2},
    ]
