import io, os, random, math, urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
PALETTES = [  # (accent, dark1, dark2)
    ((255, 205, 40), (12, 36, 74), (6, 14, 36)),
    ((60, 230, 160), (6, 56, 52), (3, 22, 26)),
    ((255, 110, 100), (70, 18, 48), (26, 8, 28)),
    ((90, 200, 255), (18, 40, 96), (8, 12, 40)),
    ((190, 140, 255), (44, 24, 96), (14, 8, 40)),
]

def F(name, size):
    try:
        return ImageFont.truetype(os.path.join(HERE, "fonts", f"Poppins-{name}.ttf"), size)
    except Exception:
        return ImageFont.load_default()

def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines

def fit_wrap(draw, text, name, start, min_size, max_w, max_lines):
    size = start
    while size > min_size:
        f = F(name, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
        size -= 4
    f = F(name, min_size)
    return f, wrap(draw, text, f, max_w)

def photo_bg(prompt):
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt + ", cinematic photo, shallow depth of field, rich colors, no text")
           + f"?width={W}&height={H}&model=flux&nologo=true&seed={random.randint(1, 99999)}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB").resize((W, H))

def art_bg(dark1, dark2, accent):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(dark1, dark2)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(9):  # soft glowing coins/circles
        r = random.randint(90, 320)
        x, y = random.randint(-80, W), random.randint(-80, H)
        ld.ellipse((x, y, x + r, y + r), fill=accent + (random.randint(14, 34),))
    for i in range(0, W + H, 90):  # subtle diagonal lines
        ld.line([(i, 0), (0, i)], fill=(255, 255, 255, 10), width=2)
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def darken(img, strength=0.55):
    """Vertical dark gradient so text stays readable on any photo."""
    ov = Image.new("RGBA", (W, H))
    od = ImageDraw.Draw(ov)
    for y in range(H):
        t = y / H
        a = int(255 * (strength + 0.35 * abs(t - 0.5) * 2 * 0.6))
        od.line([(0, y), (W, y)], fill=(5, 8, 20, min(a, 235)))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

def panel(img, box, fill=(255, 255, 255, 34), radius=36, outline=None):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def pill(img, xy, text, accent, font):
    d = ImageDraw.Draw(img)
    w = d.textlength(text, font=font)
    x, y = xy
    d.rounded_rectangle((x, y, x + w + 56, y + 62), radius=31, fill=accent)
    d.text((x + 28, y + 9), text, font=font, fill=(10, 14, 30))
    return img

def footer(img, page_name, accent):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, H - 150, 140, H - 150 + 6), radius=3, fill=accent)
    if page_name:
        d.text((70, H - 125), page_name, font=F("ExtraBold", 38), fill=(255, 255, 255))
    d.text((70, H - 72), "SAVE THIS FOR LATER  |  FOLLOW FOR DAILY MONEY TIPS", font=F("Medium", 24), fill=(200, 205, 220))

def headline(img, text, accent, y=210, max_lines=3):
    d = ImageDraw.Draw(img)
    f, lines = fit_wrap(d, text.upper(), "ExtraBold", 92, 60, W - 140, max_lines)
    lh = int(f.size * 1.12)
    for ln in lines:
        d.text((70, y), ln, font=f, fill=(255, 255, 255))
        y += lh
    d.rounded_rectangle((70, y + 26, 230, y + 38), radius=6, fill=accent)
    return y + 85

def base(item, use_photo):
    accent, d1, d2 = random.choice(PALETTES)
    bg = None
    if use_photo and item.get("image_prompt"):
        try:
            bg = darken(photo_bg(item["image_prompt"]))
        except Exception as e:
            print("photo background failed, using art background:", e)
    if bg is None:
        bg = art_bg(d1, d2, accent)
    return bg, accent

def tips_card(item, page_name, use_photo):
    img, accent = base(item, use_photo)
    img = pill(img, (70, 90), item.get("label", "MONEY TIP").upper(), accent, F("SemiBold", 30))
    y = headline(img, item["headline"], accent)
    for i, p in enumerate(item["points"][:3], 1):
        d = ImageDraw.Draw(img)
        f, lines = fit_wrap(d, p, "SemiBold", 44, 34, W - 330, 2)
        h = max(130, len(lines) * int(f.size * 1.25) + 56)
        img = panel(img, (70, y, W - 70, y + h))
        d = ImageDraw.Draw(img)
        cy = y + h // 2
        d.ellipse((100, cy - 38, 176, cy + 38), fill=accent)
        d.text((138, cy - 2), str(i), font=F("ExtraBold", 44), fill=(10, 14, 30), anchor="mm")
        ty = cy - (len(lines) * int(f.size * 1.25)) // 2
        for ln in lines:
            d.text((210, ty), ln, font=f, fill=(255, 255, 255))
            ty += int(f.size * 1.25)
        y += h + 26
    footer(img, page_name, accent)
    return img

def myth_card(item, page_name, use_photo):
    img, accent = base(item, use_photo)
    img = pill(img, (70, 90), "MYTH vs FACT", accent, F("SemiBold", 30))
    y = headline(img, item["headline"], accent, max_lines=2)
    for tag, text, col in (("MYTH", item["myth"], (255, 90, 90)), ("FACT", item["fact"], (70, 225, 150))):
        d = ImageDraw.Draw(img)
        f, lines = fit_wrap(d, text, "SemiBold", 44, 32, W - 190, 4)
        h = len(lines) * int(f.size * 1.3) + 130
        img = panel(img, (70, y, W - 70, y + h), fill=col + (40,), outline=col + (230,))
        d = ImageDraw.Draw(img)
        d.text((105, y + 28), tag, font=F("ExtraBold", 34), fill=col)
        ty = y + 86
        for ln in lines:
            d.text((105, ty), ln, font=f, fill=(255, 255, 255))
            if tag == "MYTH":
                w = d.textlength(ln, font=f)
                d.line([(105, ty + f.size * 0.72), (105 + w, ty + f.size * 0.72)], fill=(255, 90, 90), width=4)
            ty += int(f.size * 1.3)
        y += h + 30
    footer(img, page_name, accent)
    return img

def stat_card(item, page_name, use_photo):
    img, accent = base(item, use_photo)
    img = pill(img, (70, 90), item.get("label", "MONEY RULE").upper(), accent, F("SemiBold", 30))
    d = ImageDraw.Draw(img)
    f, lines = fit_wrap(d, item["big_text"].upper(), "ExtraBold", 190, 80, W - 140, 3)
    lh = int(f.size * 1.08)
    total = len(lines) * lh
    y = 420 - total // 2 + 100
    for ln in lines:
        d.text((W // 2, y), ln, font=f, fill=accent, anchor="mt")
        y += lh
    d.rounded_rectangle((W // 2 - 80, y + 30, W // 2 + 80, y + 42), radius=6, fill=(255, 255, 255))
    f2, l2 = fit_wrap(d, item["headline"], "SemiBold", 52, 36, W - 220, 4)
    y += 100
    for ln in l2:
        d.text((W // 2, y), ln, font=f2, fill=(255, 255, 255), anchor="mt")
        y += int(f2.size * 1.3)
    footer(img, page_name, accent)
    return img

TEMPLATES = {"tips": tips_card, "myth_fact": myth_card, "big_stat": stat_card}

def make_card(item, fmt, page_name="", use_photo=True):
    img = TEMPLATES[fmt](item, page_name, use_photo)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=93)
    buf.seek(0)
    return buf
