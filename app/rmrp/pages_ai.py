"""Помощь нейросети: чат, который отвечает только цитатами из базы законов (без выдумывания)."""
import tkinter as tk

from . import textutil as T
from . import ui
from .api import ApiError
from .config import ACCENT, ACCENT_LO, ACCENT_TXT, BG, BORDER2, FONT, MUTED, PANEL, PANEL2, TEXT, TEXT2

QUICK = ["Какие права есть у задержанного?", "Можно ли провести досмотр?", "Что грозит за неповиновение?",
         "Какое наказание за оскорбление сотрудника полиции?", "статья 12"]
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

        self._bot_bubble("Привет! Я помогу найти статью, объяснить норму или показать основание ответа.", chips=QUICK, on_chip=lambda q: (field.set(q), send()))

        def send():
            q = field.get()
            if not q or self._ai_busy:
                return
            field.set("")
            self._user_bubble(q)
            self._ai_busy = True
            thinking = self._bot_bubble("Ищу в базе законов…")

            def work():
                rows = self.search_articles(q, 6)
                answer, sources = self._compose(q, rows)
                if not self.guest:
                    try:
                        self.db.insert("ai_history", {"user_id": self.uid, "question": q[:1000], "answer": answer[:4000],
                                                      "law_article_id": rows[0]["id"] if rows else None})
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
