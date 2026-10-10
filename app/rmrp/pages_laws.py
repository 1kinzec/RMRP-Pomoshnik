"""Законодательство: список законов, просмотр с главами, поиск, избранное, синхронизация с форумом RMRP."""
import re
import threading
import tkinter as tk
import urllib.request
import webbrowser
from datetime import datetime, timezone
from tkinter import ttk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import (ACCENT, ACCENT_HI, ACCENT_LO, ACCENT_TXT, APP_NAME, BG, BORDER, BORDER2, FONT, LAW_SOURCES, MUTED, PANEL, PANEL2,
                     PANEL3, SUCCESS, TEXT, TEXT2, WARNING)

ART_COLS = "id,law_id,article_number,title,chapter,position"
ART_COLS_OLD = "id,law_id,article_number,title"


class LawPages:
    # ================================================================== данные
    def get_laws(self, force=False):
        """Законы со статистикой (глав/статей). Кешируется на сессию."""
        if getattr(self, "_laws_cache", None) and not force:
            return self._laws_cache
        laws = self.db.table("laws", "id,name,short_name,law_number,description,source_url,is_active,created_at,updated_at",
                             {"is_active": "eq.true"}, "name.asc")
        stats = {}
        try:
            for r in self.db.table("law_stats", "law_id,articles,chapters"):
                stats[r["law_id"]] = r
        except ApiError:
            pass
        for l in laws:
            st = stats.get(l["id"], {})
            l["articles"], l["chapters"] = st.get("articles"), st.get("chapters")
        self._laws_cache = laws
        return laws

    def law_map(self):
        if getattr(self, "_law_map", None) is None or not getattr(self, "_laws_cache", None):
            self._law_map = {l["id"]: l for l in self.get_laws()}
        return self._law_map

    def invalidate_laws(self):
        self._laws_cache = None
        self._law_map = None

    def fetch_articles_meta(self, law_id):
        flt = {"law_id": f"eq.{law_id}"}
        try:
            rows = self.db.table_all("law_articles", ART_COLS, flt, "id.asc")
        except ApiError:
            rows = self.db.table_all("law_articles", ART_COLS_OLD, flt, "id.asc")
        return sorted(rows, key=T.article_sort_key)

    # ================================================================== поиск (общий для страницы, оверлея и помощника)
    def search_articles(self, query, limit=30):
        lmap = self.law_map()
        sel = "id,law_id,article_number,title,content"
        rows, terms = [], []
        ref = T.parse_article_ref(query)
        if ref:
            num, law_hint = ref
            rows = self.db.table("law_articles", sel, {"article_number": f"eq.{num}"}, "law_id.asc", 60)
            if law_hint:
                hinted = [r for r in rows if lmap.get(r["law_id"], {}).get("law_number") == law_hint]
                rows = hinted or rows
        if not rows:
            terms = T.query_terms(query)
            if not terms:
                terms = [w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{2,}", query)][:4]
            seen = {}
            for t in terms[:3]:
                for r in self.db.table("law_articles", sel, {"or": T.or_filter([t])}, None, 120):
                    seen[r["id"]] = r
            rows = list(seen.values())
            ranked = T.rank_articles(rows, terms, query)
        else:
            ranked = [(100.0, r) for r in sorted(rows, key=lambda r: (r["law_id"], T.natural_key(r["article_number"])))]
        out = []
        for score, r in ranked[:limit]:
            law = lmap.get(r["law_id"], {})
            out.append(dict(r, score=score, law_short=law.get("short_name") or law.get("name") or "Закон", law_number=law.get("law_number"),
                            terms=terms, snippet=T.make_snippet(r.get("content"), terms)))
        return out

    # ================================================================== список законов
    def page_laws(self):
        self.set_header("Законодательство", "Актуальные законы и кодексы RMRP")
        wrap = self.content
        bar = tk.Frame(wrap, bg=BG)
        bar.pack(fill="x", pady=(4, 12))
        search = ui.Field(bar, "Поиск по законам…", height=40, icon="⌕", on_return=lambda: render())
        search.pack(side="left", fill="x", expand=True)
        if self.is_staff("ADMIN"):
            ui.RButton(bar, "Добавить закон", self.add_law_dialog, "secondary", icon="＋", height=40).pack(side="right", padx=(8, 0))
            ui.RButton(bar, "Синхронизировать RMRP", self.sync_laws, "outline", icon="⟳", height=40).pack(side="right", padx=(8, 0))
        sf = ui.ScrollFrame(wrap, bg=BG)
        sf.pack(fill="both", expand=True)
        grid = sf.body
        foot = tk.Frame(wrap, bg=BG)
        foot.pack(fill="x", pady=(8, 0))
        count_lbl = ui.lbl(foot, "", 12, True)
        count_lbl.pack(side="left")
        ui.lbl(foot, "Сортировка:", 9, False, MUTED).pack(side="right", padx=(8, 0))
        sort_var = tk.StringVar(value="По названию")
        cb = ttk.Combobox(foot, textvariable=sort_var, values=["По названию", "По числу статей", "По обновлению"], state="readonly", width=18)
        cb.pack(side="right")
        state = {"laws": []}

        def render(_e=None):
            for c in grid.winfo_children():
                c.destroy()
            q = search.get().lower()
            laws = [l for l in state["laws"] if not q or q in (l.get("name") or "").lower() or q in (l.get("short_name") or "").lower()
                    or q in (l.get("law_number") or "").lower()]
            mode = sort_var.get()
            if mode == "По числу статей":
                laws.sort(key=lambda l: -(l.get("articles") or 0))
            elif mode == "По обновлению":
                laws.sort(key=lambda l: l.get("updated_at") or "", reverse=True)
            else:
                laws.sort(key=lambda l: (l.get("short_name") or l.get("name") or "").lower())
            count_lbl.configure(text=f"Все законы ({len(laws)})")
            if not laws:
                self.card_message(grid, "Законов не найдено", "Администратор может загрузить их кнопкой «Синхронизировать RMRP».")
                return
            grid.grid_columnconfigure(0, weight=1, uniform="l")
            grid.grid_columnconfigure(1, weight=1, uniform="l")
            for i, law in enumerate(laws):
                self._law_card(grid, law).grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0, 7) if i % 2 == 0 else (7, 0), pady=7)

        cb.bind("<<ComboboxSelected>>", render)
        search.var.trace_add("write", lambda *a: render())
        loader = self.loading(grid)

        def done(laws):
            state["laws"] = laws
            loader.destroy()
            render()
        self.bg(lambda: self.get_laws(force=True), done, lambda e: (loader.configure(text=f"Не удалось загрузить: {e}")))

    def _law_card(self, parent, law):
        card = ui.Card(parent, radius=14, pad=16, height=150)
        row = tk.Frame(card.body, bg=PANEL)
        row.pack(fill="x")
        logo = ui.load_image("rmrp.png", (40, 40))
        if logo:
            tk.Label(row, image=logo, bg=PANEL).pack(side="left")
        col = tk.Frame(row, bg=PANEL)
        col.pack(side="left", padx=12, fill="x", expand=True)
        ui.lbl(col, law.get("short_name") or law.get("name"), 13, True).pack(anchor="w")
        ui.lbl(col, law.get("name") or "", 9, False, TEXT2, wraplength=330, justify="left").pack(anchor="w")
        stats = []
        if law.get("chapters"):
            stats.append(f"Глав: {law['chapters']}")
        if law.get("articles") is not None:
            stats.append(f"Статей: {law['articles']}")
        ui.lbl(card.body, "    ".join(stats) if stats else (law.get("law_number") or ""), 9, False, MUTED).pack(anchor="w", pady=(10, 8))
        ui.RButton(card.body, "Открыть", lambda: self.navigate("law", law_id=law["id"]), "outline", icon="→", height=34).pack(fill="x", side="bottom")
        card.make_clickable(lambda: self.navigate("law", law_id=law["id"]))
        return card

    # ================================================================== просмотр закона
    def page_law(self, law_id, article_id=None, highlight=None):
        self.set_header("Законодательство", "")
        wrap = self.content
        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x", pady=(0, 6))
        ui.RButton(top, "Назад", lambda: self.navigate("laws"), "ghost", icon="←", height=34).pack(side="left")
        title_lbl = ui.lbl(top, "", 16, True)
        title_lbl.pack(side="left", padx=14)
        body = tk.Frame(wrap, bg=BG)
        state = {"law": None, "arts": [], "tab": "content", "article_id": article_id}
        tabs_holder = tk.Frame(wrap, bg=BG)
        tabs_holder.pack(fill="x")
        body.pack(fill="both", expand=True, pady=(8, 0))
        loader = self.loading(body)

        def work():
            law = (self.db.table("laws", "*", {"id": f"eq.{law_id}"}) or [None])[0]
            if not law:
                raise RuntimeError("Закон не найден.")
            return law, self.fetch_articles_meta(law_id)

        def done(res):
            loader.destroy()
            state["law"], state["arts"] = res
            title_lbl.configure(text=state["law"].get("short_name") or state["law"].get("name"))
            ui.UnderTabs(tabs_holder, [("content", "Содержание"), ("about", "О законе"), ("versions", "Версии")],
                         lambda k: show_tab(k)).pack(anchor="w")
            show_tab("content")

        def show_tab(tab):
            state["tab"] = tab
            for c in body.winfo_children():
                c.destroy()
            {"content": self._law_content, "about": self._law_about, "versions": self._law_versions}[tab](body, state, highlight)

        self.bg(work, done, lambda e: (loader.configure(text=f"Ошибка: {e}")))

    # -------------------------------------------------- вкладка «Содержание»
    def _law_content(self, body, state, highlight):
        law, arts = state["law"], state["arts"]
        if not arts:
            self.card_message(body, "В этом законе пока нет статей", "Администратор может загрузить их синхронизацией с форумом RMRP.")
            return
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        left = ui.Card(body, radius=12, pad=10, height=100)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left.configure(width=320)
        left.grid_propagate(False)
        right = ui.Card(body, radius=12, pad=16, height=100)
        right.grid(row=0, column=1, sticky="nsew")

        # ---- левая панель: фильтр + главы
        flt = ui.Field(left.body, "Статья или слово…", height=34, outer=PANEL, icon="⌕")
        flt.pack(fill="x", pady=(0, 8))
        listbox = ui.ScrollFrame(left.body, bg=PANEL)
        listbox.pack(fill="both", expand=True)
        lst = listbox.body
        chapters = {}
        for a in arts:
            chapters.setdefault(a.get("chapter") or "Статьи", []).append(a)
        chapter_names = sorted(chapters, key=T.chapter_sort_key) if any(a.get("chapter") for a in arts) else list(chapters)
        expanded = set()
        rows = {}
        sel = {"id": None}

        def mark(aid):
            sel["id"] = aid
            for k, lab in rows.items():
                try:
                    lab.configure(bg=ui.mix(PANEL, ACCENT, .28) if k == aid else PANEL, fg="#ffffff" if k == aid else TEXT2)
                except tk.TclError:
                    pass

        def art_row(parent, a):
            txt = f"ст. {a['article_number']}   {a.get('title') or ''}"
            lab = tk.Label(parent, text=txt if len(txt) < 48 else txt[:46] + "…", font=(FONT, 9), fg=TEXT2, bg=PANEL, anchor="w", padx=10, pady=5,
                           cursor="hand2")
            lab.pack(fill="x")
            lab.bind("<Button-1>", lambda e, a=a: open_article(a["id"]))
            lab.bind("<Enter>", lambda e, l=lab, a=a: l.configure(bg=ui.mix(PANEL, ACCENT, .15)) if sel["id"] != a["id"] else None)
            lab.bind("<Leave>", lambda e, l=lab, a=a: l.configure(bg=PANEL) if sel["id"] != a["id"] else None)
            rows[a["id"]] = lab

        def build_list():
            for c in lst.winfo_children():
                c.destroy()
            rows.clear()
            q = flt.get().lower()
            if q:
                hits = [a for a in arts if q in str(a["article_number"]).lower() or q in (a.get("title") or "").lower()][:120]
                if not hits:
                    ui.lbl(lst, "Ничего не найдено", 9, False, MUTED).pack(pady=14)
                for a in hits:
                    art_row(lst, a)
            else:
                for name in chapter_names:
                    head = tk.Frame(lst, bg=PANEL, cursor="hand2")
                    head.pack(fill="x", pady=(4, 0))
                    is_open = name in expanded
                    txt = ("▾ " if is_open else "▸ ") + name
                    lab = tk.Label(head, text=txt if len(txt) < 50 else txt[:48] + "…", font=(FONT, 9, "bold"), fg=ACCENT_TXT if is_open else TEXT,
                                   bg=PANEL, anchor="w", padx=10, pady=7, cursor="hand2", wraplength=270, justify="left")
                    lab.pack(fill="x")
                    lab.bind("<Button-1>", lambda e, n=name: toggle(n))
                    if is_open:
                        for a in chapters[name]:
                            art_row(lst, a)
            mark(sel["id"])

        def toggle(name):
            expanded.symmetric_difference_update({name})
            build_list()
        flt.var.trace_add("write", lambda *a: build_list())

        # ---- правая панель: статья
        head = tk.Frame(right.body, bg=PANEL)
        head.pack(fill="x")
        title = tk.Label(head, text="Выберите статью слева", font=(FONT, 14, "bold"), fg=TEXT, bg=PANEL, anchor="w", justify="left", wraplength=560)
        title.pack(anchor="w")
        meta = tk.Label(head, text="", font=(FONT, 9), fg=MUTED, bg=PANEL, anchor="w")
        meta.pack(anchor="w", pady=(2, 8))
        actions = tk.Frame(right.body, bg=PANEL)
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        tbox = tk.Frame(right.body, bg=PANEL)
        tbox.pack(fill="both", expand=True)
        txt = tk.Text(tbox, bg=PANEL, fg=TEXT, font=(FONT, 11), wrap="word", relief="flat", bd=0, highlightthickness=0, padx=2, pady=4,
                      spacing1=2, spacing3=6, insertbackground=TEXT, selectbackground=ACCENT_LO, cursor="arrow")
        sb = ttk.Scrollbar(tbox, orient="vertical", style="Dark.Vertical.TScrollbar", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.tag_configure("hl", background=ui.mix(PANEL, WARNING, .45), foreground="#ffffff")
        txt.configure(state="disabled")
        fav_btn = {"b": None, "is": False, "article": None}

        def set_text(content, terms):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", content)
            for t in terms or []:
                start = "1.0"
                while True:
                    pos = txt.search(t, start, stopindex="end", nocase=True)
                    if not pos:
                        break
                    end = f"{pos}+{len(t)}c"
                    txt.tag_add("hl", pos, end)
                    start = end
            txt.configure(state="disabled")
            txt.yview_moveto(0)

        def open_article(aid, terms=None):
            mark(aid)
            title.configure(text="Загрузка…")

            def work():
                a = (self.db.table("law_articles", "*", {"id": f"eq.{aid}"}) or [None])[0]
                fav = False
                if a and not self.guest:
                    fav = bool(self.db.table("favorites", "id", {"user_id": f"eq.{self.uid}", "law_article_id": f"eq.{aid}"}, limit=1))
                    try:
                        self.db.insert("article_views", {"user_id": self.uid, "law_article_id": aid,
                                                         "viewed_at": datetime.now(timezone.utc).isoformat()},
                                       upsert_on="user_id,law_article_id")
                    except ApiError:
                        pass
                return a, fav

            def done(res):
                a, fav = res
                if not a:
                    title.configure(text="Статья не найдена")
                    return
                title.configure(text=f"Статья {a['article_number']}. {a.get('title') or ''}")
                meta.configure(text=f"{law.get('short_name') or law.get('name')}  •  {a.get('chapter') or ''}".strip(" •"))
                set_text(a.get("content") or "", terms)
                fav_btn["is"], fav_btn["article"] = fav, a
                build_actions(a, fav)
                self.presence_law = f"{law.get('short_name') or law.get('name')} • ст. {a['article_number']}"
                self.update_presence()
                chap = a.get("chapter") or "Статьи"
                if chap in chapters and chap not in expanded and not flt.get():
                    expanded.add(chap)
                    build_list()
            self.bg(work, done, lambda e: title.configure(text=f"Ошибка: {e}"))

        def build_actions(a, fav):
            for c in actions.winfo_children():
                c.destroy()
            b = ui.RButton(actions, "Убрать из избранного" if fav else "Добавить в избранное", lambda: toggle_fav(a), "secondary" if fav else "primary",
                           icon="★", height=36)
            b.pack(side="left")
            ui.RButton(actions, "Копировать", lambda: copy_article(a), "secondary", icon="⧉", height=36).pack(side="left", padx=8)
            ui.RButton(actions, "Спросить помощника", lambda: self.navigate("ai", preset=f"Объясни статью {a['article_number']} {law.get('short_name') or ''}"),
                       "ghost", icon="✦", height=36).pack(side="left")

        def toggle_fav(a):
            if not self.require_login("Избранное"):
                return

            def work():
                if fav_btn["is"]:
                    self.db.delete("favorites", {"user_id": f"eq.{self.uid}", "law_article_id": f"eq.{a['id']}"})
                    return False
                self.db.insert("favorites", {"user_id": self.uid, "law_article_id": a["id"]}, upsert_on="user_id,law_article_id", ignore_duplicates=True)
                return True

            def done(now):
                fav_btn["is"] = now
                build_actions(a, now)
                self.notify("Избранное", "Статья добавлена в избранное." if now else "Статья убрана из избранного.", "success")
            self.bg(work, done)

        def copy_article(a):
            self.clipboard_clear()
            self.clipboard_append(f"{law.get('short_name') or ''} — Статья {a['article_number']}. {a.get('title') or ''}\n\n{a.get('content') or ''}")
            self.notify("Скопировано", "Текст статьи в буфере обмена.", "success", 2200)

        # стартовое состояние: открыть нужную статью или первую главу
        start = state.get("article_id")
        if start:
            target = next((a for a in arts if a["id"] == start), None)
            if target:
                expanded.add(target.get("chapter") or "Статьи")
        elif chapter_names:
            expanded.add(chapter_names[0])
        build_list()
        if start:
            open_article(start, highlight)

    # -------------------------------------------------- вкладки «О законе» и «Версии»
    def _law_about(self, body, state, _hl):
        law, arts = state["law"], state["arts"]
        c = ui.Card(body, radius=12, pad=20)
        c.pack(fill="x")
        chapters = {a.get("chapter") for a in arts if a.get("chapter")}
        rows = [("Название", law.get("name")), ("Номер", law.get("law_number") or "—"), ("Статей", str(len(arts))),
                ("Глав", str(len(chapters)) if chapters else "—"), ("Описание", law.get("description") or "—"),
                ("Обновлён", T.fmt_date(law.get("updated_at"), True))]
        for k, v in rows:
            r = tk.Frame(c.body, bg=PANEL)
            r.pack(fill="x", pady=5)
            ui.lbl(r, k, 9, True, MUTED, width=14).pack(side="left", anchor="n")
            ui.lbl(r, v or "—", 10, False, TEXT, wraplength=720).pack(side="left", anchor="n")
        if law.get("source_url"):
            ui.RButton(c.body, "Открыть тему на форуме RMRP", lambda: webbrowser.open(law["source_url"]), "outline", icon="↗", height=36).pack(anchor="w", pady=(14, 0))

    def _law_versions(self, body, state, _hl):
        law = state["law"]
        loader = self.loading(body)

        def done(rows):
            loader.destroy()
            if not rows:
                self.card_message(body, "История версий пуста", "Запись появится после следующей синхронизации с форумом.")
                return
            for r in rows:
                c = ui.Card(body, radius=10, pad=14)
                c.pack(fill="x", pady=4)
                ui.lbl(c.body, f"Версия {r.get('version')}  •  {T.fmt_date(r.get('created_at'), True)}", 10, True).pack(anchor="w")
                ui.lbl(c.body, r.get("change_description") or "", 9, False, TEXT2, wraplength=800).pack(anchor="w", pady=(3, 0))
        self.bg(lambda: self.db.table("law_versions", "*", {"law_id": f"eq.{law['id']}"}, "created_at.desc", 50), done,
                lambda e: loader.configure(text=f"Ошибка: {e}"))

    # ================================================================== страница «Поиск»
    def page_search(self, q=""):
        self.set_header("Поиск", "По номеру статьи, названию и тексту. Например: «статья 12», «оскорбление», «УК 228»")
        wrap = self.content
        bar = tk.Frame(wrap, bg=BG)
        bar.pack(fill="x", pady=(6, 10))
        field = ui.Field(bar, "Что ищем?", height=44, icon="⌕", on_return=lambda: run())
        field.pack(side="left", fill="x", expand=True)
        go = ui.RButton(bar, "Найти", lambda: run(), height=44, width=110, size=11)
        go.pack(side="left", padx=(10, 0))
        chips = tk.Frame(wrap, bg=BG)
        chips.pack(fill="x", pady=(0, 8))
        out = ui.ScrollFrame(wrap, bg=BG)
        out.pack(fill="both", expand=True)
        res = out.body

        def run(term=None):
            term = term or field.get()
            if not term:
                return
            field.set(term)
            for c in res.winfo_children():
                c.destroy()
            self.loading(res, "Ищу…")
            self.bg(lambda: self._do_search(term), lambda rows: show(rows, term), lambda e: (self._clear(res), self.card_message(res, "Ошибка поиска", str(e))))

        def show(rows, term):
            self._clear(res)
            if not rows:
                self.card_message(res, "Ничего не найдено", "Попробуйте другое слово, номер статьи («статья 12») или часть названия.")
                return
            ui.lbl(res, f"Найдено: {len(rows)} {T.plural(len(rows), 'результат', 'результата', 'результатов')}", 9, False, MUTED).pack(anchor="w", pady=(0, 4))
            for r in rows:
                c = ui.Card(res, radius=12, pad=14)
                c.pack(fill="x", pady=5)
                head = tk.Frame(c.body, bg=PANEL)
                head.pack(fill="x")
                ui.icon_tile(head, "▤", ACCENT, 34, bg=PANEL, radius=8).pack(side="left")
                col = tk.Frame(head, bg=PANEL)
                col.pack(side="left", padx=10, fill="x", expand=True)
                ui.lbl(col, r["law_short"], 9, True, ACCENT_TXT).pack(anchor="w")
                ui.lbl(col, f"Статья {r['article_number']}. {r.get('title') or 'Без названия'}", 11, True, wraplength=640).pack(anchor="w")
                ui.RButton(head, "Открыть", lambda r=r: self.navigate("law", law_id=r["law_id"], article_id=r["id"], highlight=r["terms"]), "outline", height=32,
                           size=9).pack(side="right")
                ui.lbl(c.body, r["snippet"], 9, False, TEXT2, wraplength=820).pack(anchor="w", pady=(8, 0))
                c.make_clickable(lambda r=r: self.navigate("law", law_id=r["law_id"], article_id=r["id"], highlight=r["terms"]))

        if not self.guest:
            def hist_done(rows):
                seen = []
                for r in rows:
                    if r["query"] not in seen:
                        seen.append(r["query"])
                for qv in seen[:6]:
                    b = ui.RButton(chips, qv[:28], lambda qv=qv: run(qv), "secondary", height=28, size=8, padx=12)
                    b.pack(side="left", padx=(0, 6))
            self.bg(lambda: self.db.table("search_history", "query", {"user_id": f"eq.{self.uid}"}, "created_at.desc", 20), hist_done, lambda e: None)
        if q:
            self.after(50, lambda: run(q))
        field.focus_entry()

    def _do_search(self, term):
        rows = self.search_articles(term, 40)
        if not self.guest:
            try:
                self.db.insert("search_history", {"user_id": self.uid, "query": term[:200]})
            except ApiError:
                pass
        return rows

    @staticmethod
    def _clear(frame):
        for c in frame.winfo_children():
            c.destroy()

    # ================================================================== избранное
    def page_favorites(self):
        self.set_header("Избранное", "Статьи, которые вы сохранили")
        res = self.scroll()
        loader = self.loading(res)

        def work():
            return self.db.table("favorites", "id,created_at,law_articles(id,law_id,article_number,title,laws(short_name))",
                                 {"user_id": f"eq.{self.uid}"}, "created_at.desc", 200)

        def done(rows):
            loader.destroy()
            rows = [r for r in rows if r.get("law_articles")]
            if not rows:
                self.card_message(res, "Избранное пусто", "Откройте статью и нажмите «Добавить в избранное».")
                return
            for r in rows:
                a = r["law_articles"]
                c = ui.Card(res, radius=12, pad=14)
                c.pack(fill="x", pady=5)
                row = tk.Frame(c.body, bg=PANEL)
                row.pack(fill="x")
                ui.icon_tile(row, "★", WARNING, 36, bg=PANEL, radius=9).pack(side="left")
                col = tk.Frame(row, bg=PANEL)
                col.pack(side="left", padx=12, fill="x", expand=True)
                ui.lbl(col, (a.get("laws") or {}).get("short_name") or "Закон", 9, True, ACCENT_TXT).pack(anchor="w")
                ui.lbl(col, f"Статья {a['article_number']}. {a.get('title') or ''}", 11, True, wraplength=620).pack(anchor="w")
                ui.RButton(row, "Убрать", lambda rid=r["id"], card=c: self._remove_fav(rid, card), "ghost", height=32, size=9).pack(side="right", padx=(6, 0))
                ui.RButton(row, "Открыть", lambda a=a: self.navigate("law", law_id=a["law_id"], article_id=a["id"]), "outline", height=32, size=9).pack(side="right")
        self.bg(work, done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _remove_fav(self, fav_id, card):
        def done(_):
            card.destroy()
            self.notify("Избранное", "Статья убрана.", "success", 2000)
        self.bg(lambda: self.db.delete("favorites", {"id": f"eq.{fav_id}"}), done)

    # ================================================================== синхронизация с форумом RMRP
    def fetch_forum_articles(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RMRP-Pomoshnik/2.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
        return T.parse_articles(T.html_to_lines(raw))

    def sync_laws(self):
        if not self.is_staff("ADMIN"):
            self.notify(APP_NAME, "Синхронизация доступна только Администратору и Основателю.", "warning")
            return
        win = ui.modal(self, "Синхронизация законодательства", 560, 280, PANEL)
        ui.lbl(win, "Синхронизация законодательства RMRP", 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(22, 4))
        status = ui.lbl(win, "Подготовка…", 10, False, TEXT2, bg=PANEL, wraplength=500)
        status.pack(anchor="w", padx=24, pady=(4, 12))
        pb = ttk.Progressbar(win, mode="determinate", length=500)
        pb.pack(padx=24)
        log = tk.Text(win, height=5, bg=PANEL2, fg=TEXT2, relief="flat", font=(FONT, 8), highlightthickness=0, padx=8, pady=6)
        log.pack(fill="both", expand=True, padx=24, pady=14)
        close = ui.RButton(win, "Закрыть", win.destroy, "secondary", height=34)
        close.set_disabled(True)
        close.pack(anchor="e", padx=24, pady=(0, 16))

        def say(msg, step=None, total=None):
            def ui_update():
                try:
                    status.configure(text=msg)
                    log.insert("end", msg + "\n")
                    log.see("end")
                    if step is not None and total:
                        pb["value"] = step / total * 100
                except tk.TclError:
                    pass
            self._safe_after(ui_update)

        def worker():
            try:
                sources = [dict(s) for s in LAW_SOURCES]
                known = {s["url"] for s in sources}
                for l in self.db.table("laws", "name,short_name,law_number,source_url"):
                    if l.get("source_url") and l["source_url"] not in known:
                        sources.append({"name": l["name"], "short_name": l.get("short_name") or l["name"], "law_number": l.get("law_number"), "url": l["source_url"]})
                        known.add(l["source_url"])
            except Exception as e:  # noqa: BLE001
                say(f"Не удалось получить список законов: {e}")
                self._safe_after(lambda: close.set_disabled(False))
                return
            total, ok, art_total, errors = len(sources), 0, 0, []
            for i, src in enumerate(sources):
                say(f"[{i + 1}/{total}] Загрузка: {src['short_name']}", i, total)
                try:
                    arts = self.fetch_forum_articles(src["url"])
                    if len(arts) < 3:
                        raise RuntimeError("страница не распознана (найдено < 3 статей) — данные не тронуты")
                    n = self._store_law(src, arts)
                    art_total += n
                    ok += 1
                    say(f"   ✓ {src['short_name']}: {n} статей", i + 1, total)
                except Exception as e:  # noqa: BLE001
                    errors.append(src["short_name"])
                    say(f"   ✗ {src['short_name']}: {e}", i + 1, total)
            self.invalidate_laws()
            self.log_action("Синхронизация законов", "laws", None, {"laws": ok, "articles": art_total, "errors": errors})

            def finish():
                try:
                    close.set_disabled(False)
                    status.configure(text=f"Готово: законов {ok}/{total}, статей {art_total}." + (f" Ошибки: {', '.join(errors)}" if errors else ""))
                except tk.TclError:
                    pass
                self.notify("Синхронизация завершена", f"Законов: {ok}/{total} • Статей: {art_total}", "warning" if errors else "success", 5000)
                if self.page in ("laws", "home"):
                    self.navigate(self.page)
            self._safe_after(finish)
        threading.Thread(target=worker, daemon=True).start()

    def _store_law(self, src, arts):
        """Безопасная запись: апсерт статей, затем удаление исчезнувших. Закон не остаётся без статей при сбое."""
        db = self.db
        existing = db.table("laws", "id", {"source_url": f"eq.{src['url']}"}, "id.asc", 1)
        if not existing and src.get("law_number"):
            existing = db.table("laws", "id", {"law_number": f"eq.{src['law_number']}"}, "id.asc", 1)
        payload = {"name": src["name"], "short_name": src["short_name"], "law_number": src.get("law_number"), "source_url": src["url"],
                   "description": "Актуальная редакция RMRP.", "is_active": True}
        if existing:
            law_id = existing[0]["id"]
            db.update("laws", {"id": f"eq.{law_id}"}, payload)
        else:
            law_id = db.insert("laws", payload)[0]["id"]
        rich = True
        for k in range(0, len(arts), 40):
            batch = [dict(a, law_id=law_id) for a in arts[k:k + 40]]
            if not rich:
                batch = [{x: y for x, y in b.items() if x not in ("chapter", "position")} for b in batch]
            try:
                db.insert("law_articles", batch, select="id", upsert_on="law_id,article_number")
            except ApiError as e:
                if rich and ("chapter" in str(e) or "position" in str(e)):
                    rich = False  # старая схема БД без колонок chapter/position
                    batch = [{x: y for x, y in b.items() if x not in ("chapter", "position")} for b in batch]
                    db.insert("law_articles", batch, select="id", upsert_on="law_id,article_number")
                else:
                    raise
        keep = {a["article_number"] for a in arts}
        old = db.table_all("law_articles", "id,article_number", {"law_id": f"eq.{law_id}"})
        stale = [r["id"] for r in old if r["article_number"] not in keep]
        for k in range(0, len(stale), 50):
            db.delete("law_articles", {"id": "in.(" + ",".join(str(x) for x in stale[k:k + 50]) + ")"})
        try:
            db.insert("law_versions", {"law_id": law_id, "version": datetime.now().strftime("%Y.%m.%d %H:%M"),
                                       "change_description": f"Синхронизация с форумом RMRP: {len(arts)} статей" + (f", удалено устаревших: {len(stale)}" if stale else "")})
        except ApiError:
            pass
        return len(arts)

    # ================================================================== добавление закона
    def add_law_dialog(self, law=None):
        win = ui.modal(self, "Закон", 560, 470, PANEL)
        ui.lbl(win, "Редактировать закон" if law else "Добавить закон", 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(20, 4))
        fields = {}
        for key, label in [("name", "Полное название"), ("short_name", "Краткое название (например, УК РФ)"), ("law_number", "Номер"),
                           ("source_url", "Ссылка на тему форума (для синхронизации)")]:
            ui.lbl(win, label, 9, False, TEXT2, bg=PANEL).pack(anchor="w", padx=24, pady=(10, 4))
            f = ui.Field(win, outer=PANEL, height=36)
            f.pack(fill="x", padx=24)
            f.set((law or {}).get(key) or "")
            fields[key] = f

        def save():
            v = {k: f.get() for k, f in fields.items()}
            if not v["name"]:
                self.notify("Закон", "Введите название.", "warning")
                return
            v = {k: (x or None) for k, x in v.items()}
            v["short_name"] = v["short_name"] or v["name"]

            def work():
                if law:
                    self.db.update("laws", {"id": f"eq.{law['id']}"}, v)
                else:
                    self.db.insert("laws", dict(v, is_active=True))
                self.invalidate_laws()

            def done(_):
                win.destroy()
                self.notify("Закон сохранён", v["short_name"], "success")
                self.log_action("Сохранён закон", "laws", (law or {}).get("id"), {"name": v["name"]})
                if self.page in ("laws", "admin"):
                    self.navigate(self.page, **({"section": "laws"} if self.page == "admin" else {}))
            self.bg(work, done, bound=False)
        bar = tk.Frame(win, bg=PANEL)
        bar.pack(side="bottom", fill="x", padx=24, pady=18)
        ui.RButton(bar, "Сохранить", save).pack(side="right")
        ui.RButton(bar, "Отмена", win.destroy, "secondary").pack(side="right", padx=8)
