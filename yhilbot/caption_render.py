import io
import os
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

from .logging_setup import log

_IMPACT_CANDIDATES = [
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/truetype/impact.ttf",
    "/usr/share/fonts/TTF/impact.ttf",
    "/usr/share/fonts/impact.ttf",
    "/usr/local/share/fonts/impact.ttf",
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]

IMPACT_FONT_PATH: str | None = next((p for p in _IMPACT_CANDIDATES if os.path.exists(p)), None)
if not IMPACT_FONT_PATH:
    try:
        r = subprocess.run(
            ["fc-match", "-f", "%{file}", "Impact"], capture_output=True, text=True, timeout=5
        )
        candidate = r.stdout.strip()
        if candidate and os.path.exists(candidate):
            IMPACT_FONT_PATH = candidate
    except Exception:
        pass

if not IMPACT_FONT_PATH:
    log.warning("Impact font not found - /caption will use a fallback font")

_FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
]


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    if IMPACT_FONT_PATH:
        try:
            return ImageFont.truetype(IMPACT_FONT_PATH, size)
        except Exception:
            pass
    for fb in _FALLBACK_FONTS:
        if os.path.exists(fb):
            try:
                return ImageFont.truetype(fb, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_caption_sync(img_bytes: bytes, text: str, img_format: str) -> bytes:
    """Draw the classic white-bar/black-text meme caption above the image.

    Runs in an executor, not directly on the event loop.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    W, H = img.size
    font_size = max(24, int(H * 0.1))
    max_text_w = int(W * 0.92)
    padding = max(12, int(H * 0.04))

    def fit_text(txt: str, base: int):
        sz = base
        while sz >= 16:
            fnt = _load_font(sz)
            for ww in range(50, 10, -5):
                lines = textwrap.wrap(txt, width=ww) or [txt]
                tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                if max(tmp.textlength(ln, font=fnt) for ln in lines) <= max_text_w:
                    return fnt, lines
            sz -= 4
        return _load_font(max(12, sz)), [txt]

    font, lines = fit_text(text.upper(), font_size)
    line_h = int(font.size * 1.2)
    caption_h = padding * 2 + line_h * len(lines)
    result = Image.new("RGBA", (W, H + caption_h), (255, 255, 255, 255))
    result.paste(img, (0, caption_h))
    draw = ImageDraw.Draw(result)
    for idx, line in enumerate(lines):
        lw = draw.textlength(line, font=font)
        draw.text(((W - lw) / 2, padding + idx * line_h), line, font=font, fill=(0, 0, 0, 255))

    out_buf = io.BytesIO()
    fmt = img_format.upper() if img_format.upper() in ("PNG", "JPEG", "WEBP") else "PNG"
    if fmt == "JPEG":
        result = result.convert("RGB")
    result.save(out_buf, format=fmt)
    out_buf.seek(0)
    return out_buf.read()
