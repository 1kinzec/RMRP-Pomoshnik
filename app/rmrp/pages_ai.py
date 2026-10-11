"""Помощь нейросети: чат, который отвечает только цитатами из базы законов (без выдумывания)."""
import tkinter as tk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import ACCENT, ACCENT_LO, ACCENT_TXT, BG, BORDER2, FONT, MUTED, PANEL, PANEL2, TEXT, TEXT2

QUICK = ["Какие права есть у задержанного?", "Можно ли провести досмотр?", "Что грозит за неповиновение?",
         "Какое наказание за оскорбление сотрудника полиции?", "89 УК РФ"]
BOT_BG = ui.mix(PANEL, ACCENT, .10)


class AiPages:
    def page_ai(self, preset=None):
        self.set_header("Помощь нейросети", "Задайте любой вопрос по законам RMRP — отвечаю цитатами из базы")
        wrap = self.content
        self._ai_busy = False
        bottom = tk.Frame(wrap, bg=BG)
        bottom.pack(side="bottom", fill="x", pady=(10, 0))
        chat = ui.ScrollFrame(wrap, bg=BG)
        chat.pack(fill="both", expand=True)
        self._chat = chat
        field = ui.Field(bottom, "Напишите свой вопрос…", height=46, on_return=lambda: send())
        field.pack(side="left", fill="x", expand=True)
        send_btn = ui.RButton(bottom, "➤", lambda: send(), width=46, height=46, size=14)
        send_btn.pack(side="left", padx=(10, 0))
        ui.lbl(wrap, "Ответы формируются только из статей в базе. Если подходящего материала нет — помощник так и скажет, ничего не придумывая.",
               8, False, MUTED).pack(side="bottom", anchor="w", pady=(6, 0))

        self._bot_bubble("Привет! Назовите номер статьи («89 УК РФ») или опишите ситуацию, и я найду норму в базе законов RMRP.", chips=QUICK, on_chip=lambda q: (field.set(q), send()))

        def send():
            q = field.get()
            if not q or self._ai_busy:
                return
            field.set("")
            self._user_bubble(q)
            self._ai_busy = True
            thinking = self._bot_bubble("Ищу в базе законов…")

            def work():
                answer, sources = self._answer(q)
                if sources:
                    self._ai_last = sources[0]
                if not self.guest and not T.smalltalk(q):
                    try:
                        self.db.insert("ai_history", {"user_id": self.uid, "question": q[:1000], "answer": answer[:4000],
                                                      "law_article_id": sources[0]["id"] if sources else None})
                    except ApiError:
                        pass
                return answer, sources

            def done(res):
                self._ai_busy = False
                thinking.destroy()
                self._bot_bubble(res[0], sources=res[1])

            def fail(e):
                self._ai_busy = False
                thinking.destroy()
                self._bot_bubble(f"Не удалось выполнить поиск по базе: {e}")
            self.bg(work, done, fail)

        if preset:
            self.after(100, lambda: (field.set(preset), send()))
        field.focus_entry()

    # ------------------------------------------------------------------ составление ответа
    def _answer(self, q):
        """Понимает, что спросили: беседа, «подробнее», номер статьи или вопрос по существу."""
        chat = T.smalltalk(q)
        if chat:
            return chat, []
        text = T.strip_greeting(q) or q
        last = getattr(self, "_ai_last", None)
        if T.is_followup(text):
            if not last:
                return "Уточните, о какой статье речь: напишите номер («89 УК РФ») или вопрос.", []
            return self._compose_article(last, full=True), [last]
        ref = T.parse_article_ref(text)
        if ref:
            num, hint = ref
            rows = self.search_articles(text, 8, strict=False)
            return self._compose_ref(num, hint, rows)
        rows = [r for r in self.search_articles(text, 8) if T.is_relevant(r, r.get("terms") or [])]
        return self._compose(text, rows)

    @staticmethod
    def _compose_article(r, full=False):
        content = (r.get("content") or "").strip()
        limit = 1800 if full else 700
        body = content if len(content) <= limit else content[:limit].rsplit(" ", 1)[0] + "…"
        return f"Статья {r['article_number']} ({r['law_short']}) «{r.get('title') or 'без названия'}»:\n\n{body}"

    @classmethod
    def _compose_ref(cls, num, hint, rows):
        if not rows:
            where = f" в {hint}" if hint else ""
            return (f"Статьи {num}{where} в базе нет. Возможно, закон ещё не загружен или номер указан с опечаткой. "
                    "Администратор может нажать «Синхронизировать RMRP» в разделе «Законы»."), []
        top = rows[0]
        if hint and top.get("law_number") != hint:
            note = f"В {hint} статьи {num} в базе нет, но такая статья есть в другом законе.\n\n"
        else:
            note = ""
        text = note + cls._compose_article(top)
        others = [r for r in rows[1:4]]
        if others:
            text += "\n\nСтатья с таким номером есть и в: " + "; ".join(r["law_short"] for r in others) + "."
        return text + "\n\nНапишите «подробнее», чтобы увидеть статью полностью.", [top] + others

    @staticmethod
    def _compose(question, rows):
        if not rows:
            return ("В базе RMRP нет подходящего материала по этому вопросу. Я не буду придумывать ответ.\n\n"
                    "Попробуйте переформулировать вопрос, использовать ключевое слово или указать номер статьи, например «статья 319».", [])
        top = rows[0]
        terms = top.get("terms") or T.query_terms(question)
        quote = T.best_sentences(top.get("content") or "", terms)
        head = f"Согласно статье {top['article_number']} ({top['law_short']}) «{top.get('title') or 'без названия'}»:"
        text = f"{head}\n\n{quote}"
        others = [r for r in rows[1:4] if r["id"] != top["id"]]
        if others:
            text += "\n\nТакже может быть полезно: " + "; ".join(f"ст. {r['article_number']} {r['law_short']}" for r in others) + "."
        return text, [top] + others

    # ------------------------------------------------------------------ пузыри
    def _user_bubble(self, text):
        row = tk.Frame(self._chat.body, bg=BG)
        row.pack(fill="x", pady=6)
        b = tk.Frame(row, bg=ACCENT)
        b.pack(side="right", padx=(80, 4))
        tk.Label(b, text=text, bg=ACCENT, fg="#ffffff", font=(FONT, 10), wraplength=560, justify="left", padx=14, pady=10).pack()
        self._chat.to_bottom()

    def _bot_bubble(self, text, sources=None, chips=None, on_chip=None):
        row = tk.Frame(self._chat.body, bg=BG)
        row.pack(fill="x", pady=6)
        logo = ui.load_image("rmrp.png", (40, 40))
        av = tk.Label(row, image=logo, bg=BG) if logo else tk.Label(row, text="⚖", bg=BG, fg=ACCENT_TXT, font=(FONT, 20))
        av.pack(side="left", anchor="n")
        card = ui.Card(row, bg=BOT_BG, border=ui.mix(PANEL, ACCENT, .35), radius=12, pad=14)
        card.pack(side="left", padx=(10, 80), anchor="n")
        tk.Label(card.body, text=text, bg=BOT_BG, fg=TEXT, font=(FONT, 10), wraplength=560, justify="left", anchor="w").pack(anchor="w")
        if sources:
            top = sources[0]
            tk.Label(card.body, text=f"Источник: {top['law_short']}, Статья {top['article_number']}", bg=BOT_BG, fg=ACCENT_TXT,
                     font=(FONT, 9, "bold")).pack(anchor="w", pady=(10, 6))
            line = tk.Frame(card.body, bg=BOT_BG)
            line.pack(anchor="w")
            for i, r in enumerate(sources):
                ui.RButton(line, "Открыть статью" if i == 0 else f"ст. {r['article_number']}", lambda r=r: self.navigate(
                    "law", law_id=r["law_id"], article_id=r["id"], highlight=r.get("terms")), "outline" if i == 0 else "secondary",
                    height=30, size=9, padx=12, outer=BOT_BG).pack(side="left", padx=(0, 6))
        if chips:
            fl = tk.Frame(card.body, bg=BOT_BG)
            fl.pack(anchor="w", pady=(10, 0))
            for q in chips:
                ui.RButton(fl, q, lambda q=q: on_chip(q), "secondary", height=30, size=9, padx=12, outer=BOT_BG).pack(anchor="w", pady=2)
        self._chat.to_bottom()
        return row
