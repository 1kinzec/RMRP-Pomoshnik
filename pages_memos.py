"""Краткие памятки: короткие публикации с тегами и фото. Читают все, публикуют Основатель и администраторы."""
import tkinter as tk

from . import memo_util as M
from . import ui
from .config import (ACCENT, ACCENT_TXT, BG, BORDER, BORDER2, DANGER, FONT, MEMO_BUCKET, MEMO_TAGS, MUTED, PANEL, PANEL2, TEXT, TEXT2,
                     WARNING, role_color, role_label)
from .textutil import fmt_date

PREVIEW_CHARS = 360
THUMB = (176, 124)
PER_ROW = 4


class MemoPages:
    # ------------------------------------------------------------------ права
    def can_publish_memos(self):
        return (not self.guest) and self.is_staff("ADMIN")

    def memo_url(self, path):
        return self.db.public_url(MEMO_BUCKET, M.object_path(path))

    # ------------------------------------------------------------------ страница
    def page_memos(self):
        self.set_header("Краткие памятки", "Шпаргалки и важные заметки от команды RMRP Помощник")
        self._memo = {"rows": [], "tags": set(), "open": set(), "loaded": False}
        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", pady=(0, 8))
        self._memo_search = ui.Field(top, "Поиск по памяткам: слово из заголовка, текста или тега", height=38, icon="⌕")
        self._memo_search.pack(side="left", fill="x", expand=True)
        if self.can_publish_memos():
            ui.RButton(top, "Новая памятка", lambda: self.memo_dialog(), "primary", icon="✎", height=38).pack(side="right", padx=(10, 0))
        self._memo_tagbar = tk.Frame(self.content, bg=BG)
        self._memo_tagbar.pack(fill="x", pady=(0, 6))
        self._memo_body = self.scroll()
        self._memo_search.var.trace_add("write", lambda *_: self._memo_render())
        self.loading(self._memo_body)
        self.memo_reload()

    def memo_reload(self):
        def work():
            rows = self.db.rpc("memos_feed", {"p_limit": 300})
            return rows if isinstance(rows, list) else []

        def done(rows):
            self._memo["rows"], self._memo["loaded"] = rows, True
            self._memo_render()

        def fail(e):
            for w in self._memo_body.winfo_children():
                w.destroy()
            msg = str(e)
            hint = ("В базе ещё нет раздела памяток. Выполните migration_v2_5.sql в Supabase → SQL Editor."
                    if "memos_feed" in msg or "schema cache" in msg.lower() or getattr(e, "status", 0) == 404 else msg)
            self.card_message(self._memo_body, "Не удалось загрузить памятки", hint, WARNING)
        self.bg(work, done, fail)

    def _toggle_memo_tag(self, tag):
        tags = self._memo["tags"]
        tags.symmetric_difference_update({tag})
        self._memo_render()

    def _memo_render(self):
        st = self._memo
        if not st.get("loaded"):
            return
        # панель тегов
        bar = self._memo_tagbar
        for w in bar.winfo_children():
            w.destroy()
        tags = M.all_tags(st["rows"])
        row = None
        for i, (tag, n) in enumerate(tags):
            if i % 9 == 0:
                row = tk.Frame(bar, bg=BG)
                row.pack(fill="x", pady=2)
            color = M.tag_color(tag)
            on = tag in st["tags"]
            lb = tk.Label(row, text=f"{tag}  {n}", font=(FONT, 8, "bold"), fg="#ffffff" if on else color, bg=color if on else ui.mix(BG, color, .16),
                          padx=9, pady=3, bd=0, cursor="hand2")
            lb.pack(side="left", padx=(0, 6))
            lb.bind("<Button-1>", lambda e, t=tag: self._toggle_memo_tag(t))
        if st["tags"]:
            clear = tk.Label(row or bar, text="✕ сбросить", font=(FONT, 8), fg=MUTED, bg=BG, cursor="hand2")
            clear.pack(side="left", padx=4)
            clear.bind("<Button-1>", lambda e: (st["tags"].clear(), self._memo_render()))
        # список
        body = self._memo_body
        for w in body.winfo_children():
            w.destroy()
        shown = M.sort_memos(M.filter_memos(st["rows"], self._memo_search.get(), st["tags"]))
        if not shown:
            if st["rows"]:
                self.card_message(body, "Ничего не найдено", "Измените запрос или сбросьте выбранные теги.", MUTED)
            else:
                self.card_message(body, "Памяток пока нет",
                                  "Здесь появятся короткие шпаргалки от команды." + (" Нажмите «Новая памятка», чтобы опубликовать первую." if self.can_publish_memos() else ""))
            return
        for m in shown:
            self._memo_card(body, m)

    def _memo_card(self, parent, m):
        st = self._memo
        card = ui.Card(parent, radius=14, pad=18)
        card.pack(fill="x", pady=6)
        b = card.body
        head = tk.Frame(b, bg=PANEL)
        head.pack(fill="x")
        title = ("📌 " if m.get("pinned") else "") + (m.get("title") or "Без названия")
        ui.lbl(head, title, 14, True, wraplength=640).pack(side="left", anchor="w")
        if self.can_publish_memos():
            acts = tk.Frame(head, bg=PANEL)
            acts.pack(side="right")
            ui.RButton(acts, "✎", lambda m=m: self.memo_dialog(m), "secondary", height=28, size=9, padx=10).pack(side="left", padx=2)
            ui.RButton(acts, "Открепить" if m.get("pinned") else "Закрепить", lambda m=m: self.memo_toggle_pin(m), "secondary", height=28, size=8).pack(side="left", padx=2)
            ui.RButton(acts, "✕", lambda m=m: self.memo_delete(m), "danger", height=28, size=9, padx=10).pack(side="left", padx=2)
        if m.get("tags"):
            tr = tk.Frame(b, bg=PANEL)
            tr.pack(fill="x", pady=(8, 0))
            for t in m["tags"]:
                lb = ui.chip(tr, t, M.tag_color(t), PANEL)
                lb.pack(side="left", padx=(0, 6))
                lb.configure(cursor="hand2")
                lb.bind("<Button-1>", lambda e, t=t: self._memo_pick_tag(t))
        content = (m.get("content") or "").strip()
        if content:
            full = m["id"] in st["open"]
            text = content if (full or len(content) <= PREVIEW_CHARS) else content[:PREVIEW_CHARS].rstrip() + "…"
            ui.lbl(b, text, 10, False, TEXT2, wraplength=820).pack(anchor="w", pady=(10, 0))
            if len(content) > PREVIEW_CHARS:
                more = tk.Label(b, text="Свернуть ▴" if full else "Читать полностью ▾", font=(FONT, 9, "bold"), fg=ACCENT_TXT, bg=PANEL, cursor="hand2")
                more.pack(anchor="w", pady=(4, 0))
                more.bind("<Button-1>", lambda e, i=m["id"]: (st["open"].symmetric_difference_update({i}), self._memo_render()))
        images = m.get("images") or []
        if images:
            urls = [self.memo_url(p) for p in images]
            grid = tk.Frame(b, bg=PANEL)
            grid.pack(fill="x", pady=(12, 0))
            for i, u in enumerate(urls):
                if i % PER_ROW == 0:
                    row = tk.Frame(grid, bg=PANEL)
                    row.pack(fill="x", pady=3)
                ui.RemoteImage(row, u, THUMB, command=lambda urls=urls, i=i: ui.show_image(self, urls, i), bg=PANEL2).pack(side="left", padx=(0, 8))
        foot = tk.Frame(b, bg=PANEL)
        foot.pack(fill="x", pady=(14, 0))
        role = m.get("author_role") or "USER"
        name = m.get("author_name") or "Команда RMRP"
        ui.Avatar(foot, name, 28, m.get("author_avatar") or "", ring=role_color(role), bg=PANEL).pack(side="left")
        ui.lbl(foot, name, 9, True, role_color(role)).pack(side="left", padx=(8, 6))
        ui.chip(foot, role_label(role), role_color(role), PANEL).pack(side="left")
        when = fmt_date(m.get("created_at"), True)
        edited = m.get("updated_at") and m.get("created_at") and str(m["updated_at"])[:16] != str(m["created_at"])[:16]
        ui.lbl(foot, when + ("  •  изменено" if edited else ""), 8, False, MUTED).pack(side="right")

    def _memo_pick_tag(self, tag):
        self._memo["tags"] = {tag}
        self._memo_render()

    # ------------------------------------------------------------------ действия
    def memo_toggle_pin(self, m):
        val = not m.get("pinned")
        self.bg(lambda: self.db.update("memos", {"id": f"eq.{m['id']}"}, {"pinned": val}, expect=True),
                lambda _: (self.log_action("Закреплена памятка" if val else "Откреплена памятка", "memo", m["id"]), self.memo_reload()),
                lambda e: self.notify("Памятки", str(e), "error"), bound=False)

    def memo_delete(self, m):
        if not ui.confirm(self, "Удалить памятку?", f"«{m.get('title')}» и её фото будут удалены безвозвратно.", "Удалить", danger=True):
            return

        def work():
            self.db.delete("memos", {"id": f"eq.{m['id']}"}, expect=True)
            try:
                self.db.delete_objects(MEMO_BUCKET, [M.object_path(p) for p in m.get("images") or []])
            except Exception:  # noqa: BLE001
                pass  # памятка уже удалена; осиротевшие файлы не мешают

        def done(_):
            self.log_action("Удалена памятка", "memo", m["id"], {"title": m.get("title")})
            self.notify("Памятки", "Памятка удалена.", "success")
            if self.page == "memos":
                self.memo_reload()
        self.bg(work, done, lambda e: self.notify("Памятки", str(e), "error"), bound=False)

    def memo_persist(self, memo, fields, items, old_paths):
        """Загружает новые фото, пишет памятку (создаёт или обновляет), удаляет убранные фото. Вызывается в фоновом потоке.
        items: [{"kind": "old", "path": ...} | {"kind": "new", "file": ...}] в нужном порядке."""
        uploaded = []
        try:
            images = []
            for it in items:
                if it["kind"] == "old":
                    images.append(it["path"])
                    continue
                data, ctype, ext = M.prepare_image(it["file"])
                path = M.new_object_path(self.uid, ext)
                self.db.upload_object(MEMO_BUCKET, path, data, ctype)
                uploaded.append(path)
                images.append(path)
            row = dict(fields, images=images)
            if memo:
                self.db.update("memos", {"id": f"eq.{memo['id']}"}, row, expect=True)
            else:
                row["author_id"] = self.uid
                self.db.insert("memos", row)
        except Exception:
            try:
                self.db.delete_objects(MEMO_BUCKET, uploaded)  # откат: не оставляем сирот в хранилище
            except Exception:  # noqa: BLE001
                pass
            raise
        kept = {i.get("path") for i in items if i["kind"] == "old"}
        removed = [p for p in old_paths if p not in kept]
        if removed:
            try:
                self.db.delete_objects(MEMO_BUCKET, [M.object_path(p) for p in removed])
            except Exception:  # noqa: BLE001
                pass
        return images

    # ------------------------------------------------------------------ редактор
    def memo_dialog(self, memo=None):
        if not self.can_publish_memos():
            self.notify("Памятки", "Публиковать могут Основатель и администраторы.", "warning")
            return
        from tkinter import filedialog
        sh = self.winfo_screenheight()
        win = ui.modal(self, "Редактирование памятки" if memo else "Новая памятка", 800, min(820, sh - 90), PANEL)
        old_paths = list((memo or {}).get("images") or [])
        items = [{"kind": "old", "path": p} for p in old_paths]
        known = {n.lower() for n, _ in MEMO_TAGS}
        have = M.normalize_tags((memo or {}).get("tags") or [])
        picked = {t for t in have if t.lower() in known}
        custom_init = ", ".join(t for t in have if t.lower() not in known)
        busy = {"v": False}

        bar = tk.Frame(win, bg=PANEL)
        bar.pack(side="bottom", fill="x", padx=24, pady=16)
        scroll = ui.ScrollFrame(win, bg=PANEL)
        scroll.pack(fill="both", expand=True, padx=(24, 12), pady=(16, 0))
        body = scroll.body

        ui.lbl(body, "Заголовок", 10, True, bg=PANEL).pack(anchor="w", pady=(0, 6))
        f_title = ui.Field(body, "Коротко и по делу (до 120 символов)", outer=PANEL, height=38)
        f_title.pack(fill="x", padx=(0, 12))
        f_title.set((memo or {}).get("title") or "")

        ui.lbl(body, "Текст", 10, True, bg=PANEL).pack(anchor="w", pady=(14, 6))
        txt = tk.Text(body, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=ui.font(10), padx=12, pady=10, height=9,
                      highlightthickness=1, highlightbackground=BORDER2, highlightcolor=ACCENT)
        txt.pack(fill="x", padx=(0, 12))
        txt.insert("1.0", (memo or {}).get("content") or "")

        ui.lbl(body, "Теги", 10, True, bg=PANEL).pack(anchor="w", pady=(14, 6))
        tag_box = tk.Frame(body, bg=PANEL)
        tag_box.pack(fill="x", padx=(0, 12))
        chips = {}

        def paint(tag):
            color, on = M.tag_color(tag), tag in picked
            chips[tag].configure(fg="#ffffff" if on else color, bg=color if on else ui.mix(PANEL, color, .16))

        def toggle(tag):
            picked.symmetric_difference_update({tag})
            paint(tag)
        row = None
        for i, (tag, _c) in enumerate(MEMO_TAGS):
            if i % 5 == 0:
                row = tk.Frame(tag_box, bg=PANEL)
                row.pack(fill="x", pady=3)
            lb = tk.Label(row, text=tag, font=(FONT, 9, "bold"), padx=12, pady=4, bd=0, cursor="hand2")
            lb.pack(side="left", padx=(0, 8))
            lb.bind("<Button-1>", lambda e, t=tag: toggle(t))
            chips[tag] = lb
            paint(tag)
        f_custom = ui.Field(body, "Свои теги через запятую, например: ГИБДД, Допрос", outer=PANEL, height=36)
        f_custom.pack(fill="x", padx=(0, 12), pady=(8, 0))
        f_custom.set(custom_init)

        ui.lbl(body, "Фото", 10, True, bg=PANEL).pack(anchor="w", pady=(14, 6))
        photos = tk.Frame(body, bg=PANEL)
        photos.pack(fill="x", padx=(0, 12))
        count_lbl = ui.lbl(body, "", 8, False, MUTED, bg=PANEL)

        def render_photos():
            for w in photos.winfo_children():
                w.destroy()
            row = None
            for i, it in enumerate(items):
                if i % 6 == 0:
                    row = tk.Frame(photos, bg=PANEL)
                    row.pack(fill="x", pady=3)
                cell = tk.Frame(row, bg=PANEL)
                cell.pack(side="left", padx=(0, 8))
                if it["kind"] == "old":
                    ui.RemoteImage(cell, self.memo_url(it["path"]), (92, 68), bg=PANEL2).pack()
                else:
                    cv = tk.Canvas(cell, width=92, height=68, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER, bd=0)
                    cv.pack()
                    try:
                        im = ui.Image.open(it["file"])
                        im.thumbnail((90, 66))
                        cv._ph = ui.ImageTk.PhotoImage(im)
                        cv.create_image(46, 34, image=cv._ph)
                    except Exception:  # noqa: BLE001
                        cv.create_text(46, 34, text="фото", fill=MUTED)
                rm = tk.Label(cell, text="✕ убрать", font=(FONT, 8), fg=DANGER, bg=PANEL, cursor="hand2")
                rm.pack()
                rm.bind("<Button-1>", lambda e, it=it: (items.remove(it), render_photos()))
            count_lbl.configure(text=f"{len(items)} из {M.MAX_IMAGES}. JPG, PNG, WEBP, GIF — крупные фото автоматически сжимаются.")

        def add_photos():
            room = M.MAX_IMAGES - len(items)
            if room <= 0:
                self.notify("Памятки", f"Не больше {M.MAX_IMAGES} фото.", "warning")
                return
            files = filedialog.askopenfilenames(parent=win, title="Выберите фото", filetypes=[("Изображения", "*.jpg *.jpeg *.png *.webp *.gif"), ("Все файлы", "*.*")])
            for f in list(files)[:room]:
                items.append({"kind": "new", "file": f})
            if len(files) > room:
                self.notify("Памятки", f"Добавлено только {room}: лимит {M.MAX_IMAGES} фото.", "warning")
            render_photos()
        ui.RButton(body, "Добавить фото", add_photos, "secondary", icon="＋", height=34, size=9).pack(anchor="w", pady=(6, 0))
        count_lbl.pack(anchor="w", pady=(4, 0))
        render_photos()

        pinned = tk.BooleanVar(value=bool((memo or {}).get("pinned")))
        tk.Checkbutton(body, text="Закрепить сверху", variable=pinned, bg=PANEL, fg=TEXT2, selectcolor=PANEL2, activebackground=PANEL, activeforeground=TEXT,
                       font=(FONT, 9), bd=0, highlightthickness=0, cursor="hand2").pack(anchor="w", pady=(14, 8))

        def save():
            if busy["v"]:
                return
            title = f_title.get().strip()
            content = txt.get("1.0", "end").strip()
            tags = M.normalize_tags([n for n, _ in MEMO_TAGS if n in picked] + M.normalize_tags(f_custom.get()))
            err = M.validate_memo(title, content, tags, len(items))
            if err:
                self.notify("Памятки", err, "warning")
                return
            busy["v"] = True
            btn.configure_text("Публикуем…" if not memo else "Сохраняем…")
            btn.set_disabled(True)
            snapshot = [dict(i) for i in items]
            pin = bool(pinned.get())

            def work():
                return self.memo_persist(memo, {"title": title, "content": content, "tags": tags, "pinned": pin}, snapshot, old_paths)

            def done(images):
                try:
                    win.destroy()
                except tk.TclError:
                    pass
                self.log_action("Изменена памятка" if memo else "Опубликована памятка", "memo", (memo or {}).get("id"), {"title": title})
                self.notify("Памятки", "Сохранено." if memo else "Памятка опубликована.", "success")
                if self.page == "memos":
                    self.memo_reload()

            def fail(e):
                busy["v"] = False
                try:
                    btn.configure_text("Сохранить" if memo else "Опубликовать")
                    btn.set_disabled(False)
                except tk.TclError:
                    pass
                msg = str(e)
                if "row-level security" in msg.lower() or "violates" in msg.lower():
                    msg = "Нет прав на публикацию. Проверьте, что выполнен migration_v2_5.sql и ваша роль — Основатель или Администратор."
                self.notify("Не удалось сохранить", msg, "error", 7000)
            self.bg(work, done, fail, bound=False)

        btn = ui.RButton(bar, "Сохранить" if memo else "Опубликовать", save, "primary", height=38)
        btn.pack(side="right")
        ui.RButton(bar, "Отмена", win.destroy, "secondary", height=38).pack(side="right", padx=8)
