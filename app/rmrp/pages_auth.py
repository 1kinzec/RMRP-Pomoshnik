"""Экран входа / регистрации / гостевой режим."""
import re
import tkinter as tk
from datetime import datetime, timezone

from . import ui
from .config import ACCENT_HI, APP_NAME, APP_PUBLISHER, APP_VERSION, BG, BG2, FONT, MUTED, PANEL2, TEXT, TEXT2, ACCENT_TXT, STATUS_RU

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9_.-]{3,32}$")


class AuthPages:
    # ------------------------------------------------------------------ каркас
    def show_login(self, tab="login", prefill=""):
        self.clear_root()
        self.guest = False
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        hero = tk.Canvas(shell, bg=BG2, highlightthickness=0, bd=0)
        hero.place(relx=0, rely=0, relwidth=.55, relheight=1)
        self._hero_refs = []

        def draw(e=None):
            w, h = hero.winfo_width(), hero.winfo_height()
            if w < 50:
                return
            hero.delete("all")
            self._hero_refs.clear()
            bgimg = ui.make_hero(max(w, 760), max(h, 900))
            if bgimg:
                self._hero_refs.append(bgimg)
                hero.create_image(0, 0, image=bgimg, anchor="nw")
            logo = ui.load_image("rmrp.png", (190, 190))
            if logo:
                self._hero_refs.append(logo)
                hero.create_image(w / 2, h * .30, image=logo)
            hero.create_text(w / 2, h * .56, text="RMRP Помощник", fill=TEXT, font=(FONT, 30, "bold"))
            hero.create_text(w / 2, h * .62, text=f"by {APP_PUBLISHER}", fill=ACCENT_HI, font=(FONT, 13, "bold"))
            hero.create_text(w / 2, h * .70, text="Ваш надёжный помощник\nв изучении законов RMRP", fill=TEXT2, font=(FONT, 11), justify="center")
            hero.create_text(22, h - 22, text=f"Версия {APP_VERSION}", fill=MUTED, font=(FONT, 9), anchor="sw")
        hero.bind("<Configure>", draw)

        side = tk.Frame(shell, bg=BG)
        side.place(relx=.55, rely=0, relwidth=.45, relheight=1)
        box = tk.Frame(side, bg=BG, width=372, height=640)
        box.pack_propagate(False)
        box.place(relx=.5, rely=.5, anchor="center")
        self._auth_box = box
        self._auth_tabs = ui.UnderTabs(box, [("login", "Вход"), ("register", "Регистрация")], self._auth_switch, selected=tab)
        self._auth_tabs.pack(fill="x")
        tk.Frame(box, bg=ui.BORDER, height=1).pack(fill="x", pady=(0, 18))
        self._auth_form = tk.Frame(box, bg=BG)
        self._auth_form.pack(fill="x")
        self._auth_busy = False
        self._auth_switch(tab, prefill)

    def _auth_switch(self, tab, prefill=""):
        for w in self._auth_form.winfo_children():
            w.destroy()
        (self._build_login if tab == "login" else self._build_register)(self._auth_form, prefill)

    @staticmethod
    def _field_label(parent, text):
        ui.lbl(parent, text, 9, False, TEXT2).pack(anchor="w", pady=(10, 5))

    # ------------------------------------------------------------------ вход
    def _build_login(self, f, prefill=""):
        self._field_label(f, "Имя пользователя / Email")
        self.f_login = ui.Field(f, "Введите логин или email", on_return=self.do_login, icon="♙")
        self.f_login.pack(fill="x")
        self._field_label(f, "Пароль")
        self.f_pass = ui.Field(f, "Введите пароль", secret=True, on_return=self.do_login, icon="🔒")
        self.f_pass.pack(fill="x")
        saved = prefill or (self.settings.get("last_login", "") if self.settings.get("remember", True) else "")
        if saved:
            self.f_login.set(saved)
            self.f_pass.focus_entry()
        else:
            self.f_login.focus_entry()
        self.v_remember = tk.BooleanVar(value=bool(self.settings.get("remember", True)))
        tk.Checkbutton(f, text="Запомнить меня", variable=self.v_remember, bg=BG, fg=TEXT2, selectcolor=PANEL2, activebackground=BG,
                       activeforeground=TEXT, font=(FONT, 9), bd=0, highlightthickness=0, cursor="hand2").pack(anchor="w", pady=(12, 14))
        self.btn_login = ui.RButton(f, "Войти", self.do_login, height=42, size=11)
        self.btn_login.pack(fill="x")
        link = tk.Label(f, text="Забыли пароль?", font=(FONT, 9), fg=ACCENT_TXT, bg=BG, cursor="hand2")
        link.pack(pady=12)
        link.bind("<Button-1>", lambda e: self.do_forgot())
        row = tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=(2, 12))
        tk.Frame(row, bg=ui.BORDER, height=1).pack(side="left", fill="x", expand=True, pady=8)
        tk.Label(row, text="  или  ", font=(FONT, 9), fg=MUTED, bg=BG).pack(side="left")
        tk.Frame(row, bg=ui.BORDER, height=1).pack(side="left", fill="x", expand=True, pady=8)
        ui.RButton(f, "Продолжить как гость", self.do_guest, "secondary", height=40).pack(fill="x")

    def do_login(self):
        ident, password = self.f_login.get(), self.f_pass.raw()
        if not ident or not password:
            self.notify(APP_NAME, "Введите логин (или email) и пароль.", "warning")
            return
        if self._auth_busy:
            return
        self._auth_busy = True
        self.btn_login.configure_text("Входим…")
        self.btn_login.set_disabled(True)

        def work():
            email = ident
            if "@" not in ident:
                try:
                    res = self.db.rpc("login_email", {"p_username": ident})
                except Exception:  # noqa: BLE001
                    res = None
                email = res if isinstance(res, str) else None
                if not email:
                    raise RuntimeError("Пользователь с таким логином не найден. Попробуйте войти по email.")
            data = self.db.auth_login(email, password)
            user = data.get("user") or {}
            if not self.db.access_token or not user.get("id"):
                raise RuntimeError("Сервер не вернул активную сессию.")
            rows = self.db.table("profiles", "*", {"id": f"eq.{user['id']}"})
            if not rows:
                self.db.auth_logout()
                raise RuntimeError("Профиль пользователя не найден. Проверьте SQL-триггер profiles.")
            prof = rows[0]
            if prof.get("status") != "ACTIVE":
                self.db.auth_logout()
                raise RuntimeError(f"Доступ закрыт. Статус аккаунта: {STATUS_RU.get(prof.get('status'), prof.get('status'))}.")
            now = datetime.now(timezone.utc).isoformat()
            try:
                self.db.update("profiles", {"id": f"eq.{user['id']}"}, {"last_login": now, "last_seen_at": now})
            except Exception:  # noqa: BLE001
                try:
                    self.db.update("profiles", {"id": f"eq.{user['id']}"}, {"last_login": now})
                except Exception:  # noqa: BLE001
                    pass
            return user, prof

        def done(res):
            self._auth_busy = False
            self.user, self.prof = res
            self.guest = False
            self.settings["remember"] = bool(self.v_remember.get())
            self.settings["last_login"] = ident if self.settings["remember"] else ""
            self.save_settings()
            self.show_main()
            self.start_session()

        def fail(e):
            self._auth_busy = False
            try:
                self.btn_login.configure_text("Войти")
                self.btn_login.set_disabled(False)
            except tk.TclError:
                pass
            self.notify("Не удалось войти", self._friendly(e), "error")
        self.bg(work, done, fail, bound=False)

    @staticmethod
    def _friendly(e):
        m = str(e)
        if "Invalid login credentials" in m:
            return "Неверный логин или пароль."
        if "Email not confirmed" in m:
            return "Подтвердите email — письмо отправлено при регистрации."
        return m

    def do_guest(self):
        self.guest = True
        self.user, self.prof = {}, {"role": "GUEST", "display_name": "Гость", "username": "guest"}
        self.db.access_token = None
        self.show_main()
        self.notify("Гостевой режим", "Доступны законы, поиск, помощник и тесты без сохранения результатов.", "info", 5000)

    def do_forgot(self):
        email = ui.ask_text(self, "Восстановление пароля", "Email вашего аккаунта", self.f_login.get() if "@" in self.f_login.get() else "",
                            ok_text="Отправить письмо")
        if not email:
            return
        if not EMAIL_RE.match(email):
            self.notify("Восстановление", "Введите корректный email.", "warning")
            return
        self.bg(lambda: self.db.auth_recover(email),
                lambda _: self.notify("Письмо отправлено", "Проверьте почту — там ссылка для смены пароля.", "success", 6000), bound=False)

    # ------------------------------------------------------------------ регистрация
    def _build_register(self, f, prefill=""):
        self.r = {}
        for key, label, ph, secret in [("email", "Email", "name@example.com", False), ("username", "Логин", "3–32 символа", False),
                                       ("display", "Отображаемое имя (необязательно)", "Как вас называть", False),
                                       ("p1", "Пароль", "Минимум 6 символов", True), ("p2", "Повторите пароль", "Ещё раз пароль", True)]:
            self._field_label(f, label)
            fld = ui.Field(f, ph, secret=secret, on_return=self.do_register, height=38)
            fld.pack(fill="x")
            self.r[key] = fld
        self.r["email"].focus_entry()
        self.btn_reg = ui.RButton(f, "Создать аккаунт", self.do_register, height=42, size=11)
        self.btn_reg.pack(fill="x", pady=(18, 0))

    def do_register(self):
        v = {k: (w.raw() if k in ("p1", "p2") else w.get()) for k, w in self.r.items()}
        if not v["email"] or not v["username"] or not v["p1"]:
            self.notify(APP_NAME, "Заполните email, логин и пароль.", "warning")
            return
        if not EMAIL_RE.match(v["email"]):
            self.notify(APP_NAME, "Введите корректный email.", "warning")
            return
        if not USERNAME_RE.match(v["username"]):
            self.notify(APP_NAME, "Логин: 3–32 символа — буквы, цифры, _ . -", "warning")
            return
        if len(v["p1"]) < 6:
            self.notify(APP_NAME, "Пароль должен содержать минимум 6 символов.", "warning")
            return
        if v["p1"] != v["p2"]:
            self.notify(APP_NAME, "Пароли не совпадают.", "warning")
            return
        self.btn_reg.set_disabled(True)

        def work():
            return self.db.auth_register(v["email"], v["p1"], v["username"], v["display"] or v["username"])

        def done(_):
            self.notify("Аккаунт создан", "Если включено подтверждение email — подтвердите почту, затем войдите.", "success", 6000)
            self.show_login("login", v["username"])

        def fail(e):
            try:
                self.btn_reg.set_disabled(False)
            except tk.TclError:
                pass
            msg = str(e)
            if "already registered" in msg or "duplicate" in msg.lower():
                msg = "Такой email или логин уже зарегистрирован."
            self.notify("Ошибка регистрации", msg, "error")
        self.bg(work, done, fail, bound=False)
