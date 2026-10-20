"""Owned background jobs for shot selection and the existing R210 importer."""
from __future__ import annotations

import subprocess
import os
import signal
import secrets
import threading
from pathlib import Path

from studio.project_store import ProjectStoreError, _atomic
from studio.media_review import now, read_json, directory_lock
from music_library.errors import MusicError, MemberRequired, import_failure_message
from music_library.links import parse_link
from music_library.egress import read_target
from music_library.netease import read_session


class ReviewJobs:
    def __init__(self, review, *, spawn=subprocess.Popen):
        self.review, self.spawn = review, spawn
        self.lock = threading.RLock()
        self.shot_processes = {}
        self.imports = {}
        self.threads = []
        self.counter = 0
        self.preparation = None

    def shots(self, identity, action):
        if action not in ('start', 'restart', 'resume', 'stop'):
            raise ProjectStoreError('review_action_invalid', '挑镜头操作无效')
        folder = self.review.workspace(identity) / 'ai-analysis/shots'
        path = folder / 'progress.json'
        with self.lock, directory_lock(folder):
            running = self.shot_processes.get(folder)
            saved = read_json(path, optional=True) or {}
            if saved.get('status') == 'running' and not (running and running.poll() is None):
                pid = saved.get('pid')
                live = pid is None
                if type(pid) is int and pid > 1:
                    try:
                        os.kill(pid, 0)
                        live = True
                    except ProcessLookupError:
                        live = False
                    except PermissionError:
                        live = True
                if live:
                    raise ProjectStoreError('revision_conflict', '正在挑镜头')
            if action == 'stop':
                if running and running.poll() is None:
                    self.terminate(running)
                return {'status': 'stopping'}
            if running and running.poll() is None:
                raise ProjectStoreError('revision_conflict', '正在挑镜头')
            script = Path(__file__).resolve().parents[1] / 'scripts/select_shots.py'
            python = script.parent.parent / '.venv/bin/python'
            if not python.is_file():
                raise ProjectStoreError('runtime_unavailable', '本机运行环境不可用')
            args = [str(python), str(script), str(self.review.workspace(identity))]
            if action == 'resume':
                args.append('--resume')
            folder.mkdir(parents=True, exist_ok=True)
            job_id = secrets.token_hex(12)
            initial = dict(status='running', phase='local', completed=0, total=0, started_at=now(), job_id=job_id)
            _atomic(path, initial)
            try:
                process = self.spawn(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            except OSError as exc:
                _atomic(path, dict(status='failed', phase='local', completed=0, total=0, reason='本机运行环境不可用'))
                raise ProjectStoreError('runtime_unavailable', '本机运行环境不可用') from exc
            initial['pid'] = getattr(process, 'pid', None)
            _atomic(path, initial)
            self.shot_processes[folder] = process
            def monitor():
                code = process.wait()
                with self.lock, directory_lock(folder):
                    current = read_json(path, optional=True) or {}
                    if current.get('job_id') != job_id:
                        return
                    current.update(status='complete' if code == 0 else 'stopped' if code < 0 else 'failed', finished_at=now())
                    if code != 0:
                        current['reason'] = f'挑选进程因信号 {-code} 停止。' if code < 0 else f'挑选进程退出，退出码 {code}。'
                    _atomic(path, current)
            thread = threading.Thread(target=monitor, daemon=True); thread.start(); self.threads.append(thread)
            return {'status': 'running'}

    def import_music(self, value):
        folder = value.get('folder')
        if folder is not None:
            directory = Path(folder).expanduser().resolve()
            if not directory.is_relative_to(Path.home().resolve()) or not directory.is_dir():
                raise ProjectStoreError('music_folder_invalid', '文件夹位置必须在用户主目录内')
        else:
            parse_link(str(value.get('text', '')))
        with self.lock:
            self.counter += 1
            identity = str(self.counter)
            self.imports[identity] = {'id': identity, 'state': 'importing'}
        def worker():
            platform = None
            try:
                if folder is not None:
                    from import_music import import_folder
                    results = import_folder(self.review.music, directory)
                    if not results:
                        raise MusicError('文件夹里没有可导入的音频')
                    errors = [r['reason'] for r in results if r.get('reason')]
                    result = dict(state='error' if errors else 'complete', results=results, reason='、'.join(errors))
                else:
                    platform = parse_link(value['text']).platform
                    status, track = self.review.music.import_link(value['text'], search_elsewhere=value.get('searchElsewhere') is True)
                    result = dict(state='duplicate' if status == '已在库里' else 'complete', trackId=track['file_sha256'], title=track['title'])
                self.review.prepare_peaks()
            except MemberRequired as exc:
                result = dict(state='member', title=exc.title, artist=exc.artist)
            except MusicError as exc:
                result = dict(state='error', reason=import_failure_message(platform, exc))
            except (OSError, ValueError, subprocess.SubprocessError):
                result = dict(state='error', reason='导入数据或本地写入失败，未完成入库')
            with self.lock:
                self.imports[identity].update(result)
        thread = threading.Thread(target=worker, daemon=True); thread.start(); self.threads.append(thread)
        return self.imports[identity].copy()

    def import_status(self, identity):
        with self.lock:
            return self.imports.get(identity, {}).copy() or None

    def music_settings(self):
        result = {}
        for name, reader in [('egress', read_target), ('account', read_session)]:
            try:
                result[name] = {'state': 'configured' if reader() else 'absent'}
            except MusicError as exc:
                result[name] = {'state': 'unreadable', 'reason': str(exc)}
        return result

    @staticmethod
    def terminate(process, *, kill=False):
        if hasattr(process, 'pid'):
            try:
                os.killpg(process.pid, signal.SIGKILL if kill else signal.SIGTERM)
            except ProcessLookupError:
                pass
        elif kill:
            process.kill()
        else:
            process.terminate()

    def prepare(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/prepare_studio_media.py'
        self.preparation = self.spawn([str(script.parent.parent / '.venv/bin/python'), str(script), '--state-dir', str(self.review.store.state_dir)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def close(self):
        for process in [*self.shot_processes.values(), *([self.preparation] if self.preparation else [])]:
            if process.poll() is None:
                self.terminate(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.terminate(process, kill=True); process.wait(timeout=5)
        for thread in self.threads:
            thread.join(timeout=5)
