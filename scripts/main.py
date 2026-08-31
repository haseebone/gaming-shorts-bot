"""
Orchestrates the full pipeline: fetch news -> write script -> voiceover ->
background clip -> assemble -> upload. Run by the GitHub Actions workflow
on a schedule.
"""
import glob
import os
import random
import traceback

import config
from fetch_news import get_fresh_stories
from generate_script import build_script, build_title_and_description
from tts import generate_voiceover
from stock_media import fetch_background_clip
from graphics import is_tournament_story, build_tournament_background
from assemble_video import assemble, get_duration_seconds
from youtube_upload import upload_video


def _pick_random_music() -> str | None:
    tracks = glob.glob(os.path.join(config.MUSIC_DIR, "*.mp3"))
    return random.choice(tracks) if tracks else None


def process_story(story: dict, index: int):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    base = os.path.join(config.OUTPUT_DIR, f"video_{index}")

    audio_path = f"{base}.mp3"
    srt_path = f"{base}.srt"
    bg_path = f"{base}_bg.mp4"
    bg_image_path = f"{base}_bg.png"
    final_path = f"{base}_final.mp4"

    print(f"[{index}] Story: {story['title']}")

    script_text = build_script(story)
    print(f"[{index}] Script: {script_text}")

    generate_voiceover(script_text, audio_path, srt_path)

    # Tournament/match-result stories get an original scoreboard graphic
    # (no broadcast footage, no logos) instead of generic stock b-roll.
    if is_tournament_story(story):
        print(f"[{index}] Detected tournament result -> generating scoreboard graphic")
        voice_duration = get_duration_seconds(audio_path)
        build_tournament_background(story, bg_image_path, bg_path, voice_duration + 1)
    else:
        fetch_background_clip(story["title"], bg_path)

    music_path = _pick_random_music()
    if music_path:
        print(f"[{index}] Background music: {music_path}")
    else:
        print(f"[{index}] No background music found -- rendering without it")

    assemble(bg_path, audio_path, srt_path, final_path, music_path=music_path)

    title, description = build_title_and_description(story)
    upload_video(
        final_path,
        title=title,
        description=description,
        tags=["gaming", "esports", "gamingnews", "shorts"],
    )


def main():
    stories = get_fresh_stories(config.VIDEOS_PER_RUN)
    if not stories:
        print("No fresh stories found this run -- nothing to upload.")
        return

    for i, story in enumerate(stories, start=1):
        try:
            process_story(story, i)
        except Exception:
            print(f"[{i}] FAILED, skipping this story:")
            traceback.print_exc()


if __name__ == "__main__":
    main()

