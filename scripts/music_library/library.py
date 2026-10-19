import fcntl
import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from runtime_paths import local_media_root
from .audio import measure_audio
from .cache import read_json, write_json
from .errors import MusicError, MemberRequired
from .links import parse_link


LICENSE_LABELS = {
    'platform_copyrighted': '平台版权曲：只用来定切点和本地预览，发布时在剪映或平台曲库里换用同一首',
    'cc0': 'CC0：可商用',
    'cc_by': 'CC BY：发布时须按署名文字署名',
    'unknown': '授权未知，发布前要确认',
}
SCHEMA = Path(__file__).resolve().parents[2] / 'schemas/music-track.schema.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def validate_track(track):
    try:
        Draft202012Validator(read_json(SCHEMA, '曲目规范'), format_checker=FormatChecker()).validate(track)
    except Exception as exc:
        raise MusicError('曲目信息不符合规范，授权等必填信息不得缺失') from exc


class MusicLibrary:
    def __init__(self, media_root=None, *, adapter=None, measure=measure_audio):
        self.root = local_media_root(media_root) / 'library/music'
        self.adapter = adapter
        self.measure = measure

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _tracks(self):
        index_path = self.root / 'index.json'
        if not index_path.exists():
            if list(self.root.glob('*/track.json')):
                raise MusicError('音乐库索引缺失，请维护者从曲目文件修复索引')
            return []
        index = read_json(index_path, '音乐库索引')
        if not isinstance(index, dict) or index.get('schema_version') != 1 or not isinstance(index.get('tracks'), list):
            raise MusicError('音乐库索引格式损坏，请维护者修复')
        tracks = index['tracks']
        seen = set()
        for track in tracks:
            validate_track(track)
            identity = track['file_sha256']
            if identity in seen:
                raise MusicError('音乐库索引包含重复曲目，请维护者修复')
            seen.add(identity)
            directory = self.root / identity
            if read_json(directory / 'track.json', '曲目信息') != track or not (directory / track['audio_file']).is_file():
                raise MusicError('音乐库索引与文件不一致，请维护者检查；不会重新下载')
        if {p.parent.name for p in self.root.glob('*/track.json')} != seen:
            raise MusicError('音乐库索引与曲目目录不一致，请维护者检查')
        return tracks

    def list_tracks(self):
        with self.locked():
            return self._tracks()

    def _write_index(self, tracks):
        write_json(self.root / 'index.json', {'schema_version': 1, 'tracks': tracks})

    @staticmethod
    def _find(tracks, platform, identity, kind):
        family = lambda value: 'netease' if value == 'netease_client' else value
        return next((track for track in tracks for source in track['sources']
                     if family(source['platform']) == family(platform) and source['platform_id'] == identity and source['kind'] == kind), None)

    def import_link(self, text, *, search_elsewhere=False):
        link = parse_link(text)
        with self.locked():
            tracks = self._tracks()
            if link.platform_id:
                existing = self._find(tracks, link.platform, link.platform_id, link.kind)
                if existing:
                    return '已在库里', existing
            attempts = self.root / '.attempts'
            attempts.mkdir(exist_ok=True)
            record_path = attempts / (hashlib.sha256(link.key.encode()).hexdigest() + '.json')
            cached_member = None
            alternative_attempted = False
            if record_path.exists():
                record = read_json(record_path, '导入缓存')
                if record.get('state') == 'complete':
                    existing = next((t for t in tracks if t['file_sha256'] == record.get('file_sha256')), None)
                    if existing:
                        return '已在库里', existing
                    raise MusicError('导入缓存对应的曲目缺失，已停止重复联网')
                if record.get('state') == 'failed' and search_elsewhere and record.get('member_track') and not record.get('alternative_attempted'):
                    cached_member = record['member_track']
                elif record.get('state') == 'failed' and isinstance(record.get('reason'), str):
                    raise MusicError(record['reason'] + '（本地失败缓存，未再次联网）')
                else:
                    raise MusicError('这个链接已尝试过且未完成，已停止重复联网；请维护者检查缓存')
            if self.adapter is None:
                from .platforms import PlatformAdapter
                self.adapter = PlatformAdapter(self.root / '.http-cache')
            write_json(record_path, {'state': 'attempted'})
            try:
                with self.adapter.import_context(link.platform) if hasattr(self.adapter, "import_context") else nullcontext():
                    try:
                        if cached_member:
                            raise MemberRequired(cached_member['title'], cached_member['artist'])
                        resolved = self.adapter.resolve(link)
                    except MemberRequired as exc:
                        cached_member = {'title': exc.title, 'artist': exc.artist}
                        if not search_elsewhere:
                            raise
                        alternative_attempted = True
                        write_json(record_path, {'state': 'attempted', 'member_track': cached_member, 'alternative_attempted': True})
                        ids = {source['platform_id'] for t in tracks for source in t['sources'] if source['platform'] == 'qishui'}
                        resolved = self.adapter.search_exact(exc.title, exc.artist, existing_ids=ids)
                    identity = resolved['platform_id']
                    platform = resolved.get('source_platform', link.platform)
                    kind = 'music' if platform == 'douyin' else 'song'
                    existing = self._find(tracks, platform, identity, kind)
                    source = {'platform': platform, 'platform_id': identity, 'kind': kind,
                              'original_url': resolved.get('source_url', link.url), 'imported_at': now()}
                    if existing:
                        status, track = '已在库里', existing
                    else:
                        with tempfile.TemporaryDirectory(prefix='.import-', dir=self.root) as staging:
                            audio = Path(staging) / ('audio' + resolved['extension'])
                            self.adapter.download(resolved, audio)
                            status, track = self._store(audio, resolved, source, tracks)
                    write_json(record_path, {'state': 'complete', 'file_sha256': track['file_sha256']})
                    return status, track
            except MusicError as exc:
                write_json(record_path, {'state': 'failed', 'reason': str(exc),
                                         'member_track': cached_member, 'alternative_attempted': alternative_attempted,
                                         'failure': getattr(exc, 'diagnostic', None)})
                raise
            except (OSError, ValueError, KeyError, TypeError) as exc:
                write_json(record_path, {'state': 'failed', 'reason': '导入数据或本地写入失败，未完成入库'})
                raise MusicError('导入数据或本地写入失败，未完成入库') from exc

    def _store(self, audio, metadata, source, tracks):
        digest = file_hash(audio)
        existing = next((t for t in tracks if t['file_sha256'] == digest), None)
        if existing:
            updated = {**existing, 'sources': [*existing['sources'], source]}
            # Hash deduplication never upgrades an unknown authorization to publishable.
            validate_track(updated)
            track_path = self.root / digest / 'track.json'
            write_json(track_path, updated)
            try:
                self._write_index([updated if t is existing else t for t in tracks])
            except BaseException:
                write_json(track_path, existing)
                raise
            return '已在库里', updated
        measurements = self.measure(audio)
        if metadata.get('expected_duration') and abs(measurements['duration_seconds'] - metadata['expected_duration']) > 2:
            raise MusicError('下载音频时长与完整歌曲不符，可能是试听片段，未入库')
        track = {'schema_version': 1, 'title': metadata['title'], 'artist': metadata['artist'],
                 'album': metadata.get('album'), 'platform': source['platform'],
                 'platform_id': source['platform_id'], 'original_url': source['original_url'],
                 'imported_at': source['imported_at'], 'file_sha256': digest,
                 'audio_file': 'audio' + audio.suffix.lower(), 'license_status': metadata['license_status'],
                 'attribution': metadata.get('attribution'), 'sources': [source],
                 'bpm': None, 'beats': None, 'sections': None, **measurements}
        validate_track(track)
        directory = self.root / digest
        if directory.exists():
            raise MusicError('曲目目录与索引冲突，请维护者检查')
        with tempfile.TemporaryDirectory(prefix='.store-', dir=self.root) as staging:
            stage = Path(staging) / digest
            stage.mkdir()
            shutil.copy2(audio, stage / track['audio_file'])
            write_json(stage / 'track.json', track)
            stage.rename(directory)
            try:
                self._write_index([*tracks, track])
            except BaseException:
                shutil.rmtree(directory)
                raise
        return '已入库', track

    def import_local(self, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise MusicError('本地音频文件不存在或无法读取')
        if path.suffix.lower() not in ('.mp3', '.mp4', '.m4a', '.wav', '.flac', '.ogg', '.aac'):
            raise MusicError('不支持的本地音频格式')
        with self.locked():
            tracks = self._tracks()
            digest = file_hash(path)
            existing = self._find(tracks, 'local', digest, 'file')
            if existing:
                return '已在库里', existing
            source = {'platform': 'local', 'platform_id': digest, 'kind': 'file',
                      'original_url': path.as_uri(), 'imported_at': now()}
            return self._store(path, {'title': path.stem, 'artist': '未知歌手', 'license_status': 'unknown'}, source, tracks)

    def import_client_file(self, path):
        from .client_files import decode_ncm, read_client_metadata
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise MusicError('客户端下载文件不存在或无法读取')
        with self.locked():
            tracks = self._tracks()
            digest = file_hash(path)
            cache = self.root / '.client-files'
            cache.mkdir(exist_ok=True)
            marker = cache / (digest + '.json')
            if marker.exists():
                record = read_json(marker, '本地文件导入记录')
                existing = next((t for t in tracks if t['file_sha256'] == record.get('file_sha256')), None)
                if existing:
                    return '已在库里', existing
                raise MusicError('本地文件导入记录与曲目不一致，请维护者检查')
            with tempfile.TemporaryDirectory(prefix='.decode-', dir=self.root) as staging:
                if path.suffix.lower() == '.ncm':
                    audio, metadata = decode_ncm(path, Path(staging))
                else:
                    audio, metadata = path, read_client_metadata(path)
                identity = metadata['platform_id']
                kind = 'song' if identity else 'file'
                if identity:
                    existing = self._find(tracks, 'netease', identity, kind)
                else:
                    existing = None
                source = {'platform': 'netease_client', 'platform_id': identity or file_hash(audio), 'kind': kind,
                          'original_url': path.as_uri(), 'imported_at': now()}
                if existing:
                    status, track = '已在库里', existing
                else:
                    status, track = self._store(audio, metadata, source, tracks)
            write_json(marker, {'file_sha256': track['file_sha256']})
            return status, track
