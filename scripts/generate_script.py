"""
Turns a news story into a short (~45-55 second) narration script.

This is template-based so the whole pipeline stays free and needs no paid
LLM API key. If you want richer writing, set an OPENAI_API_KEY or
GEMINI_API_KEY secret and swap in a call to that provider here -- the
rest of the pipeline doesn't care how the script text was produced.
"""
import random
import re

from graphics import is_tournament_story

WORDS_PER_SECOND = 2.5  # rough average speaking pace
MAX_WORDS = int(55 * WORDS_PER_SECOND)  # ~137 words for a 55s short

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


def _first_n_sentences(text: str, n: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


def build_script(story: dict) -> str:
    title = story["title"]
    summary = _first_n_sentences(story["summary"], 3)  # tighter body = snappier pace

    hooks = RESULT_HOOKS if is_tournament_story(story) else NEWS_HOOKS
    hook = random.choice(hooks)
    body = summary if summary else "Here's what's happening."
    cta = random.choice(CTAS)

    full = f"{hook} {title}. {body} {cta}"
    words = full.split()
    if len(words) > MAX_WORDS:
        full = " ".join(words[:MAX_WORDS]) + "."

    return full


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

