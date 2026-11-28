#!/usr/bin/env python3
"""Generate AI background music via WaveSpeed or Bailian and store it in the local music library."""
import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import signal

from music_library.sources.ai_generate import PROVIDERS, estimate_cost
from music_library.errors import MusicError
from music_library.library import MusicLibrary


def parser():
    cli = argparse.ArgumentParser(
        description='调用 WaveSpeed（ACE-Step 1.5）或阿里百炼（Fun-Music）生成配乐并入库；相同参数复用本地缓存，不重复付费'
    )
    cli.add_argument(
        '--provider',
        required=True,
        choices=list(PROVIDERS),
        help='服务商：wavespeed（ACE-Step 1.5，$0.0003/秒）或 bailian（百炼 fun-music-v1，¥0.002/秒）',
    )
    cli.add_argument('--prompt', required=True, help='音乐风格、情绪、乐器等提示词')
    cli.add_argument('--seconds', required=True, type=float, help='目标时长（秒），例如 30')
    cli.add_argument('--bpm', type=int, default=None, help='可选，每分钟节拍数（30–300），例如 100')
    cli.add_argument('--with-vocals', action='store_true', help='生成带人声歌曲；默认生成纯音乐')
    cli.add_argument('--title', default=None, help='可选，入库显示的曲目名称')
    cli.add_argument(
        '--retry-failed',
        action='store_true',
        help='对已受理但失败的同参数请求重新发起生成，并把旧失败记录改名留档；不跳过未完成（pending）任务',
    )
    return cli


def _format_loudness(track):
    if track.get('loudness_status') == 'measured' and track.get('loudness_lufs') is not None:
        return f'{track["loudness_lufs"]:.1f} LUFS'
    return '静音'


def _main(argv=None, *, library=None, gen_kwargs=None):
    cli = parser()
    args = cli.parse_args(argv)
    target_library = library if library is not None else MusicLibrary()
    extra = dict(gen_kwargs or {})
    try:
        status, track = target_library.import_generated(
            args.provider,
            args.prompt,
            args.seconds,
            bpm=args.bpm,
            instrumental=not args.with_vocals,
            title=args.title,
            retry_failed=args.retry_failed,
            **extra,
        )
    except MusicError as exc:
        print(f'失败：{exc}')
        return 1

    generation = track.get('generation') or {}
    provider = generation.get('provider', args.provider)
    model = generation.get('model', PROVIDERS[args.provider]['model'])
    billed_seconds = generation.get('billed_seconds')
    cost = estimate_cost(provider, args.seconds, billed_seconds=billed_seconds)

    if status == '已在库里':
        print(f'{status}：{track["title"]} — {track["artist"]}（已命中库内记录，未重复生成）')
    else:
        print(f'{status}：{track["title"]} — {track["artist"]}')
    print(f'来源：AI 生成（{PROVIDERS[provider]["label"]} / {model}）')
    print(f'时长：{track["duration_seconds"]:.1f} 秒 | 响度：{_format_loudness(track)}')
    if status == '已在库里':
        print(f'本次花费：0（已入库，原估算：{cost["text"]}）')
    else:
        print(f'花费估算：{cost["text"]}')
    print('提示：本曲为 AI 生成音乐，成片发布时请按平台要求勾选「AI 生成」标识。')
    return 0


def main(argv=None, *, library=None, gen_kwargs=None):
    previous = signal.getsignal(signal.SIGTERM)

    def interrupted(*_args):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        return _main(argv, library=library, gen_kwargs=gen_kwargs)
    except KeyboardInterrupt:
        print('生成已中断')
        return 130
    except OSError:
        print('失败：本地文件无法读取或写入，请检查目录权限和可用空间')
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    raise SystemExit(main())
