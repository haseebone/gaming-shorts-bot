"""
Generates an original branded title-card clip (story title on a dark gaming
gradient) plus a YouTube thumbnail. Everything is drawn from scratch with
Pillow + ffmpeg, so it's 100% original artwork (no copyrighted images).

Both are optional-but-nice: if anything fails, the pipeline just logs and
continues without them.
"""
import random
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

import config

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

GRADIENTS = [
    ((12, 8, 30), (60, 20, 90)),      # deep purple
    ((6, 10, 40), (20, 90, 140)),     # navy -> teal
    ((10, 10, 12), (90, 30, 40)),     # dark -> red
    ((8, 24, 16), (20, 120, 90)),     # dark green
]


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _vertical_gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _centered(draw, cx, y, text, font, fill, max_width=None):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = cx - tw / 2
    if max_width and tw > max_width:
        # fall back to scaled-down wrapping handled by the caller
        return tw
    draw.text((x, y), text, font=font, fill=fill)
    return tw


def make_title_card_image(title: str, out_path: str, brand: str = None) -> str:
    w, h = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
    brand = brand or config.TITLE_CARD_BRAND
    top, bottom = random.choice(GRADIENTS)
    img = _vertical_gradient(w, h, top, bottom)
    draw = ImageDraw.Draw(img)

    # subtle diagonal accent lines for a gaming-energy feel
    accent = (255, 200, 60)
    for x0, y0, x1, y1 in [
        (0, int(h * 0.82), w, int(h * 0.86)),
        (0, int(h * 0.86), w, int(h * 0.90)),
    ]:
        draw.line([(x0, y0), (x1, y1)], fill=accent, width=6)

    brand_font = _font(FONT_BOLD, 44)
    title_font = _font(FONT_BOLD, 76)

    _centered(draw, w / 2, int(h * 0.14), brand, brand_font, (255, 200, 60))
    draw.rectangle([w / 2 - 60, int(h * 0.14) + 70, w / 2 + 60, int(h * 0.14) + 74], fill=(255, 255, 255))

    wrapped = textwrap.fill(title, width=22)
    lines = wrapped.split("\n")[:4]
    y = int(h * 0.32)
    line_h = 96
    for line in lines:
        _centered(draw, w / 2, y, line, title_font, (255, 255, 255))
        y += line_h

    footer_font = _font(FONT_REGULAR, 32)
    _centered(draw, w / 2, int(h * 0.80), "SUBSCRIBE FOR DAILY GAMING NEWS", footer_font, (200, 200, 215))

    img.save(out_path)
    return out_path


def make_thumbnail_image(title: str, out_path: str) -> str:
    """Big readable text on a bold gradient -- the YouTube custom-thumbnail look."""
    w, h = 1280, 720
    top, bottom = random.choice(GRADIENTS)
    img = _vertical_gradient(w, h, top, bottom)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, int(h * 0.82), w, h], fill=(20, 20, 24))
    font = _font(FONT_BOLD, 72)
    wrapped = textwrap.fill(title, width=20)
    lines = wrapped.split("\n")[:2]
    y = int(h * 0.30)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) / 2, y), line, font=font, fill=(255, 255, 255))
        y += 90
    img.save(out_path, quality=92)
    return out_path


def make_title_card_clip(title: str, clip_path: str, duration_seconds: float = None) -> str:
    """Render the title-card image into a short vertical video clip."""
    duration_seconds = duration_seconds or config.TITLE_CARD_SECONDS
    image_path = clip_path.rsplit(".", 1)[0] + ".png"
    make_title_card_image(title, image_path)

    fps = 30
    frames = max(int(duration_seconds * fps), fps)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf",
        f"scale={config.VIDEO_WIDTH*2}:{config.VIDEO_HEIGHT*2},"
        f"zoompan=z='min(zoom+0.0012,1.12)':d={frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}",
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        clip_path,
    ]
    subprocess.run(cmd, check=True)
    return clip_path


if __name__ == "__main__":
    make_title_card_clip("Team wins world championship in dramatic final", "test_titlecard.mp4")
    make_thumbnail_image("Team wins world championship in dramatic final", config.THUMBNAIL_PATH)
    print("Wrote test_titlecard.mp4 and thumbnail.jpg")