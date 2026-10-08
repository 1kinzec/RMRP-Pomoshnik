import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
import threading
import math
import sys
import wave
import struct
import tempfile
import time
try:
    import winsound
except ImportError:
    winsound = None
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from html.parser import HTMLParser

APP_NAME = "RMRP Помощник"
APP_VERSION = "1.4.0"
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


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


RMRP_LAW_SOURCES = [
    {"name":"Федеральный закон «О государственной службе» № 54-ФЗ","short_name":"ФЗ «О госслужбе»","law_number":"54-ФЗ","url":"https://forum.rmrp.ru/threads/federalnyj-zakon-o-gosudarstvennoj-sluzhbe-no-54-fz.25075/"},
    {"name":"Уголовный Кодекс Российской Федерации","short_name":"УК РФ","law_number":"УК РФ","url":"https://forum.rmrp.ru/threads/ugolovnyj-kodeks-rossijskoj-federacii.58209/"},
    {"name":"Кодекс об административных правонарушениях Российской Федерации","short_name":"КоАП РФ","law_number":"КоАП РФ","url":"https://forum.rmrp.ru/threads/kodeks-ob-administrativnyx-pravonarushenijax-rossijskoj-federacii.58229/"},
    {"name":"Процессуальный Кодекс Российской Федерации","short_name":"Процессуальный кодекс","law_number":"ПК РФ","url":"https://forum.rmrp.ru/threads/processualnyj-kodeks-rossijskoj-federacii.58424/"},
    {"name":"Федеральный закон «О полиции» № 74-ФЗ","short_name":"ФЗ «О полиции»","law_number":"74-ФЗ","url":"https://forum.rmrp.ru/threads/federalnyj-zakon-o-policii-no-74-fz.25074/"},
    {"name":"Федеральный закон «О Федеральной службе войск национальной гвардии» № 18-ФЗ","short_name":"ФЗ «О ФСВНГ»","law_number":"18-ФЗ","url":"https://forum.rmrp.ru/threads/federalnyj-zakon-o-federalnoj-sluzhbe-vojsk-nacionalnoj-gvardii-no-18-fz.25071/"},
]


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
        self.setup_window()
        self.db = Supabase()
        self.user = {}
        self.prof = {}
        self.nav_buttons = {}
        self.content = None
        self._hover_jobs = {}
        self._toasts = []
        self._toast_after = None
        self._sound_cache = {}
        self._prank_listener_started = False
        self.settings_path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RMRP-Pomoshnik", "settings.json")
        self.app_settings = self.load_app_settings()
        self._styles()
        self.show_login()

    def setup_window(self):
        try:
            self.overrideredirect(True)
            self._drag = [0, 0]
        except Exception:
            pass

    def titlebar(self, parent):
        bar=tk.Frame(parent,bg="#07111f",height=34,highlightbackground="#163454",highlightthickness=1)
        bar.pack(fill="x",side="top")
        bar.pack_propagate(False)
        logo=tk.Canvas(bar,width=24,height=24,bg="#07111f",highlightthickness=0); logo.pack(side="left",padx=(10,6),pady=5)
        logo.create_polygon(12,2,21,5,19,16,12,22,5,16,3,5,fill="#0b2443",outline="#4da2ff",width=1)
        logo.create_text(12,11,text="⚖",fill="#78b8ff",font=("Segoe UI Symbol",9,"bold"))
        tk.Label(bar,text=f"{APP_NAME}  •  by {APP_PUBLISHER}",bg="#07111f",fg="#c7d8ee",font=("Segoe UI",8,"bold")).pack(side="left")
        tk.Label(bar,text=f"v{APP_VERSION}",bg="#07111f",fg="#5e82ad",font=("Segoe UI",8)).pack(side="right",padx=8)
        close=tk.Button(bar,text="×",command=self.destroy,bg="#07111f",fg="#7f9ab8",activebackground="#8f2034",activeforeground="white",bd=0,font=("Segoe UI",13),width=3,cursor="hand2")
        close.pack(side="right",fill="y")
        mini=tk.Button(bar,text="—",command=lambda:self.state("iconic"),bg="#07111f",fg="#7f9ab8",activebackground="#162a45",activeforeground="white",bd=0,font=("Segoe UI",11),width=3,cursor="hand2")
        mini.pack(side="right",fill="y")
        bar.bind("<ButtonPress-1>",self._start_drag); bar.bind("<B1-Motion>",self._drag_window)
        for w in (logo,): w.bind("<ButtonPress-1>",self._start_drag); w.bind("<B1-Motion>",self._drag_window)
        return bar

    def _start_drag(self,event):
        self._drag=[event.x_root-self.winfo_x(),event.y_root-self.winfo_y()]

    def _drag_window(self,event):
        try:
            self.geometry(f"+{event.x_root-self._drag[0]}+{event.y_root-self._drag[1]}")
        except Exception: pass

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

    def load_app_settings(self):
        defaults = {"sound_enabled": True, "sound_volume": 8, "hover_sound": False, "toast_duration": 3600}
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
        return defaults

    def save_app_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.app_settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _make_tone(self, kind, freq, duration_ms, volume):
        key=(kind,freq,duration_ms,int(volume))
        if key in self._sound_cache: return self._sound_cache[key]
        path=os.path.join(tempfile.gettempdir(), f"rmrp_{kind}_{freq}_{duration_ms}_{int(volume)}.wav")
        if not os.path.exists(path):
            rate=22050; n=max(1,int(rate*duration_ms/1000)); amp=int(32767*max(0,min(100,volume))/100)
            with wave.open(path,"wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
                data=bytearray()
                for i in range(n):
                    env=min(1,i/max(1,int(rate*.006)), (n-i)/max(1,int(rate*.006)), 1)
                    sample=int(amp*env*math.sin(2*math.pi*freq*i/rate))
                    data.extend(struct.pack("<h",sample))
                w.writeframes(data)
        self._sound_cache[key]=path
        return path

    def play_sound(self, kind="click"):
        if winsound is None or not self.app_settings.get("sound_enabled", True): return
        if kind == "hover" and not self.app_settings.get("hover_sound", False): return
        volume=int(self.app_settings.get("sound_volume",8))
        tones={"click":(680,22),"hover":(520,12),"success":(610,38),"error":(250,55),"open":(480,20)}
        freq,dur=tones.get(kind,tones["click"])
        def run():
            try: winsound.PlaySound(self._make_tone(kind,freq,dur,volume), winsound.SND_FILENAME|winsound.SND_ASYNC)
            except Exception: pass
        threading.Thread(target=run,daemon=True).start()

    def notify(self, title, message, kind="info", duration=None):
        """Premium non-blocking toast notifications. Multiple toasts stack vertically."""
        if duration is None:
            duration = int(self.app_settings.get("toast_duration", 3600))
        colors = {
            "info": ("#3b82f6", "i"),
            "success": ("#22c55e", "✓"),
            "warning": ("#f59e0b", "!"),
            "error": ("#ef4444", "×"),
        }
        accent, icon = colors.get(kind, colors["info"])
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg="#081321")
        width, height = 410, 104
        outer = tk.Frame(toast, bg="#081321", highlightbackground="#23405f", highlightthickness=1)
        outer.pack(fill="both", expand=True)
        tk.Frame(outer, bg=accent, width=4).pack(side="left", fill="y")
        tk.Label(outer, text=icon, bg="#081321", fg=accent, font=("Segoe UI", 16, "bold"), width=3).pack(side="left", fill="y", padx=(5, 0))
        body = tk.Frame(outer, bg="#081321")
        body.pack(side="left", fill="both", expand=True, padx=(2, 10), pady=10)
        tk.Label(body, text=title, bg="#081321", fg=TEXT, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text=str(message), bg="#081321", fg="#a6b6ca", font=("Segoe UI", 8), anchor="w", justify="left", wraplength=330).pack(fill="x", pady=(4, 0))
        progress = tk.Frame(toast, bg=accent, height=2)
        progress.place(x=0, y=height-2, width=width)
        close = tk.Button(toast, text="×", command=toast.destroy, bg="#081321", fg="#647b96", activebackground="#10223a", activeforeground=TEXT, bd=0, font=("Segoe UI", 11), cursor="hand2")
        close.place(relx=1.0, x=-7, y=5, anchor="ne")
        toast.update_idletasks()
        self._toasts.append(toast)
        self._reposition_toasts()
        started = time.monotonic()
        def tick():
            if not toast.winfo_exists():
                if toast in self._toasts: self._toasts.remove(toast)
                self._reposition_toasts()
                return
            left = max(0, 1 - (time.monotonic() - started) / max(0.1, duration / 1000))
            progress.place_configure(width=max(1, int(width * left)))
            if left <= 0:
                try: toast.destroy()
                except Exception: pass
                if toast in self._toasts: self._toasts.remove(toast)
                self._reposition_toasts()
            else:
                self.after(30, tick)
        self.after(30, tick)
        self.play_sound("success" if kind == "success" else "click")

    def _reposition_toasts(self):
        try:
            self.update_idletasks()
            right = self.winfo_rootx() + self.winfo_width() - 20
            bottom = self.winfo_rooty() + self.winfo_height() - 20
            for toast in list(self._toasts):
                if not toast.winfo_exists():
                    self._toasts.remove(toast); continue
                toast.update_idletasks()
                x = right - toast.winfo_width()
                y = bottom - toast.winfo_height()
                toast.geometry(f"+{x}+{y}")
                bottom = y - 10
        except Exception:
            pass

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
        self.titlebar(root)
        body=tk.Frame(root,bg=BG); body.pack(fill="both",expand=True)
        visual=tk.Frame(body,bg="#07111f"); visual.pack(side="left",fill="both",expand=True)
        try:
            self._login_image=tk.PhotoImage(file=resource_path("assets","login_bg.png"))
            lab=tk.Label(visual,image=self._login_image,bg="#07111f",bd=0); lab.place(relx=0,rely=0,relwidth=1,relheight=1)
        except Exception:
            self._gradient_canvas(visual)
        tk.Frame(visual,bg="#3b82f6",width=3).place(relx=1,rely=0,relheight=1,anchor="ne")
        # Логотип остаётся отдельным элементом поверх фоновой иллюстрации.
        # Название и подпись уже встроены в artwork, поэтому повторно их не рисуем.
        tk.Label(visual,text="⚖",bg="#07111f",fg="#70b3ff",font=("Segoe UI Symbol",64,"bold")).place(relx=.255,rely=.36,anchor="center")
        auth=tk.Frame(body,bg="#091321",width=570); auth.pack(side="right",fill="y"); auth.pack_propagate(False)
        top=tk.Frame(auth,bg="#091321"); top.pack(fill="x",padx=42,pady=(26,0))
        tk.Label(top,text="RMRP Помощник",bg="#091321",fg=TEXT,font=("Segoe UI",11,"bold")).pack(side="left")
        tk.Label(top,text=f"v{APP_VERSION}",bg="#091321",fg="#4e719b",font=("Segoe UI",8)).pack(side="right")
        card=tk.Frame(auth,bg="#0d1b2d",highlightbackground="#244c78",highlightthickness=1); card.place(relx=.5,rely=.53,anchor="center",relwidth=.82,relheight=.68)
        tk.Label(card,text="Добро пожаловать",bg="#0d1b2d",fg=TEXT,font=("Segoe UI",24,"bold")).pack(anchor="w",padx=34,pady=(34,3))
        tk.Label(card,text="Войдите в аккаунт, чтобы продолжить",bg="#0d1b2d",fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=34,pady=(0,24))
        self.email=self.entry(card,"Email"); self.password=self.entry(card,"Пароль",secret=True)
        tk.Checkbutton(card,text="Запомнить меня",bg="#0d1b2d",fg="#7e93ae",selectcolor="#0d1b2d",activebackground="#0d1b2d",activeforeground=TEXT,font=("Segoe UI",9),anchor="w").pack(fill="x",padx=34,pady=(2,8))
        btn=tk.Button(card,text="ВОЙТИ  →",command=self.do_login,bd=0,bg=ACCENT,fg="white",activebackground="#4b8fff",font=("Segoe UI",10,"bold"),cursor="hand2",pady=12); btn.pack(fill="x",padx=34,pady=(10,10)); btn.bind("<Enter>",lambda e:btn.configure(bg="#4b8fff")); btn.bind("<Leave>",lambda e:btn.configure(bg=ACCENT))
        tk.Label(card,text="или",bg="#0d1b2d",fg="#4e6380",font=("Segoe UI",8)).pack(pady=(3,8))
        ttk.Button(card,text="Создать аккаунт",style="Secondary.TButton",command=lambda:(self.play_sound("click"),self.show_register())).pack(fill="x",padx=34)
        tk.Label(card,text="SUPABASE SECURE RLS  •  ЗАЩИЩЁННОЕ ПОДКЛЮЧЕНИЕ",bg="#0d1b2d",fg="#536a88",font=("Segoe UI",7,"bold")).pack(side="bottom",pady=18)

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
        self.clear(); outer=tk.Frame(self,bg=BG); outer.pack(fill="both",expand=True); self.titlebar(outer)
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
            self.notify(APP_NAME, "Введите email и пароль.")
            return
        try:
            data = self.db.auth_login(email, password)
            self.user = data.get("user") or {}
            if not self.db.access_token or not self.user.get("id"):
                raise RuntimeError("Supabase не вернул активную сессию.")
            rows = self.db.table("profiles", "id,username,display_name,avatar_url,bio,role,premium,status,allow_pranks,created_at,last_login,updated_at", {"id": f"eq.{self.user['id']}"})
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
            self.start_prank_listener()
        except Exception as e:
            self.notify("Ошибка входа", str(e), "error")

    def do_register(self):
        email = self.r_email.get().strip()
        username = self.r_username.get().strip()
        display = self.r_display.get().strip()
        p1 = self.r_password.get()
        p2 = self.r_password2.get()
        if email in ("", "Email") or username in ("", "Логин") or p1 in ("", "Пароль"):
            self.notify(APP_NAME, "Заполни обязательные поля.")
            return
        if len(p1) < 6:
            self.notify(APP_NAME, "Пароль должен содержать минимум 6 символов.")
            return
        if p1 != p2:
            self.notify(APP_NAME, "Пароли не совпадают.")
            return
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_.-]{3,32}", username):
            self.notify(APP_NAME, "Логин: 3–32 символа, только буквы, цифры, _, ., -.")
            return
        try:
            data = self.db.auth_register(email, p1, username, display or username)
            if data.get("access_token"):
                self.db.access_token = data["access_token"]
            self.notify(APP_NAME, "Аккаунт создан. Если включено подтверждение email — подтверди почту и войди.", "success")
            self.show_login()
        except Exception as e:
            self.notify("Ошибка регистрации", str(e), "error")

    def show_main(self):
        self.clear()
        shell=tk.Frame(self,bg=BG); shell.pack(fill="both",expand=True); self.titlebar(shell)
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
            "Профиль": "Личная страница и данные аккаунта.",
            "Настройки": "Звук, уведомления и поведение приложения.",
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
            "Профиль": self.profile_page,
            "Жалобы": self.reports_page,
            "Администрирование": self.admin_page,
        }
        pages.get(title, self.home)()

    def scroll_area(self):
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        track = tk.Frame(outer, bg="#07111f", width=12)
        track.pack(side="right", fill="y", padx=(8, 0))
        track.pack_propagate(False)
        thumb = tk.Canvas(track, width=12, bg="#07111f", highlightthickness=0, bd=0)
        thumb.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        dragging = {"active": False, "offset": 0}
        def refresh(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(win_id, width=max(canvas.winfo_width(), 1))
            draw_thumb()
        def draw_thumb():
            thumb.delete("all")
            h = max(thumb.winfo_height(), 1)
            region = canvas.bbox("all")
            if not region or region[3] <= canvas.winfo_height():
                return
            ratio = canvas.winfo_height() / max(region[3], 1)
            th = max(52, int(h * ratio))
            first, _ = canvas.yview()
            y = int(first * max(1, h - th))
            thumb.create_rounded = None
            thumb.create_rectangle(3, y + 2, 9, y + th - 2, fill="#2b5d91", outline="")
            thumb.create_oval(3, y, 9, y + 6, fill="#2b5d91", outline="")
            thumb.create_oval(3, y + th - 6, 9, y + th, fill="#2b5d91", outline="")
        def wheel(e):
            canvas.yview_scroll(int(-e.delta / 120), "units")
            draw_thumb()
        def thumb_press(e):
            dragging["active"] = True
            first, _ = canvas.yview()
            h = max(thumb.winfo_height(), 1)
            region = canvas.bbox("all")
            ratio = canvas.winfo_height() / max(region[3], 1) if region else 1
            th = max(52, int(h * ratio))
            dragging["offset"] = e.y - first * max(1, h - th)
        def thumb_drag(e):
            if not dragging["active"]: return
            h = max(thumb.winfo_height(), 1)
            region = canvas.bbox("all")
            if not region: return
            ratio = canvas.winfo_height() / max(region[3], 1)
            th = max(52, int(h * ratio))
            pos = max(0, min(h - th, e.y - dragging["offset"]))
            canvas.yview_moveto(pos / max(1, h - th))
            draw_thumb()
        thumb.bind("<ButtonPress-1>", thumb_press)
        thumb.bind("<B1-Motion>", thumb_drag)
        thumb.bind("<ButtonRelease-1>", lambda e: dragging.update(active=False))
        inner.bind("<Configure>", refresh)
        canvas.bind("<Configure>", refresh)
        canvas.bind("<MouseWheel>", wheel)
        canvas.bind("<Button-4>", lambda e: (canvas.yview_scroll(-3, "units"), draw_thumb()))
        canvas.bind("<Button-5>", lambda e: (canvas.yview_scroll(3, "units"), draw_thumb()))
        canvas.configure(yscrollcommand=lambda a,b: draw_thumb())
        canvas.pack(side="left", fill="both", expand=True)
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
        items=[("▤","Законодательство","Законы RMRP","Открыть",lambda:self.page("Законодательство"),"#35a9ff"),("⌕","Поиск","Быстрый поиск по знаниям","Открыть",lambda:self.page("Поиск"),"#7e8dff"),("✦","Нейросеть","Задай вопрос ИИ","Открыть",lambda:self.page("Помощь нейросети"),"#31d5ae"),("▣","Тесты","Проверь свои знания","Начать",lambda:self.page("Проверь себя"),"#f2a43b")]
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

    def _fetch_rmrp_articles(self, url):
        req=urllib.request.Request(url,headers={"User-Agent":"RMRP-Pomoshnik/1.4.0"})
        with urllib.request.urlopen(req,timeout=25) as r:
            raw=r.read().decode("utf-8","replace")
        # Convert forum HTML into clean text while keeping block boundaries.
        raw=re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>"," ",raw,flags=re.I|re.S)
        raw=re.sub(r"<(br|/p|/div|/li|/h[1-6]|/blockquote|/tr)[^>]*>","\n",raw,flags=re.I)
        raw=re.sub(r"<[^>]+>"," ",raw)
        from html import unescape
        text=unescape(raw).replace("\xa0"," ")
        lines=[re.sub(r"[ \t]+"," ",x).strip() for x in text.splitlines()]
        lines=[x for x in lines if x]
        pat=re.compile(r"^Статья\s+([0-9]+(?:-[0-9]+)?(?:\.[0-9]+)?)\.\s*(.+)$",re.I)
        chunks={}
        for i,line in enumerate(lines):
            m=pat.match(line)
            if not m: continue
            num=m.group(1); title=m.group(2).strip()
            j=i+1
            while j<len(lines) and not pat.match(lines[j]): j+=1
            content="\n".join(lines[i+1:j]).strip()
            # TOC entries are short; real article blocks are normally much longer.
            if len(content)>=30:
                old=chunks.get(num)
                if old is None or len(content)>len(old["content"]): chunks[num]={"title":title,"content":content}
        return [{"article_number":k,"title":v["title"],"content":v["content"]} for k,v in chunks.items()]

    def sync_rmrp_laws(self, notify=True):
        if self.prof.get("role") not in ("ADMIN","FOUNDER"):
            self.notify(APP_NAME,"Синхронизация законов доступна только Администратору и Основателю.","warning")
            return
        progress=tk.Toplevel(self); progress.title("RMRP • синхронизация законов"); progress.geometry("560x250"); progress.configure(bg=BG); progress.transient(self); progress.grab_set()
        tk.Label(progress,text="Синхронизация законодательства RMRP",bg=BG,fg=TEXT,font=("Segoe UI",16,"bold")).pack(pady=(30,8))
        status=tk.Label(progress,text="Подключение к форуму RMRP…",bg=BG,fg=MUTED,font=("Segoe UI",9)); status.pack(pady=8)
        progress.update_idletasks()
        def worker():
            total_articles=0; done=0; errors=[]
            for src in RMRP_LAW_SOURCES:
                try:
                    self.after(0,lambda n=src["short_name"]: status.configure(text=f"Загрузка: {n}"))
                    arts=self._fetch_rmrp_articles(src["url"])
                    existing=self.db.table("laws","id,name",{"law_number":f"eq.{src['law_number']}"},"id.asc",1)
                    if existing:
                        law_id=existing[0]["id"]
                        self.db.update("laws",{"id":f"eq.{law_id}"},{"name":src["name"],"short_name":src["short_name"],"law_number":src["law_number"],"source_url":src["url"],"description":"Актуальная редакция законодательства RMRP. Источник: форум RMRP."})
                        self.db.delete("law_articles",{"law_id":f"eq.{law_id}"})
                    else:
                        row=self.db.insert("laws",{"name":src["name"],"short_name":src["short_name"],"law_number":src["law_number"],"source_url":src["url"],"description":"Актуальная редакция законодательства RMRP. Источник: форум RMRP.","is_active":True})
                        law_id=row[0]["id"]
                    # Insert in chunks to keep requests small.
                    for k in range(0,len(arts),40):
                        batch=[dict(a,law_id=law_id) for a in arts[k:k+40]]
                        if batch: self.db.insert("law_articles",batch)
                    total_articles += len(arts)
                    done += 1
                except Exception as ex:
                    errors.append(f"{src['short_name']}: {ex}")
            def finish():
                progress.destroy(); self.laws()
                if errors:
                    self.notify(APP_NAME,f"Синхронизация завершена частично. Законов: {done}/6 • Статей: {total_articles}","warning",6000)
                else:
                    self.notify(APP_NAME,f"Загружено 6 законов RMRP и {total_articles} статей.","success",5000)
            self.after(0,finish)
        threading.Thread(target=worker,daemon=True).start()

    def laws(self):
        wrap=self.scroll_area(); toolbar=tk.Frame(wrap,bg="#0d1b2c",highlightbackground="#1a385a",highlightthickness=1); toolbar.pack(fill="x",pady=(0,12))
        ttk.Entry(toolbar).pack(side="left",fill="x",expand=True,padx=10,pady=8,ipady=3); ttk.Button(toolbar,text="Обновить",command=self.laws).pack(side="right",padx=8,pady=7)
        if self.prof.get("role") in ("ADMIN","FOUNDER"):
            ttk.Button(toolbar,text="⟳ Синхронизировать RMRP",command=self.sync_rmrp_laws).pack(side="right",padx=4,pady=7)
            ttk.Button(toolbar,text="+ Закон",command=self.add_law).pack(side="right",pady=7)
        try: laws=self.db.table("laws","id,name,short_name,law_number,description,is_active",{"is_active":"eq.true"},"name.asc")
        except Exception as e: self.card(wrap,"Ошибка загрузки",str(e)); return
        grid=tk.Frame(wrap,bg="#091321"); grid.pack(fill="x")
        if not laws:
            self.card(grid,"Законодательство RMRP пока не загружено","Это не пустые страницы: нажмите «Синхронизировать RMRP», и приложение загрузит актуальные тексты и статьи с официального форума RMRP.","Загрузить законы",self.sync_rmrp_laws)
            return
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
            self.notify("Ошибка", str(e), "error")

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
            self.notify("Ошибка", str(e), "error")

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
                self.notify(APP_NAME, "Удалено из избранного.", "info")
            else:
                self.db.insert("favorites", {"user_id": self.user["id"], "law_article_id": article_id})
                self.notify(APP_NAME, "Добавлено в избранное.", "success")
        except Exception as e:
            self.notify("Избранное", str(e), "error")

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
            self.notify("Тест", str(e), "error"); return
        if not questions:
            self.notify("Тест", "В этом тесте пока нет вопросов.", "info"); return
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
                self.notify("Тест завершён", f"Результат: {score}%.", "success"); win.destroy()
            except Exception as e:
                self.notify("Ошибка сохранения", str(e), "error")
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

    def profile_page(self):
        wrap = self.scroll_area()
        name = self.prof.get("display_name") or self.prof.get("username") or "Пользователь"
        avatar_url = self.prof.get("avatar_url") or ""
        cover = tk.Frame(wrap, bg="#102744", height=185, highlightbackground="#245383", highlightthickness=1)
        cover.pack(fill="x", pady=(0, 12)); cover.pack_propagate(False)
        # Decorative cover layers
        tk.Frame(cover, bg="#173b69", height=2).place(relx=0, rely=0.0, relwidth=.45)
        tk.Frame(cover, bg="#2f80ed", height=2).place(relx=.45, rely=0.0, relwidth=.18)
        avatar = tk.Canvas(cover, width=112, height=112, bg="#102744", highlightthickness=0)
        avatar.place(x=28, y=42)
        avatar.create_oval(3,3,109,109,fill="#081321",outline="#4d9cff",width=3)
        avatar.create_text(56,56,text=name[:1].upper(),fill="#9bcaff",font=("Segoe UI",32,"bold"))
        tk.Label(cover,text=name,bg="#102744",fg=TEXT,font=("Segoe UI",20,"bold")).place(x=162,y=55)
        tk.Label(cover,text="@" + (self.prof.get("username") or "user"),bg="#102744",fg="#7fa2c8",font=("Segoe UI",9)).place(x=164,y=88)
        tk.Label(cover,text=role_label(self.prof.get("role","USER")),bg="#102744",fg="#78b7ff",font=("Segoe UI",9,"bold")).place(x=164,y=113)
        tk.Label(cover,text="● В сети",bg="#102744",fg="#35d58a",font=("Segoe UI",8,"bold")).place(x=164,y=140)
        form = tk.Frame(wrap,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); form.pack(fill="x",pady=8)
        tk.Label(form,text="Редактировать профиль",bg=PANEL,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,3))
        tk.Label(form,text="Изменения видны в профиле и верхней панели приложения.",bg=PANEL,fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=22,pady=(0,14))
        fields={}
        for label,key in [("Отображаемое имя","display_name"),("Логин","username"),("Ссылка на аватар","avatar_url")]:
            tk.Label(form,text=label,bg=PANEL,fg="#8ea3bb",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=22,pady=(7,4))
            e=ttk.Entry(form); e.pack(fill="x",padx=22,ipady=8); e.insert(0,self.prof.get(key) or ""); fields[key]=e
            if key == "username": e.configure(state="readonly")
        tk.Label(form,text="О себе",bg=PANEL,fg="#8ea3bb",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=22,pady=(10,4))
        bio=tk.Text(form,height=5,bg="#0e1827",fg=TEXT,insertbackground=TEXT,relief="flat",font=("Segoe UI",9),wrap="word",padx=10,pady=8)
        bio.pack(fill="x",padx=22); bio.insert("1.0",self.prof.get("bio") or "")
        info=tk.Frame(form,bg="#0e1827"); info.pack(fill="x",padx=22,pady=12)
        tk.Label(info,text=f"{role_label(self.prof.get('role','USER'))}   •   {self.prof.get('status','ACTIVE')}",bg="#0e1827",fg="#7f9ab8",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=9)
        def save():
            values={"display_name":fields["display_name"].get().strip(),"avatar_url":fields["avatar_url"].get().strip(),"bio":bio.get("1.0","end").strip()}
            if not values["display_name"]:
                self.notify("Профиль","Отображаемое имя не может быть пустым.","warning"); return
            if len(values["display_name"]) > 40 or len(values["bio"]) > 500:
                self.notify("Профиль","Имя — до 40 символов, описание — до 500.","warning"); return
            try:
                self.db.update("profiles",{"id":f"eq.{self.user['id']}"},values)
                self.prof.update(values); self.notify("Профиль сохранён","Изменения применены.","success"); self.show_main()
            except Exception as e: self.notify("Профиль",str(e),"error")
        actions=tk.Frame(form,bg=PANEL); actions.pack(fill="x",padx=22,pady=18)
        ttk.Button(actions,text="Сохранить изменения",command=save).pack(side="right")
        ttk.Button(actions,text="Сбросить",style="Secondary.TButton",command=self.profile_page).pack(side="right",padx=8)

    def settings(self):
        wrap=self.scroll_area()
        sound=tk.Frame(wrap,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); sound.pack(fill="x",pady=(0,10))
        tk.Label(sound,text="Звук интерфейса",bg=PANEL,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        tk.Label(sound,text="Настрой громкость тихих кликов отдельно от звуков Windows.",bg=PANEL,fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=22,pady=(0,14))
        enabled=tk.BooleanVar(value=bool(self.app_settings.get("sound_enabled",True))); hover=tk.BooleanVar(value=bool(self.app_settings.get("hover_sound",False))); vol=tk.IntVar(value=min(25,max(0,int(self.app_settings.get("sound_volume",8)))))
        tk.Checkbutton(sound,text="Звуки нажатия",variable=enabled,bg=PANEL,fg=TEXT,selectcolor=PANEL2,activebackground=PANEL,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=5)
        tk.Checkbutton(sound,text="Звук при наведении",variable=hover,bg=PANEL,fg=TEXT,selectcolor=PANEL2,activebackground=PANEL,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=5)
        tk.Label(sound,text="Громкость кликов",bg=PANEL,fg="#8ea3bb",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=22,pady=(12,0))
        scale=tk.Scale(sound,from_=0,to=25,orient="horizontal",variable=vol,bg=PANEL,fg=TEXT,highlightthickness=0,troughcolor="#203552",activebackground=ACCENT,length=400,showvalue=True); scale.pack(anchor="w",padx=22,pady=4)
        btns=tk.Frame(sound,bg=PANEL); btns.pack(fill="x",padx=22,pady=(8,18))
        ttk.Button(btns,text="Проверить звук",command=lambda:self.play_sound("click")).pack(side="left")
        def save_sound():
            self.app_settings.update({"sound_enabled":enabled.get(),"hover_sound":hover.get(),"sound_volume":vol.get()}); self.save_app_settings(); self.notify("Настройки сохранены","Громкость применена.","success")
        ttk.Button(btns,text="Сохранить",command=save_sound).pack(side="right")
        notif=tk.Frame(wrap,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); notif.pack(fill="x",pady=8)
        tk.Label(notif,text="Уведомления",bg=PANEL,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        tk.Label(notif,text="Все обычные сообщения приложения показываются компактными toast-уведомлениями.",bg=PANEL,fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",padx=22,pady=(0,10))
        duration=tk.IntVar(value=int(self.app_settings.get("toast_duration",3600)))
        tk.Label(notif,text="Время показа (мс)",bg=PANEL,fg="#8ea3bb",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=22)
        tk.Scale(notif,from_=1500,to=8000,orient="horizontal",variable=duration,bg=PANEL,fg=TEXT,highlightthickness=0,troughcolor="#203552",activebackground=ACCENT,length=400,showvalue=True).pack(anchor="w",padx=22,pady=4)
        nb=tk.Frame(notif,bg=PANEL); nb.pack(fill="x",padx=22,pady=(6,18))
        ttk.Button(nb,text="Показать пример",command=lambda:self.notify("Готово","Так выглядят уведомления нового интерфейса.","success")).pack(side="left")
        ttk.Button(nb,text="Сохранить уведомления",command=lambda:(self.app_settings.update({"toast_duration":duration.get()}),self.save_app_settings(),self.notify("Настройки сохранены","Уведомления настроены.","success"))).pack(side="right")
        prank=tk.Frame(wrap,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); prank.pack(fill="x",pady=8)
        tk.Label(prank,text="Скример",bg=PANEL,fg=TEXT,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=22,pady=(18,4))
        tk.Label(prank,text="Розыгрыш работает только с разрешения получателя. Основатель может отправить его из админ-панели.",bg=PANEL,fg=MUTED,font=("Segoe UI",8),wraplength=850,justify="left").pack(anchor="w",padx=22,pady=(0,10))
        allow=tk.BooleanVar(value=bool(self.prof.get("allow_pranks")))
        tk.Checkbutton(prank,text="Разрешаю внутриигровые розыгрыши",variable=allow,bg=PANEL,fg=TEXT,selectcolor=PANEL2,activebackground=PANEL,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=6)
        pb=tk.Frame(prank,bg=PANEL); pb.pack(fill="x",padx=22,pady=(2,18))
        ttk.Button(pb,text="Сохранить разрешение",command=lambda:self.save_pranks(allow.get())).pack(side="left")
        ttk.Button(pb,text="Проверить скример",style="Secondary.TButton",command=self.show_screamer).pack(side="left",padx=8)
        self.card(wrap,"Версия",f"{APP_NAME} v{APP_VERSION}\n{APP_PUBLISHER}\nWindows release build")

    def change_display_name(self):
        self.page("Профиль")

    def save_pranks(self,value):
        try:
            self.db.update("profiles",{"id":f"eq.{self.user['id']}"},{"allow_pranks":bool(value)})
            self.prof["allow_pranks"]=bool(value); self.notify("Скример","Разрешение сохранено.","success")
        except Exception as e: self.notify("Скример",str(e),"error")

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
            self.notify(APP_NAME, "Жалоба отправлена.", "success"); self.reports_page()
        except Exception as e: self.notify("Жалоба", str(e), "error")

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
                except Exception as e: self.notify("Жалоба", str(e), "error")
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
        if self.prof.get("role") == "FOUNDER":
            ttk.Button(actions, text="⚡ Отправить скример", command=lambda: self.send_screamer(tree)).pack(side="left", padx=4)
            ttk.Button(actions, text="⚡ Тест на себе", style="Secondary.TButton", command=self.show_screamer).pack(side="left", padx=4)
        self.refresh_admin_users(tree)

    def refresh_admin_users(self, tree):
        for i in tree.get_children(): tree.delete(i)
        try:
            rows = self.db.table("profiles", "id,username,display_name,avatar_url,bio,role,status,premium,allow_pranks", {}, "created_at.asc", 300)
            for r in rows: tree.insert("", "end", iid=r["id"], values=(r["id"],r.get("username"),r.get("display_name"),role_label(r.get("role")),r.get("status"),"Да" if r.get("premium") else "Нет"))
        except Exception as e: self.notify("Пользователи", str(e), "error")

    def selected_user(self, tree):
        ids = tree.selection()
        if not ids: self.notify(APP_NAME, "Выбери пользователя.", "warning"); return None
        return ids[0]

    def get_profile(self, uid):
        rows = self.db.table("profiles", "id,username,display_name,avatar_url,bio,role,status,premium,allow_pranks", {"id": f"eq.{uid}"}); return rows[0] if rows else None

    def change_user_role(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        if uid == self.user["id"] and self.prof.get("role") == "FOUNDER":
            self.notify(APP_NAME, "Основатель не должен менять свою роль из клиентского интерфейса.", "warning"); return
        if target.get("role") == "FOUNDER" and self.prof.get("role") != "FOUNDER":
            self.notify(APP_NAME, "Только Основатель может управлять аккаунтом Основателя.", "error"); return
        win = tk.Toplevel(self); win.title("Роль"); win.geometry("420x220"); win.configure(bg=BG)
        tk.Label(win, text=f"Роль для {target.get('username')}", bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=20)
        values = ROLE_ORDER if self.prof.get("role") == "FOUNDER" else ["MODERATOR","PREMIUM","USER"]
        cb = ttk.Combobox(win, values=[role_label(x) for x in values], state="readonly", width=35); cb.current(values.index(target.get("role")) if target.get("role") in values else len(values)-1); cb.pack(pady=10)
        def save():
            new_role = values[cb.current()]
            if self.prof.get("role") != "FOUNDER" and new_role in ("FOUNDER","ADMIN"):
                self.notify(APP_NAME, "Администратор может выдавать только MODERATOR/PREMIUM/USER.", "error"); return
            try:
                self.db.update("profiles", {"id": f"eq.{uid}"}, {"role": new_role})
                self.log("Изменена роль", "profiles", uid, {"role": new_role}); win.destroy(); self.refresh_admin_users(tree)
            except Exception as e: self.notify("Роль", str(e), "error")
        ttk.Button(win, text="Сохранить", command=save).pack(pady=10)

    def change_user_status(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if target and target.get("role") == "FOUNDER" and self.prof.get("role") != "FOUNDER":
            self.notify(APP_NAME, "Только Основатель может изменять статус Основателя.", "error"); return
        status = simpledialog.askstring("Статус", "ACTIVE / BLOCKED / BANNED:", initialvalue=target.get("status","ACTIVE") if target else "ACTIVE")
        if status not in STATUS_VALUES: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"status": status}); self.log("Изменён статус", "profiles", uid, {"status": status}); self.refresh_admin_users(tree)
        except Exception as e: self.notify("Статус", str(e), "error")

    def toggle_premium(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"premium": not bool(target.get("premium"))}); self.log("Изменён Premium", "profiles", uid); self.refresh_admin_users(tree)
        except Exception as e: self.notify("Premium", str(e), "error")

    def toggle_prank(self, tree):
        uid = self.selected_user(tree)
        if not uid: return
        target = self.get_profile(uid)
        if not target: return
        try:
            self.db.update("profiles", {"id": f"eq.{uid}"}, {"allow_pranks": not bool(target.get("allow_pranks"))}); self.log("Изменено разрешение на розыгрыши", "profiles", uid); self.refresh_admin_users(tree)
        except Exception as e: self.notify("Скример", str(e), "error")

    def send_screamer(self, tree):
        if self.prof.get("role") != "FOUNDER":
            self.notify("Скример","Функция доступна только Основателю.","error"); return
        uid=self.selected_user(tree)
        if not uid: return
        target=self.get_profile(uid)
        if not target: return
        if not target.get("allow_pranks"):
            self.notify("Скример","Пользователь не разрешил розыгрыши в настройках.","warning"); return
        try:
            self.db.insert("prank_events",{"target_user_id":uid,"created_by":self.user["id"],"kind":"screamer"})
            self.log("Отправлен скример","profiles",uid)
            self.notify("Скример отправлен",f"Сигнал отправлен пользователю {target.get('display_name') or target.get('username') or uid}.","success")
        except Exception as e: self.notify("Скример",str(e),"error")

    def start_prank_listener(self):
        if not self.user.get("id"): return
        if getattr(self, "_prank_listener_started", False): return
        self._prank_listener_started = True
        def poll():
            try:
                rows=self.db.table("prank_events","id,kind,created_at",{"target_user_id":f"eq.{self.user['id']}","consumed_at":"is.null"},"created_at.asc",5)
                for event in rows:
                    self.db.update("prank_events",{"id":f"eq.{event['id']}"},{"consumed_at":datetime.utcnow().isoformat()+"Z"})
                    self.after(0,self.show_screamer)
            except Exception:
                pass
            if self.user.get("id"): self.after(2500,poll)
            else: self._prank_listener_started = False
        self.after(1000,poll)

    def show_screamer(self):
        if not self.prof.get("allow_pranks") and self.prof.get("role") != "FOUNDER":
            self.notify("Скример","Сначала разреши розыгрыши в настройках.","warning"); return
        win=tk.Toplevel(self); win.overrideredirect(True); win.attributes("-topmost",True); win.configure(bg="#02050a")
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight(); win.geometry(f"{sw}x{sh}+0+0")
        canvas=tk.Canvas(win,bg="#02050a",highlightthickness=0); canvas.pack(fill="both",expand=True)
        canvas.create_rectangle(0,0,sw,sh,fill="#02050a",outline="")
        glow=["#07172b","#0b2546","#102f57","#0b2546"]
        for i,col in enumerate(glow):
            r=min(sw,sh)*(.12+i*.06); canvas.create_oval(sw/2-r,sh*.42-r,sw/2+r,sh*.42+r,fill=col,outline="")
        shield=[(sw/2,sh*.16),(sw*.64,sh*.25),(sw*.60,sh*.58),(sw/2,sh*.72),(sw*.40,sh*.58),(sw*.36,sh*.25)]
        canvas.create_polygon(shield,fill="#061324",outline="#3b82f6",width=5)
        canvas.create_text(sw/2,sh*.43,text="⚡",fill="#8bc6ff",font=("Segoe UI Symbol",100,"bold"))
        canvas.create_text(sw/2,sh*.79,text="RMRP СКРИМЕР",fill="#f4f7fb",font=("Segoe UI",32,"bold"))
        canvas.create_text(sw/2,sh*.85,text="Розыгрыш от Основателя",fill="#7894b5",font=("Segoe UI",14))
        close=tk.Button(win,text="×",command=win.destroy,bg="#07111f",fg="#9ab2cc",activebackground="#182c45",activeforeground=TEXT,bd=0,font=("Segoe UI",18),cursor="hand2")
        close.place(relx=1,x=-18,y=14,anchor="ne")
        def flash(i=0):
            if not win.winfo_exists(): return
            if i>=8: return
            canvas.configure(bg="#1b0710" if i%2 else "#02050a")
            win.after(80,lambda:flash(i+1))
        flash()
        if winsound and self.app_settings.get("sound_enabled",True):
            try:
                winsound.Beep(740,90); winsound.Beep(360,140); winsound.Beep(880,110)
            except Exception: pass
        win.bind("<Escape>",lambda e:win.destroy()); win.after(5000,win.destroy)

    def admin_laws(self, parent):
        row=tk.Frame(parent,bg=BG); row.pack(fill="x",pady=10)
        ttk.Button(row, text="⟳ Синхронизировать законы RMRP", command=self.sync_rmrp_laws).pack(side="left")
        ttk.Button(row, text="+ Добавить закон", command=self.add_law).pack(side="left",padx=8)
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
            except Exception as e: self.notify(table, str(e), "error")
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
        except Exception as e: self.notify("Тест", str(e), "error")

    def admin_announcements(self, parent):
        ttk.Button(parent, text="+ Создать объявление", command=self.add_announcement).pack(anchor="w", pady=10)
        tree = ttk.Treeview(parent, columns=("id","title","type","active","date"), show="headings")
        for c,w in [("id",80),("title",320),("type",100),("active",100),("date",220)]: tree.heading(c,text=c); tree.column(c,width=w)
        tree.pack(fill="both", expand=True)
        try:
            rows = self.db.table("announcements", "id,title,type,is_active,created_at", {}, "created_at.desc", 200)
            for r in rows: tree.insert("", "end", values=(r["id"],r["title"],r["type"],r["is_active"],r["created_at"]))
        except Exception as e: self.notify("Объявления", str(e), "error")

    def add_announcement(self):
        title = simpledialog.askstring("Объявление", "Заголовок:")
        if not title: return
        content = self.text_dialog("Объявление", "Текст:")
        if content is None: return
        typ = simpledialog.askstring("Объявление", "Тип (INFO/WARN/UPDATE):", initialvalue="INFO") or "INFO"
        try:
            self.db.insert("announcements", {"title": title, "content": content, "type": typ, "is_active": True, "created_by": self.user["id"]})
            self.log("Создано объявление", "announcements", title); self.admin_page()
        except Exception as e: self.notify("Объявление", str(e), "error")

    def admin_audit(self, parent):
        tree = ttk.Treeview(parent, columns=("id","user","action","target","details","date"), show="headings")
        for c,w in [("id",70),("user",220),("action",220),("target",140),("details",300),("date",220)]: tree.heading(c,text=c); tree.column(c,width=w)
        tree.pack(fill="both", expand=True, pady=10)
        try:
            rows = self.db.table("audit_logs", "id,user_id,action,target_type,target_id,details,created_at", {}, "created_at.desc", 300)
            for r in rows: tree.insert("", "end", values=(r["id"],r.get("user_id"),r.get("action"),r.get("target_type"),r.get("target_id"),json.dumps(r.get("details"),ensure_ascii=False),r.get("created_at")))
        except Exception as e: self.notify("Журнал", str(e), "error")

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
        self.db.auth_logout(); self.user = {}; self.prof = {}; self._prank_listener_started = False; self.show_login()


if __name__ == "__main__":
    App().mainloop()
