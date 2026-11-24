"""
Downloads free, royalty-free vertical background video from Pexels.
Never fetches game footage or anything tied to a specific title/character --
only generic gaming-adjacent b-roll (setups, arenas, crowds, keyboards).

If Pexels is down/empty, falls back to generating an original animated
gradient background locally so the run never dies for lack of footage.
"""
import os
import random
import subprocess
import requests

import config

PEXELS_API_URL = "https://api.pexels.com/videos/search"


def _pick_query(story_title: str) -> str:
    # Keep it generic and safe -- never search the game's own name/brand,
    # just neutral gaming-adjacent scenery.
    return random.choice(config.FALLBACK_VISUAL_QUERIES)


def _generate_gradient_fallback(dest_path: str) -> str:
    """Make a simple animated vertical gradient (two colors shifting) so
    there is always a legal, original background even when Pexels fails."""
    w, h = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
    palette = [
        ("#1a0b2e", "#0f3460"),  # deep purple -> navy
        ("#0f2027", "#203a43"),  # dark teal
        ("#232526", "#414345"),  # gunmetal
        ("#2b1055", "#7597de"),  # neon purple -> blue
    ]
    a, b = random.choice(palette)

    # ffmpeg gradient (solid, then we add a subtle zoom) -- 30s is plenty;
    # assemble_video will loop it for the full audio duration.
    duration = 30
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"gradients=s={w}x{h}:d={duration}:c0={a}:c1={b}:"
            f"x0=0:y0=0:x1={w}:y1={h}:speed=0.05"
        ),
        "-vf", (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        dest_path,
    ]
    subprocess.run(cmd, check=True)
    return dest_path


def fetch_background_clip(story_title: str, dest_path: str) -> str:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("[media] No PEXELS_API_KEY -- using gradient fallback background.")
        return _generate_gradient_fallback(dest_path)

    last_error = None
    for _ in range(3):  # try a few different queries before giving up
        query = _pick_query(story_title)
        try:
            resp = requests.get(
                PEXELS_API_URL,
                headers={"Authorization": api_key},
                params={"query": query, "orientation": "portrait", "per_page": 10},
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                print(f"[media] No Pexels results for '{query}', trying another...")
                continue

            video = random.choice(videos)
            files = sorted(
                video["video_files"],
                key=lambda f: f.get("height", 0),
                reverse=True,
            )
            file_url = files[0]["link"]
            with requests.get(file_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return dest_path
        except Exception as e:
            last_error = e
            print(f"[media] Pexels failed ({e}), trying another query...")

    print(f"[media] Pexels unavailable after retries ({last_error}) -- using gradient fallback.")
    return _generate_gradient_fallback(dest_path)


if __name__ == "__main__":
    fetch_background_clip("demo story", "test_bg.mp4")
    print("Downloaded test_bg.mp4")
