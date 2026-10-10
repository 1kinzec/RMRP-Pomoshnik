"""Админ-панель, жалобы, скример."""
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import (ACCENT, ACCENT_TXT, APP_NAME, BG, BORDER, DANGER, DIFFICULTY_RU, FONT, MUTED, ONLINE_WINDOW_SEC, ORANGE, PANEL, PANEL2, PURPLE,
                     ROLE_ORDER, ROLE_SHORT, STATUS_RU, STATUS_VALUES, SUCCESS, TEAL, TEXT, TEXT2, WARNING, role_label)

REPORT_STATUS = {"NEW": "Новая", "IN_PROGRESS": "В работе", "RESOLVED": "Решена", "REJECTED": "Отклонена"}
ADMIN_TILES = [
    ("users", "♙", "Пользователи", "Управление аккаунтами", ACCENT),
    ("roles", "♛", "Роли и права", "Кто что может", PURPLE),
    ("reports", "⚠", "Жалобы", "Модерация обращений", WARNING),
    ("tests", "✓", "Тесты", "Вопросы и тесты", TEAL),
    ("laws", "▤", "Законодательство", "Добавление и синхронизация", ACCENT),
    ("ann", "✉", "Объявления", "Новости для всех", ORANGE),
    ("audit", "☰", "Журнал действий", "Логи и активность", "#94a3b8"),
    ("screamer", "⚡", "Скример", "Только для Основателя", DANGER),
]


class AdminPages:
    # ================================================================== общий диалог-форма
    def form_dialog(self, title, fields, on_submit, height=None, ok_text="Сохранить"):
        """fields: [(key, label, kind, extra)] kind: text|multi|choice(extra=[(value,label)])|check"""
        h = height or (150 + sum(88 if k == "multi" else 66 for _, _, k, _ in fields))
        win = ui.modal(self, title, 560, min(h, 720), PANEL)
        ui.lbl(win, title, 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(20, 2))
        getters = {}
        for key, label, kind, extra in fields:
            ui.lbl(win, label, 9, False, TEXT2, bg=PANEL).pack(anchor="w", padx=24, pady=(8, 3))
            if kind == "multi":
                t = tk.Text(win, height=4, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=(FONT, 10), padx=10, pady=8,
                            highlightthickness=1, highlightbackground=ui.BORDER2, highlightcolor=ACCENT)
                t.pack(fill="x", padx=24)
                if extra:
                    t.insert("1.0", extra)
                getters[key] = lambda t=t: t.get("1.0", "end").strip()
            elif kind == "choice":
                var = tk.StringVar()
                cb = ttk.Combobox(win, textvariable=var, values=[l for _, l in extra], state="readonly")
                cb.pack(fill="x", padx=24, ipady=3)
                cb.current(0)
                getters[key] = lambda cb=cb, ex=extra: ex[cb.current()][0]
            else:
                f = ui.Field(win, outer=PANEL, height=36)
                f.pack(fill="x", padx=24)
                if extra:
                    f.set(extra)
                getters[key] = f.get
        bar = tk.Frame(win, bg=PANEL)
        bar.pack(side="bottom", fill="x", padx=24, pady=16)

        def submit():
            vals = {k: g() for k, g in getters.items()}
            if on_submit(vals) is not False:
                win.destroy()
        ui.RButton(bar, ok_text, submit).pack(side="right")
        ui.RButton(bar, "Отмена", win.destroy, "secondary").pack(side="right", padx=8)

    # ================================================================== главная админки
    def page_admin(self, section=None):
        if not self.is_staff("ADMIN"):
            self.card_message(self.content, "Нет доступа", "Раздел доступен только администраторам и основателю.")
            return
        if section:
            self.set_header("Админ-панель", dict((k, t) for k, _, t, _, _ in ADMIN_TILES).get(section, ""))
            top = tk.Frame(self.content, bg=BG)
            top.pack(fill="x", pady=(0, 8))
            ui.RButton(top, "Админ-панель", lambda: self.navigate("admin"), "ghost", icon="←", height=34).pack(side="left")
            body = tk.Frame(self.content, bg=BG)
            body.pack(fill="both", expand=True)
            getattr(self, f"_adm_{section}")(body)
            return
        self.set_header("Админ-панель", "Управление пользователями, контентом и настройками")
        grid = tk.Frame(self.content, bg=BG)
        grid.pack(fill="x", pady=8)
        tiles = [t for t in ADMIN_TILES if t[0] != "screamer" or self.role() == "FOUNDER"]
        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="a")
        for i, (key, glyph, title, sub, color) in enumerate(tiles):
            c = ui.Card(grid, bg=ui.mix(PANEL, color, .08), border=ui.mix(PANEL, color, .4), radius=14, pad=16, height=128,
                        hover_bg=ui.mix(PANEL, color, .18), hover_border=color)
            c.grid(row=i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            ui.icon_tile(c.body, glyph, color, 44, bg=ui.mix(PANEL, color, .08)).pack(anchor="w")
            ui.lbl(c.body, title, 11, True).pack(anchor="w", pady=(10, 1))
            ui.lbl(c.body, sub, 8, False, MUTED).pack(anchor="w")
            c.make_clickable(lambda k=key: self.navigate("admin", section=k))

    # ================================================================== пользователи
    def _adm_users(self, body):
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(1, weight=1)
        bar = tk.Frame(body, bg=BG)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        search = ui.Field(bar, "Поиск по логину или имени…", height=38, icon="⌕")
        search.pack(side="left", fill="x", expand=True)
        total = ui.lbl(bar, "", 9, False, MUTED)
        total.pack(side="right", padx=10)
        ui.RButton(bar, "Обновить", lambda: reload(), "secondary", icon="⟳", height=38).pack(side="right", padx=(8, 0))
        cols = ("id", "name", "role", "status", "premium")
        tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse")
        for c, t, w in [("id", "ID", 90), ("name", "Имя", 200), ("role", "Роль", 150), ("status", "Статус", 130), ("premium", "Premium", 80)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="w")
        tree.tag_configure("online", foreground=SUCCESS)
        tree.tag_configure("banned", foreground=DANGER)
        tree.grid(row=1, column=0, sticky="nsew")
        panel = ui.Card(body, radius=12, pad=16, height=100)
        panel.configure(width=290)
        panel.grid(row=1, column=1, sticky="ns", padx=(10, 0))
        panel.grid_propagate(False)
        state = {"rows": {}}
        info = tk.Frame(panel.body, bg=PANEL)
        info.pack(fill="both", expand=True)
        ui.lbl(info, "Выберите пользователя в таблице", 10, False, MUTED).pack(pady=20)

        def reload():
            self.bg(lambda: self.db.table("profiles", "*", None, "created_at.asc", 500), fill, lambda e: self.notify("Пользователи", str(e), "error"))

        def fill(rows):
            state["rows"] = {r["id"]: r for r in rows}
            render()

        def render(*_):
            tree.delete(*tree.get_children())
            q = search.get().lower()
            shown = 0
            for i, r in enumerate(state["rows"].values(), 1):
                if q and q not in (r.get("username") or "").lower() and q not in (r.get("display_name") or "").lower():
                    continue
                online = T.is_online(r.get("last_seen_at"), ONLINE_WINDOW_SEC)
                tags = ("online",) if online else ()
                if r.get("status") != "ACTIVE":
                    tags = ("banned",)
                status = ("● Online" if online else "○ Offline") if r.get("status") == "ACTIVE" else STATUS_RU.get(r["status"], r["status"])
                tree.insert("", "end", iid=r["id"], tags=tags, values=(str(r["id"])[:8], r.get("display_name") or r.get("username"), ROLE_SHORT.get(r["role"], r["role"]),
                                                                      status, "Да" if r.get("premium") else "Нет"))
                shown += 1
            total.configure(text=f"Всего пользователей: {len(state['rows'])}" + (f" (показано {shown})" if q else ""))
        search.var.trace_add("write", render)

        def selected():
            s = tree.selection()
            return state["rows"].get(s[0]) if s else None

        def on_select(_e=None):
            u = selected()
            for c in info.winfo_children():
                c.destroy()
            if not u:
                return
            online = T.is_online(u.get("last_seen_at"), ONLINE_WINDOW_SEC)
            ui.Avatar(info, u.get("display_name") or u.get("username"), 64, u.get("avatar_url") or "", online=online).pack(anchor="w")
            ui.lbl(info, u.get("display_name") or u.get("username"), 13, True).pack(anchor="w", pady=(8, 0))
            ui.lbl(info, f"@{u.get('username')}  •  {role_label(u['role'])}", 9, False, TEXT2).pack(anchor="w")
            ui.lbl(info, f"Статус: {STATUS_RU.get(u['status'], u['status'])}  •  Premium: {'да' if u.get('premium') else 'нет'}", 9, False, MUTED).pack(anchor="w", pady=(4, 0))
            ui.lbl(info, f"Регистрация: {T.fmt_date(u.get('created_at'))}\nПоследний вход: {T.fmt_date(u.get('last_login'), True)}\nРозыгрыши: {'разрешены' if u.get('allow_pranks') else 'запрещены'}",
                   8, False, MUTED).pack(anchor="w", pady=(6, 10))
            for text, style, fn in [("Изменить роль", "primary", lambda: change_role(u)), ("Выдать / снять Premium", "secondary", lambda: patch(u, {"premium": not u.get("premium")}, "Premium")),
                                    ("Заблокировать" if u["status"] == "ACTIVE" else "Разблокировать", "secondary",
                                     lambda: set_status(u)), ("Разрешение на розыгрыши", "secondary", lambda: patch(u, {"allow_pranks": not u.get("allow_pranks")}, "Розыгрыши"))]:
                ui.RButton(info, text, fn, style, height=34, size=9).pack(fill="x", pady=3)
            if self.role() == "FOUNDER":
                ui.RButton(info, "Скример", lambda: self.send_screamer(u), "danger", icon="⚡", height=34, size=9).pack(fill="x", pady=(8, 3))
        tree.bind("<<TreeviewSelect>>", on_select)

        def protected(u):
            if u["id"] == self.uid and self.role() == "FOUNDER":
                self.notify(APP_NAME, "Основатель не меняет свой аккаунт из клиента.", "warning")
                return True
            if u["role"] == "FOUNDER" and self.role() != "FOUNDER":
                self.notify(APP_NAME, "Только Основатель управляет аккаунтом Основателя.", "error")
                return True
            if u["role"] == "ADMIN" and self.role() != "FOUNDER" and u["id"] != self.uid:
                self.notify(APP_NAME, "Администраторов может менять только Основатель.", "error")
                return True
            return False

        def patch(u, values, label):
            if protected(u):
                return

            def work():
                self.db.update("profiles", {"id": f"eq.{u['id']}"}, values)
            self.bg(work, lambda _: (self.log_action(f"Изменено: {label}", "profiles", u["id"], values), reload(), self.notify(label, "Сохранено.", "success")),
                    lambda e: self.notify(label, str(e), "error"), bound=False)

        def change_role(u):
            if protected(u):
                return
            allowed = ROLE_ORDER if self.role() == "FOUNDER" else ["MODERATOR", "PREMIUM", "USER"]
            self.form_dialog(f"Роль: {u.get('username')}", [("role", "Новая роль", "choice", [(r, role_label(r)) for r in allowed])],
                             lambda v: patch(u, {"role": v["role"]}, "Роль") and None, 230)

        def set_status(u):
            if u["status"] == "ACTIVE":
                self.form_dialog("Блокировка", [("status", "Статус", "choice", [("BLOCKED", "Заблокирован"), ("BANNED", "Забанен")])],
                                 lambda v: patch(u, {"status": v["status"]}, "Статус") and None, 230, "Применить")
            else:
                patch(u, {"status": "ACTIVE"}, "Статус")
        reload()

    # ================================================================== роли
    def _adm_roles(self, body):
        rows = [("FOUNDER", "Полный доступ. Управляет админами, скримером, общими настройками (Discord Application ID)."),
                ("ADMIN", "Управляет пользователями (кроме админов и Основателя), законами, тестами, объявлениями, журналом, синхронизацией."),
                ("MODERATOR", "Рассматривает жалобы и меняет их статус."),
                ("PREMIUM", "Как пользователь; отметка Premium в профиле."),
                ("USER", "Читает законы, ищет, проходит тесты, ведёт избранное и историю, подаёт жалобы.")]
        for role, text in rows:
            c = ui.Card(body, radius=12, pad=14)
            c.pack(fill="x", pady=4)
            ui.lbl(c.body, role_label(role), 11, True).pack(anchor="w")
            ui.lbl(c.body, text, 9, False, TEXT2, wraplength=900).pack(anchor="w", pady=(3, 0))
        ui.lbl(body, "Права проверяются на сервере (RLS Supabase): клиент не может обойти иерархию ролей.", 9, False, MUTED).pack(anchor="w", pady=10)

    # ================================================================== жалобы
    def page_reports(self):
        staff = self.is_staff("MODERATOR")
        self.set_header("Жалобы", "Модерация обращений" if staff else "Сообщите о нарушении или ошибке")
        self._reports_view(self.content, staff)

    def _adm_reports(self, body):
        self._reports_view(body, True)

    def _reports_view(self, parent, staff):
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        ui.RButton(bar, "Новая жалоба", self.create_report, "primary", icon="＋", height=36).pack(side="left")
        lst = ui.ScrollFrame(parent, bg=BG)
        lst.pack(fill="both", expand=True)
        res = lst.body
        loader = self.loading(res)
        sel = "id,reason,description,status,created_at,author:profiles!reports_author_id_fkey(username),target:profiles!reports_target_user_id_fkey(username)"

        def work():
            flt = None if staff else {"author_id": f"eq.{self.uid}"}
            try:
                return self.db.table("reports", sel, flt, "created_at.desc", 200)
            except ApiError:
                return self.db.table("reports", "id,reason,description,status,created_at", flt, "created_at.desc", 200)

        def done(rows):
            loader.destroy()
            if not rows:
                self.card_message(res, "Жалоб нет", "Здесь появятся обращения.")
                return
            for r in rows:
                c = ui.Card(res, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                head = tk.Frame(c.body, bg=PANEL)
                head.pack(fill="x")
                color = {"NEW": WARNING, "IN_PROGRESS": ACCENT, "RESOLVED": SUCCESS, "REJECTED": MUTED}.get(r["status"], MUTED)
                ui.lbl(head, r["reason"], 11, True).pack(side="left")
                ui.chip(head, REPORT_STATUS.get(r["status"], r["status"]), color, PANEL).pack(side="right")
                who = f"от {((r.get('author') or {}).get('username')) or '—'}"
                if (r.get("target") or {}).get("username"):
                    who += f"  •  на {r['target']['username']}"
                ui.lbl(c.body, f"{who}  •  {T.fmt_date(r.get('created_at'), True)}", 8, False, MUTED).pack(anchor="w", pady=(2, 4))
                ui.lbl(c.body, r.get("description") or "", 9, False, TEXT2, wraplength=900).pack(anchor="w")
                if staff:
                    row = tk.Frame(c.body, bg=PANEL)
                    row.pack(anchor="w", pady=(8, 0))
                    for st, txt, style in [("IN_PROGRESS", "В работу", "secondary"), ("RESOLVED", "Решена", "success"), ("REJECTED", "Отклонить", "ghost")]:
                        ui.RButton(row, txt, lambda rid=r["id"], st=st: self._set_report(rid, st), style, height=30, size=9, padx=12).pack(side="left", padx=(0, 6))
        self.bg(work, done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _set_report(self, rid, status):
        vals = {"status": status}
        if status in ("RESOLVED", "REJECTED"):
            vals["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self.bg(lambda: self.db.update("reports", {"id": f"eq.{rid}"}, vals),
                lambda _: (self.log_action("Статус жалобы", "reports", rid, vals), self.navigate(self.page, **self.page_args)), bound=False)

    def create_report(self):
        if not self.require_login("Жалобы"):
            return

        def submit(v):
            if not v["reason"] or not v["description"]:
                self.notify("Жалоба", "Заполните тему и описание.", "warning")
                return False
            self.bg(lambda: self.db.insert("reports", {"author_id": self.uid, "reason": v["reason"][:120], "description": v["description"][:2000]}),
                    lambda _: (self.notify("Жалоба отправлена", "Модераторы рассмотрят обращение.", "success"), self.navigate(self.page, **self.page_args)), bound=False)
        self.form_dialog("Новая жалоба", [("reason", "Тема", "text", ""), ("description", "Описание", "multi", "")], submit, 380, "Отправить")

    # ================================================================== тесты
    def _adm_tests(self, body):
        bar = tk.Frame(body, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        ui.RButton(bar, "Новый тест", self.add_test, "primary", icon="＋", height=36).pack(side="left")
        ui.RButton(bar, "Добавить вопрос", self.add_question, "secondary", icon="？", height=36).pack(side="left", padx=8)
        sf = ui.ScrollFrame(body, bg=BG)
        sf.pack(fill="both", expand=True)
        loader = self.loading(sf.body)

        def done(rows):
            loader.destroy()
            if not rows:
                self.card_message(sf.body, "Тестов пока нет", "Создайте первый тест и добавьте вопросы.")
            for t in rows:
                c = ui.Card(sf.body, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                row = tk.Frame(c.body, bg=PANEL)
                row.pack(fill="x")
                col = tk.Frame(row, bg=PANEL)
                col.pack(side="left", fill="x", expand=True)
                ui.lbl(col, t["title"], 11, True).pack(anchor="w")
                ui.lbl(col, f"{t.get('category')}  •  {DIFFICULTY_RU.get(t.get('difficulty'), '')}  •  вопросов: {t.get('question_count') or 0}", 9, False, MUTED).pack(anchor="w")
                ui.RButton(row, "Скрыть" if t.get("is_active") else "Показать", lambda t=t: self._toggle_test(t), "secondary", height=30, size=9).pack(side="right")
        self.bg(lambda: self.db.table("tests", "*", None, "title.asc"), done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _toggle_test(self, t):
        self.bg(lambda: self.db.update("tests", {"id": f"eq.{t['id']}"}, {"is_active": not t.get("is_active")}), lambda _: self.navigate("admin", section="tests"), bound=False)

    def add_test(self):
        def submit(v):
            if not v["title"]:
                self.notify("Тест", "Введите название.", "warning")
                return False
            self.bg(lambda: self.db.insert("tests", {"title": v["title"], "category": v["category"] or "Общее", "description": v["description"], "difficulty": v["difficulty"]}),
                    lambda _: (self.log_action("Создан тест", "tests", None, {"title": v["title"]}), self.navigate("admin", section="tests")), bound=False)
        self.form_dialog("Новый тест", [("title", "Название", "text", ""), ("category", "Категория", "text", ""), ("description", "Описание", "multi", ""),
                                        ("difficulty", "Сложность", "choice", [("EASY", "Лёгкий"), ("MEDIUM", "Средний"), ("HARD", "Сложный")])], submit, 500)

    def add_question(self):
        def open_form(tests):
            if not tests:
                self.notify("Вопрос", "Сначала создайте тест.", "warning")
                return

            def submit(v):
                if not all(v[k] for k in ("question", "a", "b", "c", "d")):
                    self.notify("Вопрос", "Заполните вопрос и все 4 ответа.", "warning")
                    return False

                def work():
                    self.db.insert("questions", {"test_id": v["test"], "question": v["question"], "answer_a": v["a"], "answer_b": v["b"], "answer_c": v["c"],
                                                 "answer_d": v["d"], "correct_answer": v["correct"], "explanation": v["explanation"] or None})
                    cnt = len(self.db.table("questions", "id", {"test_id": f"eq.{v['test']}"}))
                    self.db.update("tests", {"id": f"eq.{v['test']}"}, {"question_count": cnt})
                self.bg(work, lambda _: (self.notify("Вопрос добавлен", "", "success"), self.navigate("admin", section="tests")), bound=False)
            self.form_dialog("Новый вопрос", [("test", "Тест", "choice", [(t["id"], t["title"]) for t in tests]), ("question", "Вопрос", "multi", ""),
                                              ("a", "Ответ A", "text", ""), ("b", "Ответ B", "text", ""), ("c", "Ответ C", "text", ""), ("d", "Ответ D", "text", ""),
                                              ("correct", "Правильный ответ", "choice", [(x, x) for x in "ABCD"]), ("explanation", "Пояснение (необязательно)", "text", "")],
                             submit, 700)
        self.bg(lambda: self.db.table("tests", "id,title", None, "title.asc"), open_form, bound=False)

    # ================================================================== законы
    def _adm_laws(self, body):
        bar = tk.Frame(body, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        ui.RButton(bar, "Синхронизировать RMRP", self.sync_laws, "primary", icon="⟳", height=36).pack(side="left")
        ui.RButton(bar, "Добавить закон", self.add_law_dialog, "secondary", icon="＋", height=36).pack(side="left", padx=8)
        sf = ui.ScrollFrame(body, bg=BG)
        sf.pack(fill="both", expand=True)
        loader = self.loading(sf.body)

        def done(rows):
            loader.destroy()
            for l in rows:
                c = ui.Card(sf.body, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                row = tk.Frame(c.body, bg=PANEL)
                row.pack(fill="x")
                col = tk.Frame(row, bg=PANEL)
                col.pack(side="left", fill="x", expand=True)
                ui.lbl(col, l.get("short_name") or l["name"], 11, True).pack(anchor="w")
                ui.lbl(col, f"{l['name']}  •  {l.get('law_number') or ''}", 9, False, MUTED, wraplength=640).pack(anchor="w")
                ui.RButton(row, "Изменить", lambda l=l: self.add_law_dialog(l), "secondary", height=30, size=9).pack(side="right")
        self.bg(lambda: self.db.table("laws", "*", None, "name.asc"), done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    # ================================================================== объявления
    def _adm_ann(self, body):
        bar = tk.Frame(body, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        ui.RButton(bar, "Новое объявление", self.add_announcement, "primary", icon="＋", height=36).pack(side="left")
        sf = ui.ScrollFrame(body, bg=BG)
        sf.pack(fill="both", expand=True)
        loader = self.loading(sf.body)

        def done(rows):
            loader.destroy()
            if not rows:
                self.card_message(sf.body, "Объявлений нет", "Они показываются на главной странице.")
            for a in rows:
                c = ui.Card(sf.body, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                row = tk.Frame(c.body, bg=PANEL)
                row.pack(fill="x")
                ui.lbl(row, a["title"], 11, True).pack(side="left")
                ui.RButton(row, "Удалить", lambda a=a: self._del_ann(a["id"]), "ghost", height=28, size=9).pack(side="right")
                ui.lbl(c.body, f"{a.get('type')}  •  {T.fmt_date(a.get('created_at'))}  •  {'активно' if a.get('is_active') else 'скрыто'}", 8, False, MUTED).pack(anchor="w")
                ui.lbl(c.body, a.get("content") or "", 9, False, TEXT2, wraplength=900).pack(anchor="w", pady=(4, 0))
        self.bg(lambda: self.db.table("announcements", "*", None, "created_at.desc", 100), done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def add_announcement(self):
        def submit(v):
            if not v["title"] or not v["content"]:
                self.notify("Объявление", "Заполните заголовок и текст.", "warning")
                return False
            self.bg(lambda: self.db.insert("announcements", {"title": v["title"], "content": v["content"], "type": v["type"], "created_by": self.uid}),
                    lambda _: (self.log_action("Новое объявление", "announcements", None, {"title": v["title"]}), self.navigate("admin", section="ann")), bound=False)
        self.form_dialog("Новое объявление", [("title", "Заголовок", "text", ""), ("content", "Текст", "multi", ""),
                                              ("type", "Тип", "choice", [("INFO", "Информация"), ("UPDATE", "Обновление"), ("WARNING", "Важно")])], submit, 480)

    def _del_ann(self, aid):
        if ui.confirm(self, "Удалить объявление?", "Оно исчезнет у всех пользователей.", "Удалить", True):
            self.bg(lambda: self.db.delete("announcements", {"id": f"eq.{aid}"}), lambda _: self.navigate("admin", section="ann"), bound=False)

    # ================================================================== журнал
    def _adm_audit(self, body):
        tree = ttk.Treeview(body, columns=("time", "user", "action", "target"), show="headings")
        for c, t, w in [("time", "Время", 150), ("user", "Кто", 150), ("action", "Действие", 280), ("target", "Объект", 240)]:
            tree.heading(c, text=t)
            tree.column(c, width=w)
        tree.pack(fill="both", expand=True)

        def done(rows):
            for r in rows:
                tree.insert("", "end", values=(T.fmt_date(r["created_at"], True), (r.get("profiles") or {}).get("username") or "—", r["action"],
                                               f"{r.get('target_type') or ''} {r.get('target_id') or ''}".strip()))
        self.bg(lambda: self.db.table("audit_logs", "created_at,action,target_type,target_id,profiles(username)", None, "created_at.desc", 300), done,
                lambda e: self.notify("Журнал", str(e), "error"))

    # ================================================================== скример (только Основатель, только с согласия получателя)
    def _adm_screamer(self, body):
        if self.role() != "FOUNDER":
            self.card_message(body, "Нет доступа", "Только Основатель.")
            return
        ui.lbl(body, "Скример получат только пользователи, которые сами включили «Разрешаю внутриигровые розыгрыши» в настройках.", 9, False, MUTED).pack(anchor="w", pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        left = ui.Card(body, radius=12, pad=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ui.Card(body, radius=12, pad=16)
        right.pack(side="left", fill="y")
        right.configure(width=330)
        ui.lbl(left.body, "Выберите пользователя", 11, True).pack(anchor="w", pady=(0, 8))
        lst = tk.Listbox(left.body, bg=PANEL2, fg=TEXT, selectbackground=ACCENT, selectforeground="#fff", relief="flat", bd=0, highlightthickness=0, font=(FONT, 10), activestyle="none")
        lst.pack(fill="both", expand=True)
        users = []

        def done(rows):
            users[:] = [r for r in rows if r["id"] != self.uid]
            for r in users:
                lst.insert("end", f"  {r.get('display_name') or r.get('username')}   (@{r.get('username')})")
            if not users:
                lst.insert("end", "  Нет пользователей с разрешением")
        self.bg(lambda: self.db.table("profiles", "id,username,display_name", {"allow_pranks": "eq.true", "status": "eq.ACTIVE"}, "username.asc", 200), done,
                lambda e: self.notify("Скример", str(e), "error"))
        c = tk.Canvas(right.body, width=290, height=190, bg="#02050a", highlightthickness=0)
        c.pack()
        self._draw_scare(c, 290, 190)
        ui.lbl(right.body, "⚠ Аккуратно! Это может напугать пользователя.", 9, False, WARNING, wraplength=290).pack(anchor="w", pady=10)

        def go():
            s = lst.curselection()
            if s and s[0] < len(users):
                self.send_screamer(users[s[0]])
        ui.RButton(right.body, "Отправить скример", go, "danger", icon="⚡", height=42).pack(fill="x")
        ui.RButton(right.body, "Проверить на себе", self.show_screamer, "secondary", height=36).pack(fill="x", pady=(8, 0))

    def send_screamer(self, user):
        if self.role() != "FOUNDER":
            self.notify("Скример", "Только Основатель.", "error")
            return
        if not user.get("allow_pranks"):
            self.notify("Скример", "Пользователь не разрешил розыгрыши.", "warning")
            return
        name = user.get("display_name") or user.get("username")

        def work():
            self.db.insert("prank_events", {"target_user_id": user["id"], "created_by": self.uid, "kind": "screamer"})
        self.bg(work, lambda _: (self.log_action("Отправлен скример", "profiles", user["id"]), self.notify("Скример отправлен", f"Получатель: {name}", "success")),
                lambda e: self.notify("Скример", str(e), "error"), bound=False)

    def start_prank_listener(self):
        if self._prank_started or not self.uid:
            return
        self._prank_started = True

        def poll():
            if not (self._alive and self.uid and self._prank_started):
                return

            def work():
                rows = self.db.table("prank_events", "id", {"target_user_id": f"eq.{self.uid}", "consumed_at": "is.null"}, "created_at.asc", 5)
                for e in rows:
                    self.db.update("prank_events", {"id": f"eq.{e['id']}"}, {"consumed_at": datetime.now(timezone.utc).isoformat()})
                return rows
            self.bg(work, lambda rows: rows and self.show_screamer() if self.prof.get("allow_pranks") else None, lambda e: None, bound=False)
            self.after(4000, poll)
        self.after(1500, poll)

    @staticmethod
    def _draw_scare(c, w, h):
        """Тёмная «глючная» картинка с красными глазами — рисуется кодом, без внешних файлов."""
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill="#02050a", outline="")
        for r, col in [(h * .62, "#0a0a12"), (h * .45, "#12080c"), (h * .30, "#1d0a10")]:
            c.create_oval(w / 2 - r, h * .5 - r, w / 2 + r, h * .5 + r, fill=col, outline="")
        for dx in (-.16, .16):
            x, y = w / 2 + w * dx, h * .45
            c.create_oval(x - w * .07, y - h * .06, x + w * .07, y + h * .06, fill="#ff1f3d", outline="#ff6b81", width=2)
            c.create_oval(x - w * .02, y - h * .04, x + w * .02, y + h * .04, fill="#000000", outline="")
        c.create_arc(w * .30, h * .55, w * .70, h * .95, start=200, extent=140, style="arc", outline="#ff1f3d", width=3)
        for i in range(0, w, 14):
            c.create_line(i, 0, i, h, fill="#0b1018")

    def show_screamer(self):
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"{sw}x{sh}+0+0")
        c = tk.Canvas(win, bg="#02050a", highlightthickness=0)
        c.pack(fill="both", expand=True)
        self._draw_scare(c, sw, sh)
        c.create_text(sw / 2, sh * .9, text="RMRP СКРИМЕР", fill="#f4f7fb", font=(FONT, 28, "bold"))
        c.create_text(sw / 2, sh * .95, text="Розыгрыш от Основателя  •  Esc или клик — закрыть", fill="#7894b5", font=(FONT, 12))
        try:
            import winsound
            if self.settings.get("sound_enabled", True):
                import threading
                threading.Thread(target=lambda: [winsound.Beep(f, d) for f, d in ((740, 90), (360, 140), (880, 110))], daemon=True).start()
        except Exception:  # noqa: BLE001
            pass

        def flash(i=0):
            if i < 8 and win.winfo_exists():
                c.configure(bg="#1b0710" if i % 2 else "#02050a")
                win.after(80, lambda: flash(i + 1))
        flash()
        for seq in ("<Escape>", "<Button-1>"):
            win.bind(seq, lambda e: win.destroy())
        win.focus_force()
        win.after(5000, lambda: win.winfo_exists() and win.destroy())
