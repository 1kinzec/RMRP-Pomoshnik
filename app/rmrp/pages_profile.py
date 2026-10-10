"""Профиль, история, настройки, Discord Rich Presence, оверлей."""
import time
import tkinter as tk
from tkinter import ttk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import (ACCENT, ACCENT_TXT, APP_NAME, APP_PUBLISHER, APP_VERSION, BG, BORDER, FONT, MUTED, ORANGE, PANEL, PANEL2, PURPLE, SUCCESS,
                     TEAL, TEXT, TEXT2, WARNING, role_color, role_label)

DISCORD_STATUSES = ["Изучает законы на RMRP — Помощник", "Готовится к тесту по законам RMRP", "Ищет статью в кодексе", "Читает законодательство RMRP"]
HOTKEYS = ["F9", "F10", "F11", "F12", "INSERT", "HOME"]


class ProfilePages:
    # ================================================================== профиль
    def page_profile(self):
        self.set_header("Профиль", "Ваш аккаунт и статистика")
        sf = ui.ScrollFrame(self.content, bg=BG)
        sf.pack(fill="both", expand=True)
        wrap = sf.body
        p = self.prof
        name = p.get("display_name") or p.get("username") or "Пользователь"
        role = p.get("role", "USER")
        head = ui.Card(wrap, bg=ui.mix(PANEL, ACCENT, .10), border=ui.mix(PANEL, ACCENT, .4), radius=14, pad=20)
        head.pack(fill="x", pady=(2, 10))
        row = tk.Frame(head.body, bg=head._bg)
        row.pack(fill="x")
        ui.Avatar(row, name, 96, p.get("avatar_url") or "", online=True, ring=role_color(role), bg=head._bg).pack(side="left")
        col = tk.Frame(row, bg=head._bg)
        col.pack(side="left", padx=18)
        ui.lbl(col, name, 20, True, bg=head._bg).pack(anchor="w")
        ui.lbl(col, role_label(role), 10, True, role_color(role), bg=head._bg).pack(anchor="w")
        short_id = str(p.get("id", ""))[:8]
        ui.lbl(col, f"ID: {short_id}   •   Email: {self.user.get('email', '—')}", 9, False, TEXT2, bg=head._bg).pack(anchor="w", pady=(6, 0))
        ui.lbl(col, f"Регистрация: {T.fmt_date(p.get('created_at'))}   •   Последний вход: {T.fmt_date(p.get('last_login'), True)}", 9, False, MUTED, bg=head._bg).pack(anchor="w")

        stats = tk.Frame(wrap, bg=BG)
        stats.pack(fill="x", pady=4)
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="s")
        vals = {}
        for i, (k, label, color) in enumerate([("tests", "Тестов пройдено", ACCENT), ("avg", "Средний результат", SUCCESS), ("views", "Статей изучено", PURPLE), ("favs", "В избранном", WARNING)]):
            c = ui.Card(stats, radius=12, pad=14)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            v = ui.lbl(c.body, "…", 20, True, color)
            v.pack(anchor="w")
            ui.lbl(c.body, label, 9, False, MUTED).pack(anchor="w")
            vals[k] = v

        def work():
            out = {}
            res = self.db.table("test_results", "score", {"user_id": f"eq.{self.uid}"}, None, 1000)
            out["tests"], out["avg"] = len(res), (f"{round(sum(r['score'] for r in res) / len(res))}%" if res else "—")
            for key, table in (("views", "article_views"), ("favs", "favorites")):
                try:
                    out[key] = len(self.db.table(table, "id" if key == "favs" else "law_article_id", {"user_id": f"eq.{self.uid}"}, None, 1000))
                except ApiError:
                    out[key] = 0
            return out
        self.bg(work, lambda o: [vals[k].configure(text=str(v)) for k, v in o.items()], lambda e: None)

        form = ui.Card(wrap, radius=14, pad=20)
        form.pack(fill="x", pady=10)
        ui.lbl(form.body, "Редактировать профиль", 13, True).pack(anchor="w", pady=(0, 6))
        fields = {}
        for key, label in [("display_name", "Отображаемое имя"), ("avatar_url", "Ссылка на аватар (https://…)")]:
            ui.lbl(form.body, label, 9, False, TEXT2).pack(anchor="w", pady=(8, 3))
            f = ui.Field(form.body, outer=PANEL, height=38)
            f.pack(fill="x")
            f.set(p.get(key) or "")
            fields[key] = f
        ui.lbl(form.body, "О себе", 9, False, TEXT2).pack(anchor="w", pady=(8, 3))
        bio = tk.Text(form.body, height=4, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=(FONT, 10), padx=10, pady=8,
                      highlightthickness=1, highlightbackground=ui.BORDER2, highlightcolor=ACCENT)
        bio.pack(fill="x")
        bio.insert("1.0", p.get("bio") or "")

        def save():
            vals_ = {"display_name": fields["display_name"].get(), "avatar_url": fields["avatar_url"].get(), "bio": bio.get("1.0", "end").strip()}
            if not vals_["display_name"] or len(vals_["display_name"]) > 40 or len(vals_["bio"]) > 500:
                self.notify("Профиль", "Имя — от 1 до 40 символов, описание — до 500.", "warning")
                return
            if vals_["avatar_url"] and not vals_["avatar_url"].startswith(("http://", "https://")):
                self.notify("Профиль", "Ссылка на аватар должна начинаться с https://", "warning")
                return

            def done(_):
                self.prof.update(vals_)
                self._build_chip()
                self.notify("Профиль сохранён", "", "success")
                self.navigate("profile")
            self.bg(lambda: self.db.update("profiles", {"id": f"eq.{self.uid}"}, vals_), done, lambda e: self.notify("Профиль", str(e), "error"), bound=False)
        ui.RButton(form.body, "Сохранить изменения", save, height=38).pack(anchor="e", pady=(14, 0))

    # ================================================================== история
    def page_history(self):
        self.set_header("История", "Что вы читали, искали и проходили")
        holder = tk.Frame(self.content, bg=BG)
        holder.pack(fill="both", expand=True)
        tabs = ui.PillTabs(holder, [("views", "Статьи"), ("search", "Поиск"), ("ai", "Вопросы ИИ"), ("tests", "Тесты")], lambda k: load(k))
        tabs.pack(anchor="w", pady=(4, 10))
        sf = ui.ScrollFrame(holder, bg=BG)
        sf.pack(fill="both", expand=True)
        box = sf.body
        queries = {
            "views": ("article_views", "viewed_at,law_articles(id,law_id,article_number,title,laws(short_name))", "viewed_at.desc"),
            "search": ("search_history", "query,created_at", "created_at.desc"),
            "ai": ("ai_history", "question,answer,created_at,law_article_id", "created_at.desc"),
            "tests": ("test_results", "score,correct_answers,total_questions,completed_at,tests(title)", "completed_at.desc"),
        }

        def load(kind):
            for c in box.winfo_children():
                c.destroy()
            ld = self.loading(box)
            table, sel, order = queries[kind]

            def done(rows):
                ld.destroy()
                if not rows:
                    self.card_message(box, "Пока пусто", "Записи появятся по мере использования приложения.")
                    return
                for r in rows:
                    self._history_row(box, kind, r)
            self.bg(lambda: self.db.table(table, sel, {"user_id": f"eq.{self.uid}"}, order, 100), done, lambda e: ld.configure(text=f"Ошибка: {e}"))
        load("views")

    def _history_row(self, box, kind, r):
        c = ui.Card(box, radius=10, pad=12)
        c.pack(fill="x", pady=3)
        row = tk.Frame(c.body, bg=PANEL)
        row.pack(fill="x")
        if kind == "views":
            a = r.get("law_articles") or {}
            ui.lbl(row, f"{(a.get('laws') or {}).get('short_name', '')}  •  Статья {a.get('article_number')}. {a.get('title') or ''}"[:110], 10, True).pack(side="left")
            ui.RButton(row, "Открыть", lambda a=a: self.navigate("law", law_id=a["law_id"], article_id=a["id"]), "outline", height=28, size=9).pack(side="right")
            when = r.get("viewed_at")
        elif kind == "search":
            ui.lbl(row, r["query"], 10, True).pack(side="left")
            ui.RButton(row, "Повторить", lambda q=r["query"]: self.navigate("search", q=q), "outline", height=28, size=9).pack(side="right")
            when = r.get("created_at")
        elif kind == "ai":
            ui.lbl(row, r["question"][:110], 10, True).pack(side="left")
            ui.RButton(row, "Спросить снова", lambda q=r["question"]: self.navigate("ai", preset=q), "outline", height=28, size=9).pack(side="right")
            when = r.get("created_at")
        else:
            color = SUCCESS if r["score"] >= 70 else WARNING if r["score"] >= 40 else "#ef4444"
            ui.lbl(row, (r.get("tests") or {}).get("title", "Тест"), 10, True).pack(side="left")
            ui.lbl(row, f"{r['score']}%  ({r['correct_answers']}/{r['total_questions']})", 10, True, color).pack(side="right")
            when = r.get("completed_at")
        ui.lbl(c.body, T.fmt_date(when, True), 8, False, MUTED).pack(anchor="w", pady=(2, 0))

    # ================================================================== настройки
    def page_settings(self):
        self.set_header("Настройки", "Звук, уведомления, Discord, оверлей")
        sf = ui.ScrollFrame(self.content, bg=BG)
        sf.pack(fill="both", expand=True)
        wrap = sf.body
        s = self.settings

        def section(title, sub):
            c = ui.Card(wrap, radius=14, pad=20)
            c.pack(fill="x", pady=6)
            ui.lbl(c.body, title, 13, True).pack(anchor="w")
            ui.lbl(c.body, sub, 9, False, MUTED, wraplength=820).pack(anchor="w", pady=(2, 8))
            return c.body

        def switch_row(parent, text, key, after=None):
            r = tk.Frame(parent, bg=PANEL)
            r.pack(fill="x", pady=5)
            ui.lbl(r, text, 10, False, TEXT2).pack(side="left")

            def toggle(v):
                s[key] = v
                self.save_settings()
                if after:
                    after()
            ui.Switch(r, bool(s.get(key)), toggle).pack(side="right")

        snd = section("Звук интерфейса", "Тихие клики и сигналы. Работает на Windows.")
        switch_row(snd, "Звуки нажатия", "sound_enabled")
        switch_row(snd, "Звук при наведении", "hover_sound")
        vol = tk.IntVar(value=min(25, int(s.get("sound_volume", 8))))
        ui.lbl(snd, "Громкость", 9, False, MUTED).pack(anchor="w", pady=(6, 0))
        sc = tk.Scale(snd, from_=0, to=25, orient="horizontal", variable=vol, bg=PANEL, fg=TEXT, highlightthickness=0, troughcolor=PANEL2, activebackground=ACCENT, length=360,
                      command=lambda v: (s.update(sound_volume=int(float(v))), self.save_settings()))
        sc.pack(anchor="w")
        ui.RButton(snd, "Проверить звук", lambda: self.play_sound("click"), "secondary", height=32, size=9).pack(anchor="w", pady=(4, 0))

        nt = section("Уведомления", "Сколько миллисекунд показывать всплывающие сообщения.")
        dur = tk.IntVar(value=int(s.get("toast_duration", 3600)))
        tk.Scale(nt, from_=1500, to=8000, orient="horizontal", variable=dur, bg=PANEL, fg=TEXT, highlightthickness=0, troughcolor=PANEL2, activebackground=ACCENT, length=360,
                 command=lambda v: (s.update(toast_duration=int(float(v))), self.save_settings())).pack(anchor="w")
        ui.RButton(nt, "Показать пример", lambda: self.notify("Готово", "Так выглядят уведомления.", "success"), "secondary", height=32, size=9).pack(anchor="w", pady=(4, 0))

        dc = section("Discord Rich Presence", "Покажите друзьям, что вы изучаете законы RMRP. Нужен запущенный Discord на этом же компьютере.")
        status_lbl = ui.lbl(dc, f"Статус: {self.rpc.status}", 10, True, ACCENT_TXT)
        status_lbl.pack(anchor="w", pady=(0, 8))
        ui.RButton(dc, "Настроить Discord", self.discord_dialog, "primary", icon="◎", height=36).pack(anchor="w")

        ov = section("Оверлей в игре", "Быстрые разделы и мгновенный поиск по статьям поверх игры. Работает в оконном и безрамочном режимах игры.")
        switch_row(ov, "Включить оверлей", "overlay_enabled", self.apply_overlay_settings)
        r = tk.Frame(ov, bg=PANEL)
        r.pack(fill="x", pady=5)
        ui.lbl(r, "Горячая клавиша", 10, False, TEXT2).pack(side="left")
        hv = tk.StringVar(value=s.get("overlay_hotkey", "F10"))
        cb = ttk.Combobox(r, textvariable=hv, values=HOTKEYS, state="readonly", width=10)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda e: (s.update(overlay_hotkey=hv.get()), self.save_settings(), self.apply_overlay_settings()))
        ui.RButton(ov, "Открыть оверлей сейчас", self.overlay.toggle, "secondary", height=32, size=9).pack(anchor="w", pady=(6, 0))

        if not self.guest:
            pr = section("Розыгрыши", "Внутриигровой «скример» от Основателя приходит только тем, кто сам это разрешил. Отключить можно в любой момент.")
            allow = bool(self.prof.get("allow_pranks"))

            def toggle_pr(v):
                self.bg(lambda: self.db.update("profiles", {"id": f"eq.{self.uid}"}, {"allow_pranks": v}),
                        lambda _: (self.prof.update(allow_pranks=v), self.notify("Розыгрыши", "Разрешены" if v else "Запрещены", "success")),
                        lambda e: self.notify("Розыгрыши", str(e), "error"), bound=False)
            r = tk.Frame(pr, bg=PANEL)
            r.pack(fill="x")
            ui.lbl(r, "Разрешаю внутриигровые розыгрыши", 10, False, TEXT2).pack(side="left")
            ui.Switch(r, allow, toggle_pr).pack(side="right")

        if self.role() == "FOUNDER":
            fd = section("Для Основателя", "Общий Discord Application ID для всех пользователей (хранится в app_settings).")
            f = ui.Field(fd, "Application ID из discord.com/developers", outer=PANEL, height=38)
            f.pack(fill="x")
            f.set(s.get("discord_app_id", ""))

            def save_id():
                v = f.get()
                self.bg(lambda: self.db.insert("app_settings", {"key": "discord_app_id", "value": v}, upsert_on="key"),
                        lambda _: (s.update(discord_app_id=v), self.save_settings(), self.apply_discord(), self.notify("Application ID", "Сохранён для всех.", "success")),
                        lambda e: self.notify("Application ID", str(e), "error"), bound=False)
            ui.RButton(fd, "Сохранить для всех", save_id, "secondary", height=34, size=9).pack(anchor="e", pady=(8, 0))

        ab = section("О приложении", f"{APP_NAME} v{APP_VERSION}  •  {APP_PUBLISHER}")
        ui.lbl(ab, "Законодательство, обучение и тесты для RMRP.", 9, False, MUTED).pack(anchor="w")

    # ================================================================== Discord Rich Presence
    def discord_dialog(self):
        s = self.settings
        win = ui.modal(self, "Discord Rich Presence", 460, 640, BG)
        ui.lbl(win, "Discord Rich Presence", 15, True, bg=BG).pack(anchor="w", padx=24, pady=(20, 4))
        status = ui.lbl(win, "", 10, True, SUCCESS, bg=BG)
        status.pack(anchor="w", padx=24)

        def refresh_status(*_):
            try:
                text = self.rpc.status
                ok = text == "Подключено"
                status.configure(text=("● " if ok else "○ ") + text, fg=SUCCESS if ok else WARNING)
                if win.winfo_exists():
                    win.after(1000, refresh_status)
            except tk.TclError:
                pass
        refresh_status()
        card = ui.Card(win, radius=12, pad=16, outer=BG)
        card.pack(fill="x", padx=24, pady=12)

        def sw(text, key):
            r = tk.Frame(card.body, bg=PANEL)
            r.pack(fill="x", pady=6)
            ui.lbl(r, text, 10, False, TEXT2).pack(side="left")
            ui.Switch(r, bool(s.get(key)), lambda v, k=key: (s.update({k: v}), self.save_settings(), self.apply_discord(), update_preview())).pack(side="right")
        sw("Показывать активность", "discord_show_activity")
        sw("Показывать название закона", "discord_show_law")
        sw("Показывать таймер", "discord_show_timer")
        ui.lbl(win, "Статус", 9, False, TEXT2, bg=BG).pack(anchor="w", padx=24)
        sv = tk.StringVar(value=s.get("discord_status"))
        cb = ttk.Combobox(win, textvariable=sv, values=DISCORD_STATUSES)
        cb.pack(fill="x", padx=24, pady=(4, 10), ipady=3)

        def status_changed(*_):
            s["discord_status"] = sv.get()
            self.save_settings()
            self.apply_discord()
            update_preview()
        cb.bind("<<ComboboxSelected>>", status_changed)
        cb.bind("<FocusOut>", status_changed)
        ui.lbl(win, "Discord Application ID", 9, False, TEXT2, bg=BG).pack(anchor="w", padx=24)
        aid = ui.Field(win, "Число из discord.com/developers → Application", outer=BG, height=38)
        aid.pack(fill="x", padx=24, pady=(4, 4))
        aid.set(s.get("discord_app_id", ""))
        ui.lbl(win, "Создайте приложение в Discord Developer Portal, назовите его «RMRP Помощник» и вставьте его Application ID. Картинку с ключом «rmrp» загрузите в Rich Presence → Art Assets.",
               8, False, MUTED, bg=BG, wraplength=410).pack(anchor="w", padx=24)

        pv = ui.Card(win, radius=12, pad=14, outer=BG, bg=PANEL2)
        pv.pack(fill="x", padx=24, pady=12)
        row = tk.Frame(pv.body, bg=PANEL2)
        row.pack(fill="x")
        logo = ui.load_image("rmrp.png", (48, 48))
        if logo:
            tk.Label(row, image=logo, bg=PANEL2).pack(side="left")
        col = tk.Frame(row, bg=PANEL2)
        col.pack(side="left", padx=12)
        l1 = ui.lbl(col, APP_NAME, 10, True, bg=PANEL2)
        l1.pack(anchor="w")
        l2 = ui.lbl(col, "", 9, False, TEXT2, bg=PANEL2)
        l2.pack(anchor="w")
        l3 = ui.lbl(col, "", 9, False, ACCENT_TXT, bg=PANEL2)
        l3.pack(anchor="w")

        def update_preview():
            try:
                l2.configure(text=s.get("discord_status") if s.get("discord_show_activity") else "Активность скрыта")
                l3.configure(text=("◷ " + T.fmt_duration(time.time() - self.started)) if s.get("discord_show_timer") else "")
                if win.winfo_exists():
                    win.after(1000, update_preview)
            except tk.TclError:
                pass
        update_preview()
        hide = tk.BooleanVar(value=bool(s.get("discord_hide")))
        tk.Checkbutton(win, text="Не показывать мою активность в Discord", variable=hide, bg=BG, fg=TEXT2, selectcolor=PANEL2, activebackground=BG, activeforeground=TEXT,
                       font=(FONT, 9), bd=0, highlightthickness=0, command=lambda: (s.update(discord_hide=hide.get()), self.save_settings(), self.apply_discord())).pack(anchor="w", padx=24)
        enabled = {"v": bool(s.get("discord_enabled"))}
        btn = ui.RButton(win, "", None, "primary", height=42)

        def style_btn():
            btn.configure_text("Отключить" if enabled["v"] else "Включить")
            btn.st = ui.BUTTON_STYLES["secondary" if enabled["v"] else "primary"]
            btn._draw()

        def toggle():
            s["discord_app_id"] = aid.get()
            enabled["v"] = not enabled["v"]
            s["discord_enabled"] = enabled["v"]
            self.save_settings()
            self.apply_discord()
            style_btn()
            if enabled["v"] and not s["discord_app_id"]:
                self.notify("Discord", "Укажите Application ID.", "warning")
        btn.command = toggle
        btn.pack(fill="x", padx=24, pady=(14, 0))
        style_btn()
