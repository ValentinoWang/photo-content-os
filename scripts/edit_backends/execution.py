"""Registry dispatch for an explicitly chosen local editor; no substitution."""
from pathlib import Path
import json
from .registry import get_backend


def render(*, backend_id='otio_kdenlive', editing_method='open_source', **kwargs):
    output = Path(kwargs['output_dir'])
    backend = None
    try:
        backend = get_backend(backend_id)
        if editing_method not in ('open_source','software_workflow','jianying_guidance'):
            raise ValueError('editing_method_invalid')
        result = backend.render(**kwargs)
        if result.get('editor_backend') not in (None,backend_id):
            raise ValueError('editor_backend_receipt_mismatch')
        return {**result, 'editor_backend':backend_id, 'editingMethod':editing_method}
    except (ValueError, OSError, RuntimeError) as exc:
        # Detailed diagnostics and locators stay in the local receipt/log.
        output.mkdir(parents=True, exist_ok=True)
        receipt = {'status': 'failed', 'editor_backend': backend_id, 'reason': str(exc)}
        (output / 'editor-failure.json').write_text(json.dumps(receipt), encoding='utf-8')
        return receipt
    finally:
        if backend is not None:
            backend.close()
