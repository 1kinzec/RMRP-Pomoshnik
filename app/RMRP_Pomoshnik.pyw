import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
import threading
import math
try:
    import winsound
except ImportError:
    winsound = None
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

APP_NAME = "RMRP Помощник"
APP_VERSION = "1.3.0"
APP_PUBLISHER = "Kinzec X WOLF"
SUPABASE_URL = "https://cyihqnquxaxnonjbvshm.supabase.co"
SUPABASE_KEY = "sb_publishable_3X8WkqV57kAqB8v6KS458A_mPnSBBRK"

BG = "#0b0f17"
PANEL = "#121a28"
PANEL2 = "#172235"
ACCENT = "#3b82f6"
ACCENT2 = "#60a5fa"
TEXT = "#f4f7fb"
MUTED = "#91a0b8"
BORDER = "#223049"
DANGER = "#ef4444"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"

ROLE_INFO = {
    "FOUNDER": ("👑", "Основатель"),
    "ADMIN": ("🛡️", "Администратор"),
    "MODERATOR": ("🔨", "Модератор"),
    "PREMIUM": ("⭐", "Премиум пользователь"),
    "USER": ("👤", "Пользователь"),
}
ROLE_ORDER = ["FOUNDER", "ADMIN", "MODERATOR", "PREMIUM", "USER"]
STATUS_VALUES = ["ACTIVE", "BLOCKED", "BANNED"]


def role_label(role):
    icon, name = ROLE_INFO.get(role, ROLE_INFO["USER"])
    return f"{icon} {name}"


def q(value):
    return urllib.parse.quote(str(value), safe="")


class Supabase:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None

    def request(self, path, method="GET", body=None, token=None, headers=None):
        h = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
        if token or self.access_token:
            h["Authorization"] = f"Bearer {token or self.access_token}"
        if headers:
            h.update(headers)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
            except Exception:
                detail = raw
            if isinstance(detail, dict):
                msg = detail.get("message") or detail.get("msg") or detail.get("error_description") or detail.get("error")
            else:
                msg = str(detail)
            raise RuntimeError(msg or f"HTTP {e.code}")
        except Exception as e:
            raise RuntimeError(f"Ошибка соединения: {e}")

    def auth_login(self, email, password):
        data = self.request("/auth/v1/token?grant_type=password", "POST", {"email": email, "password": password})
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        return data

    def auth_register(self, email, password, username, display_name):
        return self.request("/auth/v1/signup", "POST", {
            "email": email,
            "password": password,
            "data": {"username": username, "display_name": display_name or username}
        })

    def auth_logout(self):
        if self.access_token:
            try:
                self.request("/auth/v1/logout", "POST")
            except Exception:
                pass
        self.access_token = None
        self.refresh_token = None

    def table(self, table, select="*", filters=None, order=None, limit=None):
        params = {"select": select}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        path = f"/rest/v1/{table}?" + urllib.parse.urlencode(params, safe="(),.*%")
        return self.request(path)

    def insert(self, table, rows, select="*"):
        return self.request(
            f"/rest/v1/{table}?select={q(select)}",
            "POST",
            rows,
            headers={"Prefer": "return=representation"},
        )

    def update(self, table, filters, values, select="*"):
        params = {"select": select}
        params.update(filters)
        path = f"/rest/v1/{table}?" + urllib.parse.urlencode(params, safe="(),.*%")
        return self.request(path, "PATCH", values, headers={"Prefer": "return=representation"})

    def delete(self, table, filters):
        params = filters
        path = f"/rest/v1/{table}?" + urllib.parse.urlencode(params, safe="(),.*%")
        return self.request(path, "DELETE", headers={"Prefer": "return=minimal"})

    def rpc(self, fn, payload):
        return self.request(f"/rest/v1/rpc/{fn}", "POST", payload)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION} — by Kinzec X WOLF")
        self.geometry("1360x820")
        self.minsize(1120, 720)
        self.configure(bg=BG)
        self.db = Supabase()
        self.user = {}
        self.prof = {}
        self.nav_buttons = {}
        self.content = None
        self._hover_jobs = {}
        self._styles()
        self.show_login()

    def _styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TButton", background=ACCENT, foreground="white", borderwidth=0, padding=(16, 10), font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("TButton", background=[("active", "#2563eb"), ("pressed", "#1d4ed8")], foreground=[("disabled", "#64748b")])
        s.configure("Secondary.TButton", background=PANEL2, foreground=TEXT, borderwidth=1, padding=(16, 10), font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Secondary.TButton", background=[("active", "#1e3352"), ("pressed", "#263d60")])
        s.configure("Danger.TButton", background=DANGER, foreground="white", padding=(16, 10), font=("Segoe UI", 10, "bold"), relief="flat")
        s.configure("Success.TButton", background=SUCCESS, foreground="white", padding=(16, 10), font=("Segoe UI", 10, "bold"), relief="flat")
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=38, borderwidth=0, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", background="#101a2b", foreground=MUTED, font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", "white")])
        s.configure("TCombobox", fieldbackground="#0d1522", foreground=TEXT, background=PANEL2, arrowcolor=ACCENT2)
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=4)
        s.configure("TNotebook.Tab", background="#111b2c", foreground=MUTED, padding=(18, 10), font=("Segoe UI", 9, "bold"))
        s.map("TNotebook.Tab", background=[("selected", "#1d4ed8")], foreground=[("selected", "white")])

    def play_sound(self, kind="click"):
        if winsound is None:
            try: self.bell()
            except Exception: pass
            return
        tones = {
            "click": [(740, 28)],
            "hover": [(560, 18)],
            "success": [(660, 45), (880, 55)],
            "error": [(300, 70), (220, 90)],
            "open": [(520, 25), (700, 35)],
        }
        def run():
            try:
                for freq, dur in tones.get(kind, tones["click"]): winsound.Beep(freq, dur)
            except Exception: pass
        threading.Thread(target=run, daemon=True).start()

    def animate_in(self, widget):
        widget.update_idletasks()
        widget.place_configure() if widget.winfo_manager() == "place" else None
        try:
            widget.attributes("-alpha", 0.0)
            def step(i=0):
                a=min(1.0, i/10)
                try: widget.attributes("-alpha", a)
                except Exception: return
                if a < 1: self.after(18, lambda: step(i+1))
            step()
        except Exception:
            pass

    def pulse_button(self, button, active_bg="#2563eb"):
        old = button.cget("bg")
        button.configure(bg=active_bg, fg="white")
        self.after(100, lambda: button.configure(bg=old))
        self.play_sound("click")

    def make_nav_button(self, parent, icon, title):
        b = tk.Button(parent, text=f"{icon}   {title}", command=lambda t=title: (self.play_sound("click"), self.page(t)), anchor="w", bd=0, relief="flat", bg=PANEL, fg=MUTED, activebackground="#1b2c47", activeforeground=TEXT, font=("Segoe UI", 10, "bold"), padx=18, pady=10, cursor="hand2", highlightthickness=0)
        b.pack(fill="x", padx=9, pady=2)
        b.bind("<Enter>", lambda e: self._nav_hover(b, True))
        b.bind("<Leave>", lambda e: self._nav_hover(b, False))
        return b

    def _nav_hover(self, b, entered):
        title = next((k for k,v in self.nav_buttons.items() if v is b), None)
        if title and b.cget("bg") == PANEL2: return
        b.configure(bg="#172b47" if entered else PANEL, fg=TEXT if entered else MUTED)
        if entered: self.play_sound("hover")

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def logo_mark(self, parent, size=74):
        c=tk.Canvas(parent, width=size, height=size, bg=parent.cget("bg"), highlightthickness=0)
        c.pack(pady=(20,8))
        cx=size/2; cy=size/2
        c.create_polygon(cx,7,size-9,18,size-13,size-5, cx,size-8, 13,size-5,9,18, fill="#162a48", outline="#3b82f6", width=2)
        c.create_text(cx, cy+1, text="⚖", fill="#7db5ff", font=("Segoe UI Symbol", int(size*.34), "bold"))
        return c

    def _gradient_canvas(self, parent):
        c = tk.Canvas(parent, bg="#07111f", highlightthickness=0)
        c.pack(fill="both", expand=True)
        def draw(_=None):
            w=max(c.winfo_width(),1); h=max(c.winfo_height(),1)
            c.delete("all")
            # deep blue vertical gradient
            for i in range(26):
                y0=int(h*i/26); y1=int(h*(i+1)/26)
                ratio=i/25
                r=int(5+5*ratio); g=int(13+11*ratio); b=int(27+24*ratio)
                c.create_rectangle(0,y0,w,y1,fill=f"#{r:02x}{g:02x}{b:02x}",outline="")
            # atmospheric glows
            for cx,cy,rad,col in [(int(w*.22),int(h*.22),260,"#123b73"),(int(w*.72),int(h*.10),230,"#0c2850"),(int(w*.55),int(h*.72),310,"#071d3a")]:
                for rr in range(rad,20,-18):
                    alpha=1-rr/rad
                    base=(10,45,90)
                    c.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,fill="#"+"%02x%02x%02x"%tuple(int(base[j]*alpha+5*(1-alpha)) for j in range(3)),outline="")
            # skyline
            base=h*.78
            buildings=[(.02,.20),(.09,.34),(.15,.25),(.22,.48),(.30,.30),(.37,.62),(.46,.40),(.54,.52),(.63,.30),(.70,.58),(.79,.38),(.87,.50),(.95,.28)]
            for frac, bh in buildings:
                x=frac*w; bw=max(38,w*.065)
                c.create_rectangle(x,base-h*bh*.55,x+bw,base,fill="#07111d",outline="#173454")
                for yy in range(int(base-h*bh*.5),int(base-12),22):
                    for xx in range(int(x+10),int(x+bw-8),18):
                        c.create_rectangle(xx,yy,xx+5,yy+7,fill="#173b68",outline="")
            # road / vehicle silhouette
            c.create_polygon(w*.08,h*.92,w*.27,h*.84,w*.56,h*.84,w*.77,h*.92,w*.77,h,w*.08,h,fill="#050a12",outline="")
            c.create_line(w*.18,h*.93,w*.72,h*.93,fill="#1b3d63",width=2)
            c.create_text(w*.50,h*.10,text="RMRP",fill="#3d6b9e",font=("Segoe UI",28,"bold"))
        c.bind("<Configure>",draw)
        return c

    def show_login(self):
        self.clear()
        root=tk.Frame(self,bg=BG); root.pack(fill="both",expand=True)
        visual=tk.Frame(root,bg="#07111f"); visual.place(relx=0,rely=0,relwidth=.56,relheight=1)
        self._gradient_canvas(visual)
        overlay=tk.Frame(visual,bg="#06101c"); overlay.place(relx=0,rely=0,relwidth=1,relheight=1)
        tk.Label(overlay,text="⚖",bg="#06101c",fg="#62a8ff",font=("Segoe UI Symbol",72,"bold")).place(relx=.5,rely=.33,anchor="center")
        tk.Label(overlay,text="RMRP ПОМОЩНИК",bg="#06101c",fg=TEXT,font=("Segoe UI",28,"bold")).place(relx=.5,rely=.48,anchor="center")
        tk.Label(overlay,text="by Kinzec X WOLF",bg="#06101c",fg="#63a8ff",font=("Segoe UI",11,"bold")).place(relx=.5,rely=.535,anchor="center")
        tk.Label(overlay,text="Надёжный помощник в изучении законов RMRP",bg="#06101c",fg="#8da4c2",font=("Segoe UI",10)).place(relx=.5,rely=.59,anchor="center")
        # right auth area
        auth=tk.Frame(root,bg="#0a1422"); auth.place(relx=.56,rely=0,relwidth=.44,relheight=1)
        top=tk.Frame(auth,bg="#0a1422"); top.pack(fill="x",padx=44,pady=(34,0))
        tk.Label(top,text="RMRP Помощник",bg="#0a1422",fg=TEXT,font=("Segoe UI",11,"bold")).pack(side="left")
        tk.Label(top,text="v1.3.0",bg="#0a1422",fg="#526a88",font=("Segoe UI",8)).pack(side="right")
        card=tk.Frame(auth,bg="#0d1a2c",highlightbackground="#1e416b",highlightthickness=1)
        card.place(relx=.5,rely=.52,anchor="center",relwidth=.78,relheight=.62)
        tk.Label(card,text="Добро пожаловать",bg="#0d1a2c",fg=TEXT,font=("Segoe UI",23,"bold")).pack(anchor="w",padx=34,pady=(34,3))
        tk.Label(card,text="Войдите в аккаунт, чтобы продолжить",bg="#0d1a2c",fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=34,pady=(0,24))
        self.email=self.entry(card,"Email")
        self.password=self.entry(card,"Пароль",secret=True)
        tk.Checkbutton(card,text="Запомнить меня",bg="#0d1a2c",fg="#7e93ae",selectcolor="#0d1a2c",activebackground="#0d1a2c",activeforeground=TEXT,font=("Segoe UI",9),anchor="w").pack(fill="x",padx=34,pady=(2,8))
        btn=tk.Button(card,text="ВОЙТИ  →",command=self.do_login,bd=0,bg=ACCENT,fg="white",activebackground="#4b8fff",font=("Segoe UI",10,"bold"),cursor="hand2",pady=12)
        btn.pack(fill="x",padx=34,pady=(10,10)); btn.bind("<Enter>",lambda e:btn.configure(bg="#4b8fff")); btn.bind("<Leave>",lambda e:btn.configure(bg=ACCENT))
        tk.Label(card,text="или",bg="#0d1a2c",fg="#4e6380",font=("Segoe UI",8)).pack(pady=(3,8))
        ttk.Button(card,text="Создать аккаунт",style="Secondary.TButton",command=lambda:(self.play_sound("click"),self.show_register())).pack(fill="x",padx=34)
        tk.Label(card,text="Supabase Secure RLS • Защищённое подключение",bg="#0d1a2c",fg="#536a88",font=("Segoe UI",8)).pack(side="bottom",pady=18)

    def entry(self,parent,placeholder,secret=False):
        wrap=tk.Frame(parent,bg="#0d1522",highlightbackground="#233958",highlightthickness=1); wrap.pack(fill="x",padx=48,pady=7)
        e=tk.Entry(wrap,bg="#0d1522",fg=TEXT,insertbackground=TEXT,relief="flat",bd=0,font=("Segoe UI",10),show="•" if secret else "")
        e.pack(fill="x",padx=13,ipady=9); e.insert(0,placeholder); e.bind("<FocusIn>",lambda _:self._placeholder(e,placeholder,secret)); e.bind("<FocusIn>",lambda _:wrap.configure(highlightbackground=ACCENT),add="+"); e.bind("<FocusOut>",lambda _:wrap.configure(highlightbackground="#233958"),add="+")
        return e

    def _placeholder(self,widget,text,secret=False):
        if widget.get()==text:
            widget.delete(0,"end")
            if secret: widget.configure(show="•")

    def show_register(self):
        self.clear(); outer=tk.Frame(self,bg=BG); outer.pack(fill="both",expand=True)
        card=tk.Frame(outer,bg=PANEL,highlightbackground="#29456f",highlightthickness=1); card.place(relx=.5,rely=.5,anchor="center",width=540,height=700)
        self.logo_mark(card,60)
        tk.Label(card,text="Создание аккаунта",bg=PANEL,fg=TEXT,font=("Segoe UI",22,"bold")).pack()
        tk.Label(card,text="Создай профиль RMRP Помощника",bg=PANEL,fg=MUTED,font=("Segoe UI",9)).pack(pady=(3,20))
        self.r_email=self.entry(card,"Email"); self.r_username=self.entry(card,"Логин"); self.r_display=self.entry(card,"Отображаемое имя"); self.r_password=self.entry(card,"Пароль",secret=True); self.r_password2=self.entry(card,"Повтор пароля",secret=True)
        ttk.Button(card,text="ЗАРЕГИСТРИРОВАТЬСЯ",command=self.do_register).pack(fill="x",padx=48,pady=(16,9))
        ttk.Button(card,text="← Назад ко входу",style="Secondary.TButton",command=lambda:(self.play_sound("click"),self.show_login())).pack(fill="x",padx=48)

    def do_login(self):
        email = self.email.get().strip()
        password = self.password.get()
        if not email or email == "Email" or not password or password == "Пароль":
            messagebox.showwarning(APP_NAME, "Введите email и пароль.")
            return
        try:
            data = self.db.auth_login(email, password)
            self.user = data.get("user") or {}
            if not self.db.access_token or not self.user.get("id"):
                raise RuntimeError("Supabase не вернул активную сессию.")
            rows = self.db.table("profiles", "id,username,display_name,avatar_url,role,premium,status,allow_pranks,created_at,last_login,updated_at", {"id": f"eq.{self.user['id']}"})
            if not rows:
                raise RuntimeError("Профиль пользователя не найден. Проверь SQL-триггер profiles.")
            self.prof = rows[0]
            if self.prof.get("status") != "ACTIVE":
                self.db.auth_logout()
                raise RuntimeError(f"Доступ закрыт. Статус аккаунта: {self.prof.get('status')}.")
            try:
                self.db.update("profiles", {"id": f"eq.{self.user['id']}"}, {"last_login": datetime.utcnow().isoformat() + "Z"})
            except Exception:
                pass
            self.show_main()
        except Exception as e:
            messagebox.showerror("Ошибка входа", str(e))

    def do_register(self):
        email = self.r_email.get().strip()
        username = self.r_username.get().strip()
        display = self.r_display.get().strip()
        p1 = self.r_password.get()
        p2 = self.r_password2.get()
        if email in ("", "Email") or username in ("", "Логин") or p1 in ("", "Пароль"):
            messagebox.showwarning(APP_NAME, "Заполни обязательные поля.")
            return
        if len(p1) < 6:
            messagebox.showwarning(APP_NAME, "Пароль должен содержать минимум 6 символов.")
            return
        if p1 != p2:
            messagebox.showwarning(APP_NAME, "Пароли не совпадают.")
            return
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_.-]{3,32}", username):
            messagebox.showwarning(APP_NAME, "Логин: 3–32 символа, только буквы, цифры, _, ., -.")
            return
        try:
            data = self.db.auth_register(email, p1, username, display or username)
            if data.get("access_token"):
                self.db.access_token = data["access_token"]
            messagebox.showinfo(APP_NAME, "Аккаунт создан. Если включено подтверждение email — подтверди почту и войди.")
            self.show_login()
        except Exception as e:
            messagebox.showerror("Ошибка регистрации", str(e))

    def show_main(self):
        self.clear()
        shell=tk.Frame(self,bg=BG); shell.pack(fill="both",expand=True)
        sidebar=tk.Frame(shell,bg="#081321",width=236,highlightbackground="#17304d",highlightthickness=1); sidebar.pack(side="left",fill="y"); sidebar.pack_propagate(False)
        head=tk.Frame(sidebar,bg="#081321"); head.pack(fill="x",padx=17,pady=(20,18))
        tk.Label(head,text="⚖",bg="#081321",fg="#62a8ff",font=("Segoe UI Symbol",28,"bold")).pack(side="left")
        brand=tk.Frame(head,bg="#081321"); brand.pack(side="left",padx=8)
        tk.Label(brand,text="RMRP ПОМОЩНИК",bg="#081321",fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w")
        tk.Label(brand,text="by Kinzec X WOLF",bg="#081321",fg="#5e9fff",font=("Segoe UI",7,"bold")).pack(anchor="w")
        tk.Frame(sidebar,bg="#1b3658",height=1).pack(fill="x",padx=15,pady=(0,12))
        self.content=tk.Frame(shell,bg="#091321"); self.content.pack(side="left",fill="both",expand=True)
        self.nav_buttons={}
        base=[("⌂","Главная"),("▤","Законодательство"),("⌕","Поиск"),("✦","Помощь нейросети"),("✓","Проверь себя"),("★","Избранное"),("◷","История"),("♙","Профиль")]
        role=self.prof.get("role","USER")
        for icon,title in base:
            self.nav_buttons[title]=self.make_nav_button(sidebar,icon,title)
        spacer=tk.Frame(sidebar,bg="#081321"); spacer.pack(fill="both",expand=True)
        if role in ("MODERATOR","ADMIN","FOUNDER"):
            self.nav_buttons["Жалобы"]=self.make_nav_button(sidebar,"⚠","Жалобы")
        if role in ("ADMIN","FOUNDER"):
            self.nav_buttons["Администрирование"]=self.make_nav_button(sidebar,"⚙","Администрирование")
        self.nav_buttons["Настройки"]=self.make_nav_button(sidebar,"⚙","Настройки")
        tk.Frame(sidebar,bg="#1b3658",height=1).pack(fill="x",padx=15,pady=12)
        name=self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        profile=tk.Frame(sidebar,bg="#0d1c2e",highlightbackground="#1d4168",highlightthickness=1); profile.pack(fill="x",padx=12,pady=2)
        tk.Label(profile,text="●  ONLINE",bg="#0d1c2e",fg="#35d58a",font=("Segoe UI",7,"bold")).pack(anchor="w",padx=11,pady=(8,0))
        tk.Label(profile,text=name,bg="#0d1c2e",fg=TEXT,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=11,pady=(2,0))
        tk.Label(profile,text=role_label(role),bg="#0d1c2e",fg="#79adf2",font=("Segoe UI",7,"bold")).pack(anchor="w",padx=11,pady=(0,9))
        out=tk.Button(sidebar,text="⎋   Выйти",command=self.logout,bd=0,bg="#281923",fg="#ff7d91",activebackground="#442431",font=("Segoe UI",9,"bold"),cursor="hand2",pady=9); out.pack(fill="x",padx=12,pady=12)
        self.page("Главная")

    def header(self,title,subtitle=""):
        top=tk.Frame(self.content,bg="#091321"); top.pack(fill="x",padx=28,pady=(18,12))
        row=tk.Frame(top,bg="#091321"); row.pack(fill="x")
        left=tk.Frame(row,bg="#091321"); left.pack(side="left")
        tk.Label(left,text=title,bg="#091321",fg=TEXT,font=("Segoe UI",21,"bold")).pack(anchor="w")
        if subtitle: tk.Label(left,text=subtitle,bg="#091321",fg="#748aa6",font=("Segoe UI",8)).pack(anchor="w",pady=(2,0))
        userbox=tk.Frame(row,bg="#0d1c2e",highlightbackground="#1b3c60",highlightthickness=1); userbox.pack(side="right")
        tk.Label(userbox,text="●",bg="#0d1c2e",fg="#35d58a",font=("Segoe UI",10)).pack(side="left",padx=(9,3),pady=6)
        tk.Label(userbox,text=self.prof.get("display_name") or self.prof.get("username") or "Пользователь",bg="#0d1c2e",fg=TEXT,font=("Segoe UI",8,"bold")).pack(side="left",padx=(0,10),pady=6)
        line=tk.Frame(top,bg="#17385f",height=1); line.pack(fill="x",pady=(12,0))
        accent=tk.Frame(top,bg=ACCENT,height=2); accent.place(x=0,y=top.winfo_height()-2,width=120)
        self.after(50,lambda: self._animate_accent(accent,top))

    def _animate_accent(self, accent, parent, width=60):
        try:
            target=max(180,min(420,parent.winfo_width()))
            width=min(target,width+24); accent.place_configure(width=width)
            if width<target: self.after(18,lambda:self._animate_accent(accent,parent,width))
        except Exception: pass

    def page(self, title):
        for w in self.content.winfo_children(): w.destroy()
        self.play_sound("open")
        for name,b in self.nav_buttons.items():
            active=name==title
            b.configure(bg="#17345d" if active else PANEL,fg="#ffffff" if active else MUTED)
        subtitles = {
            "Главная": "Центр подготовки и управления RMRP.",
            "Законодательство": "Законы, статьи и материалы сервера.",
            "Поиск": "Поиск по названиям и содержанию статей.",
            "Помощь нейросети": "База знаний без выдумывания ответов: сначала поиск по законам RMRP.",
            "Проверь себя": "Тесты с сохранением результатов в Supabase.",
            "Избранное": "Сохранённые статьи.",
            "История": "Результаты обучения.",
            "Настройки": "Профиль, безопасность и настройки приложения.",
            "Жалобы": "Обращения пользователей и модерация.",
            "Администрирование": "Управление пользователями, законами, тестами и системой."
        }
        self.header(title, subtitles.get(title, ""))
        pages = {
            "Главная": self.home,
            "Законодательство": self.laws,
            "Поиск": self.search_page,
            "Помощь нейросети": self.ai_page,
            "Проверь себя": self.tests,
            "Избранное": self.favorites_page,
            "История": self.history_page,
            "Настройки": self.settings,
            "Профиль": self.settings,
            "Жалобы": self.reports_page,
            "Администрирование": self.admin_page,
        }
        pages.get(title, self.home)()

    def scroll_area(self):
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True, padx=38, pady=(0, 20))
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return inner

    def card(self,parent,title,text,button=None,command=None):
        f=tk.Frame(parent,bg=PANEL,highlightbackground="#1d3556",highlightthickness=1); f.pack(fill="x",pady=6)
        f.bind("<Enter>",lambda e:f.configure(highlightbackground="#2d5d9c")); f.bind("<Leave>",lambda e:f.configure(highlightbackground="#1d3556"))
        body=tk.Frame(f,bg=PANEL); body.pack(side="left",fill="both",expand=True)
        tk.Label(body,text=title,bg=PANEL,fg=TEXT,font=("Segoe UI",12,"bold"),anchor="w").pack(fill="x",padx=18,pady=(15,4))
        tk.Label(body,text=text,bg=PANEL,fg=MUTED,font=("Segoe UI",9),wraplength=900,justify="left",anchor="w").pack(fill="x",padx=18,pady=(0,15))
        if button:
            b=tk.Button(f,text=button+"  →",command=lambda:(self.play_sound("click"),command()),bd=0,bg="#17345d",fg="#9cc6ff",activebackground=ACCENT,activeforeground="white",font=("Segoe UI",9,"bold"),cursor="hand2",padx=16,pady=8); b.pack(side="right",padx=15,pady=15)
            b.bind("<Enter>",lambda e:b.configure(bg="#24538e")); b.bind("<Leave>",lambda e:b.configure(bg="#17345d"))
        return f

    def tile(self, parent, title, text, icon="▣", accent=ACCENT, button_text="Открыть", command=None):
        f=tk.Frame(parent,bg="#0d1b2c",highlightbackground="#1a385a",highlightthickness=1)
        head=tk.Frame(f,bg="#0d1b2c"); head.pack(fill="x",padx=14,pady=(13,5))
        tk.Label(head,text=icon,bg="#102b4b",fg=accent,font=("Segoe UI Symbol",15,"bold"),width=3,pady=5).pack(side="left")
        tk.Label(head,text=title,bg="#0d1b2c",fg=TEXT,font=("Segoe UI",10,"bold"),wraplength=240,justify="left").pack(side="left",padx=10,anchor="w")
        tk.Label(f,text=text,bg="#0d1b2c",fg="#7890ad",font=("Segoe UI",8),wraplength=280,justify="left",anchor="nw").pack(fill="both",expand=True,padx=14,pady=(2,8))
        if command:
            b=tk.Button(f,text=button_text+"  →",command=lambda:(self.play_sound("click"),command()),bd=0,bg="#0e4f9d",fg="white",activebackground="#1675dd",font=("Segoe UI",8,"bold"),cursor="hand2",pady=7)
            b.pack(fill="x",padx=14,pady=(0,12))
            b.bind("<Enter>",lambda e:b.configure(bg="#1675dd")); b.bind("<Leave>",lambda e:b.configure(bg="#0e4f9d"))
        f.bind("<Enter>",lambda e:f.configure(highlightbackground="#2b70ba")); f.bind("<Leave>",lambda e:f.configure(highlightbackground="#1a385a"))
        return f

    def home(self):
        wrap=self.scroll_area(); name=self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        hero=tk.Frame(wrap,bg="#0d1c2e",highlightbackground="#214d7c",highlightthickness=1); hero.pack(fill="x",pady=(0,14))
        tk.Label(hero,text=f"Добро пожаловать, {name}!",bg="#0d1c2e",fg=TEXT,font=("Segoe UI",19,"bold")).pack(anchor="w",padx=22,pady=(18,2))
        tk.Label(hero,text="Сегодня отличный день для новых знаний.",bg="#0d1c2e",fg="#7e96b4",font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(0,18))
        grid=tk.Frame(wrap,bg="#091321"); grid.pack(fill="x")
        items=[("▤","Законодательство","30 законов RMRP","Открыть",lambda:self.page("Законодательство"),"#35a9ff"),("⌕","Поиск","Быстрый поиск по знаниям","Открыть",lambda:self.page("Поиск"),"#7e8dff"),("✦","Нейросеть","Задай вопрос ИИ","Открыть",lambda:self.page("Помощь нейросети"),"#31d5ae"),("▣","Тесты","Проверь свои знания","Начать",lambda:self.page("Проверь себя"),"#f2a43b")]
        for i,(ic,t,d,bt,cmd,ac) in enumerate(items):
            tile=self.tile(grid,t,d,ic,ac,bt,cmd); tile.grid(row=0,column=i,padx=(0 if i==0 else 5,5 if i<3 else 0),sticky="nsew"); tile.configure(height=150); grid.grid_columnconfigure(i,weight=1)
        lower=tk.Frame(wrap,bg="#091321"); lower.pack(fill="both",expand=True,pady=(14,0))
        for title,icon,accent in [("Последнее изученное","⚖","#58a8ff"),("Объявления","▣","#f1a53d")]:
            box=tk.Frame(lower,bg="#0d1b2c",highlightbackground="#1a385a",highlightthickness=1); box.pack(side="left",fill="both",expand=True,padx=(0,7) if title.startswith("Послед") else (7,0))
            tk.Label(box,text=title,bg="#0d1b2c",fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=16,pady=(14,8))
            if title.startswith("Послед"):
                rows=[("ФЗ «О полиции»","Статья 12. Порядок применения физической силы"),("УК РФ","Статья 228. Незаконный оборот наркотических средств"),("ФЗ «О ФСВНГ»","Статья 24. Полномочия войск национальной гвардии")]
            else:
                try: rows=[(a.get("title","Объявление"),(a.get("content") or "")[:100]) for a in self.db.table("announcements","title,content",{"is_active":"eq.true"},"created_at.desc",3)]
                except Exception: rows=[]
                if not rows: rows=[("Обновление законодательства","Следите за актуальными материалами RMRP.")]
            for a,b in rows:
                r=tk.Frame(box,bg="#102136"); r.pack(fill="x",padx=12,pady=4); tk.Label(r,text=icon,bg="#102136",fg=accent,font=("Segoe UI Symbol",12)).pack(side="left",padx=10,pady=8); qf=tk.Frame(r,bg="#102136"); qf.pack(side="left",fill="x",expand=True); tk.Label(qf,text=a,bg="#102136",fg=TEXT,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(7,0)); tk.Label(qf,text=b,bg="#102136",fg="#7189a7",font=("Segoe UI",7),wraplength=330,justify="left").pack(anchor="w",pady=(0,7))
        if self.prof.get("role") in ("ADMIN","FOUNDER"): self.card(wrap,"Администрирование","Управление пользователями, законами, тестами и системой.","Открыть",lambda:self.page("Администрирование"))

    def laws(self):
        wrap=self.scroll_area(); toolbar=tk.Frame(wrap,bg="#0d1b2c",highlightbackground="#1a385a",highlightthickness=1); toolbar.pack(fill="x",pady=(0,12))
        ttk.Entry(toolbar).pack(side="left",fill="x",expand=True,padx=10,pady=8,ipady=3); ttk.Button(toolbar,text="Обновить",command=self.laws).pack(side="right",padx=8,pady=7)
        if self.prof.get("role") in ("ADMIN","FOUNDER"): ttk.Button(toolbar,text="+ Закон",command=self.add_law).pack(side="right",pady=7)
        try: laws=self.db.table("laws","id,name,short_name,law_number,description,is_active",{"is_active":"eq.true"},"name.asc")
        except Exception as e: self.card(wrap,"Ошибка загрузки",str(e)); return
        grid=tk.Frame(wrap,bg="#091321"); grid.pack(fill="x")
        for i,law in enumerate(laws):
            text=" • ".join(x for x in [law.get("short_name"),law.get("law_number")] if x) or "Закон RMRP"
            tile=self.tile(grid,law.get("name","Без названия"),text,"⚖",["#2f9dff","#6878ff","#34d4aa","#f0a33c"][i%4],"Открыть",lambda lid=law["id"],name=law.get("name","Закон"):self.article_list(lid,name)); tile.grid(row=i//2,column=i%2,padx=(0,7) if i%2==0 else (7,0),pady=(0,10),sticky="nsew"); tile.configure(height=145)
        grid.grid_columnconfigure(0,weight=1); grid.grid_columnconfigure(1,weight=1)

    def add_law(self):
        if self.prof.get("role") not in ("ADMIN", "FOUNDER"):
            return
        name = simpledialog.askstring("Новый закон", "Название:")
        if not name: return
        short = simpledialog.askstring("Новый закон", "Короткое название:") or ""
        number = simpledialog.askstring("Новый закон", "Номер:") or ""
        desc = simpledialog.askstring("Новый закон", "Описание:") or ""
        try:
            self.db.insert("laws", {"name": name, "short_name": short, "law_number": number, "description": desc, "is_active": True})
            self.log("Создан закон", "laws", name)
            self.laws()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def article_list(self, law_id, law_name):
        self.page_header_replace(f"{law_name} — статьи", "")
        wrap = self.scroll_area()
        try:
            articles = self.db.table("law_articles", "id,article_number,title,content", {"law_id": f"eq.{law_id}"}, "article_number.asc")
        except Exception as e:
            self.card(wrap, "Ошибка", str(e)); return
        toolbar = tk.Frame(wrap, bg=BG); toolbar.pack(fill="x", pady=(0, 8))
        if self.prof.get("role") in ("ADMIN", "FOUNDER"):
            ttk.Button(toolbar, text="+ Статья", command=lambda: self.add_article(law_id, law_name)).pack(side="right")
        if not articles:
            self.card(wrap, "Статей пока нет", "Добавьте статьи через административную панель.")
        for a in articles:
            title = f"Статья {a.get('article_number', '')} — {a.get('title') or 'Без названия'}"
            self.card(wrap, title, a.get("content", ""), "Открыть", lambda x=a: self.article_view(x, law_name))

    def add_article(self, law_id, law_name):
        number = simpledialog.askstring("Новая статья", "Номер статьи:")
        if not number: return
        title = simpledialog.askstring("Новая статья", "Название:") or ""
        content = self.text_dialog("Текст статьи", "Вставьте текст статьи:")
        if content is None: return
        try:
            self.db.insert("law_articles", {"law_id": law_id, "article_number": number, "title": title, "content": content})
            self.log("Создана статья", "law_articles", f"{law_name} / {number}")
            self.article_list(law_id, law_name)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def article_view(self, article, law_name):
        win = tk.Toplevel(self); win.title(f"{law_name} — статья {article.get('article_number')}"); win.geometry("900x650"); win.configure(bg=BG)
        tk.Label(win, text=f"Статья {article.get('article_number')} — {article.get('title') or ''}", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold"), wraplength=820).pack(anchor="w", padx=25, pady=(22, 10))
        text = tk.Text(win, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 11), padx=18, pady=18)
        text.pack(fill="both", expand=True, padx=25, pady=10); text.insert("1.0", article.get("content", "")); text.configure(state="disabled")
        bar = tk.Frame(win, bg=BG); bar.pack(fill="x", padx=25, pady=15)
        ttk.Button(bar, text="Добавить в избранное", command=lambda: self.favorite(article["id"])).pack(side="left")
        ttk.Button(bar, text="Закрыть", style="Secondary.TButton", command=win.destroy).pack(side="right")

    def favorite(self, article_id):
        try:
            existing = self.db.table("favorites", "id", {"user_id": f"eq.{self.user['id']}", "law_article_id": f"eq.{article_id}"})
            if existing:
                self.db.delete("favorites", {"user_id": f"eq.{self.user['id']}", "law_article_id": f"eq.{article_id}"})
                messagebox.showinfo(APP_NAME, "Удалено из избранного.")
            else:
                self.db.insert("favorites", {"user_id": self.user["id"], "law_article_id": article_id})
                messagebox.showinfo(APP_NAME, "Добавлено в избранное.")
        except Exception as e:
            messagebox.showerror("Избранное", str(e))

    def search_page(self):
        wrap = self.scroll_area()
        bar = tk.Frame(wrap, bg=BG); bar.pack(fill="x", pady=(0, 10))
        e = ttk.Entry(bar); e.pack(side="left", fill="x", expand=True, ipady=4)
        result_box = tk.Frame(wrap, bg=BG); result_box.pack(fill="both", expand=True)
        def run_search():
            for w in result_box.winfo_children(): w.destroy()
            term = e.get().strip()
            if not term:
                return
            try:
                encoded_term = urllib.parse.quote(term, safe="")
                pattern = f"%{encoded_term}%"
                filters = {"or": f"(title.ilike.{pattern},content.ilike.{pattern},article_number.ilike.{pattern})"}
                articles = self.db.table("law_articles", "id,law_id,article_number,title,content", filters, "article_number.asc", 100)
                self.db.insert("search_history", {"user_id": self.user["id"], "query": term})
            except Exception as ex:
                self.card(result_box, "Ошибка поиска", str(ex)); return
            if not articles:
                self.card(result_box, "Ничего не найдено", "Попробуй другой запрос."); return
            for a in articles:
                snippet = re.sub(r"\s+", " ", a.get("content", ""))
                idx = snippet.lower().find(term.lower())
                if idx >= 0: snippet = ("…" if idx > 90 else "") + snippet[max(0, idx-90):idx+260] + ("…" if idx+260 < len(snippet) else "")
                self.card(result_box, f"Статья {a.get('article_number')} — {a.get('title') or 'Без названия'}", snippet, "Открыть", lambda x=a: self.article_view(x, "Результат поиска"))
        ttk.Button(bar, text="Поиск", command=run_search).pack(side="left", padx=8)

    def ai_page(self):
        wrap = self.scroll_area()
        self.card(wrap, "Как это работает", "Помощник сначала ищет совпадения в law_articles. Если точного материала нет, он прямо сообщает об отсутствии данных вместо выдуманного ответа.")
        box = tk.Frame(wrap, bg=PANEL, highlightbackground=BORDER, highlightthickness=1); box.pack(fill="x", pady=10)
        tk.Label(box, text="Вопрос", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(16, 5))
        inp = tk.Text(box, bg="#0f1724", fg=TEXT, insertbackground=TEXT, relief="flat", height=5, wrap="word", font=("Segoe UI", 10)); inp.pack(fill="x", padx=18, pady=(0, 10))
        answer = tk.Frame(box, bg=PANEL); answer.pack(fill="x", padx=18, pady=(0, 18))
        def ask():
            for w in answer.winfo_children(): w.destroy()
            question = inp.get("1.0", "end").strip()
            if not question: return
            terms = [x for x in re.findall(r"[A-Za-zА-Яа-яЁё0-9№.-]{3,}", question.lower()) if len(x) >= 4]
            try:
                found = []
                for term in terms[:5]:
                    encoded_term = urllib.parse.quote(term, safe="")
                    rows = self.db.table("law_articles", "id,law_id,article_number,title,content", {"or": f"(title.ilike.%{encoded_term}%,content.ilike.%{encoded_term}%)"}, "article_number.asc", 10)
                    for row in rows:
                        if row["id"] not in [x["id"] for x in found]: found.append(row)
                if found:
                    txt = "Нашёл в базе RMRP:\n\n" + "\n\n".join([f"Статья {x.get('article_number')} — {x.get('title') or ''}\n{x.get('content','')[:800]}" for x in found[:5]])
                    self.db.insert("ai_history", {"user_id": self.user["id"], "question": question, "answer": txt, "law_article_id": found[0]["id"]})
                else:
                    txt = "В базе law_articles нет подходящей статьи. Я не буду придумывать ответ — добавь нужный материал в законодательство."
                    self.db.insert("ai_history", {"user_id": self.user["id"], "question": question, "answer": txt})
            except Exception as ex:
                txt = f"Не удалось выполнить поиск по базе: {ex}"
            tk.Label(answer, text=txt, bg=PANEL, fg=TEXT, font=("Segoe UI", 10), wraplength=850, justify="left", anchor="w").pack(fill="x")
        ttk.Button(box, text="Найти ответ в базе", command=ask).pack(anchor="e", padx=18, pady=(0, 8))

    def tests(self):
        wrap=self.scroll_area()
        try: tests=self.db.table("tests","id,title,category,description,difficulty,question_count",{"is_active":"eq.true"},"title.asc")
        except Exception as e: self.card(wrap,"Ошибка",str(e)); return
        if not tests: self.card(wrap,"Тестов пока нет","Администратор может создать тесты через раздел «Администрирование»."); return
        grid=tk.Frame(wrap,bg="#091321"); grid.pack(fill="x")
        for i,test in enumerate(tests):
            desc=f"{test.get('question_count',0)} вопросов • {test.get('difficulty','MEDIUM')}\n{test.get('description') or 'Проверь свои знания.'}"
            tile=self.tile(grid,test.get("title","Тест"),desc,"▣",["#2f9dff","#6878ff","#30d5b0","#eaa13b"][i%4],"Начать",lambda t=test:self.start_test(t)); tile.grid(row=i//2,column=i%2,padx=(0,7) if i%2==0 else (7,0),pady=(0,10),sticky="nsew"); tile.configure(height=165)
        grid.grid_columnconfigure(0,weight=1); grid.grid_columnconfigure(1,weight=1)

    def start_test(self, test):
        try:
            questions = self.db.table("questions", "id,question,answer_a,answer_b,answer_c,answer_d,correct_answer,explanation", {"test_id": f"eq.{test['id']}"}, "id.asc")
        except Exception as e:
            messagebox.showerror("Тест", str(e)); return
        if not questions:
            messagebox.showinfo("Тест", "В этом тесте пока нет вопросов."); return
        win = tk.Toplevel(self); win.title(f"{test['title']} — RMRP Помощник"); win.geometry("900x650"); win.configure(bg=BG)
        idx = 0; selected = {}
        var = tk.StringVar()
        title = tk.Label(win, bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold"), wraplength=820); title.pack(anchor="w", padx=30, pady=(25, 10))
        qtext = tk.Label(win, bg=PANEL, fg=TEXT, font=("Segoe UI", 12), wraplength=780, justify="left", anchor="w", padx=20, pady=20); qtext.pack(fill="x", padx=30)
        opts = tk.Frame(win, bg=BG); opts.pack(fill="x", padx=30, pady=15)
        progress = tk.Label(win, bg=BG, fg=MUTED, font=("Segoe UI", 9)); progress.pack(anchor="w", padx=30)
        nav = tk.Frame(win, bg=BG); nav.pack(fill="x", padx=30, pady=20)
        def render():
            nonlocal idx
            qu = questions[idx]; title.configure(text=f"{test['title']} — вопрос {idx+1}/{len(questions)}")
            qtext.configure(text=qu["question"]); progress.configure(text=f"Выбран ответ: {selected.get(qu['id'], '—')}")
            for w in opts.winfo_children(): w.destroy()
            var.set(selected.get(qu["id"], ""))
            for letter, key in [("A","answer_a"),("B","answer_b"),("C","answer_c"),("D","answer_d")]:
                tk.Radiobutton(opts, text=f"{letter}. {qu[key]}", variable=var, value=letter, bg=BG, fg=TEXT, activebackground=BG, activeforeground=TEXT, selectcolor=PANEL2, font=("Segoe UI", 11), wraplength=760, justify="left", anchor="w", padx=10, pady=8).pack(fill="x")
        def save_current():
            if var.get(): selected[questions[idx]["id"]] = var.get()
        def next_q():
            nonlocal idx
            save_current()
            if idx < len(questions)-1:
                idx += 1; render()
            else:
                finish()
        def prev_q():
            nonlocal idx
            save_current()
            if idx > 0:
                idx -= 1; render()
        def finish():
            save_current(); correct = sum(1 for qu in questions if selected.get(qu["id"]) == qu["correct_answer"])
            score = round(correct / len(questions) * 100)
            if not messagebox.askyesno("Завершить", f"Результат: {correct}/{len(questions)} ({score}%).\nЗавершить тест?", parent=win): return
            try:
                result = self.db.insert("test_results", {"user_id": self.user["id"], "test_id": test["id"], "score": score, "total_questions": len(questions), "correct_answers": correct, "completed_at": datetime.utcnow().isoformat()+"Z"})
                rid = result[0]["id"]
                answers = [{"result_id": rid, "question_id": qu["id"], "selected_answer": selected.get(qu["id"], "A"), "is_correct": selected.get(qu["id"]) == qu["correct_answer"]} for qu in questions]
                self.db.insert("test_answers", answers)
                messagebox.showinfo("Готово", f"Тест завершён. Результат: {score}%.", parent=win); win.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка сохранения", str(e), parent=win)
        ttk.Button(nav, text="← Назад", style="Secondary.TButton", command=prev_q).pack(side="left")
        ttk.Button(nav, text="Далее / Завершить", command=next_q).pack(side="right")
        render()

    def favorites_page(self):
        wrap = self.scroll_area()
        try:
            favs = self.db.table("favorites", "id,law_article_id,created_at", {"user_id": f"eq.{self.user['id']}"}, "created_at.desc")
            if not favs:
                self.card(wrap, "Избранное пусто", "Открой статью и нажми «Добавить в избранное»."); return
            for fav in favs:
                rows = self.db.table("law_articles", "id,article_number,title,content", {"id": f"eq.{fav['law_article_id']}"})
                if rows:
                    a = rows[0]; self.card(wrap, f"Статья {a.get('article_number')} — {a.get('title') or ''}", a.get("content", "")[:400], "Открыть", lambda x=a: self.article_view(x, "Избранное"))
        except Exception as e:
            self.card(wrap, "Ошибка", str(e))

    def history_page(self):
        wrap = self.scroll_area()
        try:
            rows = self.db.table("test_results", "id,test_id,score,total_questions,correct_answers,started_at,completed_at", {"user_id": f"eq.{self.user['id']}"}, "started_at.desc", 100)
            if not rows:
                self.card(wrap, "История пуста", "Пройди первый тест — результат появится здесь."); return
            for r in rows:
                t = self.db.table("tests", "title", {"id": f"eq.{r['test_id']}"})
                title = t[0]["title"] if t else f"Тест #{r['test_id']}"
                self.card(wrap, title, f"Результат: {r.get('score',0)}%\nПравильных: {r.get('correct_answers',0)} из {r.get('total_questions',0)}\nДата: {r.get('completed_at') or r.get('started_at')}")
        except Exception as e:
            self.card(wrap, "Ошибка", str(e))

    def settings(self):
        wrap = self.scroll_area()
        name = self.prof.get("display_name") or self.prof.get("username") or "—"
        self.card(wrap, "Аккаунт", f"Логин: {self.prof.get('username','—')}\nИмя: {name}\nРоль: {role_label(self.prof.get('role','USER'))}\nСтатус: {self.prof.get('status','—')}\nPremium: {'Да' if self.prof.get('premium') else 'Нет'}")
        ttk.Button(wrap, text="Изменить отображаемое имя", command=self.change_display_name).pack(anchor="w", pady=8)
        allow = tk.BooleanVar(value=bool(self.prof.get("allow_pranks")))
        f = tk.Frame(wrap, bg=PANEL, highlightbackground=BORDER, highlightthickness=1); f.pack(fill="x", pady=8)
        tk.Checkbutton(f, text="Разрешаю внутриигровые розыгрыши/скример", variable=allow, bg=PANEL, fg=TEXT, selectcolor=PANEL2, activebackground=PANEL, activeforeground=TEXT, font=("Segoe UI", 10)).pack(side="left", padx=15, pady=14)
        ttk.Button(f, text="Сохранить", command=lambda: self.save_pranks(allow.get())).pack(side="right", padx=15)
        self.card(wrap, "Версия", f"{APP_NAME} v{APP_VERSION}\n{APP_PUBLISHER}\nWindows release build")

    def change_display_name(self):
        value = simpledialog.askstring("Имя", "Новое отображаемое имя:", initialvalue=self.prof.get("display_name") or "")
        if value is None: return
        try:
            self.db.update("profiles", {"id": f"eq.{self.user['id']}"}, {"display_name": value.strip()})
            self.prof["display_name"] = value.strip(); self.show_main()
        except Exception as e: messagebox.showerror("Настройки", str(e))

    def save_pranks(self, value):
        try:
            self.db.update("profiles", {"id": f"eq.{self.user['id']}"}, {"allow_pranks": bool(value)})
            self.prof["allow_pranks"] = bool(value); messagebox.showinfo(APP_NAME, "Настройки сохранены.")
        except Exception as e: messagebox.showerror("Настройки", str(e))

    def reports_page(self):
        wrap = self.scroll_area()
        if self.prof.get("role") not in ("MODERATOR", "ADMIN", "FOUNDER"):
            ttk.Button(wrap, text="Создать жалобу", command=self.create_report).pack(anchor="w", pady=8)
        else:
            ttk.Button(wrap, text="+ Создать жалобу", command=self.create_report).pack(anchor="w", pady=8)
        try:
            if self.prof.get("role") in ("MODERATOR", "ADMIN", "FOUNDER"):
                rows = self.db.table("reports", "id,author_id,target_user_id,reason,description,status,created_at,assigned_to", {}, "created_at.desc", 100)
            else:
                rows = self.db.table("reports", "id,author_id,target_user_id,reason,description,status,created_at", {"author_id": f"eq.{self.user['id']}"}, "created_at.desc", 100)
            if not rows:
                self.card(wrap, "Жалоб нет", "Новые обращения появятся здесь."); return
            for r in rows:
                self.card(wrap, f"#{r['id']} • {r.get('reason','Жалоба')}", f"Статус: {r.get('status')}\n{r.get('description') or ''}\nДата: {r.get('created_at')}", "Открыть", lambda x=r: self.report_dialog(x))
        except Exception as e: self.card(wrap, "Ошибка", str(e))

    def create_report(self):
        reason = simpledialog.askstring("Жалоба", "Причина:")
        if not reason: return
        target = simpledialog.askstring("Жалоба", "ID пользователя-нарушителя (необязательно):") or None
        desc = self.text_dialog("Жалоба", "Подробности:") or ""
        try:
            self.db.insert("reports", {"author_id": self.user["id"], "target_user_id": target, "reason": reason, "description": desc})
            messagebox.showinfo(APP_NAME, "Жалоба отправлена."); self.reports_page()
        except Exception as e: messagebox.showerror("Жалоба", str(e))

    def report_dialog(self, report):
        win = tk.Toplevel(self); win.title(f"Жалоба #{report['id']}"); win.geometry("600x500"); win.configure(bg=BG)
        tk.Label(win, text=f"Жалоба #{report['id']}", bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=25, pady=20)
        tk.Label(win, text=f"Причина: {report.get('reason')}\n\n{report.get('description') or ''}\n\nСтатус: {report.get('status')}", bg=PANEL, fg=TEXT, justify="left", wraplength=530, padx=20, pady=20).pack(fill="x", padx=25)
        if self.prof.get("role") in ("MODERATOR", "ADMIN", "FOUNDER"):
            cb = ttk.Combobox(win, values=["NEW", "IN_PROGRESS", "RESOLVED", "REJECTED"], state="readonly"); cb.set(report.get("status","NEW")); cb.pack(fill="x", padx=25, pady=15)
            def save():
                try:
                    self.db.update("reports", {"id": f"eq.{report['id']}"}, {"status": cb.get(), "resolved_at": datetime.utcnow().isoformat()+"Z" if cb.get() in ("RESOLVED","REJECTED") else None})
                    self.log("Изменён статус жалобы", "reports", report["id"]); win.destroy(); self.reports_page()
                except Exception as e: messagebox.showerror("Жалоба", str(e), parent=win)
            ttk.Button(win, text="Сохранить", command=save).pack(pady=8)
        ttk.Button(win, text="Закрыть", style="Secondary.TButton", command=win.destroy).pack(pady=8)

    def admin_page(self):
        if self.prof.get("role") not in ("ADMIN", "FOUNDER"):
            self.card(self.content, "Нет доступа", "Раздел доступен только администраторам и основателю."); return
        nb = ttk.Notebook(self.content); nb.pack(fill="both", expand=True, padx=38, pady=(0, 25))
        users = tk.Frame(nb, bg=BG); laws = tk.Frame(nb, bg=BG); tests = tk.Frame(nb, bg=BG); ann = tk.Frame(nb, bg=BG); audit = tk.Frame(nb, bg=BG)
        nb.add(users, text="Пользователи"); nb.add(laws, text="Законы"); nb.add(tests, text="Тесты"); nb.add(ann, text="Объявления"); nb.add(audit, text="Журнал")
        self.admin_users(users); self.admin_laws(laws); self.admin_tests(tests); self.admin_announcements(ann); self.admin_audit(audit)

    def admin_users(self, parent):
        toolbar = tk.Frame(parent, bg=BG); toolbar.pack(fill="x", pady=10)
        ttk.Button(toolbar, text="Обновить", command=lambda: self.refresh_admin_users(tree)).pack(side="left")
        tree = ttk.Treeview(parent, columns=("id","username","name","role","status","premium"), show="headings")
        for col, title, width in [("id","ID",180),("username","Логин",150),("name","Имя",160),("role","Роль",190),("status","Статус",110),("premium","Premium",80)]: tree.heading(col, text=title); tree.column(col, width=width)
        tree.pack(fill="both", expand=True)
        actions = tk.Frame(parent, bg=BG); actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Изменить роль", command=lambda: self.change_user_role(tree)).pack(side="left", padx=4)
        ttk.Button(actions, text="Изменить статус", command=lambda: self.change_user_status(tree)).pack(side="left", padx=4)
        ttk.Button(actions, text="Premium", command=lambda: self.toggle_premium(tree)).pack(side="left", padx=4)
        ttk.Button(actions, text="Скример: разрешение", command=lambda: self.toggle_prank(tree)).pack(side="left", padx=4)
        self.refresh_admin_users(tree)

    def refresh_admin_users(self, tree):
        for i in tree.get_children(): tree.delete(i)
        try:
            rows = self.db.table("profiles", "id,username,display_name,role,status,premium,allow_pranks", {}, "created_at.asc", 300)
            for r in rows: tree.insert("", "end", iid=r["id"], values=(r["id"],r.get("username"),r.get("display_name"),role_label(r.get("role")),r.get("status"),"Да" if r.get("premium") else "Нет"))
        except Exception as e: messagebox.showerror("Пользователи", str(e))

    def selected_user(self, tree):
        ids = tree.selection()
        if not ids: messagebox.showinfo(APP_NAME, "Выбери пользователя."); return None
        return ids[0]

    def get_profile(self, uid):
        rows = self.db.table("profiles", "id,username,display_name,role,status,premium,allow_pranks", {"id": f"eq.{uid}"}); return rows[0] if rows else None

    def change_user_role(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        if uid == self.user["id"] and self.prof.get("role") == "FOUNDER":
            messagebox.showwarning(APP_NAME, "Основатель не должен менять свою роль из клиентского интерфейса."); return
        if target.get("role") == "FOUNDER" and self.prof.get("role") != "FOUNDER":
            messagebox.showerror(APP_NAME, "Только Основатель может управлять аккаунтом Основателя."); return
        win = tk.Toplevel(self); win.title("Роль"); win.geometry("420x220"); win.configure(bg=BG)
        tk.Label(win, text=f"Роль для {target.get('username')}", bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=20)
        values = ROLE_ORDER if self.prof.get("role") == "FOUNDER" else ["MODERATOR","PREMIUM","USER"]
        cb = ttk.Combobox(win, values=[role_label(x) for x in values], state="readonly", width=35); cb.current(values.index(target.get("role")) if target.get("role") in values else len(values)-1); cb.pack(pady=10)
        def save():
            new_role = values[cb.current()]
            if self.prof.get("role") != "FOUNDER" and new_role in ("FOUNDER","ADMIN"):
                messagebox.showerror(APP_NAME, "Администратор может выдавать только MODERATOR/PREMIUM/USER.", parent=win); return
            try:
                self.db.update("profiles", {"id": f"eq.{uid}"}, {"role": new_role})
                self.log("Изменена роль", "profiles", uid, {"role": new_role}); win.destroy(); self.refresh_admin_users(tree)
            except Exception as e: messagebox.showerror("Роль", str(e), parent=win)
        ttk.Button(win, text="Сохранить", command=save).pack(pady=10)

    def change_user_status(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if target and target.get("role") == "FOUNDER" and self.prof.get("role") != "FOUNDER":
            messagebox.showerror(APP_NAME, "Только Основатель может изменять статус Основателя."); return
        status = simpledialog.askstring("Статус", "ACTIVE / BLOCKED / BANNED:", initialvalue=target.get("status","ACTIVE") if target else "ACTIVE")
        if status not in STATUS_VALUES: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"status": status}); self.log("Изменён статус", "profiles", uid, {"status": status}); self.refresh_admin_users(tree)
        except Exception as e: messagebox.showerror("Статус", str(e))

    def toggle_premium(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"premium": not bool(target.get("premium"))}); self.log("Изменён Premium", "profiles", uid); self.refresh_admin_users(tree)
        except Exception as e: messagebox.showerror("Premium", str(e))

    def toggle_prank(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"allow_pranks": not bool(target.get("allow_pranks"))}); self.log("Изменено разрешение на розыгрыши", "profiles", uid); self.refresh_admin_users(tree)
        except Exception as e: messagebox.showerror("Скример", str(e))

    def admin_laws(self, parent):
        ttk.Button(parent, text="+ Добавить закон", command=self.add_law).pack(anchor="w", pady=10)
        self.admin_list(parent, "laws", "id,name,law_number,is_active", "name.asc", ["id","name","law_number","is_active"])

    def admin_tests(self, parent):
        ttk.Button(parent, text="+ Добавить тест", command=self.add_test).pack(anchor="w", pady=10)
        self.admin_list(parent, "tests", "id,title,category,difficulty,question_count,is_active", "title.asc", ["id","title","category","difficulty","question_count","is_active"])

    def admin_list(self, parent, table, select, order, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for c in columns: tree.heading(c, text=c); tree.column(c, width=150)
        tree.pack(fill="both", expand=True, pady=5)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            try:
                rows = self.db.table(table, select, {}, order, 300)
                for r in rows: tree.insert("", "end", values=tuple(r.get(c) for c in columns))
            except Exception as e: messagebox.showerror(table, str(e))
        ttk.Button(parent, text="Обновить", command=refresh).pack(anchor="e", pady=6)
        refresh()
        return tree

    def add_test(self):
        title = simpledialog.askstring("Тест", "Название:")
        if not title: return
        category = simpledialog.askstring("Тест", "Категория:") or "Общее"
        difficulty = simpledialog.askstring("Тест", "EASY / MEDIUM / HARD:", initialvalue="MEDIUM") or "MEDIUM"
        if difficulty not in ("EASY","MEDIUM","HARD"): difficulty = "MEDIUM"
        desc = simpledialog.askstring("Тест", "Описание:") or ""
        try:
            self.db.insert("tests", {"title": title, "category": category, "description": desc, "difficulty": difficulty, "question_count": 0, "is_active": True})
            self.log("Создан тест", "tests", title); self.admin_page()
        except Exception as e: messagebox.showerror("Тест", str(e))

    def admin_announcements(self, parent):
        ttk.Button(parent, text="+ Создать объявление", command=self.add_announcement).pack(anchor="w", pady=10)
        tree = ttk.Treeview(parent, columns=("id","title","type","active","date"), show="headings")
        for c,w in [("id",80),("title",320),("type",100),("active",100),("date",220)]: tree.heading(c,text=c); tree.column(c,width=w)
        tree.pack(fill="both", expand=True)
        try:
            rows = self.db.table("announcements", "id,title,type,is_active,created_at", {}, "created_at.desc", 200)
            for r in rows: tree.insert("", "end", values=(r["id"],r["title"],r["type"],r["is_active"],r["created_at"]))
        except Exception as e: messagebox.showerror("Объявления", str(e))

    def add_announcement(self):
        title = simpledialog.askstring("Объявление", "Заголовок:")
        if not title: return
        content = self.text_dialog("Объявление", "Текст:")
        if content is None: return
        typ = simpledialog.askstring("Объявление", "Тип (INFO/WARN/UPDATE):", initialvalue="INFO") or "INFO"
        try:
            self.db.insert("announcements", {"title": title, "content": content, "type": typ, "is_active": True, "created_by": self.user["id"]})
            self.log("Создано объявление", "announcements", title); self.admin_page()
        except Exception as e: messagebox.showerror("Объявление", str(e))

    def admin_audit(self, parent):
        tree = ttk.Treeview(parent, columns=("id","user","action","target","details","date"), show="headings")
        for c,w in [("id",70),("user",220),("action",220),("target",140),("details",300),("date",220)]: tree.heading(c,text=c); tree.column(c,width=w)
        tree.pack(fill="both", expand=True, pady=10)
        try:
            rows = self.db.table("audit_logs", "id,user_id,action,target_type,target_id,details,created_at", {}, "created_at.desc", 300)
            for r in rows: tree.insert("", "end", values=(r["id"],r.get("user_id"),r.get("action"),r.get("target_type"),r.get("target_id"),json.dumps(r.get("details"),ensure_ascii=False),r.get("created_at")))
        except Exception as e: messagebox.showerror("Журнал", str(e))

    def log(self, action, target_type=None, target_id=None, details=None):
        try:
            self.db.insert("audit_logs", {"user_id": self.user["id"], "action": action, "target_type": target_type, "target_id": str(target_id) if target_id is not None else None, "details": details or {}})
        except Exception:
            pass

    def text_dialog(self, title, label):
        win = tk.Toplevel(self); win.title(title); win.geometry("700x500"); win.configure(bg=BG); result = {"value": None}
        tk.Label(win, text=label, bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 8))
        text = tk.Text(win, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 10), padx=12, pady=12); text.pack(fill="both", expand=True, padx=20)
        bar = tk.Frame(win, bg=BG); bar.pack(fill="x", padx=20, pady=15)
        def ok(): result["value"] = text.get("1.0", "end").strip(); win.destroy()
        ttk.Button(bar, text="Сохранить", command=ok).pack(side="right")
        ttk.Button(bar, text="Отмена", style="Secondary.TButton", command=win.destroy).pack(side="right", padx=8)
        win.transient(self); win.grab_set(); self.wait_window(win)
        return result["value"]

    def page_header_replace(self, title, subtitle):
        for w in self.content.winfo_children(): w.destroy()
        self.header(title, subtitle)

    def logout(self):
        self.db.auth_logout(); self.user = {}; self.prof = {}; self.show_login()


if __name__ == "__main__":
    App().mainloop()
