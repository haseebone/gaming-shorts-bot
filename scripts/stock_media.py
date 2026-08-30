"""
Downloads free, royalty-free vertical background video from Pexels.
Never fetches game footage or anything tied to a specific title/character --
only generic gaming-adjacent b-roll (setups, arenas, crowds, keyboards).
"""
import os
import random
import requests

import config

PEXELS_API_URL = "https://api.pexels.com/videos/search"


def _pick_query(story_title: str) -> str:
    # Keep it generic and safe -- never search the game's own name/brand,
    # just neutral gaming-adjacent scenery.
    return random.choice(config.FALLBACK_VISUAL_QUERIES)


def fetch_background_clip(story_title: str, dest_path: str) -> str:
    api_key = os.environ["PEXELS_API_KEY"]
    query = _pick_query(story_title)

    resp = requests.get(
        PEXELS_API_URL,
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "portrait", "per_page": 10},
        timeout=30,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels results for query '{query}'")

    video = random.choice(videos)
    # pick the highest-res vertical file available
    files = sorted(video["video_files"], key=lambda f: f.get("height", 0), reverse=True)
    file_url = files[0]["link"]

    with requests.get(file_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return dest_path


if __name__ == "__main__":
    fetch_background_clip("demo story", "test_bg.mp4")
    print("Downloaded test_bg.mp4")
