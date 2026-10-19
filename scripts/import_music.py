#!/usr/bin/env python3
"""Import a single song per input, or offline client files, into the local library."""
import argparse
import signal
from pathlib import Path

from music_library.errors import MusicError, import_failure_message
from music_library.library import LICENSE_LABELS, MusicLibrary
from music_library.links import parse_link

PLATFORMS = {'qishui': '汽水音乐', 'douyin': '抖音', 'netease': '网易云音乐',
             'netease_client': '网易云客户端下载', 'local': '本地文件'}


def parser():
    cli = argparse.ArgumentParser(description='导入汽水音乐、抖音或网易云单曲；重复输入只读本地缓存')
    cli.add_argument('inputs', nargs='*', metavar='分享文字或链接')
    cli.add_argument('--search-elsewhere', action='store_true', help='网易云会员曲只在汽水音乐搜一次相同歌名和歌手')
    cli.add_argument('--list', action='store_true', help='列出本地音乐库')
    cli.add_argument('--from-folder', nargs='?', const='~/Music/网易云音乐', metavar='文件夹',
                     help='离线导入客户端下载文件，默认 ~/Music/网易云音乐')
    cli.add_argument('--login', choices=['netease'], help='用手机扫码登录网易云')
    cli.add_argument('--browser', choices=['chrome', 'edge'], help='只读所选浏览器登录态，不保存 Cookie')
    cli.add_argument('--profile', default='Default', help='浏览器个人资料名称，默认 Default')
    return cli


def _main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if not (args.inputs or args.list or args.from_folder is not None or args.login):
        cli.error('请提供分享链接，或选择 --list、--from-folder、--login')
    if args.login and (args.inputs or args.list or args.from_folder is not None):
        cli.error('扫码登录请单独运行')
    if args.login:
        from music_library.netease import login_qr
        try:
            login_qr()
            print('网易云登录成功')
            return 0
        except MusicError as exc:
            print(f'失败：{exc}')
            return 1
    library = MusicLibrary()
    if args.browser:
        from music_library.platforms import PlatformAdapter
        library.adapter = PlatformAdapter(library.root / '.http-cache', browser=args.browser, profile=args.profile)
    failures = 0
    for number, text in enumerate(args.inputs, 1):
        platform = None
        try:
            platform = parse_link(text).platform
            status, track = library.import_link(text, search_elsewhere=args.search_elsewhere)
            print(f'{number}. {status}：{track["title"]} — {track["artist"]}；{LICENSE_LABELS[track["license_status"]]}')
        except MusicError as exc:
            print(f'{number}. 失败：{import_failure_message(platform, exc)}')
            failures += 1
    if args.from_folder is not None:
        directory = Path(args.from_folder).expanduser()
        if not directory.is_dir():
            print('失败：客户端下载文件夹不存在或无法读取')
            failures += 1
        else:
            try:
                files = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in
                               ('.ncm', '.mp3', '.flac', '.m4a', '.mp4', '.wav', '.ogg', '.aac'))
                if not files:
                    print('文件夹里没有可导入的音频')
                for number, path in enumerate(files, 1):
                    try:
                        status, track = library.import_client_file(path)
                        print(f'文件 {number}. {status}：{track["title"]}；{LICENSE_LABELS[track["license_status"]]}')
                    except MusicError as exc:
                        print(f'文件 {number}. 失败：{exc}')
                        failures += 1
            except OSError:
                print('失败：客户端下载文件夹无法读取')
                failures += 1
    if args.list:
        try:
            tracks = library.list_tracks()
            if not tracks:
                print('音乐库暂无曲目')
            for track in tracks:
                print(f'{track["title"]} — {track["artist"]} | {PLATFORMS[track["platform"]]} | '
                      f'{track["duration_seconds"]:.1f} 秒 | {LICENSE_LABELS[track["license_status"]]}')
        except MusicError as exc:
            print(f'失败：{exc}')
            failures += 1
    return 1 if failures else 0


def main(argv=None):
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(*args):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print('导入已中断，出口隧道已关闭')
        return 130
    except OSError:
        print('失败：本地文件无法读取或写入，请检查目录权限和可用空间')
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    raise SystemExit(main())
