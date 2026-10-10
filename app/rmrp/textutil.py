"""Разбор текстов форума, поиск по статьям, ответы помощника. Без зависимостей от GUI."""
import re
from datetime import datetime, timezone
from html import unescape

# --------------------------------------------------------------------------- разбор форума
ARTICLE_RE = re.compile(r"^Статья\s+([0-9]+(?:[-.][0-9]+)*)\.?\s+(.+)$", re.I)
CHAPTER_RE = re.compile(r"^Глава\s+([0-9]+(?:[-.][0-9]+)*|[IVXLC]+)\.?\s*(.*)$", re.I)
MIN_BODY = 30  # короче — это строка оглавления, а не статья


def html_to_lines(raw):
    raw = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<(br|/p|/div|/li|/h[1-6]|/blockquote|/tr)[^>]*>", "\n", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(raw).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in text.splitlines()]
    return [x for x in lines if x]


def parse_articles(lines):
    """Возвращает [{article_number, title, content, chapter, position}] в порядке следования в тексте."""
    chunks = {}
    chapter = ""
    order = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        cm = CHAPTER_RE.match(line)
        if cm and not ARTICLE_RE.match(line):
            title = cm.group(2).strip()
            if not title and i + 1 < n and not ARTICLE_RE.match(lines[i + 1]) and not CHAPTER_RE.match(lines[i + 1]) and len(lines[i + 1]) < 120:
                title = lines[i + 1]
                i += 1
            chapter = f"Глава {cm.group(1)}" + (f". {title}" if title else "")
            i += 1
            continue
        am = ARTICLE_RE.match(line)
        if not am:
            i += 1
            continue
        num, title = am.group(1), am.group(2).strip()
        j = i + 1
        while j < n and not ARTICLE_RE.match(lines[j]) and not CHAPTER_RE.match(lines[j]):
            j += 1
        content = "\n".join(lines[i + 1:j]).strip()
        if len(content) >= MIN_BODY:
            old = chunks.get(num)
            if old is None or len(content) > len(old["content"]):
                order += 1
                chunks[num] = {"article_number": num, "title": title, "content": content, "chapter": chapter,
                               "position": old["position"] if old else order}
        i = j
    return sorted(chunks.values(), key=lambda a: a["position"])


# --------------------------------------------------------------------------- сортировка / формат
def natural_key(value):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", str(value or ""))]


def article_sort_key(a):
    pos = a.get("position")
    if pos is not None:
        return (0, pos, natural_key(a.get("article_number")))
    return (1, 0, natural_key(a.get("article_number")))


def chapter_sort_key(name):
    m = re.match(r"Глава\s+(\d+)(?:[-.](\d+))?", name or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (10 ** 6, 0)


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_date(value, with_time=False):
    d = parse_ts(value)
    if not d:
        return "—"
    d = d.astimezone()
    return d.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def is_online(last_seen, window=180, now=None):
    d = parse_ts(last_seen)
    if not d:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - d).total_seconds() <= window


def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def plural(n, one, few, many):
    n = abs(int(n))
    if 11 <= n % 100 <= 14:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


# --------------------------------------------------------------------------- поиск
STOP = set("""что как где когда кто кого чем чего для при над под про без или это эта этот эти того там тут вот так тоже
есть быть был была были будет можно нужно ли же бы если его ее её их они она оно мне мой наш ваш какие какой какая какое
какого каких каком какую сколько почему зачем чтобы также только уже еще ещё может могут должен должна должны надо
статья статьи статье статью закон закона законе по на за из от до во со об обо не ни да нет""".split())

ENDINGS = sorted("""ого его ому ему ыми ими ать ять ить еть ает ают ует уют ете ите ишь ешь ами ями ов ев ей ий ый ой
ая яя ое ее ые ие ых их ую юю ом ем ам ям ах ях ия ть ет ют ут ат ят ит ла ло ли ся сь а я ы и у ю е о ь й""".split(),
                 key=len, reverse=True)


def stem(word):
    w = word.lower().replace("ё", "е")
    for e in ENDINGS:
        if w.endswith(e) and len(w) - len(e) >= 4:
            w = w[: -len(e)]
            break
    return w[:-1] if w.endswith("нн") else w  # задержанн-ого / задержан-ие


def query_terms(text, limit=6):
    words = re.findall(r"[a-zа-яё0-9]{3,}", text.lower())
    out = []
    for w in words:
        if w in STOP or w.isdigit():
            continue
        s = stem(w)
        if len(s) >= 3 and s not in out:
            out.append(s)
    # длинные (более специфичные) основы важнее
    out.sort(key=len, reverse=True)
    return out[:limit]


LAW_HINTS = {
    "ук": "УК РФ", "уголовн": "УК РФ", "коап": "КоАП РФ", "административн": "КоАП РФ",
    "пк": "ПК РФ", "процессуальн": "ПК РФ", "полици": "74-ФЗ", "фсвнг": "18-ФЗ", "гвард": "18-ФЗ",
    "госслужб": "54-ФЗ", "государственной служб": "54-ФЗ",
}


def parse_article_ref(text):
    """«статья 12», «ст. 228.1», «ук 319» -> (номер, law_number|None) либо None."""
    t = text.lower()
    m = re.search(r"(?:ст(?:атья|атьи|атье|атью)?\.?\s*)(\d+(?:[.-]\d+)*)", t)
    law = None
    for hint, number in LAW_HINTS.items():
        if re.search(r"(?<![а-яa-z])" + re.escape(hint), t):
            law = number
            break
    if m:
        return m.group(1), law
    m = re.fullmatch(r"\s*(?:ук|коап|пк|фз)?\s*(?:рф)?\s*(\d+(?:[.-]\d+)*)\s*", t)
    if m:
        return m.group(1), law
    return None


def or_filter(terms, fields=("title", "content")):
    parts = [f"{f}.ilike.*{t}*" for t in terms for f in fields]
    return "(" + ",".join(parts) + ")"


def rank_articles(rows, terms, query=""):
    """Сортирует найденные статьи по релевантности. Возвращает [(score, row)]."""
    q = query.lower().replace("ё", "е")
    scored = []
    for r in rows:
        title = (r.get("title") or "").lower().replace("ё", "е")
        body = (r.get("content") or "").lower().replace("ё", "е")
        score = 0.0
        hit = 0
        for t in terms:
            in_t = title.count(t)
            in_b = body.count(t)
            if in_t or in_b:
                hit += 1
            score += 6 * min(in_t, 2) + min(in_b, 6)
        if terms:
            score += 8 * hit / len(terms) * len(terms)  # бонус за покрытие
            if hit == len(terms) and len(terms) > 1:
                score += 10
        if q and q in title:
            score += 12
        scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], natural_key(x[1].get("article_number"))))
    return scored


def make_snippet(content, terms, size=300):
    flat = re.sub(r"\s+", " ", content or "").strip()
    low = flat.lower().replace("ё", "е")
    idx = -1
    for t in terms:
        idx = low.find(t)
        if idx >= 0:
            break
    if idx < 0:
        return flat[:size] + ("…" if len(flat) > size else "")
    start = max(0, idx - 80)
    end = min(len(flat), start + size)
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


def best_sentences(content, terms, max_chars=520):
    """Выбирает предложения/пункты статьи, где больше всего совпадений с вопросом."""
    parts = [p.strip() for p in re.split(r"(?<=[.;:])\s+|\n+", content or "") if len(p.strip()) > 15]
    if not parts:
        return (content or "")[:max_chars]
    scored = []
    for i, p in enumerate(parts):
        low = p.lower().replace("ё", "е")
        s = sum(low.count(t) for t in terms)
        scored.append((s, i, p))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))[:3]
    best.sort(key=lambda x: x[1])
    text, total = [], 0
    for s, _, p in best:
        if s == 0 and text:
            continue
        if total + len(p) > max_chars and text:
            break
        text.append(p)
        total += len(p)
    return " ".join(text)[:max_chars + 80]
