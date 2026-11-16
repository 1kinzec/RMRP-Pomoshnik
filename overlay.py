"""Оверлей поверх игры (по умолчанию F10): быстрые разделы и мгновенный поиск по статьям.

Работает поверх игры в оконном и безрамочном режимах. В «настоящем» полноэкранном режиме Windows
не даёт показать чужие окна — это ограничение системы, а не приложения.
"""
import tkinter as tk

from . import ui
from .config import ACCENT, ACCENT_TXT, BG, BORDER, BORDER2, FONT, MUTED, PANEL, PANEL2, SIDEBAR, TEXT, TEXT2

ITEMS = [("laws", "▤", "Законодательство"), ("search", "⌕", "Поиск"), ("ai", "✦", "Нейросеть (ИИ)"),
         ("tests", "✓", "Проверь себя"), ("settings", "⛭", "Настройки")]


class Overlay:
    def __init__(self, app):
        self.app = app
        self.win = None
        self.results_box = None
        self.field = None
        self._after = None

    @property
    def visible(self):
        return bool(self.win and self.win.winfo_exists() and self.win.state() != "withdrawn")

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def hide(self):
        if self.win:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
        self.win = None

    def show(self):
        app = self.app
        if not (app.uid or app.guest):
            return
        self.hide()
        w = tk.Toplevel(app)
        self.win = w
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-alpha", 0.96)
        except tk.TclError:
            pass
        w.configure(bg=BORDER2)
        width = 320
        sw = w.winfo_screenwidth()
        w.geometry(f"{width}x470+{sw - width - 24}+70")
        body = tk.Frame(w, bg=SIDEBAR)
        body.pack(fill="both", expand=True, padx=1, pady=1)

        head = tk.Frame(body, bg=SIDEBAR)
        head.pack(fill="x", padx=14, pady=(12, 8))
        logo = ui.load_image("rmrp.png", (26, 26))
        if logo:
            tk.Label(head, image=logo, bg=SIDEBAR).pack(side="left")
        tk.Label(head, text="RMRP Помощник", font=(FONT, 11, "bold"), fg=TEXT, bg=SIDEBAR).pack(side="left", padx=8)
        close = tk.Label(head, text="✕", font=(FONT, 11), fg=MUTED, bg=SIDEBAR, cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.hide())
        for wdg in (head,):
            wdg.bind("<ButtonPress-1>", self._drag_start)
            wdg.bind("<B1-Motion>", self._drag)

        for key, glyph, title in ITEMS:
            ui.RButton(body, title, lambda k=key: self._go(k), "nav", icon=glyph, height=34, anchor="w", padx=12, outer=SIDEBAR,
                       icon_color=ACCENT_TXT).pack(fill="x", padx=10, pady=1)

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", padx=14, pady=8)
        tk.Label(body, text="БЫСТРЫЙ ПОИСК ПО СТАТЬЯМ", font=(FONT, 7, "bold"), fg=MUTED, bg=SIDEBAR).pack(anchor="w", padx=16)
        self.field = ui.Field(body, "Например: статья 228 или оскорбление", height=36, outer=SIDEBAR, on_return=self._search, icon="⌕")
        self.field.pack(fill="x", padx=12, pady=(6, 4))
        self.results_box = tk.Frame(body, bg=SIDEBAR)
        self.results_box.pack(fill="both", expand=True, padx=12)
        key = app.settings.get("overlay_hotkey", "F10")
        tk.Label(body, text=f"Нажмите {key} для открытия / закрытия", font=(FONT, 8), fg=MUTED, bg=SIDEBAR).pack(side="bottom", pady=8)
        w.update_idletasks()
        w.focus_force()
        self.field.focus_entry()

    def _drag_start(self, e):
        self._off = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _drag(self, e):
        if self.win:
            self.win.geometry(f"+{e.x_root - self._off[0]}+{e.y_root - self._off[1]}")

    def _go(self, key):
        app = self.app
        self.hide()
        app.deiconify()
        app.lift()
        app.focus_force()
        if app.content is not None:
            app.navigate(key)

    def _search(self):
        q = self.field.get()
        if not q:
            return
        box = self.results_box
        for c in box.winfo_children():
            c.destroy()
        tk.Label(box, text="Ищу…", font=(FONT, 9), fg=MUTED, bg=SIDEBAR).pack(pady=8)
        app = self.app

        def done(res):
            if not (self.win and box.winfo_exists()):
                return
            for c in box.winfo_children():
                c.destroy()
            if not res:
                tk.Label(box, text="Ничего не найдено", font=(FONT, 9), fg=MUTED, bg=SIDEBAR).pack(pady=8)
                return
            for r in res[:5]:
                row = tk.Frame(box, bg=PANEL, cursor="hand2")
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{r['law_short']} • ст. {r['article_number']}", font=(FONT, 8, "bold"), fg=ACCENT_TXT, bg=PANEL,
                         anchor="w").pack(fill="x", padx=8, pady=(5, 0))
                tk.Label(row, text=(r.get("title") or "")[:60], font=(FONT, 9), fg=TEXT, bg=PANEL, anchor="w").pack(fill="x", padx=8, pady=(0, 5))
                for wdg in (row, *row.winfo_children()):
                    wdg.bind("<Button-1>", lambda e, rr=r: self._open(rr))
        app.bg(lambda: app.search_articles(q, 5), done, fail=lambda e: done([]), bound=False)

    def _open(self, r):
        app = self.app
        self.hide()
        app.deiconify()
        app.lift()
        app.focus_force()
        app.navigate("law", law_id=r["law_id"], article_id=r["id"])
