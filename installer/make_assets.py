"""Рисует картинки мастера установки в стиле приложения (тёмно-синий город, свечение, логотип).

Запуск: python installer/make_assets.py   (нужен Pillow). Результат кладётся в installer/assets и коммитится,
так что сборка установщика этот скрипт не требует.
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
LOGO = os.path.join(HERE, "..", "app", "assets", "rmrp.png")
BG, BG2, ACCENT, ACCENT_TXT, TEXT, MUTED = (7, 11, 20), (12, 24, 48), (47, 123, 245), (111, 176, 255), (242, 246, 252), (126, 145, 173)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
FONTS_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]


def font(size, bold=True):
    for p in (FONTS if bold else FONTS_REG):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("Не найден шрифт с кириллицей")


def glow(size, center, radius, color, strength):
    layer = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=tuple(int(c * strength) for c in color))
    return layer.filter(ImageFilter.GaussianBlur(radius / 2))


def city(img, seed=7):
    """Силуэты зданий с горящими окнами по нижней части картинки."""
    w, h = img.size
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)
    x = -10
    while x < w:
        bw = rnd.randint(int(w * .14), int(w * .26))
        bh = rnd.randint(int(h * .16), int(h * .42))
        top = h - int(h * .06) - bh
        d.rectangle([x, top, x + bw, h], fill=(8, 13, 24), outline=(18, 34, 60))
        step = max(8, w // 16)
        for wy in range(top + step // 2, h - int(h * .08), step):
            for wx in range(x + step // 2, x + bw - step // 3, step):
                if rnd.random() < .42:
                    d.rectangle([wx, wy, wx + step // 4, wy + step // 4], fill=(30, 70, 130) if rnd.random() < .8 else (60, 120, 200))
        x += bw + rnd.randint(2, 8)
    d.rectangle([0, h - int(h * .06), w, h], fill=(3, 6, 12))
    d.line([0, h - int(h * .06), w, h - int(h * .06)], fill=(31, 64, 112), width=max(1, h // 300))


def logo_img(px):
    return Image.open(LOGO).convert("RGBA").resize((px, px), Image.LANCZOS)


def wizard(w, h):
    img = Image.new("RGB", (w, h), BG)
    img = Image.blend(img, glow((w, h), (w // 2, int(h * .22)), int(w * .8), ACCENT, .55), .9).point(lambda v: min(255, v))
    d0 = ImageDraw.Draw(img)
    for y in range(h):  # плавный переход к тёмному низу
        a = y / h
        d0.line([0, y, w, y], fill=tuple(int(c * (1 - .55 * a)) for c in img.getpixel((0, y))))
    city(img)
    lg = logo_img(int(w * .62))
    img.paste(lg, ((w - lg.width) // 2, int(h * .08)), lg)
    d = ImageDraw.Draw(img)
    f1, f2, f3 = font(max(12, int(w * .105))), font(max(9, int(w * .06))), font(max(8, int(w * .052)), False)
    y = int(h * .08) + lg.height + int(h * .03)
    for text, f, col in (("RMRP", f1, TEXT), ("ПОМОЩНИК", f1, TEXT)):
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, y), text, font=f, fill=col)
        y += int(f.size * 1.25)
    for text, f, col in (("by Kinzec X WOLF", f2, ACCENT_TXT),):
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, y + int(h * .008)), text, font=f, fill=col)
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
