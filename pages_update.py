"""Премиальное окно автообновления RMRP Помощника (Midnight Navy / Electric Blue)."""
import threading
import tkinter as tk
import webbrowser

from . import ui
from . import updater
from .config import (
    ACCENT, ACCENT_HI, ACCENT_TXT, APP_VERSION, BG, BG2, BORDER, BORDER2,
    FONT, MUTED, PANEL, PANEL2, PANEL3, SIDEBAR, TEXT, TEXT2, UPDATE_MANIFEST_URL,
)

CHECK_EVERY_MS = 6 * 60 * 60 * 1000
BLUE = "#159BFF"
BLUE_GLOW = "#35C5FF"


class UpdatePages:
    def schedule_update_checks(self):
        self._update_open = False
        self.after(5000, self._auto_update_tick)

    def _auto_update_tick(self):
        if not self._alive:
            return
        if self.settings.get("auto_update", True):
            self.check_updates()
        self.after(CHECK_EVERY_MS, self._auto_update_tick)

    def check_updates(self, manual=False):
        if not UPDATE_MANIFEST_URL:
            if manual:
                self.notify("Обновления", "Адрес сервера обновлений не настроен.", "warning")
            return

        def done(info):
            if not info:
                if manual:
                    self.notify("Обновления", f"У вас последняя версия ({APP_VERSION}).", "success")
                return
            if not manual and info["version"] == self.settings.get("skip_version"):
                return
            if not self._update_open:
                self.update_dialog(info)

        def fail(e):
            if manual:
                self.notify("Обновления", f"Не удалось проверить: {e}", "error")
        self.bg(lambda: updater.check_latest(manifest_url=UPDATE_MANIFEST_URL), done, fail, bound=False)

    def update_dialog(self, info):
        """Полноценное окно обновления; сетевые операции остаются в фоновом потоке."""
        self._update_open = True
        win = ui.modal(self, "Обновление RMRP Помощника", 1180, 790, BG)
        win.minsize(1000, 700)
        win.bind("<Destroy>", lambda e: setattr(self, "_update_open", False) if e.widget is win else None)
        win.configure(bg=BG)

        # Шапка приложения
        header = tk.Frame(win, bg="#050B18", height=88, highlightthickness=1, highlightbackground=BORDER)
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg="#050B18")
        brand.pack(side="left", padx=28, fill="y")
        logo = tk.Canvas(brand, width=54, height=54, bg="#050B18", highlightthickness=0)
        logo.pack(side="left", pady=15)
        logo.create_polygon(7, 8, 48, 8, 36, 20, 18, 20, 18, 45, 7, 45, fill=BLUE, outline=BLUE_GLOW)
        logo.create_polygon(23, 23, 43, 23, 51, 31, 35, 49, 24, 39, 37, 31, 23, 31, fill="#1472E8", outline=BLUE_GLOW)
        brand_text = tk.Frame(brand, bg="#050B18")
        brand_text.pack(side="left", padx=(14, 0))
        ui.lbl(brand_text, "RMRP Помощник", 17, True, TEXT, bg="#050B18").pack(anchor="w", pady=(20, 0))
        ui.lbl(brand_text, "by Kinzec X WOLF", 9, False, ACCENT_TXT, bg="#050B18").pack(anchor="w")
        profile = tk.Frame(header, bg="#050B18")
        profile.pack(side="right", padx=30)
        ui.lbl(profile, "◉   Kinzec", 11, True, TEXT, bg="#050B18").pack(anchor="e", pady=(22, 0))
        ui.lbl(profile, "♛  Основатель", 9, False, BLUE_GLOW, bg="#050B18").pack(anchor="e")

        # Основная область: боковая панель + контент
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=SIDEBAR, width=218, highlightthickness=1, highlightbackground=BORDER)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        for label, symbol, active in [
            ("Главная", "⌂", False), ("Законодательство", "⚖", False), ("Поиск", "⌕", False),
            ("Нейросеть", "✧", False), ("Проверь себя", "☑", False),
            ("Статистика", "▥", False), ("Настройки", "⚙", False), ("О приложении", "ⓘ", False),
        ]:
            row = tk.Frame(side, bg=("#102B63" if active else SIDEBAR), height=52)
            row.pack(fill="x", padx=8, pady=(12 if label == "Главная" else 2, 2))
            row.pack_propagate(False)
            ui.lbl(row, symbol, 18, True, BLUE_GLOW, bg=row["bg"], width=3).pack(side="left", padx=(12, 4))
            ui.lbl(row, label, 10, label == "Главная", TEXT2, bg=row["bg"]).pack(side="left")
        side_bottom = tk.Frame(side, bg=SIDEBAR)
        side_bottom.pack(side="bottom", fill="x", padx=18, pady=24)
        ui.lbl(side_bottom, "RMRP Помощник", 10, True, TEXT, bg=SIDEBAR).pack(anchor="w")
        ui.lbl(side_bottom, "Твой помощник в мире\nзаконов RMRP", 9, False, MUTED, bg=SIDEBAR).pack(anchor="w", pady=(5, 0))

        content = tk.Frame(body, bg=BG)
        content.pack(side="left", fill="both", expand=True, padx=18, pady=18)

        def card(parent, padx=18, pady=14, bg="#0C1930"):
            f = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=BORDER2)
            f.pack(fill="x", pady=(0, 14))
            inner = tk.Frame(f, bg=bg)
            inner.pack(fill="both", expand=True, padx=padx, pady=pady)
            return f, inner

        # Hero banner
        hero = tk.Frame(content, bg="#0B2450", height=116, highlightthickness=1, highlightbackground="#174F9D")
        hero.pack(fill="x", pady=(0, 16))
        hero.pack_propagate(False)
        ui.lbl(hero, "⟳", 48, True, BLUE_GLOW, bg="#0B2450").pack(side="left", padx=34)
        hero_text = tk.Frame(hero, bg="#0B2450")
        hero_text.pack(side="left", fill="y", pady=22)
        ui.lbl(hero_text, "Обновление приложения", 22, True, TEXT, bg="#0B2450").pack(anchor="w")
        ui.lbl(hero_text, "Проверяем и устанавливаем актуальную версию RMRP Помощника", 10, False, "#B9D1F9", bg="#0B2450").pack(anchor="w", pady=(5, 0))
        ui.lbl(hero, "✦", 58, True, "#1D5CB4", bg="#0B2450").pack(side="right", padx=34)

        # Версия и описание изменений
        _, version_inner = card(content, pady=17)
        version_row = tk.Frame(version_inner, bg="#0C1930")
        version_row.pack(fill="x")
        left = tk.Frame(version_row, bg="#0C1930")
        left.pack(side="left", fill="y", padx=(0, 24))
        ui.lbl(left, "Найдена новая версия:", 11, True, ACCENT_TXT, bg="#0C1930").pack(anchor="w")
        ui.lbl(left, f"{info['version']}", 36, True, TEXT, bg="#0C1930").pack(anchor="w", pady=(0, 0))
        ui.lbl(left, f"Текущая версия: {APP_VERSION}", 10, False, MUTED, bg="#0C1930").pack(anchor="w")
        divider = tk.Frame(version_row, bg=BORDER2, width=1)
        divider.pack(side="left", fill="y", padx=16)
        right = tk.Frame(version_row, bg="#0C1930")
        right.pack(side="left", fill="both", expand=True)
        ui.lbl(right, f"Что нового в версии {info['version']}?", 12, True, TEXT, bg="#0C1930").pack(anchor="w", pady=(0, 7))
        notes = info.get("notes") or "Исправлены ошибки и улучшена стабильность приложения."
        for line in [x.strip(" •\t-") for x in notes.splitlines() if x.strip()][:5]:
            ui.lbl(right, f"✓   {line}", 9, False, TEXT2, bg="#0C1930", wraplength=570).pack(anchor="w", pady=2)

        # Загрузка и проверка
        _, download_inner = card(content, pady=13)
        top = tk.Frame(download_inner, bg="#0C1930")
        top.pack(fill="x")
        ui.lbl(top, "⇩", 24, True, BLUE_GLOW, bg="#0C1930").pack(side="left", padx=(0, 18))
        ui.lbl(top, "Скачивание обновления", 13, True, TEXT, bg="#0C1930").pack(side="left")
        percent = ui.lbl(top, "Ожидание", 12, True, TEXT, bg="#0C1930")
        percent.pack(side="right")
        progress_canvas = tk.Canvas(download_inner, height=14, bg="#0C1930", highlightthickness=0)
        progress_canvas.pack(fill="x", pady=(10, 6))
        detail = ui.lbl(download_inner, f"Размер файла: {info.get('size', 0) // 1024 // 1024} МБ  •  Загрузка начнётся после нажатия кнопки", 9, False, MUTED, bg="#0C1930")
        detail.pack(anchor="w")

        _, verify_inner = card(content, pady=12)
        verify_row = tk.Frame(verify_inner, bg="#0C1930")
        verify_row.pack(fill="x")
        ui.lbl(verify_row, "⬡", 23, True, BLUE_GLOW, bg="#0C1930").pack(side="left", padx=(0, 18))
        verify_text = tk.Frame(verify_row, bg="#0C1930")
        verify_text.pack(side="left", fill="x", expand=True)
        ui.lbl(verify_text, "Проверка целостности файла", 12, True, TEXT, bg="#0C1930").pack(anchor="w")
        verify_status = ui.lbl(verify_text, "SHA-256 будет проверен после загрузки", 9, False, MUTED, bg="#0C1930")
        verify_status.pack(anchor="w", pady=(3, 0))
        verify_mark = ui.lbl(verify_row, "◌", 20, True, ACCENT_TXT, bg="#0C1930")
        verify_mark.pack(side="right", padx=8)

        # Нижняя панель действий
        bottom = tk.Frame(content, bg=BG)
        bottom.pack(fill="x", pady=(2, 0))
        notice = tk.Frame(bottom, bg="#0B1C3B", highlightthickness=1, highlightbackground="#174F9D")
        notice.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ui.lbl(notice, "ⓘ", 22, True, BLUE_GLOW, bg="#0B1C3B").pack(side="left", padx=14, pady=13)
        ui.lbl(notice, "После установки приложение будет\nперезапущено для применения обновлений.", 9, False, TEXT2, bg="#0B1C3B").pack(side="left", pady=12)
        actions = tk.Frame(bottom, bg=BG)
        actions.pack(side="right", fill="y")
        state = {"busy": False}

        def draw(frac):
            progress_canvas.delete("all")
            w = max(1, progress_canvas.winfo_width())
            h = 14
            progress_canvas.create_polygon(ui.rr_points(0, 1, w, h - 1, 7), smooth=True, fill="#1B3158", outline="")
            if frac > 0:
                progress_canvas.create_polygon(ui.rr_points(0, 1, max(12, w * min(1, frac)), h - 1, 7), smooth=True, fill=BLUE, outline="")

        progress_canvas.bind("<Configure>", lambda e: draw(0))

        def progress(done, total):
            frac = done / total if total else 0
            def paint():
                draw(frac)
                percent.configure(text=f"{int(frac * 100)}%")
                total_mb = max(total // 1024 // 1024, 1)
                detail.configure(text=f"Скачано: {done // 1024 // 1024} МБ из {total_mb} МБ")
            self._safe_after(paint)

        def install():
            if state["busy"]:
                return
            if not updater.can_self_update():
                webbrowser.open(info["page"])
                self.notify("Обновление", "Автоустановка работает в собранной версии Windows. Открыл страницу релиза.", "info", 5000)
                win.destroy()
                return
            state["busy"] = True
            go.set_disabled(True)
            later.set_disabled(True)
            skip.set_disabled(True)
            verify_status.configure(text="Скачиваем файл и вычисляем SHA-256…", fg=ACCENT_TXT)
            verify_mark.configure(text="◌", fg=ACCENT_TXT)

            def worker():
                try:
                    path = updater.download(info, progress=progress)
                except Exception as e:  # noqa: BLE001
                    def failed(err=e):
                        state["busy"] = False
                        verify_status.configure(text=f"Ошибка проверки/загрузки: {err}", fg="#FF6B78")
                        verify_mark.configure(text="!", fg="#FF6B78")
                        go.set_disabled(False); later.set_disabled(False); skip.set_disabled(False)
                    self._safe_after(failed)
                    return

                def launch():
                    percent.configure(text="100%")
                    verify_status.configure(text="SHA-256 совпадает. Файл проверен.", fg="#39BDF8")
                    verify_mark.configure(text="✓", fg="#39BDF8")
                    detail.configure(text="Загрузка завершена. Подготовка установщика…")
                    try:
                        updater.launch_installer(path)
                    except Exception as e:  # noqa: BLE001
                        verify_status.configure(text=f"Не удалось запустить установщик: {e}", fg="#FF6B78")
                        state["busy"] = False
                        go.set_disabled(False); later.set_disabled(False); skip.set_disabled(False)
                        return
                    detail.configure(text="Установщик запущен. Приложение будет перезапущено.")
                    self.after(900, self.on_close)
                self._safe_after(launch)
            threading.Thread(target=worker, daemon=True).start()

        def skip_version():
            self.settings["skip_version"] = info["version"]
            self.save_settings()
            win.destroy()

        go = ui.RButton(actions, "Установить обновление", install, "primary", icon="↓", width=300, height=58, size=13, radius=12)
        go.pack(fill="x", pady=(0, 8))
        later = ui.RButton(actions, "Позже", win.destroy, "secondary", width=300, height=34, size=9)
        later.pack(fill="x", pady=(0, 5))
        skip = ui.RButton(actions, "Пропустить эту версию", skip_version, "ghost", width=300, height=30, size=8)
        skip.pack(fill="x")

        footer = tk.Frame(content, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(12, 0))
        ui.lbl(footer, "●  Обновление готово к загрузке", 9, False, ACCENT_TXT, bg=BG).pack(side="left")
        ui.lbl(footer, "Проверка безопасности: SHA-256", 9, False, MUTED, bg=BG).pack(side="right")
        draw(0)
