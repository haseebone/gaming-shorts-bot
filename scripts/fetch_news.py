"""
Pulls the latest gaming/esports stories from free RSS feeds and returns
the freshest N that haven't been turned into a video yet.
"""
import json
import os
import re
import feedparser

import config


def _load_seen():
    if os.path.exists(config.STATE_FILE):
        with open(config.STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def _save_seen(seen):
    os.makedirs(os.path.dirname(config.STATE_FILE), exist_ok=True)
    with open(config.STATE_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def _clean_summary(raw_html: str) -> str:
    text = re.sub("<[^<]+?>", "", raw_html or "")
    return re.sub(r"\s+", " ", text).strip()


def get_fresh_stories(limit: int):
    """Returns up to `limit` stories not previously used, newest first."""
    seen = _load_seen()
    candidates = []

    for feed_url in config.RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[warn] could not fetch {feed_url}: {e}")
            continue

        for entry in parsed.entries[:10]:
            link = entry.get("link")
            if not link or link in seen:
                continue
            title = entry.get("title", "").strip()
            summary = _clean_summary(entry.get("summary", ""))
            published = entry.get("published_parsed")
            if not title:
                continue
            candidates.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "source": parsed.feed.get("title", feed_url),
            })

    # newest first when timestamps are available
    candidates.sort(key=lambda c: c["published"] or 0, reverse=True)

    chosen = candidates[:limit]
    for c in chosen:
        seen.add(c["link"])
    _save_seen(seen)

    return chosen


if __name__ == "__main__":
    for story in get_fresh_stories(config.VIDEOS_PER_RUN):
        print(f"- {story['title']}  ({story['source']})")
