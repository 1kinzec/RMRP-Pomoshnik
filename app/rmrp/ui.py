"""UI-тулкит: скруглённые карточки, кнопки, поля, переключатели, скролл, тосты, аватары."""
import io
import os
import random
import sys
import threading
import tkinter as tk
import urllib.request
from tkinter import ttk
from tkinter import font as tkfont

from .config import (ACCENT, ACCENT_HI, ACCENT_LO, ACCENT_TXT, BG, BORDER, BORDER2, DANGER, DANGER_HI, FONT, FONT_SYM,
                     MUTED, PANEL, PANEL2, PANEL3, SIDEBAR, SUCCESS, TEXT, TEXT2, WARNING)

try:  # Pillow необязателен: без него просто не будет картинок
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
except Exception:  # noqa: BLE001
    Image = ImageDraw = ImageFilter = ImageTk = None


# ----------------------------------------------------------------------------- утилиты
def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return os.path.normpath(os.path.join(base, *parts))


def mix(c1, c2, t):
    """Смешивает два цвета: t=0 -> c1, t=1 -> c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rr_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def parent_bg(widget, default=BG):
    try:
        return widget.cget("bg")
    except Exception:  # noqa: BLE001
        return default


def font(size=10, bold=False, family=FONT):
    return (family, size, "bold" if bold else "normal")


def lbl(parent, text="", size=10, bold=False, color=TEXT, bg=None, **kw):
    kw.setdefault("anchor", "w")
    kw.setdefault("justify", "left")
    return tk.Label(parent, text=text, font=font(size, bold), fg=color, bg=bg or parent_bg(parent), bd=0, **kw)


def bind_tree(widget, sequence, func):
    widget.bind(sequence, func, add="+")
    for child in widget.winfo_children():
        bind_tree(child, sequence, func)


def set_dark_titlebar(window, caption=BG):
    """Тёмная рамка окна Windows 10/11 (на других ОС — ничего не делает)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        val = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                break
        rgb = int(caption[5:7] + caption[3:5] + caption[1:3], 16)  # COLORREF = 0x00BBGGRR
        col = ctypes.c_int(rgb)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(col), 4)  # DWMWA_CAPTION_COLOR (Win11)
    except Exception:  # noqa: BLE001
        pass


def setup_styles(root):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=40, borderwidth=0, font=font(9))
    s.configure("Treeview.Heading", background=SIDEBAR, foreground=MUTED, font=font(9, True), relief="flat", borderwidth=0)
    s.map("Treeview", background=[("selected", mix(ACCENT, PANEL, .45))], foreground=[("selected", "#ffffff")])
    s.map("Treeview.Heading", background=[("active", SIDEBAR)])
    s.configure("TCombobox", fieldbackground=PANEL2, background=PANEL3, foreground=TEXT, arrowcolor=ACCENT_TXT,
                bordercolor=BORDER2, lightcolor=PANEL2, darkcolor=PANEL2, padding=6)
    s.map("TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", TEXT)], selectbackground=[("readonly", PANEL2)],
          selectforeground=[("readonly", TEXT)])
    s.configure("Dark.Vertical.TScrollbar", background=PANEL3, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                lightcolor=PANEL3, darkcolor=PANEL3, gripcount=0, width=10)
    s.map("Dark.Vertical.TScrollbar", background=[("active", BORDER2)])
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", font(10))


# ----------------------------------------------------------------------------- картинки
_img_cache = {}


def pil_to_tk(img):
    return ImageTk.PhotoImage(img) if ImageTk else None


def load_image(name, size=None):
    if Image is None:
        return None
    key = (name, size)
    if key in _img_cache:
        return _img_cache[key]
    try:
        img = Image.open(resource_path("assets", name)).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        _img_cache[key] = ImageTk.PhotoImage(img)
    except Exception:  # noqa: BLE001
        _img_cache[key] = None
    return _img_cache[key]


def make_hero(w, h, seed=7):
    """Ночной город с неоновым свечением — фон экрана входа (генерируется, не хранится в репозитории)."""
    if Image is None:
        return None
    key = ("hero", w, h)
    if key in _img_cache:
        return _img_cache[key]
    rnd = random.Random(seed)
    img = Image.new("RGB", (w, h), "#060b16")
    px = ImageDraw.Draw(img)
    for y in range(h):  # вертикальный градиент неба
        t = y / h
        px.line([(0, y), (w, y)], fill=(int(8 + 14 * (1 - t)), int(14 + 34 * (1 - t) ** 1.4), int(30 + 70 * (1 - t) ** 1.2)))
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w * .15, h * .02, w * .95, h * .62], fill=(20, 70, 160))
    glow = glow.filter(ImageFilter.GaussianBlur(w // 6))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), .55)
    d = ImageDraw.Draw(img)
    x = -10
    while x < w:  # дома
        bw = rnd.randint(int(w * .06), int(w * .13))
        bh = rnd.randint(int(h * .22), int(h * .62))
        shade = rnd.randint(8, 18)
        d.rectangle([x, h - bh, x + bw, h], fill=(shade, shade + 6, shade + 20), outline=(24, 48, 84))
        for wy in range(h - bh + 12, h - 8, 16):
            for wx in range(x + 8, x + bw - 8, 12):
                if rnd.random() < .22:
                    d.rectangle([wx, wy, wx + 4, wy + 6], fill=(70, 140, 230) if rnd.random() < .8 else (230, 190, 90))
        x += bw + rnd.randint(2, 8)
    d.rectangle([0, int(h * .93), w, h], fill=(4, 8, 14))  # дорога
    d.line([(0, int(h * .93)), (w, int(h * .93))], fill=(28, 70, 130), width=2)
    over = Image.new("RGBA", (w, h), (0, 0, 0, 0))  # затемнение к низу и краям
    od = ImageDraw.Draw(over)
    for y in range(h):
        od.line([(0, y), (w, y)], fill=(4, 8, 16, int(150 * (y / h) ** 2)))
    img = Image.alpha_composite(img.convert("RGBA"), over)
    _img_cache[key] = ImageTk.PhotoImage(img)
    return _img_cache[key]


class Avatar(tk.Canvas):
    """Круглый аватар: картинка по ссылке (если получилось загрузить) или инициал. Опционально точка статуса."""
    _url_cache = {}

    def __init__(self, parent, name="?", size=40, url="", online=None, ring=ACCENT, bg=None):
        bg = bg or parent_bg(parent)
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self.size, self.name, self.ring, self.online, self._photo = size, name or "?", ring, online, None
        self._draw()
        if url and Image is not None:
            self._load(url)

    def _draw(self):
        s = self.size
        self.delete("all")
        self.create_oval(1, 1, s - 1, s - 1, fill=mix(ACCENT, "#06101f", .72), outline=self.ring, width=2)
        if self._photo:
            self.create_image(s / 2, s / 2, image=self._photo)
        else:
            self.create_text(s / 2, s / 2, text=(self.name[:1] or "?").upper(), fill="#b8d6ff", font=font(max(9, s // 3), True))
        if self.online is not None:
            r = max(4, s // 8)
            self.create_oval(s - 2 * r - 1, s - 2 * r - 1, s - 1, s - 1, fill=SUCCESS if self.online else "#5d6b82", outline=self["bg"], width=2)

    def _load(self, url):
        if url in Avatar._url_cache:
            self._set(Avatar._url_cache[url])
            return

        def work():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "RMRP-Pomoshnik"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = r.read(2_000_000)
                img = Image.open(io.BytesIO(data)).convert("RGBA").resize((self.size - 6, self.size - 6), Image.LANCZOS)
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).ellipse([0, 0, img.size[0] - 1, img.size[1] - 1], fill=255)
                img.putalpha(mask)
                Avatar._url_cache[url] = img
                self.after(0, lambda: self._set(img))
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=work, daemon=True).start()

    def _set(self, img):
        try:
            if self.winfo_exists():
                self._photo = ImageTk.PhotoImage(img)
                self._draw()
        except tk.TclError:
            pass


# ----------------------------------------------------------------------------- Card
class Card(tk.Canvas):
    """Скруглённая карточка. Содержимое кладётся в card.body (обычный Frame)."""

    def __init__(self, parent, bg=PANEL, border=BORDER, radius=12, pad=14, outer=None, height=None, hover_bg=None,
                 hover_border=None, **kw):
        self._bg, self._border, self._radius, self._pad = bg, border, radius, pad
        self._hover_bg = hover_bg
        self._hover_border = hover_border
        self._fixed = height
        super().__init__(parent, bg=outer or parent_bg(parent), highlightthickness=0, bd=0, height=height or 10, **kw)
        self.body = tk.Frame(self, bg=bg)
        self._win = self.create_window(pad, pad, anchor="nw", window=self.body)
        self._cur = (bg, border)
        self._last = (0, 0)
        self.bind("<Configure>", self._on_canvas)
        self.body.bind("<Configure>", self._on_body)

    def _on_canvas(self, e):
        self.itemconfigure(self._win, width=max(1, e.width - 2 * self._pad))
        if self._fixed:
            self.itemconfigure(self._win, height=max(1, e.height - 2 * self._pad))
        self._redraw(e.width, e.height)

    def _on_body(self, e):
        if not self._fixed:
            h = e.height + 2 * self._pad
            if int(float(self.cget("height"))) != h:
                self.configure(height=h)

    def _redraw(self, w, h):
        self._last = (w, h)
        self.delete("bgshape")
        fill, outline = self._cur
        self.create_polygon(rr_points(1, 1, w - 1, h - 1, self._radius), smooth=True, fill=fill, outline=outline, width=1, tags="bgshape")
        self.tag_lower("bgshape")

    def set_colors(self, bg=None, border=None):
        bg = bg or self._bg
        border = border or self._border
        self._cur = (bg, border)
        self.body.configure(bg=bg)
        _recolor(self.body, bg)
        self._redraw(*self._last)

    def make_clickable(self, command):
        self.configure(cursor="hand2")
        hb = self._hover_bg or mix(self._bg, ACCENT, .10)
        hr = self._hover_border or ACCENT_LO
        bind_tree(self, "<Enter>", lambda e: self.set_colors(hb, hr))
        bind_tree(self, "<Leave>", lambda e: self._leave())
        bind_tree(self, "<Button-1>", lambda e: command())
        for w in _descendants(self.body):
            try:
                if not isinstance(w, (RButton, Switch)):
                    w.configure(cursor="hand2")  # type: ignore[call-arg]
            except tk.TclError:
                pass

    def _leave(self):
        x, y = self.winfo_pointerxy()
        w = self.winfo_containing(x, y)
        while w is not None:
            if w is self:
                return
            w = getattr(w, "master", None)
        self.set_colors(self._bg, self._border)


def _descendants(w):
    for c in w.winfo_children():
        yield c
        yield from _descendants(c)


def _recolor(widget, new_bg):
    """Подкрашивает вложенные Label/Frame, у которых фон совпадал с прежним фоном карточки."""
    old = widget["bg"] if "bg" in widget.keys() else None
    for c in widget.winfo_children():
        if isinstance(c, (tk.Label, tk.Frame)) and "bg" in c.keys():
            if c["bg"] in (old, PANEL, PANEL2) and not isinstance(c, Card):
                c.configure(bg=new_bg)
            _recolor(c, new_bg)


# ----------------------------------------------------------------------------- Button
BUTTON_STYLES = {
    "primary": dict(bg=ACCENT, hover=ACCENT_HI, press=ACCENT_LO, fg="#ffffff", border=None),
    "secondary": dict(bg=PANEL2, hover=PANEL3, press=BORDER, fg=TEXT, border=BORDER2),
    "ghost": dict(bg=None, hover=PANEL2, press=PANEL3, fg=TEXT2, border=None),
    "outline": dict(bg=None, hover=mix(ACCENT, BG, .82), press=mix(ACCENT, BG, .7), fg=ACCENT_TXT, border=ACCENT_LO),
    "danger": dict(bg=DANGER, hover=DANGER_HI, press="#c93030", fg="#ffffff", border=None),
    "success": dict(bg=SUCCESS, hover="#3ad67d", press="#17a34a", fg="#04210f", border=None),
    "nav": dict(bg=None, hover=mix(SIDEBAR, ACCENT, .12), press=mix(SIDEBAR, ACCENT, .25), fg=TEXT2, border=None,
                active_bg=mix(SIDEBAR, ACCENT, .28), active_fg="#ffffff"),
    "link": dict(bg=None, hover=None, press=None, fg=ACCENT_TXT, border=None),
}


class RButton(tk.Canvas):
    click_hook = None  # приложение подставляет сюда звук клика

    def __init__(self, parent, text="", command=None, style="primary", icon=None, width=None, height=36, radius=9,
                 anchor="center", size=10, bold=True, outer=None, padx=16, active=False, icon_color=None):
        self.text, self.command, self.style_name, self.icon = text, command, style, icon
        self.st = BUTTON_STYLES[style]
        self.radius, self.anchor_mode, self.size, self.bold, self.padx = radius, anchor, size, bold, padx
        self.active, self.hovering, self.pressed, self.disabled = active, False, False, False
        self.icon_color = icon_color
        f = tkfont.Font(family=FONT, size=size, weight="bold" if bold else "normal")
        tw = f.measure(text) + (28 if icon else 0)
        w = width or (tw + 2 * padx)
        super().__init__(parent, width=w, height=height, bg=outer or parent_bg(parent), highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set(hovering=True))
        self.bind("<Leave>", lambda e: self._set(hovering=False, pressed=False))
        self.bind("<ButtonPress-1>", lambda e: self._set(pressed=True))
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self._draw()

    def _release(self, e):
        was = self.pressed
        self._set(pressed=False)
        if was and not self.disabled and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            if RButton.click_hook:
                RButton.click_hook()
            if self.command:
                self.command()

    def configure_text(self, text):
        self.text = text
        self._draw()

    def set_active(self, value):
        self.active = value
        self._draw()

    def set_disabled(self, value):
        self.disabled = value
        self.configure(cursor="arrow" if value else "hand2")
        self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            w, h = int(self["width"]), int(self["height"])
        st = self.st
        fill = st["bg"]
        fg = st["fg"]
        if self.active and "active_bg" in st:
            fill, fg = st["active_bg"], st["active_fg"]
        if not self.disabled:
            if self.pressed and st.get("press"):
                fill = st["press"]
            elif self.hovering and st.get("hover") and not (self.active and "active_bg" in st):
                fill = st["hover"]
        if self.disabled:
            fill = mix(fill, BG, .55) if fill else None
            fg = MUTED
        self.delete("all")
        if fill or st.get("border"):
            self.create_polygon(rr_points(1, 1, w - 1, h - 1, self.radius), smooth=True, fill=fill or "",
                                outline=st["border"] if st.get("border") else (fill or ""), width=1)
        cy = h / 2
        if self.anchor_mode == "w":
            x = self.padx
            if self.icon:
                self.create_text(x, cy, text=self.icon, anchor="w", fill=self.icon_color or fg, font=(FONT_SYM, self.size + 2))
                x += 28
            self.create_text(x, cy, text=self.text, anchor="w", fill=fg, font=font(self.size, self.bold))
        else:
            label = f"{self.icon}  {self.text}" if self.icon else self.text
            self.create_text(w / 2, cy, text=label, fill=fg, font=font(self.size, self.bold))


# ----------------------------------------------------------------------------- Field / Switch
class Field(tk.Canvas):
    """Поле ввода со скруглением и плейсхолдером."""

    def __init__(self, parent, placeholder="", secret=False, height=40, width=None, outer=None, fill=PANEL2, radius=8, on_return=None,
                 icon=None):
        super().__init__(parent, height=height, width=width or 200, bg=outer or parent_bg(parent), highlightthickness=0, bd=0)
        self.placeholder, self.fill, self.radius, self.focused, self.icon = placeholder, fill, radius, False, icon
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, bg=fill, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                              highlightthickness=0, font=font(10), show="•" if secret else "", disabledbackground=fill,
                              disabledforeground=MUTED)
        self._ex = 40 if icon else 12
        self._win = self.create_window(self._ex, height / 2, anchor="w", window=self.entry)
        self.bind("<Configure>", lambda e: self._draw())
        self.entry.bind("<FocusIn>", lambda e: self._focus(True))
        self.entry.bind("<FocusOut>", lambda e: self._focus(False))
        self.var.trace_add("write", lambda *a: self._draw())
        if on_return:
            self.entry.bind("<Return>", lambda e: on_return())

    def _focus(self, v):
        self.focused = v
        self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        self.delete("shape")
        self.create_polygon(rr_points(1, 1, w - 1, h - 1, self.radius), smooth=True, fill=self.fill,
                            outline=ACCENT if self.focused else BORDER2, width=1, tags="shape")
        self.tag_lower("shape")
        self.itemconfigure(self._win, width=max(10, w - self._ex - 12), height=h - 14)
        if self.icon:
            self.create_text(20, h / 2, text=self.icon, fill=MUTED, font=(FONT_SYM, 11), tags="shape")
        self.delete("ph")
        if not self.var.get() and self.placeholder:
            self.create_text(self._ex + 2, h / 2, text=self.placeholder, anchor="w", fill=MUTED, font=font(10), tags="ph")
            self.tag_bind("ph", "<Button-1>", lambda e: self.entry.focus_set())

    def get(self):
        return self.var.get().strip()

    def raw(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value or "")

    def focus_entry(self):
        self.entry.focus_set()

    def set_state(self, state):
        self.entry.configure(state=state)


class Switch(tk.Canvas):
    def __init__(self, parent, value=False, command=None, outer=None):
        super().__init__(parent, width=46, height=26, bg=outer or parent_bg(parent), highlightthickness=0, bd=0, cursor="hand2")
        self.value, self.command = bool(value), command
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _toggle(self, _e=None):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command(self.value)

    def set(self, v):
        self.value = bool(v)
        self._draw()

    def get(self):
        return self.value

    def _draw(self):
        self.delete("all")
        self.create_polygon(rr_points(1, 2, 45, 24, 11), smooth=True, fill=ACCENT if self.value else PANEL3,
                            outline=ACCENT_HI if self.value else BORDER2)
        x = 33 if self.value else 13
        self.create_oval(x - 8, 5, x + 8, 21, fill="#ffffff", outline="")


# ----------------------------------------------------------------------------- Tabs
class UnderTabs(tk.Frame):
    def __init__(self, parent, items, on_change, selected=None, bg=None):
        super().__init__(parent, bg=bg or parent_bg(parent))
        self.on_change, self.items, self.cells = on_change, items, {}
        self.bg = bg or parent_bg(parent)
        for key, text in items:
            cell = tk.Frame(self, bg=self.bg, cursor="hand2")
            cell.pack(side="left", padx=(0, 4))
            l = tk.Label(cell, text=text, font=font(10, True), bg=self.bg, fg=MUTED, padx=16, pady=9, cursor="hand2")
            l.pack()
            u = tk.Frame(cell, bg=self.bg, height=2)
            u.pack(fill="x")
            for w in (cell, l):
                w.bind("<Button-1>", lambda e, k=key: self.select(k))
            self.cells[key] = (l, u)
        self.current = None
        self.select(selected or items[0][0], fire=False)

    def select(self, key, fire=True):
        self.current = key
        for k, (l, u) in self.cells.items():
            on = k == key
            l.configure(fg=TEXT if on else MUTED, bg=mix(self.bg, ACCENT, .08) if on else self.bg)
            u.configure(bg=ACCENT_HI if on else self.bg)
        if fire:
            self.on_change(key)


class PillTabs(tk.Frame):
    def __init__(self, parent, items, on_change, selected=None):
        super().__init__(parent, bg=parent_bg(parent))
        self.on_change, self.btns, self.current = on_change, {}, None
        for key, text in items:
            b = RButton(self, text, lambda k=key: self.select(k), style="secondary", height=32, size=9, padx=16)
            b.pack(side="left", padx=(0, 8))
            self.btns[key] = b
        self.select(selected or items[0][0], fire=False)

    def select(self, key, fire=True):
        self.current = key
        for k, b in self.btns.items():
            b.st = BUTTON_STYLES["primary" if k == key else "secondary"]
            b._draw()
        if fire:
            self.on_change(key)


# ----------------------------------------------------------------------------- ScrollFrame
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG, padx=0):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", style="Dark.Vertical.TScrollbar", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        for w in (self, self.canvas, self.body):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def _on_scroll(self, lo, hi):
        self.sb.set(lo, hi)
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.sb.pack_forget()
        elif not self.sb.winfo_ismapped():
            self.sb.pack(side="right", fill="y", before=self.canvas)

    def _bind_wheel(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self._scroll(-3))
        self.canvas.bind_all("<Button-5>", lambda e: self._scroll(3))

    def _unbind_wheel(self, _e=None):
        x, y = self.winfo_pointerxy()
        w = self.winfo_containing(x, y)
        while w is not None:
            if w is self:
                return
            w = getattr(w, "master", None)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(seq)

    def _wheel(self, e):
        self._scroll(-1 * (e.delta // 120) * 3 if e.delta else 0)

    def _scroll(self, units):
        if self.body.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(units, "units")

    def to_top(self):
        self.canvas.yview_moveto(0)

    def to_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1)


# ----------------------------------------------------------------------------- IconTile / Chip
def icon_tile(parent, glyph, color, size=44, bg=None, radius=11):
    bg = bg or parent_bg(parent)
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
    c.create_polygon(rr_points(1, 1, size - 1, size - 1, radius), smooth=True, fill=mix(bg, color, .22), outline=mix(bg, color, .5))
    c.create_text(size / 2, size / 2, text=glyph, fill=color, font=(FONT_SYM, int(size * .42), "bold"))
    return c


def chip(parent, text, color=ACCENT_TXT, bg=None, size=8):
    bg = bg or parent_bg(parent)
    return tk.Label(parent, text=text, font=font(size, True), fg=color, bg=mix(bg, color, .16), padx=8, pady=2, bd=0)


# ----------------------------------------------------------------------------- Toast
class Toasts:
    COLORS = {"info": (ACCENT, "i"), "success": (SUCCESS, "✓"), "warning": (WARNING, "!"), "error": (DANGER, "×")}

    def __init__(self, root):
        self.root = root
        self.items = []

    def show(self, title, message="", kind="info", duration=3600):
        color, glyph = self.COLORS.get(kind, self.COLORS["info"])
        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        try:
            t.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        t.configure(bg=color)
        inner = tk.Frame(t, bg=PANEL2)
        inner.pack(padx=(3, 0), fill="both", expand=True)
        row = tk.Frame(inner, bg=PANEL2)
        row.pack(fill="both", padx=14, pady=11)
        tk.Label(row, text=glyph, bg=mix(PANEL2, color, .3), fg=color, font=font(11, True), width=2).pack(side="left", anchor="n")
        col = tk.Frame(row, bg=PANEL2)
        col.pack(side="left", padx=(10, 0))
        tk.Label(col, text=title, bg=PANEL2, fg=TEXT, font=font(10, True), anchor="w", justify="left", wraplength=300).pack(anchor="w")
        if message:
            tk.Label(col, text=message, bg=PANEL2, fg=TEXT2, font=font(9), anchor="w", justify="left", wraplength=300).pack(anchor="w", pady=(2, 0))
        t.update_idletasks()
        self.items.append(t)
        self._layout()
        self._fade(t, 0.0, 0.97)
        t.after(duration, lambda: self._close(t))
        t.bind("<Button-1>", lambda e: self._close(t))

    def _fade(self, t, a, target):
        try:
            if not t.winfo_exists():
                return
            a = min(target, a + 0.16)
            t.attributes("-alpha", a)
            if a < target:
                t.after(20, lambda: self._fade(t, a, target))
        except tk.TclError:
            pass

    def _close(self, t):
        if t in self.items:
            self.items.remove(t)
        try:
            t.destroy()
        except tk.TclError:
            pass
        self._layout()

    def _layout(self):
        try:
            self.root.update_idletasks()
            x2 = self.root.winfo_rootx() + self.root.winfo_width() - 22
            y = self.root.winfo_rooty() + self.root.winfo_height() - 22
        except tk.TclError:
            return
        for t in reversed(self.items):
            try:
                w, h = t.winfo_reqwidth(), t.winfo_reqheight()
                y -= h
                t.geometry(f"{w}x{h}+{x2 - w}+{y}")
                y -= 8
            except tk.TclError:
                pass


# ----------------------------------------------------------------------------- модальные окна
def modal(app, title, width, height, bg=BG):
    win = tk.Toplevel(app)
    win.title(title)
    win.configure(bg=bg)
    app.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - width) // 2
    y = app.winfo_rooty() + (app.winfo_height() - height) // 2
    win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
    win.resizable(False, False)
    win.transient(app)
    try:
        win.iconbitmap(resource_path("assets", "rmrp.ico"))
    except Exception:  # noqa: BLE001
        pass
    set_dark_titlebar(win)
    try:
        win.wait_visibility()
        win.grab_set()
    except tk.TclError:
        pass
    return win


def confirm(app, title, message, ok_text="Да", danger=False):
    win = modal(app, title, 440, 210, PANEL)
    res = {"ok": False}
    lbl(win, title, 14, True, bg=PANEL).pack(anchor="w", padx=24, pady=(22, 6))
    lbl(win, message, 10, False, TEXT2, bg=PANEL, wraplength=390).pack(anchor="w", padx=24)
    bar = tk.Frame(win, bg=PANEL)
    bar.pack(side="bottom", fill="x", padx=24, pady=20)

    def yes():
        res["ok"] = True
        win.destroy()
    RButton(bar, ok_text, yes, "danger" if danger else "primary").pack(side="right")
    RButton(bar, "Отмена", win.destroy, "secondary").pack(side="right", padx=8)
    app.wait_window(win)
    return res["ok"]


def ask_text(app, title, label, initial="", multiline=False, secret=False, ok_text="Сохранить"):
    win = modal(app, title, 560, 420 if multiline else 230, PANEL)
    res = {"v": None}
    lbl(win, label, 11, True, bg=PANEL).pack(anchor="w", padx=24, pady=(22, 8))
    if multiline:
        t = tk.Text(win, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=font(10), padx=12, pady=10,
                    highlightthickness=1, highlightbackground=BORDER2, highlightcolor=ACCENT)
        t.pack(fill="both", expand=True, padx=24)
        t.insert("1.0", initial)
        getter = lambda: t.get("1.0", "end").strip()  # noqa: E731
        t.focus_set()
    else:
        f = Field(win, secret=secret, outer=PANEL)
        f.pack(fill="x", padx=24)
        f.set(initial)
        f.focus_entry()
        getter = f.get
    bar = tk.Frame(win, bg=PANEL)
    bar.pack(side="bottom", fill="x", padx=24, pady=18)

    def ok():
        res["v"] = getter()
        win.destroy()
    RButton(bar, ok_text, ok).pack(side="right")
    RButton(bar, "Отмена", win.destroy, "secondary").pack(side="right", padx=8)
    app.wait_window(win)
    return res["v"]
