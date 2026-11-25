"""
Pulls the latest gaming/esports stories from free RSS feeds and returns
the freshest N that haven't been turned into a video yet.

Dedup works on BOTH the link AND a normalized version of the headline, so
the same story syndicated by two feeds (different URLs, same headline) is
only posted once.
"""
import html
import json
import os
import re
import time
import feedparser

import config


def _load_state():
    """Returns (links:set, titles:set). Handles both the old list format
    (just links) and the new dict format {links:[], titles:[]}."""
    links, titles = set(), set()
    if os.path.exists(config.STATE_FILE):
        try:
            with open(config.STATE_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                links = set(data.get("links", []))
                titles = set(data.get("titles", []))
            elif isinstance(data, list):
                links = set(data)
        except Exception as e:
            print(f"[warn] could not read {config.STATE_FILE}: {e}")
    return links, titles


def _save_state(links, titles):
    os.makedirs(os.path.dirname(config.STATE_FILE), exist_ok=True)
    with open(config.STATE_FILE, "w") as f:
        json.dump({"links": sorted(links), "titles": sorted(titles)}, f, indent=2)


def _clean_summary(raw_html: str) -> str:
    text = re.sub("<[^<]+?>", "", raw_html or "")
    text = html.unescape(text)  # &amp; &#39; &ldquo; -> real characters
    return re.sub(r"\s+", " ", text).strip()


def _normalize_headline(title: str) -> str:
    """Lowercase, strip punctuation/spaces, drop source suffixes like '- IGN'."""
    t = title.strip()
    t = re.sub(r"\s+[-|–—]\s*[A-Za-z0-9 .&']{0,40}$", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def _is_fresh(entry, max_age_hours):
    """True if the story was published within max_age_hours (or has no date)."""
    published = entry.get("published_parsed")
    if not published:
        # No timestamp: keep it (better than dropping a valid story).
        return True
    try:
        published_ts = time.mktime(published)
        age_hours = (time.time() - published_ts) / 3600
        return age_hours <= max_age_hours
    except Exception:
        return True


def get_fresh_stories(limit: int):
    """Returns up to `limit` fresh stories not previously used, newest first."""
    seen_links, seen_titles = _load_state()
    candidates = []

    for feed_url in config.RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[warn] could not fetch {feed_url}: {e}")
            continue

        for entry in parsed.entries[:12]:
            link = entry.get("link")
            title = entry.get("title", "").strip()
            if not link or not title:
                continue
            if link in seen_links:
                continue
            norm = _normalize_headline(title)
            if norm and norm in seen_titles:
                print(f"[dedup] already posted similar story: {title}")
                continue
            if not _is_fresh(entry, config.MAX_STORY_AGE_HOURS):
                continue

            candidates.append({
                "title": title,
                "summary": _clean_summary(entry.get("summary", "")),
                "link": link,
                "published": entry.get("published_parsed"),
                "source": parsed.feed.get("title", feed_url),
            })

    # newest first when timestamps are available
    candidates.sort(key=lambda c: c["published"] or 0, reverse=True)

    chosen = candidates[:limit]
    for c in chosen:
        seen_links.add(c["link"])
        norm = _normalize_headline(c["title"])
        if norm:
            seen_titles.add(norm)
    _save_state(seen_links, seen_titles)

    return chosen


if __name__ == "__main__":
    for story in get_fresh_stories(config.VIDEOS_PER_RUN):
        print(f"- {story['title']}  ({story['source']})")