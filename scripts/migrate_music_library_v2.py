#!/usr/bin/env python3
"""Preview or apply the music library v2 migration after a verified external backup."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from music_library.cache import read_json, write_json
from music_library.errors import MusicError
from music_library.library import MusicLibrary, validate_track

REMOVED = {'license_status', 'attribution', 'bpm', 'beats', 'sections'}


def migrate(media_root=None, *, apply=False, backup_root=None):
    library = MusicLibrary(media_root)
    with library.locked():
        index_path = library.root / 'index.json'
        index = read_json(index_path, '音乐库索引')
        if index.get('schema_version') == 2:
            library._tracks()
            return {'state': 'unchanged', 'tracks': len(index['tracks'])}
        if index.get('schema_version') != 1 or not isinstance(index.get('tracks'), list):
            raise MusicError('迁移输入不是 v1 曲库')
        plans = {}
        tracks = []
        for old in index['tracks']:
            if old.get('schema_version') != 1:
                raise MusicError('曲目版本和索引不一致，拒绝迁移')
            track = {k: v for k, v in old.items() if k not in REMOVED}
            track['schema_version'] = 2
            validate_track(track)
            path = library.root / track['file_sha256'] / 'track.json'
            if path in plans or read_json(path, '曲目信息') != old or not (path.parent / track['audio_file']).is_file():
                raise MusicError('曲目和索引不一致，拒绝迁移')
            plans[path] = track
            tracks.append(track)
        if set(library.root.glob('*/track.json')) != set(plans):
            raise MusicError('曲目目录和索引不一致，拒绝迁移')
        plans[index_path] = {'schema_version': 2, 'tracks': tracks}
        if not apply:
            return {'state': 'preview', 'tracks': len(tracks), 'files': len(plans)}
        backup_base = Path(backup_root) if backup_root else Path.home() / '.photo-content-os/backups'
        if backup_base.resolve().is_relative_to(library.root.resolve()):
            raise MusicError('备份必须在曲库外')
        backup = backup_base / ('music-library-v1-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        backup.mkdir(parents=True)
        # Verify every backup before the first write. No audio or derived assets are copied.
        for path in plans:
            destination = backup / path.relative_to(library.root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(destination.read_bytes()).digest():
                raise MusicError('备份校验失败，未迁移')
        try:
            for path, data in plans.items():
                write_json(path, data)
            library._tracks()
        except BaseException:
            for path in plans:
                shutil.copy2(backup / path.relative_to(library.root), path)
            raise
        return {'state': 'applied', 'tracks': len(tracks), 'backup': str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media-root')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(migrate(args.media_root, apply=args.apply), ensure_ascii=False))
    except (MusicError, OSError, ValueError) as exc:
        print(f'迁移失败：{exc}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
