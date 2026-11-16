"""Админ-панель, жалобы, скример."""
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import (ACCENT, ACCENT_TXT, APP_NAME, BG, BORDER, DANGER, DIFFICULTY_RU, FONT, MUTED, ONLINE_WINDOW_SEC, ORANGE, PANEL, PANEL2, PURPLE,
                     ROLE_ORDER, ROLE_SHORT, STATUS_RU, STATUS_VALUES, SUCCESS, TEAL, TEXT, TEXT2, WARNING, role_color, role_label)

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
        h = height or (150 + sum((200 if k == "bigmulti" else 88) if k in ("multi", "bigmulti") else 66 for _, _, k, *_ in fields))
        win = ui.modal(self, title, 560, min(h, 720), PANEL)
        ui.lbl(win, title, 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(20, 2))
        getters = {}
        for fld in fields:
            key, label, kind, extra = fld[:4]
            default_idx = fld[4] if len(fld) > 4 else 0
            ui.lbl(win, label, 9, False, TEXT2, bg=PANEL).pack(anchor="w", padx=24, pady=(8, 3))
            if kind in ("multi", "bigmulti"):
                t = tk.Text(win, height=12 if kind == "bigmulti" else 4, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=(FONT, 10), padx=10, pady=8,
                            highlightthickness=1, highlightbackground=ui.BORDER2, highlightcolor=ACCENT)
                t.pack(fill="x", padx=24)
                if extra:
                    t.insert("1.0", extra)
                getters[key] = lambda t=t: t.get("1.0", "end").strip()
            elif kind == "choice":
                var = tk.StringVar()
                cb = ttk.Combobox(win, textvariable=var, values=[l for _, l in extra], state="readonly")
                cb.pack(fill="x", padx=24, ipady=3)
                cb.current(default_idx)
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
        self._admin_stats(self.content)
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

    def _admin_stats(self, parent):
        """Сводка: цифры по пользователям и жалобам, популярные запросы. Каждый блок грузится отдельно и не ломает страницу."""
        box = tk.Frame(parent, bg=BG)
        box.pack(fill="x", pady=(4, 0))
        for i in range(4):
            box.grid_columnconfigure(i, weight=1, uniform="stat")
        loader = ui.lbl(box, "Загружаю сводку…", 9, False, MUTED)
        loader.grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=6)

        def work():
            data = {"users": self.db.table_all("profiles", "id,created_at,last_seen_at,status", None, "created_at.asc", 5000)}
            for key, table, flt in (("new_reports", "reports", {"status": "eq.NEW"}), ):
                try:
                    data[key] = self.db.table_all(table, "id", flt, None, 5000)
                except ApiError:
                    data[key] = None
            for key, table in (("searches", "search_history"), ("questions", "ai_history")):
                try:
                    data[key] = self.db.table(table, "*", None, "created_at.desc", 400)
                except ApiError:
                    data[key] = None  # нет политики: выполните migration_v2_3.sql
            return data

        def tile(col, value, label, color, goto=None):
            c = ui.Card(box, bg=ui.mix(PANEL, color, .08), border=ui.mix(PANEL, color, .35), radius=12, pad=14, height=84)
            c.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)
            ui.lbl(c.body, str(value), 20, True, color).pack(anchor="w")
            ui.lbl(c.body, label, 8, False, MUTED).pack(anchor="w")
            if goto:
                c.make_clickable(lambda: self.navigate("admin", section=goto))

        def top_card(row, col, title, items, empty):
            c = ui.Card(box, radius=12, pad=14)
            c.grid(row=row, column=col, columnspan=2, sticky="nsew", padx=6, pady=6)
            ui.lbl(c.body, title, 10, True).pack(anchor="w")
            if not items:
                ui.lbl(c.body, empty, 9, False, MUTED, wraplength=380).pack(anchor="w", pady=(4, 0))
            for text, n in items:
                line = tk.Frame(c.body, bg=PANEL)
                line.pack(fill="x", pady=1)
                ui.lbl(line, text, 9, False, TEXT2).pack(side="left")
                ui.lbl(line, f"×{n}", 9, True, ACCENT_TXT).pack(side="right")

        def done(d):
            loader.destroy()
            users = d["users"]
            online = sum(1 for u in users if u.get("status") == "ACTIVE" and T.is_online(u.get("last_seen_at"), ONLINE_WINDOW_SEC))
            tile(0, online, "онлайн сейчас", SUCCESS, "users")
            tile(1, len(users), "всего пользователей", ACCENT, "users")
            tile(2, T.count_since(users, "created_at", 7), "новых за 7 дней", TEAL, "users")
            nr = d["new_reports"]
            tile(3, "—" if nr is None else len(nr), "новых жалоб", WARNING if nr else MUTED, "reports")
            miss = "Нет данных: выполните migration_v2_3.sql в Supabase."
            top_card(1, 0, "Частые поисковые запросы", T.top_items(d["searches"] or [], "query"), miss if d["searches"] is None else "Пока нет запросов.")
            top_card(1, 2, "Частые вопросы к ИИ", T.top_items(d["questions"] or [], "question"), miss if d["questions"] is None else "Пока нет вопросов.")
        self.bg(work, done, lambda e: loader.configure(text=f"Сводка недоступна: {e}"))

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
        role_opts = [("", "Все роли")] + [(r, role_label(r)) for r in ROLE_ORDER]
        stat_opts = [("", False, "Любой статус"), ("ACTIVE", True, "Онлайн"), ("ACTIVE", False, "Активные"), ("BLOCKED", False, "Заблокированные"), ("BANNED", False, "Забаненные")]
        role_var, stat_var = tk.StringVar(), tk.StringVar()
        stat_cb = ttk.Combobox(bar, textvariable=stat_var, values=[o[2] for o in stat_opts], state="readonly", width=16)
        stat_cb.pack(side="right", padx=(8, 0))
        stat_cb.current(0)
        role_cb = ttk.Combobox(bar, textvariable=role_var, values=[o[1] for o in role_opts], state="readonly", width=16)
        role_cb.pack(side="right", padx=(8, 0))
        role_cb.current(0)
        cols = ("id", "name", "role", "status", "premium")
        tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="extended")
        for c, t, w in [("id", "ID", 90), ("name", "Имя", 200), ("role", "Роль", 150), ("status", "Статус", 130), ("premium", "Premium", 80)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="w")
        for _r in ROLE_ORDER:
            tree.tag_configure(f"role_{_r}", foreground=role_color(_r))
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
            st_code, st_online = stat_opts[max(stat_cb.current(), 0)][:2]
            rows = T.filter_users(list(state["rows"].values()), q, role_opts[max(role_cb.current(), 0)][0], st_code, st_online, ONLINE_WINDOW_SEC)
            for r in rows:
                online = T.is_online(r.get("last_seen_at"), ONLINE_WINDOW_SEC)
                tags = (f"role_{r.get('role')}",)  # имя роли и строка красятся цветом роли; статус виден в колонке
                if r.get("status") != "ACTIVE":
                    tags = ("banned",)
                status = ("● Online" if online else "○ Offline") if r.get("status") == "ACTIVE" else STATUS_RU.get(r["status"], r["status"])
                tree.insert("", "end", iid=r["id"], tags=tags, values=(str(r["id"])[:8], r.get("display_name") or r.get("username"), ROLE_SHORT.get(r["role"], r["role"]),
                                                                      status, "Да" if r.get("premium") else "Нет"))
                shown += 1
            total.configure(text=f"Всего пользователей: {len(state['rows'])}" + (f" (показано {shown})" if shown != len(state["rows"]) else ""))
        search.var.trace_add("write", render)
        role_cb.bind("<<ComboboxSelected>>", render)
        stat_cb.bind("<<ComboboxSelected>>", render)

        def selected():
            s = tree.selection()
            return state["rows"].get(s[0]) if len(s) == 1 else None

        def on_select(_e=None):
            u = selected()
            for c in info.winfo_children():
                c.destroy()
            if len(tree.selection()) > 1:
                bulk_panel([state["rows"][i] for i in tree.selection() if i in state["rows"]])
                return
            if not u:
                ui.lbl(info, "Выберите пользователя в таблице.\nCtrl или Shift: выбрать несколько для массовых действий.", 10, False, MUTED, wraplength=250).pack(pady=20)
                return
            online = T.is_online(u.get("last_seen_at"), ONLINE_WINDOW_SEC)
            ui.Avatar(info, u.get("display_name") or u.get("username"), 64, u.get("avatar_url") or "", online=online).pack(anchor="w")
            ui.lbl(info, u.get("display_name") or u.get("username"), 13, True).pack(anchor="w", pady=(8, 0))
            ui.lbl(info, f"@{u.get('username')}  •  {role_label(u['role'])}", 9, True, role_color(u["role"])).pack(anchor="w")
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

        def protect_reason(u):
            if u["id"] == self.uid and self.role() == "FOUNDER":
                return "Основатель не меняет свой аккаунт из клиента."
            if u["role"] == "FOUNDER" and self.role() != "FOUNDER":
                return "Только Основатель управляет аккаунтом Основателя."
            if u["role"] == "ADMIN" and self.role() != "FOUNDER" and u["id"] != self.uid:
                return "Администраторов может менять только Основатель."
            return None

        def protected(u):
            why = protect_reason(u)
            if why:
                self.notify(APP_NAME, why, "warning" if "не меняет" in why else "error")
            return bool(why)

        def bulk_panel(users):
            ui.lbl(info, f"Выбрано: {len(users)}", 13, True).pack(anchor="w", pady=(4, 2))
            ui.lbl(info, "Свой аккаунт, Основатель и администраторы (если вы не Основатель) пропускаются.", 8, False, MUTED, wraplength=250).pack(anchor="w", pady=(0, 10))
            for text, style, values, label in [("Выдать Premium", "secondary", {"premium": True}, "Premium выдан"), ("Снять Premium", "secondary", {"premium": False}, "Premium снят"),
                                                ("Заблокировать", "danger", {"status": "BLOCKED"}, "Заблокированы"), ("Разблокировать", "secondary", {"status": "ACTIVE"}, "Разблокированы")]:
                ui.RButton(info, text, lambda v=values, l=label: bulk(users, v, l), style, height=34, size=9).pack(fill="x", pady=3)

        def bulk(users, values, label):
            ok = [u for u in users if u["id"] != self.uid and not protect_reason(u)]
            skipped = len(users) - len(ok)
            if not ok:
                self.notify("Массовое действие", "Нет пользователей, которых можно изменить.", "warning")
                return
            if not ui.confirm(self, f"{label}?", f"Будет изменено пользователей: {len(ok)}" + (f" (пропущено: {skipped})." if skipped else "."), "Применить", "status" in values and values["status"] != "ACTIVE"):
                return

            def work():
                return self.db.update("profiles", {"id": T.in_filter(u["id"] for u in ok)}, values)
            self.bg(work, lambda _: (self.log_action(f"Массово: {label}", "profiles", None, {"count": len(ok), **values}), reload(),
                                     self.notify(label, f"Изменено: {len(ok)}" + (f", пропущено: {skipped}" if skipped else ""), "success")),
                    lambda e: self.notify("Массовое действие", str(e), "error"), bound=False)

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
            ui.lbl(c.body, role_label(role), 11, True, role_color(role)).pack(anchor="w")
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
        is_admin = self.is_staff("ADMIN")
        state = {"rows": [], "status": "", "sel": set()}
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        ui.RButton(bar, "Новая жалоба", self.create_report, "primary", icon="＋", height=36).pack(side="left")
        if staff and is_admin:
            ui.RButton(bar, "Удалить закрытые", self.delete_closed_reports, "ghost", icon="🗑", height=36).pack(side="left", padx=8)
        search = None
        if staff:
            search = ui.Field(bar, "Поиск по теме, тексту, автору…", height=36, icon="⌕")
            search.pack(side="right", fill="x", expand=True, padx=(12, 0))
            tabs = ui.PillTabs(parent, [("", "Все"), ("NEW", "Новые"), ("IN_PROGRESS", "В работе"), ("RESOLVED", "Решены"), ("REJECTED", "Отклонены")],
                               lambda k: (state.update(status=k, sel=set()), render()))
            tabs.pack(anchor="w", pady=(0, 8))
        bulk = tk.Frame(parent, bg=BG)  # панель массовых действий, видна при выборе
        bulk_lbl = ui.lbl(bulk, "", 10, True)
        bulk_lbl.pack(side="left", padx=(0, 12))
        lst = ui.ScrollFrame(parent, bg=BG)
        lst.pack(fill="both", expand=True)
        res = lst.body
        loader = self.loading(res)
        sel = "id,reason,description,status,created_at,author:profiles!reports_author_id_fkey(username),target:profiles!reports_target_user_id_fkey(username)"

        def work():
            flt = None if staff else {"author_id": f"eq.{self.uid}"}
            try:
                return self.db.table("reports", sel, flt, "created_at.desc", 500)
            except ApiError:
                return self.db.table("reports", "id,reason,description,status,created_at", flt, "created_at.desc", 500)

        def shown():
            return T.filter_reports(state["rows"], search.get() if search else "", state["status"])

        def refresh_bulk():
            n = len(state["sel"])
            if not staff or not n:
                bulk.pack_forget()
                return
            bulk_lbl.configure(text=f"Выбрано: {n}")
            bulk.pack(fill="x", pady=(0, 8), before=lst)

        def set_many(status):
            ids = sorted(state["sel"])
            vals = {"status": status}
            if status in ("RESOLVED", "REJECTED"):
                vals["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self.bg(lambda: self.db.update("reports", {"id": T.in_filter(ids)}, vals),
                    lambda _: (self.log_action("Массово: статус жалоб", "reports", None, {"count": len(ids), "status": status}),
                               self.notify("Готово", f"Обновлено жалоб: {len(ids)}", "success", 2400), self._after_change()), bound=False)

        def delete_many():
            ids = sorted(state["sel"])
            if not is_admin or not ids:
                return
            if not ui.confirm(self, "Удалить выбранные жалобы?", f"Будет удалено жалоб: {len(ids)}. Это нельзя отменить.", "Удалить", True):
                return
            self.bg(lambda: self.db.delete("reports", {"id": T.in_filter(ids)}, expect=True),
                    lambda _: (self.log_action("Массово удалены жалобы", "reports", None, {"count": len(ids)}),
                               self.notify("Жалобы удалены", f"Удалено: {len(ids)}", "success", 2400), self._after_change()), bound=False)

        def pick_all():
            state["sel"] = {r["id"] for r in shown()}
            render()

        for txt, style, fn in [("В работу", "secondary", lambda: set_many("IN_PROGRESS")), ("Решены", "success", lambda: set_many("RESOLVED")),
                               ("Отклонить", "ghost", lambda: set_many("REJECTED"))]:
            ui.RButton(bulk, txt, fn, style, height=30, size=9, padx=12).pack(side="left", padx=(0, 6))
        if is_admin:
            ui.RButton(bulk, "Удалить", delete_many, "danger", icon="🗑", height=30, size=9, padx=12).pack(side="left", padx=(0, 6))
        ui.RButton(bulk, "Снять выбор", lambda: (state["sel"].clear(), render()), "ghost", height=30, size=9, padx=12).pack(side="left")

        def toggle(rid, var):
            (state["sel"].add if var.get() else state["sel"].discard)(rid)
            refresh_bulk()

        def render(*_):
            for w in res.winfo_children():
                w.destroy()
            rows = shown()
            refresh_bulk()
            if not rows:
                self.card_message(res, "Жалоб нет" if not state["rows"] else "Ничего не найдено", "Здесь появятся обращения." if not state["rows"] else "Измените поиск или фильтр.")
                return
            if staff:
                ui.RButton(res, f"Выбрать все ({len(rows)})", pick_all, "ghost", height=28, size=9, padx=10).pack(anchor="w", pady=(0, 2))
            for r in rows:
                c = ui.Card(res, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                head = tk.Frame(c.body, bg=PANEL)
                head.pack(fill="x")
                if staff:
                    var = tk.BooleanVar(value=r["id"] in state["sel"])
                    tk.Checkbutton(head, variable=var, command=lambda rid=r["id"], v=var: toggle(rid, v), bg=PANEL, activebackground=PANEL, selectcolor=PANEL2,
                                   bd=0, highlightthickness=0).pack(side="left", padx=(0, 6))
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
                    if is_admin:
                        ui.RButton(row, "Удалить", lambda r=r: self.delete_report(r), "danger", icon="🗑", height=30, size=9, padx=12).pack(side="left", padx=(12, 0))

        def done(rows):
            loader.destroy()
            state["rows"] = rows
            render()
        if search:
            search.var.trace_add("write", lambda *a: render())
        self.bg(work, done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _set_report(self, rid, status):
        vals = {"status": status}
        if status in ("RESOLVED", "REJECTED"):
            vals["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self.bg(lambda: self.db.update("reports", {"id": f"eq.{rid}"}, vals),
                lambda _: (self.log_action("Статус жалобы", "reports", rid, vals), self.navigate(self.page, **self.page_args)), bound=False)

    def _after_change(self):
        self.navigate(self.page, **self.page_args)

    def delete_report(self, r):
        if not self.is_staff("ADMIN"):
            return
        if not ui.confirm(self, "Удалить жалобу?", f"«{r.get('reason')}» будет удалена безвозвратно.", "Удалить", True):
            return
        self.bg(lambda: self.db.delete("reports", {"id": f"eq.{r['id']}"}, expect=True),
                lambda _: (self.log_action("Удалена жалоба", "reports", r["id"], {"reason": r.get("reason")}), self.notify("Жалоба удалена", "", "success", 2200), self._after_change()),
                bound=False)

    def delete_closed_reports(self):
        if not self.is_staff("ADMIN"):
            return
        if not ui.confirm(self, "Удалить закрытые жалобы?", "Все жалобы со статусами «Решена» и «Отклонена» будут удалены безвозвратно.", "Удалить", True):
            return

        def work():
            return self.db.delete("reports", {"status": "in.(RESOLVED,REJECTED)"})

        def done(rows):
            n = len(rows) if isinstance(rows, list) else 0
            self.log_action("Удалены закрытые жалобы", "reports", None, {"count": n})
            self.notify("Готово", f"Удалено жалоб: {n}" if n else "Закрытых жалоб нет.", "success", 2600)
            self._after_change()
        self.bg(work, done, bound=False)

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
                ui.RButton(row, "Удалить", lambda t=t: self.delete_test(t), "danger", height=30, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Скрыть" if t.get("is_active") else "Показать", lambda t=t: self._toggle_test(t), "secondary", height=30, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Вопросы", lambda t=t: self.questions_dialog(t), "secondary", height=30, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Изменить", lambda t=t: self.edit_test(t), "secondary", height=30, size=9).pack(side="right")
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

    def edit_test(self, t):
        def submit(v):
            if not v["title"]:
                self.notify("Тест", "Введите название.", "warning")
                return False
            vals = {"title": v["title"], "category": v["category"] or "Общее", "description": v["description"], "difficulty": v["difficulty"]}
            self.bg(lambda: self.db.update("tests", {"id": f"eq.{t['id']}"}, vals, expect=True),
                    lambda _: (self.log_action("Изменён тест", "tests", t["id"], {"title": v["title"]}), self.navigate("admin", section="tests")), bound=False)
        diffs = [("EASY", "Лёгкий"), ("MEDIUM", "Средний"), ("HARD", "Сложный")]
        self.form_dialog("Изменить тест", [("title", "Название", "text", t.get("title") or ""), ("category", "Категория", "text", t.get("category") or ""),
                                           ("description", "Описание", "multi", t.get("description") or ""),
                                           ("difficulty", "Сложность", "choice", diffs, [d for d, _ in diffs].index(t.get("difficulty")) if t.get("difficulty") in dict(diffs) else 1)],
                         submit, 500)

    def delete_test(self, t):
        if not ui.confirm(self, "Удалить тест?", f"«{t.get('title')}», все его вопросы и результаты прохождений будут удалены безвозвратно.", "Удалить", True):
            return
        self.bg(lambda: self.db.delete("tests", {"id": f"eq.{t['id']}"}, expect=True),
                lambda _: (self.log_action("Удалён тест", "tests", t["id"], {"title": t.get("title")}), self.notify("Тест удалён", t.get("title") or "", "success", 2200),
                           self.navigate("admin", section="tests")), bound=False)

    def _recount_test(self, test_id):
        cnt = len(self.db.table("questions", "id", {"test_id": f"eq.{test_id}"}))
        self.db.update("tests", {"id": f"eq.{test_id}"}, {"question_count": cnt})

    def questions_dialog(self, t):
        """Список вопросов теста с правкой и удалением."""
        win = ui.modal(self, f"Вопросы: {t.get('title')}", 760, 600, PANEL)
        ui.lbl(win, f"Вопросы теста «{t.get('title')}»", 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(18, 2))
        bar = tk.Frame(win, bg=PANEL)
        bar.pack(fill="x", padx=24, pady=(0, 6))
        ui.RButton(bar, "Добавить вопрос", lambda: (win.destroy(), self.add_question(t["id"])), "primary", icon="＋", height=32, size=9).pack(side="left")
        ui.RButton(bar, "Закрыть", win.destroy, "secondary", height=32, size=9).pack(side="right")
        sf = ui.ScrollFrame(win, bg=PANEL)
        sf.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        loader = self.loading(sf.body)

        def done(rows):
            loader.destroy()
            if not rows:
                ui.lbl(sf.body, "В этом тесте пока нет вопросов.", 10, False, MUTED, bg=PANEL).pack(pady=30)
            for i, q in enumerate(rows, 1):
                c = ui.Card(sf.body, bg=PANEL2, radius=10, pad=12)
                c.pack(fill="x", pady=3, padx=8)
                ui.lbl(c.body, f"{i}. {q['question']}", 10, True, bg=PANEL2, wraplength=620).pack(anchor="w")
                ui.lbl(c.body, f"Правильный ответ: {q.get('correct_answer')}", 8, False, MUTED, bg=PANEL2).pack(anchor="w", pady=(2, 6))
                row = tk.Frame(c.body, bg=PANEL2)
                row.pack(anchor="w")
                ui.RButton(row, "Изменить", lambda q=q: (win.destroy(), self.edit_question(t, q)), "secondary", height=28, size=9).pack(side="left")
                ui.RButton(row, "Удалить", lambda q=q: self._del_question(t, q, win), "danger", height=28, size=9).pack(side="left", padx=6)
        self.bg(lambda: self.db.table("questions", "*", {"test_id": f"eq.{t['id']}"}, "id.asc"), done, lambda e: loader.configure(text=f"Ошибка: {e}"), bound=False)

    def _del_question(self, t, q, win):
        if not ui.confirm(self, "Удалить вопрос?", q["question"][:140], "Удалить", True):
            return

        def work():
            self.db.delete("questions", {"id": f"eq.{q['id']}"}, expect=True)
            self._recount_test(t["id"])

        def done(_):
            self.log_action("Удалён вопрос", "questions", q["id"], {"test": t.get("title")})
            win.destroy()
            self.questions_dialog(t)
        self.bg(work, done, bound=False)

    def edit_question(self, t, q):
        def submit(v):
            if not all(v[k] for k in ("question", "a", "b", "c", "d")):
                self.notify("Вопрос", "Заполните вопрос и все 4 ответа.", "warning")
                return False
            vals = {"question": v["question"], "answer_a": v["a"], "answer_b": v["b"], "answer_c": v["c"], "answer_d": v["d"],
                    "correct_answer": v["correct"], "explanation": v["explanation"] or None}
            self.bg(lambda: self.db.update("questions", {"id": f"eq.{q['id']}"}, vals, expect=True),
                    lambda _: (self.log_action("Изменён вопрос", "questions", q["id"], None), self.notify("Вопрос сохранён", "", "success", 2200), self.questions_dialog(t)), bound=False)
        letters = [(x, x) for x in "ABCD"]
        cur = "ABCD".index(q["correct_answer"]) if q.get("correct_answer") in list("ABCD") else 0
        self.form_dialog("Изменить вопрос", [("question", "Вопрос", "multi", q.get("question") or ""), ("a", "Ответ A", "text", q.get("answer_a") or ""),
                                             ("b", "Ответ B", "text", q.get("answer_b") or ""), ("c", "Ответ C", "text", q.get("answer_c") or ""),
                                             ("d", "Ответ D", "text", q.get("answer_d") or ""), ("correct", "Правильный ответ", "choice", letters, cur),
                                             ("explanation", "Пояснение (необязательно)", "text", q.get("explanation") or "")], submit, 700)

    def add_question(self, test_id=None):
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
                    self._recount_test(v["test"])
                self.bg(work, lambda _: (self.notify("Вопрос добавлен", "", "success"), self.navigate("admin", section="tests")), bound=False)
            ids = [t["id"] for t in tests]
            self.form_dialog("Новый вопрос", [("test", "Тест", "choice", [(t["id"], t["title"]) for t in tests], ids.index(test_id) if test_id in ids else 0), ("question", "Вопрос", "multi", ""),
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
        search = ui.Field(bar, "Поиск закона…", height=36, icon="⌕")
        search.pack(side="right", fill="x", expand=True, padx=(12, 0))
        sf = ui.ScrollFrame(body, bg=BG)
        sf.pack(fill="both", expand=True)
        loader = self.loading(sf.body)
        state = {"rows": []}

        def done(rows):
            loader.destroy()
            state["rows"] = rows
            render()

        def render(*_):
            for w in sf.body.winfo_children():
                w.destroy()
            q = search.get().strip().lower()
            rows = [l for l in state["rows"] if not q or q in " ".join(str(l.get(k) or "") for k in ("name", "short_name", "law_number")).lower()]
            if not rows:
                self.card_message(sf.body, "Ничего не найдено", "Измените запрос.")
            for l in rows:
                c = ui.Card(sf.body, radius=12, pad=14)
                c.pack(fill="x", pady=4)
                row = tk.Frame(c.body, bg=PANEL)
                row.pack(fill="x")
                col = tk.Frame(row, bg=PANEL)
                col.pack(side="left", fill="x", expand=True)
                ui.lbl(col, l.get("short_name") or l["name"], 11, True).pack(anchor="w")
                ui.lbl(col, f"{l['name']}  •  {l.get('law_number') or ''}", 9, False, MUTED, wraplength=640).pack(anchor="w")
                ui.RButton(row, "Удалить", lambda l=l: self.delete_law(l), "danger", height=30, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Статьи", lambda l=l: self.navigate("law", law_id=l["id"]), "secondary", height=30, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Изменить", lambda l=l: self.add_law_dialog(l), "secondary", height=30, size=9).pack(side="right")
        search.var.trace_add("write", render)
        self.bg(lambda: self.db.table("laws", "*", None, "name.asc"), done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def edit_article(self, law, a):
        def submit(v):
            if not v["number"] or not v["content"]:
                self.notify("Статья", "Укажите номер и текст.", "warning")
                return False
            vals = {"article_number": v["number"], "title": v["title"] or None, "chapter": v["chapter"] or None, "content": v["content"]}
            self.bg(lambda: self.db.update("law_articles", {"id": f"eq.{a['id']}"}, vals, expect=True),
                    lambda _: (self.invalidate_laws(), self.log_action("Изменена статья", "law_articles", a["id"], {"law": law.get("short_name"), "article": v["number"]}),
                               self.notify("Статья сохранена", "", "success", 2200), self.navigate("law", law_id=law["id"], article_id=a["id"])), bound=False)
        self.form_dialog("Изменить статью", [("number", "Номер статьи", "text", a.get("article_number") or ""), ("title", "Название", "text", a.get("title") or ""),
                                             ("chapter", "Глава", "text", a.get("chapter") or ""), ("content", "Текст", "bigmulti", a.get("content") or "")], submit, 700)

    def delete_article(self, law, a):
        if not ui.confirm(self, "Удалить статью?", f"Статья {a.get('article_number')}. {a.get('title') or ''} будет удалена безвозвратно. "
                          "Синхронизация с форумом может вернуть её.", "Удалить", True):
            return

        def done(_):
            self.invalidate_laws()
            self.log_action("Удалена статья", "law_articles", a["id"], {"law": law.get("short_name"), "article": a.get("article_number")})
            self.notify("Статья удалена", "", "success", 2200)
            self.navigate("law", law_id=law["id"])
        self.bg(lambda: self.db.delete("law_articles", {"id": f"eq.{a['id']}"}, expect=True), done, bound=False)

    def delete_law(self, law):
        name = law.get("short_name") or law.get("name")
        if not ui.confirm(self, "Удалить закон?", f"«{name}» со всеми статьями, версиями, избранным и историей просмотров будет удалён безвозвратно. "
                          "Повторная синхронизация вернёт закон только если у него есть ссылка на форум.", "Удалить", True):
            return

        def done(_):
            self.invalidate_laws()
            self.log_action("Удалён закон", "laws", law["id"], {"name": name})
            self.notify("Закон удалён", name, "success", 2400)
            self.navigate("admin", section="laws")
        self.bg(lambda: self.db.delete("laws", {"id": f"eq.{law['id']}"}, expect=True), done, bound=False)

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
        bar = tk.Frame(body, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        search = ui.Field(bar, "Поиск: кто, действие, объект…", height=36, icon="⌕")
        search.pack(side="left", fill="x", expand=True)
        total = ui.lbl(bar, "", 9, False, MUTED)
        total.pack(side="right", padx=(10, 0))
        periods = [(0, "За всё время"), (1, "Сегодня"), (7, "7 дней"), (30, "30 дней")]
        per_var, act_var = tk.StringVar(), tk.StringVar()
        per_cb = ttk.Combobox(bar, textvariable=per_var, values=[p[1] for p in periods], state="readonly", width=14)
        per_cb.pack(side="right", padx=(8, 0))
        per_cb.current(0)
        act_cb = ttk.Combobox(bar, textvariable=act_var, values=["Все действия"], state="readonly", width=28)
        act_cb.pack(side="right", padx=(8, 0))
        act_cb.current(0)
        tree = ttk.Treeview(body, columns=("time", "user", "action", "target"), show="headings")
        for c, t, w in [("time", "Время", 150), ("user", "Кто", 150), ("action", "Действие", 280), ("target", "Объект", 240)]:
            tree.heading(c, text=t)
            tree.column(c, width=w)
        tree.pack(fill="both", expand=True)
        state = {"rows": [], "actions": []}

        def render(*_):
            tree.delete(*tree.get_children())
            i = act_cb.current()
            action = state["actions"][i - 1] if i > 0 and i - 1 < len(state["actions"]) else ""
            rows = T.filter_audit(state["rows"], search.get(), action, periods[max(per_cb.current(), 0)][0])
            for r in rows:
                tree.insert("", "end", values=(T.fmt_date(r["created_at"], True), (r.get("profiles") or {}).get("username") or "—", r["action"],
                                               f"{r.get('target_type') or ''} {r.get('target_id') or ''}".strip()))
            total.configure(text=f"Записей: {len(rows)} из {len(state['rows'])}")

        def done(rows):
            state["rows"] = rows
            state["actions"] = sorted({r["action"] for r in rows if r.get("action")})
            act_cb.configure(values=["Все действия"] + state["actions"])
            act_cb.current(0)
            render()
        search.var.trace_add("write", render)
        per_cb.bind("<<ComboboxSelected>>", render)
        act_cb.bind("<<ComboboxSelected>>", render)
        self.bg(lambda: self.db.table("audit_logs", "created_at,action,target_type,target_id,profiles(username)", None, "created_at.desc", 1000), done,
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
