#!/usr/bin/env python3
"""Generate or estimate a videoretalk clip."""
import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.avatar.videoretalk import AvatarError, forget_unknown, generate_avatar_clip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path)
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--material', choices=['public-sample', 'self'])
    parser.add_argument('--owner-consent')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--max-seconds', type=float, default=110)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--wait-seconds', type=float, default=900)
    parser.add_argument('--forget-unknown', type=int, metavar='段号', help='确认百炼未创建任务后，解除指定段的提交限制。段号从 0 开始。')
    parser.add_argument('--reason', help='操作原话，将写入账本。')
    args = parser.parse_args()
    if args.forget_unknown is not None:
        if not (args.reason or '').strip():
            parser.error('--forget-unknown 必须提供非空的 --reason')
        try:
            forget_unknown(args.out_dir, args.forget_unknown, args.reason)
        except (AvatarError, OSError) as e:
            print(str(e) if isinstance(e, AvatarError) else 'avatar_input_invalid', file=sys.stderr)
            return 1
        return 0
    if args.reason is not None:
        parser.error('--reason 只能和 --forget-unknown 一起使用')
    missing = [flag for flag in ('video', 'audio', 'material') if getattr(args, flag) is None]
    if missing:
        parser.error('生成片段需要 ' + ', '.join('--' + flag for flag in missing))
    key = os.environ.get('DASHSCOPE_API_KEY', '')
    try:
        if not key and args.env_file:
            for line in args.env_file.read_text(encoding='utf-8').splitlines():
                name, sep, value = line.strip().partition('=')
                if sep and name in ('DASHSCOPE_API_KEY', 'SPEECH_TO_TEXT_API_KEY'):
                    key = value.strip().strip('\"\'')
                    if key:
                        break
        result = generate_avatar_clip(args.video, args.audio, args.out_dir, material=args.material, owner_consent=args.owner_consent, api_key=key, live=args.live, max_seconds=args.max_seconds, wait_seconds=args.wait_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (AvatarError, OSError) as e:
        print(str(e) if isinstance(e, AvatarError) else 'avatar_api_key_missing', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
