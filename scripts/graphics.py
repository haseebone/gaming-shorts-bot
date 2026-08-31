"""
For stories that are tournament/match results, this generates an
ORIGINAL scoreboard-style graphic (no broadcast footage, no team/league
logos, no copyrighted material) and turns it into a slow Ken-Burns-style
video clip. For everything else, the pipeline falls back to generic
Pexels stock (see stock_media.py).

Why not use real tournament clips: broadcast footage belongs to the
organizer/platform holder and is normally Content-ID fingerprinted, so
reposting it -- even a few seconds -- gets claimed or strikes the channel
almost immediately. A from-scratch graphic sidesteps that entirely.
"""
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

import config

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

TOURNAMENT_KEYWORDS = re.compile(
    r"\b(wins?|defeats?|beat|beats|champion(ship)?|grand final|finals?|"
    r"bracket|tournament|playoffs?|qualifie[rd]s?|clinch(es|ed)?)\b",
    re.IGNORECASE,
)
SCORE_PATTERN = re.compile(r"\b(\d{1,2})\s*[-:–]\s*(\d{1,2})\b")
# Letters/spaces/apostrophes only in each captured name -- deliberately
# excludes digits so a trailing score (e.g. "...Phoenix 3-1") never leaks
# into the team name.
VS_PATTERN = re.compile(
    r"([A-Z][A-Za-z.\' ]{1,24})\s+(?:def\.?|defeats?|beats?|vs\.?|over)\s+([A-Z][A-Za-z.\' ]{1,24})",
)


def is_tournament_story(story: dict) -> bool:
    text = f"{story['title']} {story['summary']}"
    return bool(TOURNAMENT_KEYWORDS.search(text))


def _extract_matchup(story: dict):
    text = f"{story['title']} {story['summary']}"

    teams = ("Team A", "Team B")
    match = VS_PATTERN.search(text)
    if match:
        teams = (match.group(1).strip(" .'"), match.group(2).strip(" .'"))

    score = ("", "")
    score_match = SCORE_PATTERN.search(text)
    if score_match:
        score = (score_match.group(1), score_match.group(2))

    return teams, score


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _centered_text(draw, y, text, font, fill, width=config.VIDEO_WIDTH):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) / 2, y), text, font=font, fill=fill)


def generate_scoreboard_image(story: dict, image_path: str) -> str:
    w, h = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # vertical dark gradient background (navy -> near-black), original artwork
    top = (18, 22, 45)
    bottom = (8, 8, 14)
    for y in range(h):
        t = y / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    (team_a, team_b), (score_a, score_b) = _extract_matchup(story)

    label_font = _font(FONT_REGULAR, 42)
    team_font = _font(FONT_BOLD, 58)
    score_font = _font(FONT_BOLD, 140)
    vs_font = _font(FONT_BOLD, 44)

    # Fixed vertical slots, generously spaced so no element can ever
    # collide regardless of how long a team name or the divider run is.
    _centered_text(draw, 220, "TOURNAMENT RESULT", label_font, (0, 200, 255))
    _centered_text(draw, 640, team_a[:24], team_font, (255, 255, 255))
    _centered_text(draw, 760, "VS", vs_font, (150, 150, 160))
    _centered_text(draw, 860, team_b[:24], team_font, (255, 255, 255))

    draw.rectangle([w // 2 - 90, 1020, w // 2 + 90, 1026], fill=(0, 200, 255))

    if score_a and score_b:
        _centered_text(draw, 1100, f"{score_a}  -  {score_b}", score_font, (0, 200, 255))

    footer_font = _font(FONT_REGULAR, 32)
    _centered_text(draw, h - 260, story["source"][:40], footer_font, (150, 150, 160))

    img.save(image_path)
    return image_path


def image_to_video(image_path: str, out_path: str, duration_seconds: float):
    """Slow zoom-in (Ken Burns effect) on the static graphic, silent, vertical."""
    fps = 30
    frames = max(int(duration_seconds * fps), fps)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf",
        f"scale={config.VIDEO_WIDTH*2}:{config.VIDEO_HEIGHT*2},"
        f"zoompan=z='min(zoom+0.0007,1.15)':d={frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}",
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def build_tournament_background(story: dict, image_path: str, video_path: str, duration_seconds: float) -> str:
    generate_scoreboard_image(story, image_path)
    image_to_video(image_path, video_path, duration_seconds)
    return video_path


if __name__ == "__main__":
    demo = {
        "title": "Shadow Wolves def. Iron Phoenix 3-1 to win the grand final",
        "summary": "The championship series wrapped up tonight after a dramatic reverse sweep attempt fell short.",
        "source": "Demo Esports Wire",
        "link": "https://example.com",
    }
    generate_scoreboard_image(demo, "test_scoreboard.png")
    image_to_video("test_scoreboard.png", "test_scoreboard.mp4", 6)
    print("Wrote test_scoreboard.png and test_scoreboard.mp4")
