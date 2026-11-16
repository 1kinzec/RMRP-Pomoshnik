"""Главная: плитки разделов, последнее изученное, объявления."""
import tkinter as tk
from datetime import datetime, timezone

from . import ui
from .config import (ACCENT, APP_VERSION, BORDER, FONT, MUTED, ONLINE_WINDOW_SEC, ORANGE, PANEL, PANEL2, PURPLE, ROLE_ORDER, SUCCESS, TEAL, TEXT, TEXT2, WARNING,
                     ACCENT_TXT, role_color, role_label)
from .textutil import fmt_date, is_online, parse_ts, plural

ANN_COLORS = {"INFO": ACCENT, "UPDATE": SUCCESS, "WARNING": WARNING, "IMPORTANT": "#ef4444"}


class HomePages:
    def page_home(self):
        name = self.prof.get("display_name") or self.prof.get("username") or "Гость"
        self.set_header("Главная", "Ваш центр работы с законодательством RMRP")
        wrap = self.scroll()

        # Welcome / city hero — drawn natively so it works in the packaged EXE without network assets.
        hero = tk.Canvas(wrap, height=174, bg="#08162b", highlightthickness=1, highlightbackground="#1d4779")
        hero.pack(fill="x", pady=(2, 16))
        hero.update_idletasks()
        hw = max(hero.winfo_width(), 700)
        hero.create_rectangle(0, 0, hw, 174, fill="#08162b", outline="")
        # Electric-blue atmospheric glow and skyline on the right.
        hero.create_oval(hw * .48, -130, hw * 1.08, 250, fill="#102f62", outline="")
        hero.create_oval(hw * .68, -100, hw * 1.12, 210, fill="#123b78", outline="")
        import random
        rnd = random.Random(31)
        x = int(hw * .48)
        while x < hw + 20:
            bw = rnd.randint(28, 68)
            bh = rnd.randint(48, 132)
            top = 158 - bh
            hero.create_rectangle(x, top, x + bw, 160, fill=rnd.choice(["#0b1d39", "#10284d", "#0c2346"]), outline="#1b4d89")
            for wx in range(x + 7, x + bw - 5, 13):
                for wy in range(top + 9, 151, 15):
                    if rnd.random() > .52:
                        hero.create_rectangle(wx, wy, wx + 3, wy + 5, fill="#3478f6", outline="")
            x += bw + rnd.randint(5, 12)
        hero.create_rectangle(0, 160, hw, 174, fill="#061020", outline="")
        hero.create_text(28, 42, text=f"Привет, {name}!", anchor="w", fill="#f3f7ff", font=(FONT, 22, "bold"))
        hero.create_text(29, 79, text="Рады видеть вас в RMRP Помощнике", anchor="w", fill="#d7e6ff", font=(FONT, 11))
        hero.create_rectangle(28, 105, 32, 145, fill=ACCENT, outline="")
        hero.create_text(44, 125, text="Изучай законы, проходи тесты и будь готов к любой ситуации!", anchor="w", fill="#a9c6f2", font=(FONT, 9))
        hero.create_text(hw - 34, 40, text="RMRP", anchor="e", fill="#4b91ff", font=(FONT, 28, "bold"))
        hero.create_text(hw - 34, 68, text=f"LEGAL TECH  •  v{APP_VERSION}", anchor="e", fill="#8db8ff", font=(FONT, 8, "bold"))

        tiles = tk.Frame(wrap, bg=wrap["bg"])
        tiles.pack(fill="x", pady=(0, 15))
        for i in range(4):
            tiles.grid_columnconfigure(i, weight=1, uniform="t")
        self._home_tiles = {}
        specs = [("laws", "§", "Законодательство", "Полная база законов RMRP", ACCENT),
                 ("search", "⌕", "Поиск", "Быстрый поиск по статьям", PURPLE),
                 ("ai", "✦", "Нейросеть", "Помощь по законодательству", "#8b75ff"),
                 ("tests", "✓", "Проверь себя", "Тесты и проверка знаний", "#e6a94a")]
        for i, (key, glyph, title, sub, color) in enumerate(specs):
            card = ui.Card(tiles, bg=ui.mix(PANEL, color, .10), border=ui.mix(PANEL, color, .48), radius=15, pad=15, height=145,
                           hover_bg=ui.mix(PANEL, color, .20), hover_border=color)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            ui.icon_tile(card.body, glyph, color, 48, bg=ui.mix(PANEL, color, .13)).pack(anchor="w")
            ui.lbl(card.body, title, 12, True).pack(anchor="w", pady=(9, 2))
            sub_l = ui.lbl(card.body, sub, 8, False, TEXT2)
            sub_l.pack(anchor="w")
            card.make_clickable(lambda k=key: self.navigate(k))
            self._home_tiles[key] = sub_l

        # Personal learning metrics.
        stats = tk.Frame(wrap, bg=wrap["bg"])
        stats.pack(fill="x", pady=(0, 14))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="stats")
        stat_values = {}
        stat_specs = [("tests", "…", "Пройдено тестов", ACCENT), ("avg", "…", "Успешность", SUCCESS),
                      ("views", "…", "Изучено статей", PURPLE), ("favs", "…", "В избранном", WARNING)]
        for i, (key, value, label, color) in enumerate(stat_specs):
            c = ui.Card(stats, radius=12, pad=12)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            v = ui.lbl(c.body, value, 19, True, color)
            v.pack(anchor="w")
            ui.lbl(c.body, label, 8, False, MUTED).pack(anchor="w")
            stat_values[key] = v
        if self.guest:
            for v in stat_values.values():
                v.configure(text="—")
        else:
            def stats_work():
                out = {"tests": 0, "avg": "—", "views": 0, "favs": 0}
                try:
                    results = self.db.table("test_results", "score", {"user_id": f"eq.{self.uid}"}, None, 500)
                    out["tests"] = len(results)
                    scores = [float(r.get("score")) for r in results if r.get("score") is not None]
                    out["avg"] = f"{round(sum(scores) / len(scores))}%" if scores else "—"
                except Exception:
                    pass
                for key, table, field in (("views", "article_views", "id"), ("favs", "favorites", "id")):
                    try:
                        out[key] = len(self.db.table(table, field, {"user_id": f"eq.{self.uid}"}, None, 500))
                    except Exception:
                        pass
                return out
            self.bg(stats_work, lambda data: [stat_values[k].configure(text=str(v)) for k, v in data.items()])

        cols = tk.Frame(wrap, bg=wrap["bg"])
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure(0, weight=3, uniform="c")
        cols.grid_columnconfigure(1, weight=2, uniform="c")
        left = ui.Card(cols, radius=14, pad=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        right = ui.Card(cols, radius=14, pad=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        ui.lbl(left.body, "Последнее изученное", 12, True).pack(anchor="w", pady=(0, 9))
        ui.lbl(right.body, "Объявления", 12, True).pack(anchor="w", pady=(0, 9))
        self._home_recent = tk.Frame(left.body, bg=PANEL)
        self._home_recent.pack(fill="x")
        self._home_ann = tk.Frame(right.body, bg=PANEL)
        self._home_ann.pack(fill="x")
        self.loading(self._home_recent)
        self.loading(self._home_ann)
        self._home_team = ui.Card(wrap, radius=14, pad=16)
        self._home_team.pack(fill="x", pady=(13, 0))
        ui.lbl(self._home_team.body, "Команда приложения", 12, True).pack(anchor="w")
        ui.lbl(self._home_team.body, "Основатель, администраторы и модераторы RMRP Помощник.", 8, False, MUTED).pack(anchor="w", pady=(2, 8))
        self._home_team_grid = tk.Frame(self._home_team.body, bg=PANEL)
        self._home_team_grid.pack(fill="x")

        def work():
            out = {"laws": None, "recent": [], "ann": [], "team": []}
            try:
                out["laws"] = len(self.db.table("laws", "id", {"is_active": "eq.true"}))
            except Exception:
                pass
            if not self.guest:
                try:
                    out["recent"] = self.db.table("article_views", "viewed_at,law_articles(id,law_id,article_number,title,laws(short_name))",
                                                  {"user_id": f"eq.{self.uid}"}, "viewed_at.desc", 5)
                except Exception:
                    pass
            try:
                out["ann"] = self.db.table("announcements", "id,title,content,type,created_at,expires_at", {"is_active": "eq.true"}, "created_at.desc", 6)
            except Exception:
                pass
            try:
                out["team"] = self.db.rpc("app_team")
            except Exception:
                pass
            return out

        def done(d):
            if d["laws"] is not None:
                n = d["laws"]
                self._home_tiles["laws"].configure(text=f"{n} {plural(n, 'закон', 'закона', 'законов')} RMRP")
            self._render_recent(d["recent"])
            self._render_ann(d["ann"])
            self._render_team(d["team"])
        self.bg(work, done)

    def _render_team(self, rows):
        rows = [r for r in (rows if isinstance(rows, list) else []) if isinstance(r, dict)]
        if not rows:
            self._home_team.destroy()
            return
        rank = {r: i for i, r in enumerate(ROLE_ORDER)}
        rows.sort(key=lambda r: (rank.get(r.get("role"), 99), (r.get("display_name") or r.get("username") or "").lower()))
        grid = self._home_team_grid
        for c in grid.winfo_children():
            c.destroy()
        cols = 3
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="team")
        for i, r in enumerate(rows):
            role = r.get("role") or "USER"
            color = role_color(role)
            name = r.get("display_name") or r.get("username") or "—"
            cell = tk.Frame(grid, bg=PANEL2, highlightbackground=ui.mix(PANEL2, color, .45), highlightthickness=1)
            cell.grid(row=i // cols, column=i % cols, sticky="nsew", padx=4, pady=4)
            inner = tk.Frame(cell, bg=PANEL2)
            inner.pack(fill="x", padx=12, pady=10)
            ui.Avatar(inner, name, 44, r.get("avatar_url") or "", online=is_online(r.get("last_seen_at"), ONLINE_WINDOW_SEC), ring=color, bg=PANEL2).pack(side="left")
            col = tk.Frame(inner, bg=PANEL2)
            col.pack(side="left", padx=10)
            ui.lbl(col, name, 11, True, color, bg=PANEL2).pack(anchor="w")
            ui.lbl(col, role_label(role), 9, False, TEXT2, bg=PANEL2).pack(anchor="w")

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
