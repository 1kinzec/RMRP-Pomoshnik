"""Константы, цвета, роли и источники законов."""
import os

APP_NAME = "RMRP Помощник"
APP_VERSION = "2.0.1"
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

# ---- Цвета (палитра с макета) ----
BG = "#070b14"
BG2 = "#0a101c"
SIDEBAR = "#0a1220"
PANEL = "#0f1828"
PANEL2 = "#132036"
PANEL3 = "#18294a"
BORDER = "#1c2d4a"
BORDER2 = "#27406a"
ACCENT = "#2f7bf5"
ACCENT_HI = "#4d92ff"
ACCENT_LO = "#1f5fd0"
ACCENT_TXT = "#6fb0ff"
TEXT = "#f2f6fc"
TEXT2 = "#c3d0e4"
MUTED = "#7e91ad"
DANGER = "#ef4444"
DANGER_HI = "#ff5d5d"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
PURPLE = "#8b5cf6"
TEAL = "#14b8a6"
ORANGE = "#f59e0b"

FONT = "Segoe UI"
FONT_SYM = "Segoe UI Symbol"

# ---- Роли ----
ROLE_INFO = {
    "FOUNDER": ("👑", "Основатель", "#f5c542"),
    "ADMIN": ("🛡", "Администратор", "#ff6b6b"),
    "MODERATOR": ("🔨", "Модератор", "#a78bfa"),
    "PREMIUM": ("⭐", "Премиум пользователь", "#fbbf24"),
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


def role_color(role):
    return ROLE_INFO.get(role, ROLE_INFO["USER"])[2]


def settings_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "RMRP-Pomoshnik")
