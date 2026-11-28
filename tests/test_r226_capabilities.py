"""Capabilities are independent of connection readiness and UI defaults."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from creative.roughcut_capabilities import CapabilityError, capabilities_for_choice


@pytest.mark.parametrize('editor,method',[('otio_kdenlive','external'),('chatcut','external'),('openchatcut','external'),('otio_kdenlive','guide')])
def test_four_choices_cover_five_techniques_and_swap(editor,method):
    result = capabilities_for_choice({'editor':editor,'method':method},ready=True)
    assert set(result['techniques']) == {'jcut','bed','duck','pause','action'}
    assert set(result['swap']) == {'mode','support','reason'}
    assert type(result['can_generate']) is bool
    assert (result['block_reason'] is None) == result['can_generate']
    for row in [*result['techniques'].values(),result['swap']]:
        assert row['mode'] in ('auto','manual')
        assert row['support'] in ('implemented','unsupported','unverified')
    assert result['editor'] == editor and result['method']==method


def test_kdenlive_cuts_are_supported_but_audio_not_promoted_before_acceptance():
    result = capabilities_for_choice({'editor':'otio_kdenlive','method':'external'},ready=True)
    assert result['can_generate']
    assert all(result['techniques'][tech]['mode']=='auto' for tech in ('pause','action'))
    assert all(result['techniques'][tech]['mode']=='manual' for tech in ('jcut','bed','duck'))
    assert result['swap']['mode'] == 'manual'


@pytest.mark.parametrize('editor',['chatcut','openchatcut'])
def test_multi_source_generation_is_explicitly_blocked_until_decision(editor):
    result = capabilities_for_choice({'editor':editor,'method':'external'},ready=True)
    assert result['can_generate'] is False
    assert result['block_reason'] == 'multi_source_unverified'
    assert all(row['mode']=='manual' for row in result['techniques'].values())


def test_guide_uses_manual_list_and_self_preserves_openfilm():
    guide = capabilities_for_choice({'editor':'chatcut','method':'guide'},ready=False)
    assert guide['can_generate']
    assert all(row['mode']=='manual' for row in guide['techniques'].values())
    own = capabilities_for_choice({'editor':'chatcut','method':'self'},ready=True)
    assert own['editor'] == 'openfilm'
    assert not own['can_generate']
    assert own['block_reason'] == 'self_workflow_outside_roughcut'


@pytest.mark.parametrize('ready,reason',[(None,'editor_readiness_unknown'),(False,'editor_not_ready')])
def test_unknown_or_disconnected_editor_never_falls_back(ready,reason):
    result = capabilities_for_choice({'editor':'otio_kdenlive','method':'external'},ready=ready)
    assert not result['can_generate'] and result['block_reason']==reason
    assert result['editor'] == 'otio_kdenlive'


@pytest.mark.parametrize('choice',[{},None,{'editor':'missing','method':'external'},{'editor':'chatcut','method':'invented'}])
def test_invalid_choice_is_not_default_kdenlive(choice):
    with pytest.raises(CapabilityError) as error:
        capabilities_for_choice(choice,ready=True)
    assert error.value.code == 'editor_choice_invalid'


def test_result_mutation_cannot_change_authority_matrix():
    choice = {'editor':'otio_kdenlive','method':'external'}
    result = capabilities_for_choice(choice,ready=True)
    result['techniques']['jcut']['mode'] = 'auto'
    assert capabilities_for_choice(choice,ready=True)['techniques']['jcut']['mode']=='manual'


def test_invalid_readiness_is_distinct():
    with pytest.raises(CapabilityError) as error:
        capabilities_for_choice({'editor':'chatcut','method':'external'},ready='ready')
    assert error.value.code == 'editor_readiness_invalid'


@pytest.mark.parametrize('field',['editor','method'])
def test_malformed_saved_choice_has_stable_failure(field):
    choice = {'editor':'chatcut','method':'external'}
    choice[field] = []
    with pytest.raises(CapabilityError) as error:
        capabilities_for_choice(choice,ready=True)
    assert error.value.code == 'editor_choice_invalid'
