import json, os, urllib.request, urllib.error
import tkinter as tk
from tkinter import ttk, messagebox

SUPABASE_URL = "https://cyihqnquxaxnonjbvshm.supabase.co"
SUPABASE_KEY = "sb_publishable_3X8WkqV57kAqB8v6KS458A_mPnSBBRK"

BG = "#0b0f17"
PANEL = "#121a28"
PANEL2 = "#172235"
ACCENT = "#3b82f6"
TEXT = "#f4f7fb"
MUTED = "#91a0b8"
BORDER = "#223049"
DANGER = "#ef4444"


def api(path, method="GET", body=None, token=None, extra=None):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try: detail = json.loads(raw)
        except Exception: detail = raw
        msg = detail.get("msg") or detail.get("message") or detail.get("error_description") or detail.get("error") if isinstance(detail, dict) else str(detail)
        raise RuntimeError(msg or f"HTTP {e.code}")
    except Exception as e:
        raise RuntimeError(f"Ошибка соединения: {e}")


def login(email, password):
    return api("/auth/v1/token?grant_type=password", "POST", {"email": email, "password": password})


def register(email, password):
    return api("/auth/v1/signup", "POST", {"email": email, "password": password})


def profile(token, user_id):
    path = "/rest/v1/profiles?select=id,username,display_name,role,premium,status,allow_pranks&id=eq." + user_id
    rows = api(path, "GET", token=token)
    return rows[0] if rows else {}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RMRP Помощник — by Kinzec X WOLF")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.configure(bg=BG)
        self.token = None
        self.user = None
        self.prof = {}
        self._styles()
        self.show_login()

    def _styles(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except Exception: pass
        s.configure("TButton", background=ACCENT, foreground="white", borderwidth=0, padding=(14,10), font=("Segoe UI",10,"bold"))
        s.map("TButton", background=[("active", "#2563eb")])
        s.configure("Secondary.TButton", background=PANEL2, foreground=TEXT, borderwidth=1, padding=(14,10))
        s.configure("Danger.TButton", background=DANGER, foreground="white", padding=(14,10), font=("Segoe UI",10,"bold"))
        s.configure("TEntry", fieldbackground="#0f1724", foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=10)
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=34, borderwidth=0)
        s.configure("Treeview.Heading", background=PANEL2, foreground=MUTED, font=("Segoe UI",9,"bold"))

    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def show_login(self):
        self.clear()
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center", width=460, height=570)
        tk.Label(card, text="⚖", bg=PANEL, fg=ACCENT, font=("Segoe UI Symbol",38)).pack(pady=(38,0))
        tk.Label(card, text="RMRP ПОМОЩНИК", bg=PANEL, fg=TEXT, font=("Segoe UI",24,"bold")).pack()
        tk.Label(card, text="by Kinzec X WOLF", bg=PANEL, fg=MUTED, font=("Segoe UI",10)).pack(pady=(4,28))
        tk.Label(card, text="Вход в аккаунт", bg=PANEL, fg=TEXT, font=("Segoe UI",17,"bold")).pack(anchor="w", padx=42)
        self.email = ttk.Entry(card); self.email.insert(0, ""); self.email.pack(fill="x", padx=42, pady=(18,10))
        self.email.insert(0, "Email")
        self.email.bind("<FocusIn>", lambda e: self._placeholder(self.email, "Email"))
        self.password = ttk.Entry(card, show="•"); self.password.pack(fill="x", padx=42, pady=10)
        self.password.insert(0, "Пароль")
        self.password.bind("<FocusIn>", lambda e: self._placeholder(self.password, "Пароль", True))
        ttk.Button(card, text="Войти", command=self.do_login).pack(fill="x", padx=42, pady=(18,8))
        ttk.Button(card, text="Создать аккаунт", style="Secondary.TButton", command=self.do_register).pack(fill="x", padx=42)
        tk.Label(card, text="Без дополнительных библиотек • Supabase", bg=PANEL, fg=MUTED, font=("Segoe UI",8)).pack(side="bottom", pady=20)

    def _placeholder(self, widget, text, secret=False):
        if widget.get() == text:
            widget.delete(0, "end")
            if secret: widget.configure(show="•")

    def do_login(self):
        email, password = self.email.get().strip(), self.password.get()
        if email in ("", "Email") or password in ("", "Пароль"):
            messagebox.showwarning("RMRP Помощник", "Введите email и пароль."); return
        try:
            data = login(email, password)
            self.token = data.get("access_token")
            self.user = data.get("user") or {}
            if not self.token or not self.user.get("id"): raise RuntimeError("Supabase не вернул данные сессии.")
            self.prof = profile(self.token, self.user["id"])
            self.show_main()
        except Exception as e:
            messagebox.showerror("Ошибка входа", str(e))

    def do_register(self):
        email, password = self.email.get().strip(), self.password.get()
        if email in ("", "Email") or len(password) < 6 or password == "Пароль":
            messagebox.showwarning("RMRP Помощник", "Укажи email и пароль минимум из 6 символов."); return
        try:
            register(email, password)
            messagebox.showinfo("Готово", "Аккаунт создан. Если Supabase требует подтверждение почты — подтверди email и затем войди.")
        except Exception as e:
            messagebox.showerror("Ошибка регистрации", str(e))

    def show_main(self):
        self.clear()
        self.configure(bg=BG)
        sidebar = tk.Frame(self, bg=PANEL, width=245, highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="⚖  RMRP", bg=PANEL, fg=TEXT, font=("Segoe UI",21,"bold")).pack(anchor="w", padx=22, pady=(28,0))
        tk.Label(sidebar, text="ПОМОЩНИК", bg=PANEL, fg=ACCENT, font=("Segoe UI",12,"bold")).pack(anchor="w", padx=24)
        tk.Label(sidebar, text="by Kinzec X WOLF", bg=PANEL, fg=MUTED, font=("Segoe UI",9)).pack(anchor="w", padx=24, pady=(2,25))
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        items = [("⌂", "Главная"),("▤", "Законодательство"),("⌕", "Поиск"),("✦", "Помощь нейросети"),("✓", "Проверь себя"),("★", "Избранное"),("◷", "История"),("⚙", "Настройки")]
        self.nav = []
        for icon, title in items:
            b = tk.Button(sidebar, text=f"{icon}   {title}", command=lambda t=title:self.page(t), anchor="w", bd=0, relief="flat", bg=PANEL, fg=MUTED, activebackground=PANEL2, activeforeground=TEXT, font=("Segoe UI",10,"bold"), padx=22, pady=11, cursor="hand2")
            b.pack(fill="x", padx=10, pady=2); self.nav.append(b)
        tk.Frame(sidebar,bg=BORDER,height=1).pack(fill="x", padx=20, pady=16)
        name = self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        role = self.prof.get("role", "USER")
        tk.Label(sidebar, text=name, bg=PANEL, fg=TEXT, font=("Segoe UI",10,"bold")).pack(anchor="w", padx=22)
        tk.Label(sidebar, text=f"🛡 {role}", bg=PANEL, fg=MUTED, font=("Segoe UI",9)).pack(anchor="w", padx=22, pady=(2,10))
        ttk.Button(sidebar, text="Выйти", style="Danger.TButton", command=self.logout).pack(side="bottom", fill="x", padx=18, pady=18)
        self.page("Главная")

    def header(self, title, subtitle):
        tk.Label(self.content, text=title, bg=BG, fg=TEXT, font=("Segoe UI",28,"bold")).pack(anchor="w", padx=38, pady=(34,4))
        tk.Label(self.content, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI",10)).pack(anchor="w", padx=40, pady=(0,25))

    def page(self, title):
        for w in self.content.winfo_children(): w.destroy()
        for b in self.nav:
            active = title in b.cget("text")
            b.configure(bg=PANEL2 if active else PANEL, fg=TEXT if active else MUTED)
        subtitles = {
            "Главная":"Центр управления подготовкой по законодательству RMRP.",
            "Законодательство":"Законы, статьи и материалы сервера в одном месте.",
            "Поиск":"Быстрый поиск по базе законодательства.",
            "Помощь нейросети":"Помощник, который должен опираться на базу RMRP.",
            "Проверь себя":"Тесты для подготовки к переаттестации.",
            "Избранное":"Сохранённые статьи и материалы.",
            "История":"История обучения и результатов.",
            "Настройки":"Параметры аккаунта и приложения."
        }
        self.header(title, subtitles[title])
        if title == "Главная": self.home()
        elif title == "Законодательство": self.laws()
        elif title == "Поиск": self.search_page()
        elif title == "Проверь себя": self.tests()
        elif title == "Настройки": self.settings()
        else:
            self.placeholder(title)

    def card(self, parent, title, text):
        f=tk.Frame(parent,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); f.pack(fill="x", pady=7)
        tk.Label(f,text=title,bg=PANEL,fg=TEXT,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=20,pady=(17,4))
        tk.Label(f,text=text,bg=PANEL,fg=MUTED,font=("Segoe UI",10),wraplength=800,justify="left").pack(anchor="w",padx=20,pady=(0,17))
        return f

    def home(self):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="x",padx=38)
        name=self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        role=self.prof.get("role","USER")
        self.card(wrap,"Добро пожаловать, " + name, f"Роль: {role}\nПодключение к Supabase активно. Здесь будет твой основной рабочий центр.")
        self.card(wrap,"Быстрый старт","📚 Законодательство — база законов\n✓ Проверь себя — тесты\n⌕ Поиск — поиск по материалам\n✦ Помощь нейросети — интеллектуальный помощник")

    def laws(self):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="both",expand=True,padx=38)
        for x in ["ФЗ о государственной службе №54-ФЗ","Уголовный кодекс РФ","КоАП РФ","Процессуальный кодекс РФ","ФЗ о полиции №74-ФЗ","ФЗ о ФСВНГ №18-ФЗ"]:
            self.card(wrap,x,"Раздел подготовлен под материалы RMRP. Контент можно наполнять из базы Supabase.")

    def search_page(self):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="x",padx=38)
        e=ttk.Entry(wrap); e.pack(side="left",fill="x",expand=True,ipady=5)
        ttk.Button(wrap,text="Поиск",command=lambda: messagebox.showinfo("Поиск","Поиск по базе будет подключён к таблице law_articles.")).pack(side="left",padx=10)

    def tests(self):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="x",padx=38)
        for x in ["ФЗ о госслужбе","УК РФ","КоАП РФ","Процессуальный кодекс","ФЗ о полиции","ФЗ о ФСВНГ","Тест СК","Смешанный тест"]:
            self.card(wrap,x,"Нажми, чтобы открыть тест. Система результатов будет сохраняться в Supabase.")

    def settings(self):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="x",padx=38)
        name=self.prof.get("display_name") or self.prof.get("username") or "—"
        role=self.prof.get("role","USER")
        self.card(wrap,"Аккаунт",f"Имя: {name}\nРоль: {role}\nPremium: {'Да' if self.prof.get('premium') else 'Нет'}")
        self.card(wrap,"Версия","RMRP Помощник v1.0 • by Kinzec X WOLF")

    def placeholder(self,title):
        wrap=tk.Frame(self.content,bg=BG); wrap.pack(fill="x",padx=38)
        self.card(wrap,title,"Раздел уже создан в интерфейсе. Следующим этапом его можно подключить к данным Supabase.")

    def logout(self):
        self.token=None; self.user=None; self.prof={}; self.show_login()


if __name__ == "__main__":
    App().mainloop()
