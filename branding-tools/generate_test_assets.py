from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Базовые цвета из конфига
COLOR_PRIMARY = "#292523"   # тёмный фон
COLOR_LIGHT = "#ffffff"
COLOR_OLED = "#000000"
COLOR_ACCENT = "#F47C30"    # оранжевый

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

try:
    # Попробуем взять системный шрифт, если нет — Pillow возьмёт дефолтный
    FONT = ImageFont.truetype("arial.ttf", 64)
except Exception:
    FONT = ImageFont.load_default()


def save_png(name: str, img: Image.Image):
    path = ASSETS_DIR / name
    img.save(path, format="PNG")
    print(f"saved {path}")


def draw_center_text(draw: ImageDraw.ImageDraw, text: str, box, fill=COLOR_LIGHT, font=FONT):
    # Совместимый способ получить размер текста в разных версиях Pillow
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except AttributeError:
        w, h = font.getsize(text)

    x = box[0] + (box[2] - box[0] - w) / 2
    y = box[1] + (box[3] - box[1] - h) / 2
    draw.text((x, y), text, fill=fill, font=font)


def make_square_icon(size: int, bg: str, fg: str, text: str = "SA") -> Image.Image:
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    # Простой "монограммный" значок: круг и текст
    margin = int(size * 0.15)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=COLOR_LIGHT,
        width=max(1, size // 32),
        fill=fg,
    )
    draw_center_text(draw, text, (0, 0, size, size), fill=COLOR_LIGHT)
    return img


def generate_favicon_png():
    img = make_square_icon(64, COLOR_PRIMARY, COLOR_ACCENT)
    save_png("favicon.png", img)


def generate_favicon_dark_png():
    img = make_square_icon(64, COLOR_OLED, COLOR_ACCENT)
    save_png("favicon-dark.png", img)


def generate_favicon_96():
    img = make_square_icon(96, COLOR_PRIMARY, COLOR_ACCENT)
    save_png("favicon-96x96.png", img)


def generate_apple_touch():
    size = 180
    img = make_square_icon(size, COLOR_PRIMARY, COLOR_ACCENT)
    # Скруглим углы маской
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    r = int(size * 0.2)
    draw.rounded_rectangle([0, 0, size, size], radius=r, fill=255)
    img.putalpha(mask)
    save_png("apple-touch-icon.png", img)


def generate_logo():
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Круглый знак слева
    circle_size = int(size * 0.5)
    margin = int(size * 0.08)
    circle_box = [margin, (size - circle_size) // 2, margin + circle_size, (size + circle_size) // 2]
    draw.ellipse(circle_box, fill=COLOR_ACCENT)

    # Текст "Sollers AI" справа
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except Exception:
        font = ImageFont.load_default()

    text = "Sollers AI"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except AttributeError:
        w, h = font.getsize(text)
    text_x = circle_box[2] + int(size * 0.05)
    text_y = (size - h) // 2
    draw.text((text_x, text_y), text, font=font, fill=COLOR_PRIMARY)

    save_png("logo.png", img)


def generate_web_app_manifest_icons():
    img192 = make_square_icon(192, COLOR_PRIMARY, COLOR_ACCENT)
    save_png("web-app-manifest-192x192.png", img192)

    img512 = make_square_icon(512, COLOR_PRIMARY, COLOR_ACCENT)
    save_png("web-app-manifest-512x512.png", img512)


def generate_splash_light():
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), COLOR_LIGHT)
    draw = ImageDraw.Draw(img)

    # Логотип-иконка
    icon_size = 400
    icon = make_square_icon(icon_size, COLOR_PRIMARY, COLOR_ACCENT)
    icon_x = (w - icon_size) // 2
    icon_y = int(h * 0.25)
    img.paste(icon, (icon_x, icon_y), icon)

    # Текст "Sollers AI"
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except Exception:
        font = ImageFont.load_default()
    text = "Sollers AI"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = font.getsize(text)
    tx = (w - tw) // 2
    ty = icon_y + icon_size + 80
    draw.text((tx, ty), text, font=font, fill=COLOR_PRIMARY)

    save_png("splash.png", img)


def generate_splash_dark():
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), COLOR_PRIMARY)
    draw = ImageDraw.Draw(img)

    # Логотип-иконка
    icon_size = 400
    icon = make_square_icon(icon_size, COLOR_PRIMARY, COLOR_ACCENT)
    icon_x = (w - icon_size) // 2
    icon_y = int(h * 0.25)
    img.paste(icon, (icon_x, icon_y), icon)

    # Текст "Sollers AI"
    try:
      font = ImageFont.truetype("arial.ttf", 80)
    except Exception:
      font = ImageFont.load_default()
    text = "Sollers AI"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = font.getsize(text)
    tx = (w - tw) // 2
    ty = icon_y + icon_size + 80
    draw.text((tx, ty), text, font=font, fill=COLOR_LIGHT)

    save_png("splash-dark.png", img)


def generate_favicon_svg():
    svg_path = ASSETS_DIR / "favicon.svg"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" ry="12" fill="{COLOR_PRIMARY}"/>
  <circle cx="32" cy="32" r="20" fill="{COLOR_ACCENT}"/>
  <text x="32" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" fill="{COLOR_LIGHT}">SA</text>
</svg>
"""
    svg_path.write_text(svg, encoding="utf-8")
    print(f"saved {svg_path}")


def generate_favicon_ico():
    # ICO можно собрать из уже созданного favicon.png
    png_path = ASSETS_DIR / "favicon.png"
    if not png_path.exists():
        generate_favicon_png()
    img = Image.open(png_path).convert("RGBA")
    ico_path = ASSETS_DIR / "favicon.ico"
    img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"saved {ico_path}")


def main():
    generate_favicon_png()
    generate_favicon_dark_png()
    generate_favicon_96()
    generate_apple_touch()
    generate_logo()
    generate_web_app_manifest_icons()
    generate_splash_light()
    generate_splash_dark()
    generate_favicon_svg()
    generate_favicon_ico()


if __name__ == "__main__":
    main()