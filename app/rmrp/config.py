"""Константы, цвета, роли и источники законов."""
import json
import os
import re

APP_NAME = "RMRP Помощник"
try:
    from .version import __version__ as APP_VERSION
except ImportError:  # pragma: no cover
    APP_VERSION = "0.0.0"
try:  # создаётся при сборке в GitHub Actions: GITHUB_REPO = "владелец/репозиторий"
    from .build_info import GITHUB_REPO
except ImportError:
    GITHUB_REPO = ""
APP_PUBLISHER = "Kinzec X WOLF"

# Publishable key лежит в клиенте намеренно. Secret/service_role ключ сюда добавлять НЕЛЬЗЯ:
# доступ к данным ограничивается политиками RLS в Supabase.
SUPABASE_URL = "https://cyihqnquxaxnonjbvshm.supabase.co"
SUPABASE_KEY = "sb_publishable_3X8WkqV57kAqB8v6KS458A_mPnSBBRK"

# Разделы форума RMRP, которые синхронизируются по умолчанию.
LAW_SOURCES = [
    {"name": "Федеральный закон «О государственной службе» № 54-ФЗ", "short_name": "ФЗ «О госслужбе»", "law_number": "54-ФЗ",
     "url": "https://forum.rmrp.ru/threads/federalnyj-zakon-o-gosudarstvennoj-sluzhbe-no-54-fz.25075/"},
    {"name": "Уголовный Кодекс Российской Федерации", "short_name": "УК РФ", "law_number": "УК РФ",
     "url": "https://forum.rmrp.ru/threads/ugolovnyj-kodeks-rossijskoj-federacii.58209/"},
    {"name": "Кодекс об административных правонарушениях Российской Федерации", "short_name": "КоАП РФ", "law_number": "КоАП РФ",
     "url": "https://forum.rmrp.ru/threads/kodeks-ob-administrativnyx-pravonarushenijax-rossijskoj-federacii.58229/"},
    {"name": "Процессуальный Кодекс Российской Федерации", "short_name": "Процессуальный кодекс", "law_number": "ПК РФ",
     "url": "https://forum.rmrp.ru/threads/processualnyj-kodeks-rossijskoj-federacii.58424/"},
    {"name": "Федеральный закон «О полиции» № 74-ФЗ", "short_name": "ФЗ «О полиции»", "law_number": "74-ФЗ",
     "url": "https://forum.rmrp.ru/threads/federalnyj-zakon-o-policii-no-74-fz.25074/"},
    {"name": "Федеральный закон «О Федеральной службе войск национальной гвардии» № 18-ФЗ", "short_name": "ФЗ «О ФСВНГ»", "law_number": "18-ФЗ",
     "url": "https://forum.rmrp.ru/threads/federalnyj-zakon-o-federalnoj-sluzhbe-vojsk-nacionalnoj-gvardii-no-18-fz.25071/"},
]

# ---- Цвета: тёмная «стеклянная» тема с фиолетовым акцентом ----
BG = "#07070d"
BG2 = "#0c0d1a"
SIDEBAR = "#0a0a15"
PANEL = "#0f0f1e"
PANEL2 = "#14152a"
PANEL3 = "#1a1c30"
BORDER = "#2a2d4b"
BORDER2 = "#3a3d5f"
ACCENT = "#8b6cf0"
ACCENT_HI = "#a48bff"
ACCENT_LO = "#6f52d6"
ACCENT_TXT = "#a48bff"
ACCENT_SOFT = "#2b214a"
TEXT = "#f5f5fa"
TEXT2 = "#a8aabe"
MUTED = "#6e7090"
DANGER = "#e27676"
DANGER_HI = "#ec8a8a"
SUCCESS = "#76d5a0"
WARNING = "#f0b95a"
PURPLE = "#b794f6"
TEAL = "#4fd1c5"
ORANGE = "#f0a15a"

FONT = "Segoe UI"
FONT_SYM = "Segoe UI Symbol"

# ---- Роли ----
ROLE_INFO = {
    "FOUNDER": ("👑", "Основатель", "#f5c542"),
    "ADMIN": ("🛡", "Администратор", "#ff6b6b"),
    "MODERATOR": ("🔨", "Модератор", "#c4a8ff"),
    "PREMIUM": ("⭐", "Премиум пользователь", "#38bdf8"),
    "USER": ("👤", "Пользователь", "#8ea3bb"),
}
ROLE_ORDER = ["FOUNDER", "ADMIN", "MODERATOR", "PREMIUM", "USER"]
ROLE_SHORT = {"FOUNDER": "Основатель", "ADMIN": "Администратор", "MODERATOR": "Модератор", "PREMIUM": "Premium", "USER": "Пользователь"}
STATUS_VALUES = ["ACTIVE", "BLOCKED", "BANNED"]
STATUS_RU = {"ACTIVE": "Активен", "BLOCKED": "Заблокирован", "BANNED": "Забанен"}
DIFFICULTY_RU = {"EASY": "Лёгкий", "MEDIUM": "Средний", "HARD": "Сложный"}
DIFFICULTY_STARS = {"EASY": 1, "MEDIUM": 2, "HARD": 3}

# Пользователь считается «в сети», если heartbeat был не позже этого числа секунд назад.
ONLINE_WINDOW_SEC = 180
HEARTBEAT_SEC = 60


def role_label(role):
    icon, name, _ = ROLE_INFO.get(role, ROLE_INFO["USER"])
    return f"{icon} {name}"


# Цвета ролей, заданные Основателем (хранятся в app_settings.role_colors, общие для всех).
ROLE_COLOR_OVERRIDES = {}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def role_color(role):
    return ROLE_COLOR_OVERRIDES.get(role) or ROLE_INFO.get(role, ROLE_INFO["USER"])[2]


def default_role_color(role):
    return ROLE_INFO.get(role, ROLE_INFO["USER"])[2]


def parse_role_colors(text):
    """JSON {"ADMIN": "#ff0000"} -> только корректные роли и цвета #rrggbb."""
    try:
        data = json.loads(text) if isinstance(text, str) else dict(text or {})
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {r: str(c).lower() for r, c in data.items() if r in ROLE_INFO and isinstance(c, str) and _HEX.match(c)}


def set_role_colors(colors):
    ROLE_COLOR_OVERRIDES.clear()
    ROLE_COLOR_OVERRIDES.update(parse_role_colors(colors))


# ---- Краткие памятки ----
MEMO_BUCKET = "memo-images"
MEMO_TAGS = [("Важно", "#ef4444"), ("Полиция", "#3b82f6"), ("Суд", "#8b5cf6"), ("Процесс", "#14b8a6"), ("Закон", "#2f7bf5"),
             ("Штрафы", "#f59e0b"), ("Задержание", "#ec4899"), ("Правила", "#22c55e"), ("Инструкция", "#06b6d4"), ("Новости", "#a3e635")]


def settings_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "RMRP-Pomoshnik")
