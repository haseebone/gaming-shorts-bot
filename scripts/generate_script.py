"""
Turns a news story into a short narration script + a CTR-boosting title.

Two engines:
  * Gemini (free) writes a natural, retention-optimized script when a
    GEMINI_API_KEY is set; template fallback otherwise.
  * Titles are always built in code from the story so they stay 100%
    factual while using proven Shorts CTR patterns (curiosity gap,
    direct address, "here's what happened").

Everything below is free -- no paid APIs.
"""
import json
import os
import random
import re
import time

import requests

from graphics import is_tournament_story

WORDS_PER_SECOND = 2.6  # rough average speaking pace
MAX_WORDS = int(170 * WORDS_PER_SECOND)  # ~442 words -> up to ~170s short

# ---------------------------------------------------------------------------
# Scroll-stopping opening hooks (pattern-interrupt openers). These are the
# first 1-2 seconds of the video -- the highest-leverage moment for retention.
# Each one is generic energy only; it never states anything the story doesn't
# say.
# ---------------------------------------------------------------------------
NEWS_HOOKS = [
    "Okay, this is actually huge —",
    "Nobody saw this one coming —",
    "Big gaming news just dropped —",
    "You need to hear what just happened —",
    "Wait for it, this is big —",
    "Here's what everyone's about to be talking about —",
    "This just hit the wire —",
]
RESULT_HOOKS = [
    "The final result is in —",
    "It's officially official —",
    "This match just wrapped up —",
    "You won't believe the final score —",
    "Massive upset or expected win? Here's what went down —",
]
CTAS = [
    "Follow for daily gaming news.",
    "Follow so you never miss a story.",
    "Hit follow for more every day.",
    "New video every single day — follow so you don't miss it.",
]

# ---------------------------------------------------------------------------
# Curiosity-gap title frames. Applied to the real headline so titles stay
# factual but stop the scroll. Frames are chosen by story type and length.
# ---------------------------------------------------------------------------
NEWS_TITLE_FRAMES = [
    "Here's What Just Happened: {t}",
    "{t} — Explained",
    "Big News: {t}",
    "This Is Why Everyone's Talking About {t}",
    "Wait For It: {t}",
]
RESULT_TITLE_FRAMES = [
    "The Result Is In: {t}",
    "Final Score Inside: {t}",
    "It's Official: {t}",
    "Who Won? {t}",
]

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]

GEMINI_PROMPT_TEMPLATE = """You are writing a YouTube Shorts narration script for a \
gaming news channel targeting a USA audience. Make it sound like a real, energetic \
human gaming news host -- not a robot. Your #1 job is RETENTION: people must stay \
to the end.

The news story:
Title: {title}
Summary: {summary}

Retention rules:
- FIRST SENTENCE must be a scroll-stopping hook: a short, punchy pattern \
interrupt ("Wait for it...", "You won't believe this...", "This is huge...") \
that raises a question or stakes. Never start with "Today we'll talk about".
- Talk directly to the viewer using "you".
- Structure: hook -> what happened (who/what/why, chronological, no invented \
facts) -> why it matters -> quick takeaway.
- If the story mentions a number, stat, or score, put it up front in the hook.
- Keep it 130-260 words (roughly 50-100 seconds). Richer stories may go up to \
~420 words (~160s) but never pad.
- End with ONE short CTA to follow the channel.

Respond with ONLY a JSON object, nothing else:
{{
  "script": "..."
}}
"""


def _first_n_sentences(text: str, n: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


def _truncate_words(text: str, n: int) -> str:
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]).rstrip("., ") + "."


def _call_gemini(title: str, summary: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    prompt = GEMINI_PROMPT_TEMPLATE.format(title=title, summary=summary)
    for model in GEMINI_MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":generateContent?key="
            + api_key
        )
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=60,
                )
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 5 * (2 ** attempt)
                    print(f"[script] {model} {resp.status_code} -- retry in {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
                data = json.loads(text)
                script = str(data.get("script", "")).strip()
                if script:
                    return script
            except Exception as e:
                print(f"[script] {model} attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        print(f"[script] Moving on from {model}...")
    return None


def _template_script(story: dict) -> str:
    title = story["title"]
    summary = _first_n_sentences(story["summary"], 3)
    hooks = RESULT_HOOKS if is_tournament_story(story) else NEWS_HOOKS
    hook = random.choice(hooks)
    body = summary if summary else "Here's what's happening."
    cta = random.choice(CTAS)
    full = f"{hook} {title}. {body} {cta}"
    return _truncate_words(full, MAX_WORDS)


def build_script(story: dict) -> str:
    """Try free Gemini for a retention-optimized script; fall back to template."""
    gemini_script = _call_gemini(story["title"], story.get("summary", ""))
    if gemini_script:
        print("[script] Used Gemini")
        return gemini_script
    print("[script] Used template fallback")
    return _template_script(story)


# ---------------------------------------------------------------------------
# Title builder -- CTR-focused but always factual.
# ---------------------------------------------------------------------------
def _clean_headline(headline: str) -> str:
    """Trim trailing junk like ' - IGN' or ' | Eurogamer' some feeds append."""
    h = headline.strip()
    h = re.sub(r"\s+[-|–—]\s*[A-Za-z0-9 .&']{0,40}$", "", h)
    return h.strip()


def build_yt_title(story: dict) -> str:
    headline = _clean_headline(story["title"])
    frames = RESULT_TITLE_FRAMES if is_tournament_story(story) else NEWS_TITLE_FRAMES

    # Short headline -> try to wrap it in a curiosity frame.
    for frame in frames:
        candidate = frame.format(t=headline)
        if len(candidate) <= 90:
            return candidate + " #Shorts"

    # Long headline -> keep it factual but truncated, add a hook suffix.
    trimmed = headline[:80].rstrip(" .,;:")
    return f"{trimmed}... #Shorts"


def _story_hashtags(headline: str, limit: int = 4) -> str:
    """Pull a few relevant hashtags from the title for discovery."""
    words = re.findall(r"[A-Za-z0-9]+", headline)
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "was", "were", "at", "from", "by", "after", "new", "its",
        "it's", "what", "why", "how", "who", "when", "be", "this", "that",
    }
    out = []
    seen = set()
    for w in words:
        lw = w.lower()
        if lw in stop or lw in seen or len(w) < 4:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= limit:
            break
    return " ".join("#" + c for c in out)


def build_title_and_description(story: dict) -> tuple[str, str]:
    yt_title = build_yt_title(story)

    hashtags = _story_hashtags(story["title"])
    description = (
        f"{story['title']}\n\n"
        f"Source: {story['source']}\n"
        f"Read more: {story['link']}\n\n"
        "#gaming #esports #gamingnews #shorts"
        + (f" {hashtags}" if hashtags else "")
    )
    return yt_title, description


if __name__ == "__main__":
    demo = {
        "title": "Team wins world championship in dramatic final - IGN",
        "summary": "The grand final went the distance. Fans packed the arena. The winning team clinched it in the last round.",
        "source": "Demo Feed",
        "link": "https://example.com",
    }
    print(build_script(demo))
    print(build_title_and_description(demo))