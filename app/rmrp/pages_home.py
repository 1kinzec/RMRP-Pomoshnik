"""Главная: плитки разделов, последнее изученное, объявления."""
import tkinter as tk
from datetime import datetime, timezone

from . import ui
from .config import ACCENT, BORDER, FONT, MUTED, ORANGE, PANEL, PURPLE, SUCCESS, TEAL, TEXT, TEXT2, WARNING, ACCENT_TXT
from .textutil import fmt_date, parse_ts, plural

ANN_COLORS = {"INFO": ACCENT, "UPDATE": SUCCESS, "WARNING": WARNING, "IMPORTANT": "#ef4444"}


class HomePages:
    def page_home(self):
        name = self.prof.get("display_name") or self.prof.get("username") or "Гость"
        self.set_header(f"Добро пожаловать, {name}!", "Сегодня отличный день для новых знаний!")
        wrap = self.scroll()
        tiles = tk.Frame(wrap, bg=wrap["bg"])
        tiles.pack(fill="x", pady=(8, 16))
        for i in range(4):
            tiles.grid_columnconfigure(i, weight=1, uniform="t")
        self._home_tiles = {}
        specs = [("laws", "▤", "Законодательство", "…", ACCENT), ("search", "⌕", "Поиск", "Быстрый поиск по законам", PURPLE),
                 ("ai", "✦", "Нейросеть", "Задай вопрос помощнику", TEAL), ("tests", "✓", "Тесты", "Проверь свои знания", ORANGE)]
        for i, (key, glyph, title, sub, color) in enumerate(specs):
            card = ui.Card(tiles, bg=ui.mix(PANEL, color, .10), border=ui.mix(PANEL, color, .45), radius=14, pad=16, height=150,
                           hover_bg=ui.mix(PANEL, color, .2), hover_border=color)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 3 else 7))
            ui.icon_tile(card.body, glyph, color, 52, bg=ui.mix(PANEL, color, .10)).pack(anchor="w")
            ui.lbl(card.body, title, 13, True).pack(anchor="w", pady=(12, 2))
            sub_l = ui.lbl(card.body, sub, 9, False, TEXT2)
            sub_l.pack(anchor="w")
            card.make_clickable(lambda k=key: self.navigate(k))
            self._home_tiles[key] = sub_l

        cols = tk.Frame(wrap, bg=wrap["bg"])
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure(0, weight=3, uniform="c")
        cols.grid_columnconfigure(1, weight=2, uniform="c")
        left = ui.Card(cols, radius=14, pad=18)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ui.Card(cols, radius=14, pad=18)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ui.lbl(left.body, "Последнее изученное", 13, True).pack(anchor="w", pady=(0, 10))
        ui.lbl(right.body, "Объявления", 13, True).pack(anchor="w", pady=(0, 10))
        self._home_recent = tk.Frame(left.body, bg=PANEL)
        self._home_recent.pack(fill="x")
        self._home_ann = tk.Frame(right.body, bg=PANEL)
        self._home_ann.pack(fill="x")
        self.loading(self._home_recent)
        self.loading(self._home_ann)

        def work():
            out = {"laws": None, "recent": [], "ann": []}
            try:
                out["laws"] = len(self.db.table("laws", "id", {"is_active": "eq.true"}))
            except Exception:  # noqa: BLE001
                pass
            if not self.guest:
                try:
                    out["recent"] = self.db.table(
                        "article_views", "viewed_at,law_articles(id,law_id,article_number,title,laws(short_name))",
                        {"user_id": f"eq.{self.uid}"}, "viewed_at.desc", 5)
                except Exception:  # noqa: BLE001
                    pass
            try:
                out["ann"] = self.db.table("announcements", "id,title,content,type,created_at,expires_at", {"is_active": "eq.true"}, "created_at.desc", 6)
            except Exception:  # noqa: BLE001
                pass
            return out

        def done(d):
            if d["laws"] is not None:
                n = d["laws"]
                self._home_tiles["laws"].configure(text=f"{n} {plural(n, 'закон', 'закона', 'законов')} RMRP")
            self._render_recent(d["recent"])
            self._render_ann(d["ann"])
        self.bg(work, done)

    def _render_recent(self, rows):
        box = self._home_recent
        for c in box.winfo_children():
            c.destroy()
        rows = [r for r in rows if r.get("law_articles")]
        if self.guest:
            ui.lbl(box, "Войдите в аккаунт, чтобы здесь появилась история изучения.", 10, False, MUTED, wraplength=420).pack(anchor="w", pady=12)
            return
        if not rows:
            ui.lbl(box, "Пока пусто — откройте любую статью, и она появится здесь.", 10, False, MUTED, wraplength=420).pack(anchor="w", pady=12)
            return
        for r in rows:
            a = r["law_articles"]
            law = (a.get("laws") or {}).get("short_name") or "Закон"
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill="x", pady=5)
            ui.icon_tile(row, "▤", ACCENT, 38, bg=PANEL, radius=9).pack(side="left")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", padx=12, fill="x", expand=True)
            ui.lbl(col, law, 10, True).pack(anchor="w")
            ui.lbl(col, f"Статья {a.get('article_number')}. {a.get('title') or ''}"[:80], 9, False, TEXT2).pack(anchor="w")
            ui.lbl(row, fmt_date(r.get("viewed_at")), 8, False, MUTED).pack(side="right")
            for w in (row, *row.winfo_children(), *col.winfo_children()):
                w.bind("<Button-1>", lambda e, a=a: self.navigate("law", law_id=a["law_id"], article_id=a["id"]))
                try:
                    w.configure(cursor="hand2")
                except tk.TclError:
                    pass

    def _render_ann(self, rows):
        box = self._home_ann
        for c in box.winfo_children():
            c.destroy()
        now = datetime.now(timezone.utc)
        rows = [r for r in rows if not r.get("expires_at") or (parse_ts(r["expires_at"]) or now) > now]
        if not rows:
            ui.lbl(box, "Новых объявлений нет.", 10, False, MUTED).pack(anchor="w", pady=12)
            return
        for r in rows[:4]:
            color = ANN_COLORS.get((r.get("type") or "INFO").upper(), ACCENT)
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill="x", pady=6)
            tk.Frame(row, bg=color, width=3).pack(side="left", fill="y")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", padx=10, fill="x", expand=True)
            ui.lbl(col, r.get("title", ""), 10, True, wraplength=330).pack(anchor="w")
            ui.lbl(col, (r.get("content") or "")[:140], 9, False, TEXT2, wraplength=330).pack(anchor="w", pady=(2, 2))
            ui.lbl(col, fmt_date(r.get("created_at")), 8, False, MUTED).pack(anchor="w")
