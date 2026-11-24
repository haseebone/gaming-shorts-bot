"""
Turns a news story into a short narration script.

Default: template-based so the whole pipeline stays free and needs no paid
LLM API key. If a free GEMINI_API_KEY secret is set, the script is written
by Gemini for much richer, more natural copy (with the template as a fallback
when Gemini is down) -- the rest of the pipeline doesn't care how the script
text was produced.
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

# Punchy openers -- randomized so consecutive videos don't all start the
# same way (repetition hurts retention). These only add energy; they
# never state anything the story itself doesn't already say.
NEWS_HOOKS = [
    "Big gaming news —",
    "You need to hear this —",
    "Here's what just happened —",
    "This is huge —",
    "Just in —",
]
RESULT_HOOKS = [
    "It's official —",
    "The results are in —",
    "This just wrapped up —",
    "Huge moment for esports —",
]
CTAS = [
    "Follow for daily gaming news.",
    "Follow so you never miss a story.",
    "Hit follow for more every day.",
]

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]

GEMINI_PROMPT_TEMPLATE = """You are writing a YouTube Shorts narration script for a \
gaming news channel targeting a USA audience. Make it sound like a real, energetic \
human gaming news host -- not a robot.

The news story:
Title: {title}
Summary: {summary}

Rules:
- Length: 130-260 words (that's roughly 50 to 100 seconds at normal speaking pace).
  If the story is rich, you may go a bit longer -- up to about 420 words (~160s) --
  but never pad it; always stay tight and informative.
- Start with a punchy one-line hook.
- Cover the who/what/why in a clear, chronological, easy-to-follow way.
- Use plain, conversational language. No jargon. Do not invent facts that are not
  in the summary.
- End with one short CTA to follow the channel.

Respond with ONLY a JSON object, nothing else:
{{
  "script": "..."
}}
"""


def _first_n_sentences(text: str, n: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


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
    words = full.split()
    if len(words) > MAX_WORDS:
        full = " ".join(words[:MAX_WORDS]) + "."
    return full


def build_script(story: dict) -> str:
    """Try free Gemini for a natural script; fall back to the template."""
    gemini_script = _call_gemini(story["title"], story.get("summary", ""))
    if gemini_script:
        print("[script] Used Gemini")
        return gemini_script
    print("[script] Used template fallback")
    return _template_script(story)


def build_title_and_description(story: dict) -> tuple[str, str]:
    base_title = story["title"].strip()
    if len(base_title) > 90:
        base_title = base_title[:87] + "..."
    yt_title = f"{base_title} #Shorts"

    description = (
        f"{story['title']}\n\n"
        f"Source: {story['source']}\n"
        f"Read more: {story['link']}\n\n"
        "#gaming #esports #gamingnews #shorts"
    )
    return yt_title, description


if __name__ == "__main__":
    demo = {
        "title": "Team wins world championship in dramatic final",
        "summary": "The grand final went the distance. Fans packed the arena. The winning team clinched it in the last round.",
        "source": "Demo Feed",
        "link": "https://example.com",
    }
    print(build_script(demo))
    print(build_title_and_description(demo))

