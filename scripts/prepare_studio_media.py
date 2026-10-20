#!/usr/bin/env python3
"""Prepare the Studio derivative caches without changing shot decisions."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.project_store import ProjectStore
from studio.media_review import MediaReview
from shot_previews import generate_previews


def prepare(state_dir, *, rebuild_posters=False):
    review=MediaReview(ProjectStore(state_dir))
    review.prepare_posters(rebuild=rebuild_posters)
    review.prepare_peaks()
    from asset_library_index import load_index
    for asset in load_index(Path(state_dir) / 'asset-library/index.json')['assets']:
        review.prepare_asset(asset)
    for project in review.store.list_projects():
        if not project['local_workspace']['connected']:
            continue
        root=review.workspace(project['id'])
        path=root/'ai-analysis/shots/shots.json'
        if path.is_file():
            from studio.media_review import read_json
            generate_previews(root,read_json(path))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--state-dir',required=True,type=Path)
    cli.add_argument('--rebuild-posters', action='store_true')
    args = cli.parse_args()
    prepare(args.state_dir, rebuild_posters=args.rebuild_posters)
