"""Проверь себя: список тестов, прохождение прямо в окне, разбор ответов, сохранение результатов."""
import random
import tkinter as tk
from datetime import datetime, timezone

from . import textutil as T
from . import ui
from .api import ApiError
from .config import (ACCENT, ACCENT_TXT, BG, BORDER, BORDER2, DANGER, DIFFICULTY_RU, DIFFICULTY_STARS, FONT, MUTED, ORANGE, PANEL, PANEL2, PURPLE,
                     SUCCESS, TEAL, TEXT, TEXT2, WARNING)

ACCENTS = [ACCENT, PURPLE, TEAL, ORANGE]
LETTERS = ("A", "B", "C", "D")


class TestPages:
    # ================================================================== список
    def page_tests(self):
        self.set_header("Проверь себя", "Проверьте свои знания и закрепите материал")
        wrap = self.content
        holder = tk.Frame(wrap, bg=BG)
        holder.pack(fill="both", expand=True)
        state = {"tests": [], "results": {}, "favs": set(), "tab": "all"}
        tabs = ui.PillTabs(holder, [("all", "Все тесты"), ("passed", "Пройденные"), ("fav", "Избранные")], lambda k: (state.update(tab=k), render()))
        tabs.pack(anchor="w", pady=(4, 12))
        sf = ui.ScrollFrame(holder, bg=BG)
        sf.pack(fill="both", expand=True)
        grid = sf.body
        loader = self.loading(grid)

        def work():
            tests = self.db.table("tests", "id,title,category,description,difficulty,question_count", {"is_active": "eq.true"}, "title.asc")
            results, favs = {}, set()
            if not self.guest:
                for r in self.db.table("test_results", "test_id,score,completed_at", {"user_id": f"eq.{self.uid}"}, "completed_at.desc", 500):
                    results.setdefault(r["test_id"], []).append(r)
                try:
                    favs = {r["test_id"] for r in self.db.table("test_favorites", "test_id", {"user_id": f"eq.{self.uid}"})}
                except ApiError:
                    pass
            return tests, results, favs

        def done(res):
            loader.destroy()
            state["tests"], state["results"], state["favs"] = res
            render()

        def render():
            for c in grid.winfo_children():
                c.destroy()
            tab = state["tab"]
            items = state["tests"]
            if tab == "passed":
                items = [t for t in items if t["id"] in state["results"]]
            elif tab == "fav":
                items = [t for t in items if t["id"] in state["favs"]]
            if not items:
                msg = {"all": "Администратор ещё не добавил тесты.", "passed": "Вы ещё не прошли ни одного теста.", "fav": "Нажмите ☆ на карточке теста, чтобы добавить его сюда."}[tab]
                self.card_message(grid, "Здесь пока пусто", msg)
                return
            grid.grid_columnconfigure(0, weight=1, uniform="t")
            grid.grid_columnconfigure(1, weight=1, uniform="t")
            for i, t in enumerate(items):
                self._test_card(grid, t, i, state, render).grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0, 7) if i % 2 == 0 else (7, 0), pady=7)
        self.bg(work, done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _test_card(self, parent, t, i, state, rerender):
        color = ACCENTS[i % len(ACCENTS)]
        card = ui.Card(parent, radius=14, pad=16, height=160)
        row = tk.Frame(card.body, bg=PANEL)
        row.pack(fill="x")
        ui.icon_tile(row, "✓", color, 46, bg=PANEL).pack(side="left")
        col = tk.Frame(row, bg=PANEL)
        col.pack(side="left", padx=12, fill="x", expand=True)
        ui.lbl(col, t.get("title", "Тест"), 12, True, wraplength=300).pack(anchor="w")
        ui.lbl(col, f"{t.get('question_count') or 0} {T.plural(t.get('question_count') or 0, 'вопрос', 'вопроса', 'вопросов')}", 9, False, TEXT2).pack(anchor="w")
        star = tk.Label(row, text="★" if t["id"] in state["favs"] else "☆", font=(FONT, 15), fg=WARNING if t["id"] in state["favs"] else MUTED, bg=PANEL,
                        cursor="hand2")
        star.pack(side="right", anchor="n")
        star.bind("<Button-1>", lambda e: self._toggle_test_fav(t["id"], state, rerender))
        n = DIFFICULTY_STARS.get(t.get("difficulty"), 2)
        diff = f"Сложность: {'★' * n}{'☆' * (3 - n)}  {DIFFICULTY_RU.get(t.get('difficulty'), '')}"
        ui.lbl(card.body, diff, 9, False, WARNING).pack(anchor="w", pady=(10, 0))
        best = max((r["score"] for r in state["results"].get(t["id"], [])), default=None)
        ui.lbl(card.body, f"Лучший результат: {best}%" if best is not None else (t.get("description") or "")[:70], 9, False, MUTED).pack(anchor="w", pady=(2, 8))
        ui.RButton(card.body, "Начать" if best is None else "Пройти ещё раз", lambda: self.start_test(t), "primary", height=34).pack(fill="x", side="bottom")
        return card

    def _toggle_test_fav(self, test_id, state, rerender):
        if not self.require_login("Избранные тесты"):
            return
        on = test_id not in state["favs"]

        def work():
            if on:
                self.db.insert("test_favorites", {"user_id": self.uid, "test_id": test_id}, upsert_on="user_id,test_id", ignore_duplicates=True)
            else:
                self.db.delete("test_favorites", {"user_id": f"eq.{self.uid}", "test_id": f"eq.{test_id}"})

        def done(_):
            (state["favs"].add if on else state["favs"].discard)(test_id)
            rerender()
        self.bg(work, done, lambda e: self.notify("Избранные тесты", "Не удалось сохранить. Примените SQL-миграцию 2.0.", "error"))

    # ================================================================== прохождение
    def start_test(self, test):
        for w in self.content.winfo_children():
            w.destroy()
        self.nav_id += 1
        self.set_header(test.get("title", "Тест"), "Загрузка вопросов…")
        loader = self.loading(self.content)

        def work():
            return self.db.table("questions", "id,question,answer_a,answer_b,answer_c,answer_d,correct_answer,explanation", {"test_id": f"eq.{test['id']}"}, "id.asc")

        def done(qs):
            loader.destroy()
            if not qs:
                self.card_message(self.content, "В тесте пока нет вопросов", "Администратор может добавить их в разделе «Админ-панель → Тесты».")
                ui.RButton(self.content, "К тестам", lambda: self.navigate("tests"), "secondary").pack(anchor="w", pady=10)
                return
            random.shuffle(qs)
            self._run_test(test, qs)
        self.bg(work, done, lambda e: loader.configure(text=f"Ошибка: {e}"))

    def _run_test(self, test, qs):
        wrap = self.content
        st = {"i": 0, "ans": {}}
        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x")
        prog_lbl = ui.lbl(top, "", 10, True, ACCENT_TXT)
        prog_lbl.pack(side="left")
        ui.RButton(top, "Выйти из теста", lambda: self.navigate("tests"), "ghost", height=32, size=9).pack(side="right")
        bar = tk.Canvas(wrap, height=6, bg=BG, highlightthickness=0)
        bar.pack(fill="x", pady=(8, 14))
        qcard = ui.Card(wrap, radius=14, pad=20)
        qcard.pack(fill="x")
        qlbl = tk.Label(qcard.body, text="", bg=PANEL, fg=TEXT, font=(FONT, 13, "bold"), wraplength=840, justify="left", anchor="w")
        qlbl.pack(anchor="w")
        opts = tk.Frame(wrap, bg=BG)
        opts.pack(fill="x", pady=12)
        nav = tk.Frame(wrap, bg=BG)
        nav.pack(fill="x")
        back = ui.RButton(nav, "Назад", lambda: move(-1), "secondary", icon="←")
        back.pack(side="left")
        nxt = ui.RButton(nav, "Далее", lambda: move(1), "primary", icon="→")
        nxt.pack(side="right")

        def draw_bar():
            bar.delete("all")
            w = bar.winfo_width() or 800
            bar.create_polygon(ui.rr_points(0, 0, w, 6, 3), smooth=True, fill=PANEL2, outline="")
            frac = (st["i"] + 1) / len(qs)
            bar.create_polygon(ui.rr_points(0, 0, max(8, w * frac), 6, 3), smooth=True, fill=ACCENT, outline="")
        bar.bind("<Configure>", lambda e: draw_bar())

        def render():
            q = qs[st["i"]]
            prog_lbl.configure(text=f"Вопрос {st['i'] + 1} из {len(qs)}")
            self.set_header(test.get("title", "Тест"), "Выберите один вариант ответа")
            qlbl.configure(text=q["question"])
            draw_bar()
            for c in opts.winfo_children():
                c.destroy()
            chosen = st["ans"].get(q["id"])
            for letter in LETTERS:
                sel = chosen == letter
                oc = ui.Card(opts, bg=ui.mix(PANEL, ACCENT, .30) if sel else PANEL, border=ACCENT if sel else BORDER, radius=10, pad=12)
                oc.pack(fill="x", pady=4)
                r = tk.Frame(oc.body, bg=oc._bg)
                r.pack(fill="x")
                tk.Label(r, text=letter, font=(FONT, 10, "bold"), fg="#ffffff" if sel else ACCENT_TXT, bg=ACCENT if sel else PANEL2, width=3, pady=3).pack(side="left")
                tk.Label(r, text=q["answer_" + letter.lower()], font=(FONT, 10), fg=TEXT, bg=oc._bg, wraplength=760, justify="left", anchor="w").pack(side="left", padx=12)
                oc.make_clickable(lambda l=letter, qid=q["id"]: pick(qid, l))
            back.set_disabled(st["i"] == 0)
            nxt.configure_text("Завершить" if st["i"] == len(qs) - 1 else "Далее")

        def pick(qid, letter):
            st["ans"][qid] = letter
            render()

        def move(d):
            q = qs[st["i"]]
            if d > 0 and q["id"] not in st["ans"]:
                self.notify("Тест", "Выберите вариант ответа.", "warning", 2000)
                return
            if d > 0 and st["i"] == len(qs) - 1:
                unanswered = [x for x in qs if x["id"] not in st["ans"]]
                if unanswered:
                    self.notify("Тест", f"Остались вопросы без ответа: {len(unanswered)}.", "warning")
                    return
                self._finish_test(test, qs, st["ans"])
                return
            st["i"] = max(0, min(len(qs) - 1, st["i"] + d))
            render()
        render()

    def _finish_test(self, test, qs, ans):
        correct = sum(1 for q in qs if ans.get(q["id"]) == q["correct_answer"])
        score = round(correct / len(qs) * 100)
        for w in self.content.winfo_children():
            w.destroy()
        self.set_header(test.get("title", "Тест"), "Результат")
        color = SUCCESS if score >= 70 else WARNING if score >= 40 else DANGER
        sf = ui.ScrollFrame(self.content, bg=BG)
        sf.pack(fill="both", expand=True)
        body = sf.body
        c = ui.Card(body, radius=14, pad=22)
        c.pack(fill="x", pady=(4, 10))
        ui.lbl(c.body, f"{score}%", 34, True, color).pack(anchor="w")
        verdict = "Отлично!" if score >= 85 else "Хороший результат" if score >= 70 else "Есть что повторить" if score >= 40 else "Нужно подтянуть знания"
        ui.lbl(c.body, f"{verdict} — верно {correct} из {len(qs)}", 12, True).pack(anchor="w", pady=(2, 4))
        saved = ui.lbl(c.body, "Сохраняю результат…" if not self.guest else "Гостевой режим: результат не сохраняется. Войдите в аккаунт, чтобы вести историю.", 9, False, MUTED)
        saved.pack(anchor="w")
        row = tk.Frame(c.body, bg=PANEL)
        row.pack(anchor="w", pady=(14, 0))
        ui.RButton(row, "Пройти ещё раз", lambda: self.start_test(test), "primary").pack(side="left")
        ui.RButton(row, "К тестам", lambda: self.navigate("tests"), "secondary").pack(side="left", padx=8)

        ui.lbl(body, "Разбор ответов", 13, True).pack(anchor="w", pady=(8, 6))
        for n, q in enumerate(qs, 1):
            got = ans.get(q["id"])
            ok = got == q["correct_answer"]
            qc = ui.Card(body, border=ui.mix(PANEL, SUCCESS if ok else DANGER, .55), radius=12, pad=14)
            qc.pack(fill="x", pady=4)
            ui.lbl(qc.body, f"{n}. {q['question']}", 10, True, wraplength=840).pack(anchor="w")
            if not ok:
                ui.lbl(qc.body, f"Ваш ответ: {got}. {q.get('answer_' + (got or 'a').lower(), '')}", 9, False, DANGER, wraplength=840).pack(anchor="w", pady=(6, 0))
            ui.lbl(qc.body, f"Правильно: {q['correct_answer']}. {q.get('answer_' + q['correct_answer'].lower(), '')}", 9, False, SUCCESS, wraplength=840).pack(anchor="w", pady=(2, 0))
            if q.get("explanation"):
                ui.lbl(qc.body, q["explanation"], 9, False, TEXT2, wraplength=840).pack(anchor="w", pady=(4, 0))
        if self.guest:
            return

        def work():
            now = datetime.now(timezone.utc).isoformat()
            res = self.db.insert("test_results", {"user_id": self.uid, "test_id": test["id"], "score": score, "total_questions": len(qs),
                                                  "correct_answers": correct, "completed_at": now})
            rid = res[0]["id"]
            self.db.insert("test_answers", [{"result_id": rid, "question_id": q["id"], "selected_answer": ans.get(q["id"], "A"),
                                            "is_correct": ans.get(q["id"]) == q["correct_answer"]} for q in qs])
        self.bg(work, lambda _: saved.configure(text="Результат сохранён в истории.", fg=SUCCESS),
                lambda e: saved.configure(text=f"Не удалось сохранить результат: {e}", fg=DANGER), bound=False)
