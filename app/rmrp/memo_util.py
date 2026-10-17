"""Краткие памятки: теги, фильтр, подготовка фото. Без зависимостей от GUI (Pillow — по возможности)."""
import io
import os
import re
import uuid
import zlib

from .config import MEMO_BUCKET, MEMO_TAGS

try:
    from PIL import Image, ImageOps
except Exception:  # noqa: BLE001
    Image = ImageOps = None

MAX_IMAGES = 8
MAX_TAGS = 8
MAX_TAG_LEN = 24
MAX_TITLE = 120
MAX_CONTENT = 8000
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
IMAGE_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
_PALETTE = ["#2f7bf5", "#8b5cf6", "#14b8a6", "#f59e0b", "#ec4899", "#22c55e", "#06b6d4", "#ef4444"]
_KNOWN = {name.lower(): color for name, color in MEMO_TAGS}


def normalize_tags(raw):
    """Строка «важно, #суд; Штрафы» или список -> список уникальных тегов (без регистра), не длиннее лимитов."""
    if isinstance(raw, str):
        raw = re.split(r"[,;\n]+", raw)
    out, seen = [], set()
    for item in raw or []:
        t = re.sub(r"\s+", " ", str(item).replace("#", " ")).strip()[:MAX_TAG_LEN].strip()
        if not t or t.lower() in seen:
            continue
        seen.add(t.lower())
        # известные теги приводим к каноническому написанию
        canon = next((n for n, _ in MEMO_TAGS if n.lower() == t.lower()), t)
        out.append(canon)
        if len(out) >= MAX_TAGS:
            break
    return out


def tag_color(tag):
    c = _KNOWN.get(str(tag).lower())
    return c or _PALETTE[zlib.crc32(str(tag).lower().encode("utf-8")) % len(_PALETTE)]


def all_tags(memos):
    """Теги для панели фильтра: сначала стандартные (если есть в памятках), затем остальные по частоте."""
    count = {}
    for m in memos:
        for t in m.get("tags") or []:
            count[t] = count.get(t, 0) + 1
    known = [n for n, _ in MEMO_TAGS if n in count]
    rest = sorted((t for t in count if t not in known), key=lambda t: (-count[t], t.lower()))
    return [(t, count[t]) for t in known + rest]


def filter_memos(memos, query="", tags=()):
    """Все выбранные теги должны присутствовать; запрос ищется в заголовке, тексте и тегах."""
    q = (query or "").strip().lower()
    want = {t.lower() for t in tags}
    out = []
    for m in memos:
        mt = {str(t).lower() for t in m.get("tags") or []}
        if want and not want <= mt:
            continue
        if q:
            hay = " ".join([m.get("title") or "", m.get("content") or "", " ".join(m.get("tags") or [])]).lower()
            if q not in hay:
                continue
        out.append(m)
    return out


def sort_memos(memos):
    """Закреплённые сверху, внутри — новые первыми."""
    newest = sorted(memos, key=lambda m: str(m.get("created_at") or ""), reverse=True)
    return sorted(newest, key=lambda m: not m.get("pinned"))  # сортировка устойчива


def validate_memo(title, content, tags, image_count):
    """Возвращает текст ошибки или None."""
    if not (title or "").strip():
        return "Введите заголовок."
    if len(title.strip()) > MAX_TITLE:
        return f"Заголовок длиннее {MAX_TITLE} символов."
    if not (content or "").strip() and not image_count:
        return "Добавьте текст или хотя бы одно фото."
    if len(content or "") > MAX_CONTENT:
        return f"Текст длиннее {MAX_CONTENT} символов."
    if image_count > MAX_IMAGES:
        return f"Не больше {MAX_IMAGES} фото в одной памятке."
    return None


def prepare_image(path, max_side=1600):
    """Читает файл, уменьшает и сжимает. Возвращает (bytes, content_type, ext). Бросает ValueError при проблеме."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMAGE_EXT:
        raise ValueError("Поддерживаются JPG, PNG, WEBP и GIF.")
    with open(path, "rb") as f:
        raw = f.read(30 * 1024 * 1024 + 1)
    if len(raw) > 30 * 1024 * 1024:
        raise ValueError("Файл больше 30 МБ.")
    if Image is None:  # без Pillow — только как есть
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("Файл больше 5 МБ (установите Pillow для автосжатия).")
        return raw, IMAGE_EXT[ext], ext.lstrip(".").replace("jpeg", "jpg")
    try:
        img = Image.open(io.BytesIO(raw))
        if getattr(img, "is_animated", False) and ext == ".gif" and len(raw) <= MAX_UPLOAD_BYTES:
            return raw, "image/gif", "gif"  # анимацию не трогаем
        img = ImageOps.exif_transpose(img)
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        img.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        if has_alpha:
            img.convert("RGBA").save(buf, "PNG", optimize=True)
            ctype, out_ext = "image/png", "png"
        else:
            img.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
            ctype, out_ext = "image/jpeg", "jpg"
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Не удалось прочитать картинку: {e}")
    data = buf.getvalue()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("После сжатия фото всё равно больше 5 МБ.")
    return data, ctype, out_ext


def new_object_path(user_id, ext):
    return f"{user_id or 'anon'}/{uuid.uuid4().hex}.{ext}"


def object_path(value, bucket=MEMO_BUCKET):
    """В БД лежит путь объекта; на всякий случай принимаем и полный публичный URL."""
    marker = f"/object/public/{bucket}/"
    s = str(value or "")
    return s.split(marker, 1)[1] if marker in s else s
