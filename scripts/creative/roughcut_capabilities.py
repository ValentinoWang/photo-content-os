"""Roughcut capability authority, independent of installation and job success."""
import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
from copy import deepcopy


class CapabilityError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _cell(mode, support, reason=None):
    return {'mode': mode, 'support': support, 'reason': reason}


# Promote audio here only after the corresponding editor execution is accepted.
_TECHNIQUES = ('jcut', 'bed', 'duck', 'pause', 'action')
_MATRIX = {
    'otio_kdenlive': {
        'can_generate': True, 'block_reason': None,
        'techniques': {tech: _cell('auto', 'implemented') if tech in ('pause', 'action')
                       else _cell('manual', 'unverified', 'audio_acceptance_pending') for tech in _TECHNIQUES},
        'swap': _cell('manual', 'unverified', 'audio_acceptance_pending'),
    },
    'chatcut': {
        'can_generate': False, 'block_reason': 'multi_source_unverified',
        'techniques': {tech: _cell('manual', 'unverified', 'multi_source_unverified') for tech in _TECHNIQUES},
        'swap': _cell('manual', 'unverified', 'audio_unverified'),
    },
    'openchatcut': {
        'can_generate': False, 'block_reason': 'multi_source_unverified',
        'techniques': {tech: _cell('manual', 'unsupported' if tech in ('jcut', 'bed', 'duck') else 'unverified',
                                  'audio_request_unsupported' if tech in ('jcut', 'bed', 'duck') else 'multi_source_unverified')
                       for tech in _TECHNIQUES},
        'swap': _cell('manual', 'unsupported', 'audio_request_unsupported'),
    },
    'guide': {
        'can_generate': True, 'block_reason': None,
        'techniques': {tech: _cell('manual', 'unsupported', 'manual_editing') for tech in _TECHNIQUES},
        'swap': _cell('manual', 'unsupported', 'manual_editing'),
    },
    'openfilm': {
        'can_generate': False, 'block_reason': 'self_workflow_outside_roughcut',
        'techniques': {tech: _cell('manual', 'unverified', 'self_workflow_outside_roughcut') for tech in _TECHNIQUES},
        'swap': _cell('manual', 'unsupported', 'audio_request_unsupported'),
    },
}


def capabilities_for_choice(choice: dict, *, ready: bool | None = None) -> dict:
    """Retain the saved method; unknown readiness never means a usable editor."""
    if (not isinstance(choice, dict) or choice.get('editor') not in
            ('otio_kdenlive', 'chatcut', 'openchatcut', 'openfilm') or
            choice.get('method') not in ('external', 'guide', 'self')):
        raise CapabilityError('editor_choice_invalid')
    if ready is not None and type(ready) is not bool:
        raise CapabilityError('editor_readiness_invalid')
    method = choice['method']
    editor = 'openfilm' if method == 'self' else choice['editor']
    result = deepcopy(_MATRIX['guide' if method == 'guide' else editor])
    result.update(editor=editor, method=method)
    if method == 'external' and ready is not True:
        result.update(can_generate=False, block_reason='editor_not_ready' if ready is False else 'editor_readiness_unknown')
    return result
