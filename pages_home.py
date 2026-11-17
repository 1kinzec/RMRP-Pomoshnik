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
        """Главная панель в стиле Midnight Navy / Electric Blue."""
        name = self.prof.get("display_name") or self.prof.get("username") or "Гость"
        self.set_header("Главная", "Ваш центр работы с законодательством RMRP")
        wrap = self.scroll()

        # Hero banner: typography and subtle legal-tech motif, drawn locally.
        hero = tk.Canvas(wrap, height=192, bg="#101D32", highlightthickness=1, highlightbackground=BORDER)
        hero.pack(fill="x", pady=(2, 16))
        def draw_hero(_event=None):
            hero.delete("all")
            w = max(hero.winfo_width(), 680)
            hero.create_rectangle(0, 0, w, 192, fill="#101D32", outline="")
            hero.create_oval(w * .67, -125, w * 1.08, 260, fill="#152B50", outline="")
            hero.create_oval(w * .78, -75, w * 1.13, 225, fill="#173665", outline="")
            # Thin blue orbit lines add depth without turning the banner into a noisy illustration.
            for pad in (0, 13, 26):
                hero.create_oval(w - 260 + pad, 28 + pad, w - 70 - pad, 218 - pad, outline="#244C86", width=1)
            hero.create_text(28, 29, text="ВАШЕ РАБОЧЕЕ ПРОСТРАНСТВО", anchor="w", fill="#75A9FF", font=(FONT, 8, "bold"))
            hero.create_text(28, 69, text=f"Добро пожаловать, {name}", anchor="w", fill=TEXT, font=(FONT, 21, "bold"))
            hero.create_text(29, 104, text="Знание закона — ваше преимущество.", anchor="w", fill="#D5E3F8", font=(FONT, 11, "bold"))
            hero.create_text(29, 132, text="Изучайте актуальные нормы сервера, находите статьи и готовьтесь к проверкам.", anchor="w", fill="#9EB1CD", font=(FONT, 9))
            hero.create_rectangle(28, 157, 208, 185, fill=ACCENT, outline="")
            hero.create_text(118, 171, text="Открыть законодательство  →", fill="#FFFFFF", font=(FONT, 8, "bold"))
            hero.create_text(w - 155, 78, text="§", fill="#5796FF", font=(FONT, 64, "normal"))
            hero.create_text(w - 155, 139, text="RMRP  •  LAW CENTER", fill="#91B6F2", font=(FONT, 8, "bold"))
        hero.bind("<Configure>", draw_hero)
        hero.bind("<Button-1>", lambda _e: self.navigate("laws"))
        hero.configure(cursor="hand2")

        # Live metrics — values are populated from Supabase, never hardcoded mock data.
        stats = tk.Frame(wrap, bg=wrap["bg"])
        stats.pack(fill="x", pady=(0, 16))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="home_stats")
        metric_values = {}
        metric_specs = [("laws", "—", "АКТИВНЫХ ЗАКОНОВ", ACCENT_TXT),
                        ("articles", "—", "СТАТЕЙ В БАЗЕ", TEXT),
                        ("tests", "—", "ПРОЙДЕНО ТЕСТОВ", PURPLE),
                        ("avg", "—", "СРЕДНИЙ РЕЗУЛЬТАТ", SUCCESS)]
        for i, (key, value, caption, color) in enumerate(metric_specs):
            card = ui.Card(stats, radius=13, pad=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            ui.lbl(card.body, caption, 8, True, MUTED).pack(anchor="w")
            val = ui.lbl(card.body, value, 22, True, color)
            val.pack(anchor="w", pady=(5, 1))
            ui.lbl(card.body, "Обновляется автоматически", 7, False, MUTED).pack(anchor="w")
            metric_values[key] = val

        # Two-column workspace: useful actions + latest announcements.
        columns = tk.Frame(wrap, bg=wrap["bg"])
        columns.pack(fill="x", pady=(0, 14))
        columns.grid_columnconfigure(0, weight=3, uniform="home_cols")
        columns.grid_columnconfigure(1, weight=2, uniform="home_cols")
        quick = ui.Card(columns, radius=15, pad=16)
        quick.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        latest = ui.Card(columns, radius=15, pad=16)
        latest.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        ui.lbl(quick.body, "Быстрый доступ", 13, True).pack(anchor="w")
        ui.lbl(quick.body, "Основные инструменты для ежедневной работы", 8, False, MUTED).pack(anchor="w", pady=(3, 12))
        quick_grid = tk.Frame(quick.body, bg=PANEL)
        quick_grid.pack(fill="x")
        for i in range(2):
            quick_grid.grid_columnconfigure(i, weight=1, uniform="quick")
        actions = [("laws", "§", "Законодательство", "Действующие нормативные акты", ACCENT),
                   ("ai", "✦", "Помощь нейросети", "Ответы по базе законов", PURPLE),
                   ("tests", "✓", "Проверь себя", "Тесты по направлениям службы", SUCCESS),
                   ("memos", "▤", "Краткие памятки", "Важное в удобном формате", WARNING)]
        for i, (key, glyph, title, subtitle, color) in enumerate(actions):
            card = tk.Frame(quick_grid, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0 if i % 2 == 0 else 5, 5 if i % 2 == 0 else 0), pady=5, ipady=7)
            icon = tk.Canvas(card, width=38, height=38, bg=PANEL2, highlightthickness=0)
            icon.pack(side="left", padx=(11, 9), pady=8)
            icon.create_rectangle(1, 1, 37, 37, fill=ui.mix(PANEL2, color, .18), outline="")
            icon.create_text(19, 19, text=glyph, fill=color, font=(FONT, 17, "bold"))
            copy = tk.Frame(card, bg=PANEL2)
            copy.pack(side="left", fill="both", expand=True, pady=9)
            tk.Label(copy, text=title, font=(FONT, 9, "bold"), fg=TEXT, bg=PANEL2, anchor="w").pack(fill="x")
            tk.Label(copy, text=subtitle, font=(FONT, 7), fg=MUTED, bg=PANEL2, anchor="w").pack(fill="x", pady=(3, 0))
            for widget in (card, icon, copy, *copy.winfo_children()):
                widget.bind("<Button-1>", lambda _e, k=key: self.navigate(k))
                widget.bind("<Enter>", lambda _e, c=card: c.configure(highlightbackground=ACCENT))
                widget.bind("<Leave>", lambda _e, c=card: c.configure(highlightbackground=BORDER))
        ui.lbl(latest.body, "Последние обновления", 13, True).pack(anchor="w")
        ui.lbl(latest.body, "Объявления и важная информация", 8, False, MUTED).pack(anchor="w", pady=(3, 12))
        self._home_ann = tk.Frame(latest.body, bg=PANEL)
        self._home_ann.pack(fill="x")
        self.loading(self._home_ann, "Загружаем обновления…")

        recent = ui.Card(wrap, radius=15, pad=16)
        recent.pack(fill="x", pady=(0, 14))
        ui.lbl(recent.body, "Последнее изученное", 12, True).pack(anchor="w", pady=(0, 8))
        self._home_recent = tk.Frame(recent.body, bg=PANEL)
        self._home_recent.pack(fill="x")
        self.loading(self._home_recent, "Загружаем историю…")

        if self.guest:
            metric_values["tests"].configure(text="—")
            metric_values["avg"].configure(text="—")
        def work():
            out = {"laws": "—", "articles": "—", "tests": "—", "avg": "—", "recent": [], "ann": []}
            try:
                out["laws"] = str(len(self.db.table("laws", "id", {"is_active": "eq.true"})))
            except Exception:
                pass
            try:
                out["articles"] = str(len(self.db.table("law_articles", "id", {"is_active": "eq.true"})))
            except Exception:
                try:
                    out["articles"] = str(len(self.db.table("law_articles", "id")))
                except Exception:
                    pass
            if not self.guest:
                try:
                    results = self.db.table("test_results", "score", {"user_id": f"eq.{self.uid}"}, None, 500)
                    out["tests"] = str(len(results))
                    scores = [float(r.get("score")) for r in results if r.get("score") is not None]
                    out["avg"] = f"{round(sum(scores) / len(scores))}%" if scores else "—"
                except Exception:
                    pass
                try:
                    out["recent"] = self.db.table("article_views", "viewed_at,law_articles(id,law_id,article_number,title,laws(short_name))",
                                                  {"user_id": f"eq.{self.uid}"}, "viewed_at.desc", 5)
                except Exception:
                    pass
            try:
                out["ann"] = self.db.table("announcements", "id,title,content,type,created_at,expires_at", {"is_active": "eq.true"}, "created_at.desc", 5)
            except Exception:
                pass
            return out
        def done(data):
            for key in ("laws", "articles", "tests", "avg"):
                metric_values[key].configure(text=data[key])
            self._render_ann(data["ann"])
            self._render_recent(data["recent"])
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
