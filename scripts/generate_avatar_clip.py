#!/usr/bin/env python3
"""Generate or estimate a videoretalk clip."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.avatar.videoretalk import AvatarError, generate_avatar_clip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--material', required=True, choices=['public-sample', 'self'])
    parser.add_argument('--owner-consent')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--max-seconds', type=float, default=110)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--wait-seconds', type=float, default=900)
    args = parser.parse_args()
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
