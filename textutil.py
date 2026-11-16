"""Разбор текстов форума, поиск по статьям, ответы помощника. Без зависимостей от GUI."""
import random
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
статья статьи статье статью закон закона законе по на за из от до во со об обо не ни да нет
грозит грозят грозило светит светят дадут дают дадим полагается положено бывает случится происходит накажут
сделать делать делают делает можете могу хочу скажи скажите подскажи подскажите расскажи расскажите объясни объясните""".split())

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


def _norm_text(text):
    return (text or "").lower().replace("ё", "е")


def count_term(text, stem):
    """Сколько слов в тексте начинается с основы (text уже в нижнем регистре и без «ё»)."""
    if not stem:
        return 0
    return len(re.findall(r"(?<![а-яa-z0-9])" + re.escape(stem), text))


INTENT_STEMS = {stem(w) for w in ("наказание", "наказания", "штраф", "штрафы", "ответственность", "санкция", "санкции", "срок", "сроки",
                                  "статья", "пункт", "размер")}


# Синонимы, разговорные слова и формы глаголов, которые простое отсечение окончаний не сводит к одной основе
# («задержали» ≠ «задержание»). Строки:
#   «а б в»            — эти слова равнозначны друг другу;
#   «разг1 разг2 => закон1 закон2» — разговорные слова ищутся ещё и по «юридическим».
SYNONYMS = """
задержание задержать задержали задерживать задерживают задержанный
арест арестовать арестовали арестован арестовывать
оскорбление оскорбить оскорбил оскорбили оскорблять оскорбляет
неповиновение неисполнение невыполнение
убийство убить убил убивать
угроза угрожать угрожал угрожает
обыск досмотр досматривать обыскать
адвокат защитник
взятка взяточничество
мент мусор коп легавый полицейский => полиции сотрудник
наручники дубинка спецсредства => спецсредств специальные
украл украсть кража воровство воровать => хищение
ограбление грабёж => грабеж разбой
угон угнать угнали => завладение
драка подраться избил избить => побои хулиганство
наркотики наркота => наркотическое психотропное
пьяный выпил алкоголь => опьянение алкогольное
машина авто => автомобиль транспортное
"""


def _build_aliases():
    out = {}

    def add(a, b):
        if a != b and b not in out.setdefault(a, []):
            out[a].append(b)
    for line in SYNONYMS.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "=>" in line:
            left, right = line.split("=>")
            lstems = [stem(w) for w in left.split()]
            rstems = [stem(w) for w in right.split()]
            for a in lstems:
                for b in rstems:
                    add(a, b)
        else:
            stems = [stem(w) for w in line.split()]
            for a in stems:
                for b in stems:
                    add(a, b)
    return out


ALIASES = _build_aliases()


def aliases(term):
    """Равнозначные основы для слова запроса (пусто, если синонимов нет)."""
    return ALIASES.get(term, [])


def term_hits(text, term):
    """Сколько раз слово запроса или его синоним встречается в тексте (с начала слова)."""
    return count_term(text, term) + sum(count_term(text, a) for a in aliases(term))


def query_terms(text, limit=6):
    words = re.findall(r"[a-zа-яё0-9]{3,}", text.lower())
    out = []
    for w in words:
        if w in STOP or w.isdigit():
            continue
        s = stem(w)
        if len(s) >= 3 and s not in out:
            out.append(s)
    # «наказание», «штраф», «ответственность» — это про что спрашивают (тип вопроса), а не о чём: если есть другие слова,
    # они только мешают подбору статей, поэтому в основы не попадают (само наказание ищется в тексте отдельно).
    topical = [t for t in out if t not in INTENT_STEMS]
    if len(topical) >= 2:  # при одном предметном слове («виды наказаний») тип вопроса оставляем
        out = topical
    # длинные (более специфичные) основы важнее
    out.sort(key=len, reverse=True)
    return out[:limit]


LAW_HINTS = {
    "ук": "УК РФ", "уголовн": "УК РФ", "коап": "КоАП РФ", "административн": "КоАП РФ",
    "пк": "ПК РФ", "упк": "ПК РФ", "процессуальн": "ПК РФ", "полици": "74-ФЗ", "74-фз": "74-ФЗ", "фсвнг": "18-ФЗ", "гвард": "18-ФЗ",
    "18-фз": "18-ФЗ", "госслужб": "54-ФЗ", "государственной служб": "54-ФЗ", "54-фз": "54-ФЗ",
}
_NUM = r"\d+(?:[.-]\d+)*"
_CODE = r"(?:ук|коап|упк|пк)"


def law_hint(text):
    t = text.lower().replace("ё", "е")
    for hint, number in LAW_HINTS.items():
        tail = r"(?![а-яa-z])" if len(hint) <= 4 else ""
        if re.search(r"(?<![а-яa-z0-9-])" + re.escape(hint) + tail, t):
            return number
    return None


def parse_article_ref(text):
    """«статья 12», «ст. 228.1 УК», «ук 319», «89 ук рф», «ук рф 89», «89» -> (номер, law_number|None) либо None."""
    t = text.lower().replace("ё", "е")
    law = law_hint(t)
    pats = [
        r"(?<![а-яa-z])ст(?:атья|атьи|атье|атью|\.)?\s*(?:№\s*)?(" + _NUM + r")(?![\d])(?!\s*-?\s*фз)",
        r"(?<![\d.-])(" + _NUM + r")\s*(?:-?\s*(?:я|ю|й|ой))?\s*(?:ст(?:атья|атьи|атье|атью|\.)?\s*)?(?:" + _CODE + r")(?![а-яa-z])",
        r"(?<![а-яa-z])" + _CODE + r"\s*(?:рф\s*)?(?:ст(?:атья|\.)?\s*)?(?:№\s*)?(" + _NUM + r")(?![\d]|\s*-?\s*фз)",
        r"(?<![а-яa-z])(?:" + _CODE + r"\s*)?(?:рф\s*)?(" + _NUM + r")\s*(?:рф)?\s*",
    ]
    for i, pat in enumerate(pats):
        m = re.search(pat, t) if i < 3 else re.fullmatch(r"\s*" + pat + r"\s*", t)
        if m:
            return m.group(1), law
    return None


# --------------------------------------------------------------------------- «разговор»
_GREET = (r"(?:привет\w*|здравствуй\w*|здорово|здарова|хай|хей|ку|салам|добр(?:ый|ое|ого)\s+(?:день|вечер|утро|ночи)|доброго\s+времени\s+суток|"
          r"hello|hi|hey|приветствую|алло|йоу)")


def _norm(text):
    t = text.lower().replace("ё", "е")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", t)).strip()


def strip_greeting(text):
    """Убирает приветствие в начале: «привет, что грозит за …» -> «что грозит за …» (остальное не трогает)."""
    low = text.lower().replace("ё", "е")
    m = re.match(r"^\W*(?:" + _GREET + r"[\W]*)+(?:(?:бот|помощник|нейросеть|друг|братан|бро)\b\W*)?", low)
    return text[m.end():].strip() if m else text.strip()


SMALLTALK = [
    ("greet", r"(?:" + _GREET + r")(?:\s+(?:бот|помощник|нейросеть|друг|всем|народ|братан|бро))?",
     ["Привет! Я помощник по законам RMRP. Назовите номер статьи («89 УК РФ») или опишите ситуацию, например «что грозит за оскорбление сотрудника», и я найду норму в базе.",
      "Здравствуйте! Чем помочь? Могу найти статью по номеру, объяснить норму или подобрать закон под вашу ситуацию."]),
    ("how", r"(?:как (?:твои )?дела|как ты|как жизнь|как сам|как поживаешь|что нового|как настроение|че как|чо как|как оно)(?: у тебя| сегодня)?",
     ["Всё хорошо, работаю с базой законов. А у вас какой вопрос: нужна статья или разбор ситуации?",
      "Отлично, спасибо! Чем могу помочь по законам RMRP?"]),
    ("thanks", r"(?:спасибо|благодарю|спс|благодарствую|мерси|thx|thanks|пасиб\w*)(?: большое| тебе| вам| огромное)?",
     ["Пожалуйста! Если нужна ещё статья или разбор, пишите.", "Рад помочь! Обращайтесь."]),
    ("bye", r"(?:пока|до свидания|досвидания|до встречи|удачи|бывай|всего доброго|прощай|bye)",
     ["До встречи! Удачной службы."]),
    ("ok", r"(?:ок|окей|ладно|понятно|хорошо|ясно|понял|поняла|круто|отлично|супер|ага|угу|ну ладно|класс)",
     ["Хорошо. Если появятся вопросы по законам, спрашивайте."]),
    ("who", r"(?:кто ты|ты кто|кто такой|как тебя зовут|как твое имя|ты бот|ты нейросеть|ты человек|ты робот|что ты такое|ты настоящий)",
     ["Я помощник RMRP: ищу статьи в базе законов проекта (УК, КоАП, ПК, ФЗ «О полиции» и другие) и отвечаю по ним цитатами. Я не человек и не выдумываю нормы: если в базе ничего нет, так и скажу."]),
    ("help", r"(?:что (?:ты )?(?:умеешь|можешь)|помощь|помоги(?:те)?|help|как (?:тобой |с тобой )?пользоваться|как это работает|что делать|с чего начать|команды)",
     ["Вот что я умею:\n• найти статью по номеру: «89 УК РФ», «статья 319», «ст. 228.1 КоАП»;\n• подобрать нормы под ситуацию: «что грозит за оскорбление сотрудника»;\n• показать статью полностью: напишите «подробнее» после ответа.\nВсе ответы строятся только на статьях из базы."]),
]


def smalltalk(text):
    """Ответ на светскую беседу, если сообщение целиком такое; иначе None."""
    n = _norm(text)
    if not n or len(n) > 60:
        return None
    for kind, pat, replies in SMALLTALK:
        if re.fullmatch(r"(?:" + pat + r")(?:\s+(?:" + pat + r"))*", n):
            return random.choice(replies)
    rest = _norm(strip_greeting(text))
    if rest != n:
        if not rest:
            return SMALLTALK[0][2][0]
        for kind, pat, replies in SMALLTALK[1:]:
            if re.fullmatch(pat, rest):
                return "Привет! " + random.choice(replies)
    return None


def is_followup(text):
    n = _norm(text)
    return bool(re.fullmatch(r"(?:а |и )?(?:подробнее|подробней|полностью|целиком|весь текст|дальше|еще|развернуто|расскажи (?:подробнее|больше|еще)|"
                             r"покажи (?:всю|полностью|текст|статью)|что там|что в ней|открой|прочитай)(?: статью| текст| ее)?", n))


def is_relevant(row, terms):
    """Статья подходит под вопрос.

    Одно слово: оно в названии или встречается не меньше двух раз в тексте.
    Несколько слов: совпала хотя бы половина И найдено самое длинное (самое «предметное») слово —
    иначе общее слово вроде «наказание» вытаскивало бы чужие статьи.
    Слова ищутся с начала слова: «гроз» не совпадает с «угроза».
    """
    if not terms:
        return False
    title = _norm_text(row.get("title"))
    body = _norm_text(row.get("content"))
    hits = {t: term_hits(title, t) + term_hits(body, t) for t in terms}
    if len(terms) == 1:
        t = terms[0]
        return term_hits(title, t) > 0 or hits[t] >= 2
    covered = sum(1 for t in terms if hits[t] > 0)
    key = max([t for t in terms if t not in INTENT_STEMS] or terms, key=len)
    return covered * 2 >= len(terms) and hits[key] > 0


def or_filter(terms, fields=("title", "content")):
    parts = [f"{f}.ilike.*{t}*" for t in terms for f in fields]
    return "(" + ",".join(parts) + ")"


def and_filter(groups, fields=("title", "content")):
    """Статьи, где есть КАЖДОЕ слово (или любой его синоним): and=((…),(…)). groups — [[слово, синоним…], …]."""
    parts = []
    for g in groups:
        parts.append("or(" + ",".join(f"{f}.ilike.*{t}*" for t in g for f in fields) + ")")
    return "(" + ",".join(parts) + ")"


def rank_articles(rows, terms, query=""):
    """Сортирует найденные статьи по релевантности. Возвращает [(score, row)]."""
    q = query.lower().replace("ё", "е")
    scored = []
    for r in rows:
        title = _norm_text(r.get("title"))
        body = _norm_text(r.get("content"))
        score = 0.0
        hit = 0
        for t in terms:
            in_t = term_hits(title, t)
            in_b = term_hits(body, t)
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
        m = re.search(r"(?<![а-яa-z0-9])" + re.escape(t), low)
        idx = m.start() if m else -1
        if idx >= 0:
            break
    if idx < 0:
        return flat[:size] + ("…" if len(flat) > size else "")
    start = max(0, idx - 80)
    end = min(len(flat), start + size)
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


PENALTY_Q = re.compile(r"грозит|грозят|наказани|накажут|наказыва|штраф|срок|ответственност|санкци|посадят|сколько дад|что будет|светит|арест|тюрьм", re.I)
SANCTION = re.compile(r"наказыва|наказани|штраф|лишени[яе]\s+свобод|арест|исправительн|обязательн\w+\s+работ|ограничени[яе]\s+свобод|"
                      r"принудительн\w+\s+работ|сроком|на\s+срок|лишени[яе]\s+права", re.I)
_DANGLING = ("–", "—", "-", ",", ":")


def wants_penalty(question):
    """Спрашивают про наказание/штраф («что грозит за…», «сколько дадут»)."""
    return bool(PENALTY_Q.search(_norm_text(question)))


def best_sentences(content, terms, max_chars=520, penalty=False):
    """Выбирает предложения/пункты статьи, где больше всего совпадений с вопросом.

    penalty=True: пункты с санкцией (штраф, лишение свободы, арест…) получают приоритет, чтобы ответ на
    «что грозит за…» содержал само наказание. Если пункт обрывается на «–» или «:», следом берётся продолжение.
    """
    parts = [p.strip() for p in re.split(r"(?<=[.;:])\s+|\n+", content or "") if len(p.strip()) > 15]
    if not parts:
        return (content or "")[:max_chars]
    scored = []
    for i, p in enumerate(parts):
        low = _norm_text(p)
        s_ = sum(term_hits(low, t) for t in terms)
        if penalty and SANCTION.search(low):
            s_ += 3
        scored.append((s_, i, p))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))[:3]
    best.sort(key=lambda x: x[1])
    chosen, total = [], 0
    for s_, i, p in best:
        if s_ == 0 and chosen:
            continue
        if total + len(p) > max_chars and chosen:
            break
        chosen.append(i)
        total += len(p)
    extra = []
    for i in chosen:  # «…этой угрозы, –» → добавляем, что дальше
        if parts[i].rstrip().endswith(_DANGLING) and i + 1 < len(parts) and (i + 1) not in chosen and (i + 1) not in extra:
            extra.append(i + 1)
    idx = sorted(set(chosen) | set(extra))
    text = " ".join(parts[i] for i in idx)
    return text[:max_chars + 220]


# --------------------------------------------------------------------------- админ-аналитика и фильтры
def count_since(rows, field, days, now=None):
    """Сколько строк, у которых поле-дата не старше days дней."""
    now = now or datetime.now(timezone.utc)
    n = 0
    for r in rows:
        d = parse_ts(r.get(field))
        if d and (now - d).total_seconds() <= days * 86400:
            n += 1
    return n


def top_items(rows, field, limit=5):
    """Самые частые значения поля без учёта регистра и пунктуации: [(текст, сколько)]."""
    counts, shown = {}, {}
    for r in rows:
        raw = (r.get(field) or "").strip()
        key = re.sub(r"[^\w\s.-]", "", raw.lower().replace("ё", "е")).strip()
        if len(key) < 2:
            continue
        counts[key] = counts.get(key, 0) + 1
        shown.setdefault(key, raw[:70])
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [(shown[k], n) for k, n in best]


def filter_users(rows, query="", role="", status="", online_only=False, window=180, now=None):
    q = (query or "").strip().lower()
    out = []
    for r in rows:
        if q and q not in (r.get("username") or "").lower() and q not in (r.get("display_name") or "").lower():
            continue
        if role and r.get("role") != role:
            continue
        if status and r.get("status") != status:
            continue
        if online_only and not is_online(r.get("last_seen_at"), window, now):
            continue
        out.append(r)
    return out


def filter_reports(rows, query="", status=""):
    q = (query or "").strip().lower()
    out = []
    for r in rows:
        if status and r.get("status") != status:
            continue
        hay = " ".join(str(x) for x in (r.get("reason"), r.get("description"), (r.get("author") or {}).get("username"),
                                       (r.get("target") or {}).get("username")) if x).lower()
        if q and q not in hay:
            continue
        out.append(r)
    return out


def filter_audit(rows, query="", action="", days=0, now=None):
    q = (query or "").strip().lower()
    now = now or datetime.now(timezone.utc)
    out = []
    for r in rows:
        if action and r.get("action") != action:
            continue
        if days:
            d = parse_ts(r.get("created_at"))
            if not d or (now - d).total_seconds() > days * 86400:
                continue
        hay = " ".join(str(x) for x in ((r.get("profiles") or {}).get("username"), r.get("action"), r.get("target_type"), r.get("target_id")) if x).lower()
        if q and q not in hay:
            continue
        out.append(r)
    return out


def in_filter(ids):
    """Значение для PostgREST: id=in.(a,b,c)."""
    return "in.(" + ",".join(str(i) for i in ids) + ")"
