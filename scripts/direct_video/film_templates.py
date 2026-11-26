#!/usr/bin/env python3
"""Build and validate the pinned MotionGit film-template index."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).with_suffix("")
COMMIT = "b74e9c9e800cc3158bc16f6e9468f0f560248243"
REPO = "https://github.com/motiontemplates/all"
LICENSE_URL = "https://raw.githubusercontent.com/motiontemplates/385712/9dfbe7d7c6a6d4aa03f6f8e2f2285e631099faae/template.json"


def read_json(source):
    if source.startswith("https://"):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return response.json()
    return json.loads(Path(source).read_text(encoding="utf-8"))


def build_catalog(source, open_license=None):
    upstream = read_json(source)
    templates = []
    for item in upstream["templates"]:
        is_open = item["download"]["type"] == "direct-package"
        media = item.get("media", {})
        zh, en = media.get("zh", {}), media.get("en", {})
        if is_open and open_license is None:
            open_license = read_json(LICENSE_URL)["license"]
        templates.append({
            "id": str(item["repositoryId"]), "template_id": item["templateId"],
            "title_zh": item["title"]["zh"], "title_en": item["title"]["en"],
            "group": item["group"], "orientation": item["orientation"], "ratio": item["ratio"],
            "width": item["width"], "height": item["height"], "fps": item["fps"],
            "version": item["version"], "summary_zh": item["summary"]["zh"],
            "materials_zh": item.get("materials", {}).get("zh"),
            "demo_url": zh.get("demo") or en.get("demo") or item.get("demo"),
            "poster_url": zh.get("poster") or en.get("poster") or item.get("poster"),
            "website": item["website"], "repository": item.get("repository"),
            "commit": item.get("commit"),
            "source_status": "open-package" if is_open else "account-required",
            "license": open_license if is_open else "unknown",
        })
    templates.sort(key=lambda t: t["id"])
    return {"upstream_repo": REPO, "upstream_commit": COMMIT, "count": len(templates), "templates": templates}


def check_catalog(catalog):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", catalog.get("upstream_commit", "")):
        raise ValueError("invalid upstream commit")
    entries = catalog["templates"]
    if catalog["count"] != 206 or len(entries) != 206:
        raise ValueError("catalog must contain 206 templates")
    if len({x["id"] for x in entries}) != len(entries):
        raise ValueError("duplicate template id")
    required = ("id", "template_id", "title_zh", "title_en", "group", "orientation", "ratio", "width", "height", "fps", "version", "summary_zh", "demo_url", "poster_url", "website", "source_status", "license")
    for item in entries:
        for key in required:
            if not item.get(key):
                raise ValueError(f"{item.get('id')}: missing {key}")
        for key in ("demo_url", "poster_url", "website", "repository"):
            value = item.get(key)
            if value and (urlparse(value).scheme != "https" or not urlparse(value).netloc):
                raise ValueError(f"{item['id']}: invalid URL {key}")


def check_scene(scene, entry):
    if scene.get("id") != entry["id"] or scene.get("commit") != entry.get("commit"):
        raise ValueError(f"{entry['id']}: scene provenance mismatch")
    for part in scene["scenes"]:
        if part.get("source_commit") != entry["commit"] or not part.get("source_file"):
            raise ValueError(f"{entry['id']}: scene source mismatch")
        if isinstance(part.get("duration_seconds"), bool) or not isinstance(part.get("duration_seconds"), (int, float)) or part["duration_seconds"] <= 0:
            raise ValueError(f"{entry['id']}: invalid scene duration")
        if not part.get("key") or not part.get("purpose") or len(part["purpose"]) > 40 or not isinstance(part.get("required_fields"), list):
            raise ValueError(f"{entry['id']}: invalid scene fields")


def check_scenes(catalog, directory):
    entries = {entry["id"]: entry for entry in catalog["templates"]}
    for path in directory.glob("*.json"):
        scene = read_json(str(path))
        if path.stem != scene.get("id") or scene.get("id") not in entries:
            raise ValueError(f"{path}: unknown scene id")
        check_scene(scene, entries[scene["id"]])


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--summary", action="store_true")
    parser.add_argument("--upstream")
    args = parser.parse_args()
    path = ROOT / "catalog.json"
    if args.build:
        if not args.upstream:
            parser.error("--build requires --upstream")
        catalog = build_catalog(args.upstream)
        check_catalog(catalog)
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        catalog = read_json(str(path))
        if args.check:
            check_catalog(catalog)
            check_scenes(catalog, ROOT / "scenes")
            print("catalog OK: 206")
        else:
            print(f"total: {len(catalog['templates'])}")
            for key in ("group", "orientation", "source_status"):
                print(f"{key}:")
                for name, count in sorted(Counter(item[key] for item in catalog["templates"]).items()):
                    print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
