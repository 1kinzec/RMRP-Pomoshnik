"""Окно обновления: проверка при запуске, раз в 6 часов и вручную из настроек."""
import threading
import tkinter as tk
import webbrowser

from . import ui
from . import updater
from .config import ACCENT_TXT, APP_NAME, APP_VERSION, FONT, MUTED, PANEL, PANEL2, TEXT, TEXT2

CHECK_EVERY_MS = 6 * 60 * 60 * 1000


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
        if not updater.GITHUB_REPO and not manual:
            return
        if not updater.GITHUB_REPO:
            self.notify("Обновления", "В этой сборке автообновление не настроено (собирайте через GitHub Actions).", "warning")
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
        self.bg(updater.check_latest, done, fail, bound=False)

    def update_dialog(self, info):
        self._update_open = True
        win = ui.modal(self, "Доступно обновление", 560, 520, PANEL)
        win.bind("<Destroy>", lambda e: setattr(self, "_update_open", False) if e.widget is win else None)
        ui.lbl(win, f"Доступна версия {info['version']}", 16, True, bg=PANEL).pack(anchor="w", padx=24, pady=(22, 2))
        ui.lbl(win, f"У вас установлена {APP_VERSION}", 9, False, MUTED, bg=PANEL).pack(anchor="w", padx=24)
        ui.lbl(win, "Что нового", 10, True, ACCENT_TXT, bg=PANEL).pack(anchor="w", padx=24, pady=(14, 4))
        notes = tk.Text(win, height=10, bg=PANEL2, fg=TEXT2, relief="flat", wrap="word", font=(FONT, 9), padx=12, pady=10, highlightthickness=0)
        notes.pack(fill="both", expand=True, padx=24)
        notes.insert("1.0", info.get("notes") or "Список изменений не указан.")
        notes.configure(state="disabled")
        status = ui.lbl(win, "Windows может запросить подтверждение установки. Настройки и данные сохранятся.", 8, False, MUTED, bg=PANEL, wraplength=500)
        status.pack(anchor="w", padx=24, pady=(10, 4))
        bar = tk.Canvas(win, height=6, bg=PANEL, highlightthickness=0)
        bar.pack(fill="x", padx=24)
        btns = tk.Frame(win, bg=PANEL)
        btns.pack(fill="x", padx=24, pady=16)
        state = {"busy": False}

        def draw(frac):
            bar.delete("all")
            w = bar.winfo_width() or 500
            bar.create_polygon(ui.rr_points(0, 0, w, 6, 3), smooth=True, fill=PANEL2, outline="")
            if frac > 0:
                bar.create_polygon(ui.rr_points(0, 0, max(8, w * frac), 6, 3), smooth=True, fill=ui.ACCENT, outline="")

        def progress(done, total):
            frac = done / total if total else 0
            self._safe_after(lambda: (status.configure(text=f"Скачивание… {done // 1024 // 1024} из {max(total // 1024 // 1024, 1)} МБ"), draw(frac)))

        def install():
            if state["busy"]:
                return
            if not updater.can_self_update():
                webbrowser.open(info["page"])
                self.notify("Обновление", "Автоустановка работает в собранной версии для Windows. Открыл страницу релиза.", "info", 5000)
                win.destroy()
                return
            state["busy"] = True
            go.set_disabled(True)
            later.set_disabled(True)
            skip.set_disabled(True)

            def worker():
                try:
                    path = updater.download(info, progress=progress)
                except Exception as e:  # noqa: BLE001
                    def failed():
                        state["busy"] = False
                        status.configure(text=f"Ошибка: {e}", fg="#ef4444")
                        go.set_disabled(False)
                        later.set_disabled(False)
                        skip.set_disabled(False)
                    self._safe_after(failed)
                    return

                def launch():
                    status.configure(text="Устанавливаю… приложение перезапустится.")
                    try:
                        updater.launch_installer(path)
                    except Exception as e:  # noqa: BLE001
                        status.configure(text=f"Не удалось запустить установщик: {e}", fg="#ef4444")
                        return
                    self.after(600, self.on_close)
                self._safe_after(launch)
            threading.Thread(target=worker, daemon=True).start()

        def skip_version():
            self.settings["skip_version"] = info["version"]
            self.save_settings()
            win.destroy()
        go = ui.RButton(btns, "Обновить сейчас", install, height=40)
        go.pack(side="right")
        later = ui.RButton(btns, "Позже", win.destroy, "secondary", height=40)
        later.pack(side="right", padx=8)
        skip = ui.RButton(btns, "Пропустить версию", skip_version, "ghost", height=40, size=9)
        skip.pack(side="left")
