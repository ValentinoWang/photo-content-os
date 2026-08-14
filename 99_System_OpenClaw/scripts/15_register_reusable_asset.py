#!/usr/bin/env python3
"""Register a project media file as a reusable asset without duplicating source media."""

from __future__ import annotations

import argparse
from pathlib import Path

from media_common import media_id, project_path, relative_posix, safe_slug


DEFAULT_INDEX_NAME = "Reusable_通用素材索引.md"


def find_library_root(project: Path, value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    for parent in [project, *project.parents]:
        if (parent / "99_System_OpenClaw" / "docs" / "00_本地素材与剪映HyperFrames流转总纲.md").exists():
            return parent / "02_Asset_Library"
    return project.parent / "02_Asset_Library"


def resolve_media(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    try:
        path.relative_to(project)
    except ValueError as exc:
        raise RuntimeError(f"media path must be inside project: {path}") from exc
    if not path.exists():
        raise FileNotFoundError(f"media file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"media path is not a file: {path}")
    return path


def split_values(value: str | None) -> list[str]:
    if not value:
        return []
    separators = ["、", "，", ",", ";", "；", "|", "\n"]
    text = value
    for separator in separators:
        text = text.replace(separator, "\n")
    return [part.strip() for part in text.splitlines() if part.strip()]


def bullet_list(items: list[str], fallback: str = "待补充") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def build_card(
    *,
    title: str,
    project: Path,
    media: Path,
    library_root: Path,
    category: str,
    tags: list[str],
    uses: list[str],
    cuts: list[str],
    public_status: str,
    icloud_copy: str,
    notes: str,
) -> str:
    rel_media = relative_posix(media, project)
    return f"""# {title}

- 原始项目：{project.name}
- 源文件位置：{rel_media}
- 源文件绝对路径：{media}
- 资产分类：{category}
- 公开状态：{public_status}
- iCloud 精选副本：{icloud_copy or "无 / 未登记"}

## 复用标签

{bullet_list(tags)}

## 适合用途

{bullet_list(uses)}

## 建议截取

{bullet_list(cuts)}

## 归档原则

- 源文件只保留在项目目录，不复制到通用资产库。
- 这里保存的是复用索引；真正可直接剪辑的调色、裁切、Wink 成品副本再单独登记。
- 多重价值通过标签和用途复用，不通过到处复制源文件解决。

## 备注

{notes or "待补充"}

## 索引位置

- 资产库：{library_root}
- 索引：{DEFAULT_INDEX_NAME}
"""


def upsert_index(index_path: Path, title: str, card_rel: str, tags: list[str], uses: list[str]) -> None:
    line = f"- [{title}]({card_rel})：{'; '.join(tags[:6]) or '未标注'}；用途：{'; '.join(uses[:4]) or '待补充'}"
    if index_path.exists():
        lines = index_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            "# Reusable 通用素材索引",
            "",
            "这个索引只记录可复用素材的来源和用途，不存放源文件副本。",
            "",
            "## 素材",
            "",
        ]
    prefix = f"- [{title}]("
    updated = False
    for index, old_line in enumerate(lines):
        if old_line.startswith(prefix):
            lines[index] = line
            updated = True
            break
    if not updated:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(line)
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def register_asset(args: argparse.Namespace) -> tuple[Path, Path]:
    project = project_path(args.project_dir)
    media = resolve_media(project, args.media_path)
    library_root = find_library_root(project, args.library_root)
    category = args.category.strip() or "Reusable_通用素材"
    title = args.title.strip() if args.title else media.stem
    tags = split_values(args.tags)
    uses = split_values(args.uses)
    cuts = split_values(args.cuts)
    public_status = args.public_status.strip() if args.public_status else "待确认"
    notes = args.notes.strip() if args.notes else ""
    icloud_copy = args.icloud_copy.strip() if args.icloud_copy else ""

    category_dir = library_root / safe_slug(category)
    category_dir.mkdir(parents=True, exist_ok=True)
    asset_key = media_id(f"{project.name}/{relative_posix(media, project)}")
    card_path = category_dir / f"{asset_key}_{safe_slug(title)}.asset.md"
    index_path = library_root / DEFAULT_INDEX_NAME

    card = build_card(
        title=title,
        project=project,
        media=media,
        library_root=library_root,
        category=category,
        tags=tags,
        uses=uses,
        cuts=cuts,
        public_status=public_status,
        icloud_copy=icloud_copy,
        notes=notes,
    )
    card_path.write_text(card, encoding="utf-8")
    upsert_index(index_path, title, relative_posix(card_path, library_root), tags, uses)
    return index_path, card_path


def main() -> None:
    parser = argparse.ArgumentParser(description="登记多重价值素材到通用资产索引")
    parser.add_argument("project_dir", help="素材所属项目目录")
    parser.add_argument("media_path", help="项目内相对路径或绝对路径")
    parser.add_argument("--library-root", help="资产库目录，默认查找本地素材根下的 02_Asset_Library")
    parser.add_argument("--category", default="Reusable_通用素材", help="资产分类目录，如 Reusable_颜值类")
    parser.add_argument("--title", help="索引标题")
    parser.add_argument("--tags", help="标签，支持用顿号/逗号/分号分隔")
    parser.add_argument("--uses", help="复用用途，支持用顿号/逗号/分号分隔")
    parser.add_argument("--cuts", help="建议截取，支持用顿号/逗号/分号分隔")
    parser.add_argument("--public-status", help="公开状态，例如 可公开 / 待确认 / 私密")
    parser.add_argument("--icloud-copy", help="已进入 80_To_iCloudPhotos_精选入库 的副本路径")
    parser.add_argument("--notes", help="补充备注")
    args = parser.parse_args()

    index_path, card_path = register_asset(args)
    print(f"通用素材索引已更新：{index_path}")
    print(f"资产卡片已写入：{card_path}")


if __name__ == "__main__":
    main()
