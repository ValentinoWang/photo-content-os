"""Recipe catalog and project-scoped promotional image uploads."""
from pathlib import Path
from uuid import uuid4

from direct_video import recipe_library
from direct_video.generate import DirectVideoError

CATEGORIES = [('opening', '开场'), ('typography', '文字'), ('ui-entrance', '界面入场'),
              ('transition', '转场'), ('rhythm', '节奏'), ('data', '数据'),
              ('effects', '特效'), ('interaction', '交互'), ('camera', '运镜'), ('outro', '收尾')]
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def catalog():
    names = dict(CATEGORIES)
    entries = recipe_library.load_index()
    rows = []
    for entry in entries:
        row = {key: entry[key] for key in ('id', 'name', 'category', 'summary', 'use', 'seconds', 'energy')}
        row['categoryName'] = names[entry['category']]
        base = '/api/direct/recipes/' + entry['id']
        row['posterUrl'] = base + '/poster.jpg' if entry['poster'] else None
        row['clipUrl'] = base + '/clip.mp4' if entry['clip'] else None
        rows.append(row)
    return {'recipes': rows, 'categories': [{'key': key, 'name': name,
            'count': sum(row['category'] == key for row in rows)} for key, name in CATEGORIES]}


def artifact(recipe_id, kind):
    try:
        entry = recipe_library.get(recipe_id)
    except KeyError as exc:
        raise DirectVideoError('recipe_not_found') from exc
    root = recipe_library.ROOT if kind == 'poster.jpg' else recipe_library.CLIP_DIR
    relative = entry['poster'] if kind == 'poster.jpg' else entry['clip']
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise DirectVideoError('recipe_clip_missing' if kind == 'clip.mp4' else 'recipe_not_found')
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise DirectVideoError('recipe_clip_missing' if kind == 'clip.mp4' else 'recipe_not_found')
    return path


def upload(store, project_id, stream, length, content_type):
    store.get_project(project_id)
    if length <= 0 or length > MAX_IMAGE_BYTES or content_type not in ('image/png', 'image/jpeg'):
        raise DirectVideoError('promo_image_invalid')
    data = stream.read(length)
    valid = (content_type == 'image/png' and data.startswith(b'\x89PNG\r\n\x1a\n') or
             content_type == 'image/jpeg' and data.startswith(b'\xff\xd8\xff'))
    if len(data) != length or not valid:
        raise DirectVideoError('promo_image_invalid')
    image_id = uuid4().hex
    directory = store.state_dir / 'direct-promo-images' / project_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / image_id).write_bytes(data)
    return image_id
