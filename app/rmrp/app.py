"""Главное окно: маршрутизация, фоновые запросы, настройки, звук, Discord, оверлей."""
import json
import math
import os
import struct
import tempfile
import threading
import time
import tkinter as tk
import wave
from datetime import datetime, timezone

from . import ui
from .api import ApiError, Supabase
from .config import (ACCENT, ACCENT_HI, ACCENT_TXT, APP_NAME, APP_PUBLISHER, APP_VERSION, BG, BG2, BORDER, FONT, HEARTBEAT_SEC, MUTED,
                     PANEL, PANEL2, ROLE_ORDER, SIDEBAR, TEXT, TEXT2, PURPLE, role_color, role_label, settings_dir)
from .discord_rpc import DiscordRPC, build_activity
from .hotkey import GlobalHotkey
from .overlay import Overlay
from .pages_admin import AdminPages
from .pages_ai import AiPages
from .pages_auth import AuthPages
from .pages_home import HomePages
from .pages_laws import LawPages
from .pages_profile import ProfilePages
from .pages_tests import TestPages

try:
    import winsound
except ImportError:  # не Windows
    winsound = None

DEFAULT_SETTINGS = {
    "sound_enabled": True, "sound_volume": 8, "hover_sound": False, "toast_duration": 3600,
    "remember": True, "last_login": "",
    "discord_enabled": False, "discord_app_id": "", "discord_show_activity": True, "discord_show_law": True,
    "discord_show_timer": True, "discord_status": "Изучает законы на RMRP — Помощник", "discord_hide": False,
    "overlay_enabled": True, "overlay_hotkey": "F10",
}

NAV_MAIN = [
    ("home", "⌂", "Главная"),
    ("laws", "▤", "Законодательство"),
    ("search", "⌕", "Поиск"),
    ("ai", "✦", "Нейросеть (ИИ)"),
    ("tests", "✓", "Проверь себя"),
    ("favorites", "★", "Избранное"),
    ("history", "◷", "История"),
    ("reports", "⚠", "Жалобы"),
    ("profile", "♙", "Профиль"),
]
GUEST_HIDDEN = {"favorites", "history", "reports", "profile"}
PAGE_TITLES = {"home": "Главная", "laws": "Законодательство", "law": "Законодательство", "search": "Поиск", "ai": "Нейросеть (ИИ)",
               "tests": "Проверь себя", "favorites": "Избранное", "history": "История", "reports": "Жалобы", "profile": "Профиль",
               "settings": "Настройки", "admin": "Админ-панель"}


class App(AuthPages, HomePages, LawPages, AiPages, TestPages, AdminPages, ProfilePages, tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(f"{APP_NAME} v{APP_VERSION} — by {APP_PUBLISHER}")
        self.configure(bg=BG)
        w, h = 1200, 760
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(w, sw - 60)}x{min(h, sh - 90)}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(1040, 660)
        try:
            self.iconbitmap(ui.resource_path("assets", "rmrp.ico"))
        except Exception:  # noqa: BLE001
            pass
        ui.set_dark_titlebar(self)
        ui.setup_styles(self)

        self.db = Supabase()
        self.user = {}
        self.prof = {}
        self.guest = False
        self.page = None
        self.page_args = {}
        self.nav_id = 0
        self.nav_buttons = {}
        self.content = None
        self.header_title = self.header_sub = None
        self.chip_holder = None
        self.started = time.time()
        self.presence_law = None
        self._sound_cache = {}
        self._prank_started = False
        self._alive = True

        self.settings_path = os.path.join(settings_dir(), "settings.json")
        self.settings = self.load_settings()
        self.toasts = ui.Toasts(self)
        ui.RButton.click_hook = lambda: self.play_sound("click")

        self.rpc = DiscordRPC()
        self.hotkey = None
        self.overlay = Overlay(self)
        self.apply_overlay_settings()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_login()
        self.after(HEARTBEAT_SEC * 1000, self._heartbeat)

    # ------------------------------------------------------------------ настройки
    def load_settings(self):
        data = dict(DEFAULT_SETTINGS)
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:  # noqa: BLE001
            pass
        return data

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ уведомления и звук
    def notify(self, title, message="", kind="info", duration=None):
        self.play_sound({"success": "success", "error": "error", "warning": "error"}.get(kind, "open"))
        try:
            self.toasts.show(title, message, kind, duration or int(self.settings.get("toast_duration", 3600)))
        except tk.TclError:
            pass

    def _tone(self, kind, freq, ms, vol):
        key = (kind, freq, ms, vol)
        if key in self._sound_cache:
            return self._sound_cache[key]
        path = os.path.join(tempfile.gettempdir(), f"rmrp2_{kind}_{freq}_{ms}_{vol}.wav")
        if not os.path.exists(path):
            rate = 22050
            n = max(1, int(rate * ms / 1000))
            amp = int(32767 * max(0, min(100, vol)) / 100)
            ramp = max(1, int(rate * .006))
            data = bytearray()
            for i in range(n):
                env = min(1, i / ramp, (n - i) / ramp)
                data.extend(struct.pack("<h", int(amp * env * math.sin(2 * math.pi * freq * i / rate))))
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(bytes(data))
        self._sound_cache[key] = path
        return path

    def play_sound(self, kind="click"):
        if winsound is None or not self.settings.get("sound_enabled", True):
            return
        if kind == "hover" and not self.settings.get("hover_sound"):
            return
        freq, ms = {"click": (680, 22), "hover": (520, 12), "success": (610, 38), "error": (250, 55), "open": (480, 20)}.get(kind, (680, 22))
        vol = int(self.settings.get("sound_volume", 8))

        def run():
            try:
                winsound.PlaySound(self._tone(kind, freq, ms, vol), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ фоновые запросы
    def bg(self, work, done=None, fail=None, bound=True):
        """Выполняет work() в потоке и вызывает done(result) в GUI-потоке.
        bound=True: результат отбрасывается, если пользователь уже перешёл на другую страницу."""
        token = self.nav_id

        def deliver(fn, arg):
            if not self._alive:
                return
            if bound and token != self.nav_id:
                return
            try:
                fn(arg)
            except tk.TclError:
                pass  # виджет уже уничтожен
            except Exception as e:  # noqa: BLE001
                self.notify("Ошибка интерфейса", str(e), "error")

        def run():
            try:
                res = work()
            except Exception as e:  # noqa: BLE001
                err = e
                if fail:
                    self._safe_after(lambda: deliver(fail, err))
                else:
                    self._safe_after(lambda: deliver(lambda x: self.notify("Ошибка", str(x), "error"), err))
                return
            if done:
                self._safe_after(lambda: deliver(done, res))
        threading.Thread(target=run, daemon=True).start()

    def _safe_after(self, fn):
        try:
            self.after(0, fn)
        except (tk.TclError, RuntimeError):
            pass

    # ------------------------------------------------------------------ права
    def role(self):
        return self.prof.get("role", "GUEST" if self.guest else "USER")

    def is_staff(self, minimum="MODERATOR"):
        r = self.role()
        return r in ROLE_ORDER and ROLE_ORDER.index(r) <= ROLE_ORDER.index(minimum)

    @property
    def uid(self):
        return self.user.get("id")

    def log_action(self, action, target_type=None, target_id=None, details=None):
        def work():
            self.db.insert("audit_logs", {"user_id": self.uid, "action": action, "target_type": target_type,
                                          "target_id": str(target_id) if target_id is not None else None, "details": details})
        self.bg(work, bound=False, fail=lambda e: None)

    # ------------------------------------------------------------------ каркас главного окна
    def clear_root(self):
        self.overlay.hide()
        for w in self.winfo_children():
            if isinstance(w, (tk.Frame, tk.Canvas)):
                w.destroy()
        self.nav_buttons = {}
        self.content = None

    def show_main(self):
        self.clear_root()
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg=SIDEBAR, width=214, highlightbackground=BORDER, highlightthickness=1)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        brand = tk.Frame(side, bg=SIDEBAR)
        brand.pack(fill="x", padx=16, pady=(16, 12))
        logo = ui.load_image("rmrp.png", (34, 34))
        if logo:
            tk.Label(brand, image=logo, bg=SIDEBAR, bd=0).pack(side="left")
        tk.Label(brand, text="RMRP\nПомощник", font=(FONT, 10, "bold"), fg=TEXT, bg=SIDEBAR, justify="left").pack(side="left", padx=8)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(0, 10))

        for key, glyph, title in NAV_MAIN:
            if self.guest and key in GUEST_HIDDEN:
                continue
            self._nav_item(side, key, glyph, title)
        tk.Frame(side, bg=SIDEBAR).pack(fill="both", expand=True)
        if self.is_staff("ADMIN"):
            self._nav_item(side, "admin", "⚙", "Админ-панель", color=PURPLE)
        self._nav_item(side, "settings", "⛭", "Настройки")
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=14, pady=8)
        self._nav_item(side, "__logout", "⎋", "Выход", color="#ff8095")
        tk.Label(side, text=f"v{APP_VERSION}  •  {APP_PUBLISHER}", font=(FONT, 7), fg=MUTED, bg=SIDEBAR).pack(pady=(2, 10))

        right = tk.Frame(shell, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        top = tk.Frame(right, bg=BG)
        top.pack(fill="x", padx=28, pady=(18, 6))
        titles = tk.Frame(top, bg=BG)
        titles.pack(side="left")
        self.header_title = tk.Label(titles, text="", font=(FONT, 20, "bold"), fg=TEXT, bg=BG, anchor="w")
        self.header_title.pack(anchor="w")
        self.header_sub = tk.Label(titles, text="", font=(FONT, 9), fg=MUTED, bg=BG, anchor="w")
        self.header_sub.pack(anchor="w")
        self.chip_holder = tk.Frame(top, bg=BG)
        self.chip_holder.pack(side="right")
        self._build_chip()
        self.content = tk.Frame(right, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=(6, 20))
        self.navigate("home")

    def _nav_item(self, parent, key, glyph, title, color=None):
        cmd = self.logout if key == "__logout" else (lambda k=key: self.navigate(k))
        b = ui.RButton(parent, title, cmd, "nav", icon=glyph, height=38, anchor="w", padx=14, outer=SIDEBAR, icon_color=color or ACCENT_TXT)
        b.pack(fill="x", padx=10, pady=1)
        if key != "__logout":
            self.nav_buttons[key] = b

    def _build_chip(self):
        for w in self.chip_holder.winfo_children():
            w.destroy()
        if self.guest:
            ui.RButton(self.chip_holder, "Войти", self.show_login, "outline", height=34).pack()
            return
        name = self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        role = self.prof.get("role", "USER")
        txt = tk.Frame(self.chip_holder, bg=BG)
        txt.pack(side="left", padx=(0, 10))
        tk.Label(txt, text=name, font=(FONT, 10, "bold"), fg=TEXT, bg=BG, anchor="e").pack(anchor="e")
        tk.Label(txt, text=role_label(role), font=(FONT, 8), fg=role_color(role), bg=BG, anchor="e").pack(anchor="e")
        ui.Avatar(self.chip_holder, name, 40, self.prof.get("avatar_url") or "", online=True, ring=role_color(role)).pack(side="left")

    def set_header(self, title, subtitle=""):
        if self.header_title:
            self.header_title.configure(text=title)
            self.header_sub.configure(text=subtitle)

    def navigate(self, key, **kw):
        if key == "admin" and not self.is_staff("ADMIN"):
            self.notify(APP_NAME, "Раздел доступен только администраторам.", "warning")
            return
        self.nav_id += 1
        self.page, self.page_args = key, kw
        if key != "law":
            self.presence_law = None
        for k, b in self.nav_buttons.items():
            b.set_active(k == ("laws" if key == "law" else key))
        for w in self.content.winfo_children():
            w.destroy()
        self.set_header(PAGE_TITLES.get(key, ""), "")
        builder = getattr(self, f"page_{key}", None)
        if builder is None:
            self.card_message(self.content, "Раздел в разработке", "Эта страница появится в одном из ближайших обновлений.")
        else:
            try:
                builder(**kw)
            except Exception as e:  # noqa: BLE001
                self.notify("Ошибка страницы", f"{key}: {e}", "error")
        self.update_presence()

    # ------------------------------------------------------------------ строительные блоки страниц
    def scroll(self, parent=None):
        sf = ui.ScrollFrame(parent or self.content, bg=BG)
        sf.pack(fill="both", expand=True)
        return sf.body

    def loading(self, parent, text="Загрузка…"):
        l = tk.Label(parent, text=text, font=(FONT, 10), fg=MUTED, bg=parent["bg"])
        l.pack(pady=40)
        return l

    def card_message(self, parent, title, text, color=ACCENT_TXT):
        c = ui.Card(parent, bg=PANEL, border=BORDER, radius=12, pad=18)
        c.pack(fill="x", pady=6)
        ui.lbl(c.body, title, 12, True, color).pack(anchor="w")
        ui.lbl(c.body, text, 10, False, TEXT2, wraplength=760).pack(anchor="w", pady=(6, 0))
        return c

    def require_login(self, what="Эта функция"):
        if self.guest:
            self.notify("Нужен вход", f"{what} доступна после входа в аккаунт.", "info")
            return False
        return True

    # ------------------------------------------------------------------ сессия
    def start_session(self):
        self._prank_started = False
        self.start_prank_listener()
        self.refresh_discord_app_id()
        self.apply_discord()

    def _heartbeat(self):
        if not self._alive:
            return
        if self.uid and not self.guest:
            now = datetime.now(timezone.utc).isoformat()
            self.bg(lambda: self.db.update("profiles", {"id": f"eq.{self.uid}"}, {"last_seen_at": now}), bound=False, fail=lambda e: None)
        self.after(HEARTBEAT_SEC * 1000, self._heartbeat)

    def logout(self):
        self.db.auth_logout()
        self.user, self.prof, self.guest = {}, {}, False
        self._prank_started = False
        self.rpc.configure("", False)
        self.show_login()

    # ------------------------------------------------------------------ Discord / оверлей
    def refresh_discord_app_id(self):
        """Если локально Application ID не задан — берём общий из app_settings (задаёт Основатель)."""
        if self.settings.get("discord_app_id") or self.guest:
            return

        def work():
            rows = self.db.table("app_settings", "value", {"key": "eq.discord_app_id"}, limit=1)
            return rows[0]["value"] if rows and rows[0].get("value") else ""

        def done(v):
            if v:
                self.settings["discord_app_id"] = v
                self.apply_discord()
        self.bg(work, done, fail=lambda e: None, bound=False)

    def apply_discord(self):
        s = self.settings
        enabled = bool(s.get("discord_enabled") and not s.get("discord_hide") and s.get("discord_show_activity") and not self.guest and self.uid)
        self.rpc.configure(s.get("discord_app_id", ""), enabled, self._activity() if enabled else None)

    def _activity(self):
        s = self.settings
        details = s.get("discord_status") or "Изучает законы на RMRP — Помощник"
        state = PAGE_TITLES.get(self.page or "home", "RMRP Помощник")
        if s.get("discord_show_law") and self.presence_law:
            state = self.presence_law
        return build_activity(details, state, self.started if s.get("discord_show_timer") else None)

    def update_presence(self):
        if self.rpc.enabled:
            self.rpc.activity = self._activity()
            self.rpc._dirty.set()

    def apply_overlay_settings(self):
        key = self.settings.get("overlay_hotkey", "F10")
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None
        if self.settings.get("overlay_enabled"):
            self.hotkey = GlobalHotkey(key, lambda: self._safe_after(self.overlay.toggle))
            self.hotkey.start()

    def on_close(self):
        self._alive = False
        try:
            self.rpc.shutdown()
            if self.hotkey:
                self.hotkey.stop()
        finally:
            self.destroy()
