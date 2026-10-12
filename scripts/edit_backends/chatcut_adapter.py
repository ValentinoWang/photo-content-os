"""External ChatCut descriptor and explicit MCP handoff, never a fallback."""
import json
import os
from pathlib import Path
from .interface import BackendError
from .chatcut_handoff import prepare_package, execute_handoff


class Backend:
    def describe(self):
        return {'id': 'chatcut', 'display_name': 'ChatCut', 'license': '闭源',
            'capability_notes': {'automatic_first_cut':'登录后','transparent_overlay':'待验证','chinese_subtitle_burn_in':'待验证','undo':'软件内'},
            'capabilities': {
            'automatic_first_cut': True, 'transparent_overlay': False, 'chinese_subtitle_burn_in': False,
            'web_refine': False, 'undo': False, 'read_back': False, 'export_formats': ['mp4']}}

    def probe(self):
        from doctor import probe_app
        app = probe_app(Path('/Applications/ChatCut.app'))
        return {'id': 'chatcut', 'installed': app['installed'], 'version': app['version'],
                'runnable': False, 'status': 'unknown' if app['installed'] else 'unavailable',
                'reason': 'chatcut_handshake_required'}

    def render(self, *, source, suggestions_path, output_dir, subtitles=None, animations=None,
               project_id='spoken-test', project_revision=1, timeout_seconds=300):
        binding = os.environ.get('CONTENT_OS_CHATCUT_ADAPTER')
        if not binding or subtitles is None:
            raise BackendError('chatcut_explicit_mcp_binding_required')
        prepare_package(source=source, subtitles=subtitles, suggestions=suggestions_path,
                        animations=[Path(a['path']) for a in animations or []], output_dir=output_dir,
                        project_id=project_id, project_revision=project_revision)
        return execute_handoff(output_dir, live=True, adapter=json.loads(Path(binding).read_text()))

    def open_for_refine(self, *, project_dir):
        raise BackendError('chatcut_use_native_editor')

    def read_back(self, *, project_dir):
        raise BackendError('chatcut_return_export_required')

    def close(self):
        return {'id': 'chatcut', 'started_pids': [], 'remaining_pids': []}
