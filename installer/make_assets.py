"""Рисует картинки мастера установки в стиле приложения (тёмный фон с фиолетовым свечением, каркасная графика, логотип).

Запуск: python installer/make_assets.py   (нужен Pillow). Результат кладётся в installer/assets и коммитится,
так что сборка установщика этот скрипт не требует.
"""
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
LOGO = os.path.join(HERE, "..", "app", "assets", "rmrp.png")
BG, BG2, ACCENT, ACCENT_TXT, TEXT, MUTED = (7, 7, 13), (12, 13, 26), (139, 108, 240), (164, 139, 255), (245, 245, 250), (110, 112, 144)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
FONTS_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]


def font(size, bold=True):
    for p in (FONTS if bold else FONTS_REG):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("Не найден шрифт с кириллицей")


def backdrop(w, h):
    """Радиальный градиент как в приложении: светлее слева сверху, к краям почти чёрный."""
    small = Image.new("RGB", (32, 32))
    px = small.load()
    c1, c2, c3 = (0x1f, 0x18, 0x38), (0x0c, 0x0d, 0x1a), (0x07, 0x07, 0x0d)
    for y in range(32):
        for x in range(32):
            t = min(1.0, (((x / 31 - .15) ** 2 + (y / 31 - .2) ** 2) ** .5) / 1.1)
            a, b, k = (c1, c2, t / .45) if t < .45 else (c2, c3, (t - .45) / .55)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
    return small.resize((w, h), Image.BICUBIC)


def glow(size, center, radius, color, strength):
    layer = Image.new("RGB", size, (0, 0, 0))
    ImageDraw.Draw(layer).ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
                                  fill=tuple(int(c * strength) for c in color))
    return layer.filter(ImageFilter.GaussianBlur(radius / 2))


def wire(img, seed=7):
    """Тонкие каркасные фигуры и точки поверх фона."""
    w, h = img.size
    rnd = random.Random(seed)
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    line = (0x3a, 0x49, 0x70, 130)
    s = int(w * .42)
    x, y = int(w * .06), int(h * .70)
    d.polygon([(x, y + s * .22), (x + s * .5, y), (x + s, y + s * .22), (x + s * .5, y + s * .44)], outline=line)
    d.line([(x, y + s * .22), (x, y + s * .72), (x + s * .5, y + s * .94), (x + s, y + s * .72), (x + s, y + s * .22)], fill=line)
    d.line([(x + s * .5, y + s * .44), (x + s * .5, y + s * .94)], fill=line)
    p = int(w * .3)
    x2, y2 = int(w * .62), int(h * .08)
    d.polygon([(x2 + p / 2, y2), (x2, y2 + p * .75), (x2 + p, y2 + p * .75)], outline=line)
    d.line([(x2 + p / 2, y2), (x2 + p / 2, y2 + p * .47), (x2, y2 + p * .75)], fill=line)
    d.line([(x2 + p / 2, y2 + p * .47), (x2 + p, y2 + p * .75)], fill=line)
    for _ in range(18):
        px, py, r = rnd.randint(0, w), rnd.randint(0, h), rnd.choice((1, 1, 2))
        d.ellipse([px - r, py - r, px + r, py + r], fill=(0x6e, 0x70, 0x90, rnd.randint(80, 180)))
    img.paste(over, (0, 0), over)


def logo_img(px):
    return Image.open(LOGO).convert("RGBA").resize((px, px), Image.LANCZOS)


def wizard(w, h):
    img = backdrop(w, h)
    img = ImageChops.add(img, glow((w, h), (w // 2, int(h * .24)), int(w * .55), (0x4a, 0x38, 0x9a), .9))
    wire(img)
    lg = logo_img(int(w * .62))
    img.paste(lg, ((w - lg.width) // 2, int(h * .10)), lg)
    d = ImageDraw.Draw(img)
    f1, f2 = font(max(12, int(w * .105))), font(max(9, int(w * .06)))
    y = int(h * .10) + lg.height + int(h * .035)
    for text in ("RMRP", "ПОМОЩНИК"):
        tw = d.textlength(text, font=f1)
        d.text(((w - tw) / 2, y), text, font=f1, fill=TEXT)
        y += int(f1.size * 1.25)
    text = "by Kinzec X WOLF"
    tw = d.textlength(text, font=f2)
    d.text(((w - tw) / 2, y + int(h * .008)), text, font=f2, fill=ACCENT_TXT)
    return img


def small(px):
    img = Image.new("RGB", (px, px), BG2)
    lg = logo_img(int(px * .86))
    img.paste(lg, ((px - lg.width) // 2, (px - lg.height) // 2), lg)
    return img


def main():
    os.makedirs(ASSETS, exist_ok=True)
    for w, h in ((164, 314), (192, 366), (246, 459), (328, 628)):
        wizard(w * 2, h * 2).resize((w, h), Image.LANCZOS).save(os.path.join(ASSETS, f"wizard-{w}x{h}.bmp"))
    for px in (55, 64, 80, 110):
        small(px * 4).resize((px, px), Image.LANCZOS).save(os.path.join(ASSETS, f"small-{px}.bmp"))
    print("Готово:", sorted(f for f in os.listdir(ASSETS) if f.endswith(".bmp")))


if __name__ == "__main__":
    main()
