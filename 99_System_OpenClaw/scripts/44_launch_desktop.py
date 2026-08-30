#!/usr/bin/env python3
"""Launch the local-first Photo Content OS Studio in the default browser."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parent.parent
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.server import serve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".photo-content-os" / "studio")
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "localhost", "::1"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    def ready(url: str) -> None:
        print(f"Photo Content OS Studio: {url}")
        print(f"Local state: {args.state_dir.expanduser().resolve()}")
        if not args.no_browser:
            webbrowser.open(url)

    server = serve(state_dir=args.state_dir, host=args.host, port=args.port, on_ready=ready)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStudio stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
