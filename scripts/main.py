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
from title_card import make_title_card_clip, make_thumbnail_image, make_end_card_clip
from assemble_video import assemble, get_duration_seconds
from youtube_upload import upload_video
from notify import send_video_notification


def _pick_random_music() -> str | None:
    tracks = glob.glob(os.path.join(config.MUSIC_DIR, "*.mp3"))
    return random.choice(tracks) if tracks else None


def process_story(story: dict, index: int, upload: bool = True):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    base = os.path.join(config.OUTPUT_DIR, f"video_{index}")

    audio_path = f"{base}.mp3"
    srt_path = f"{base}.srt"
    bg_path = f"{base}_bg.mp4"
    bg_image_path = f"{base}_bg.png"
    title_card_path = f"{base}_title.mp4"
    end_card_path = f"{base}_end.mp4"
    thumbnail_path = config.THUMBNAIL_PATH
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

    # Branded title card (optional, never fatal).
    try:
        make_title_card_clip(story["title"], title_card_path)
        print(f"[{index}] Title card generated")
    except Exception as e:
        print(f"[{index}] Title card failed ({e}), continuing without it")
        title_card_path = None

    # Branded end card (optional, never fatal).
    try:
        make_end_card_clip(end_card_path, duration_seconds=3.0)
        print(f"[{index}] End card generated")
    except Exception as e:
        print(f"[{index}] End card failed ({e}), continuing without it")
        end_card_path = None

    assemble(bg_path, audio_path, srt_path, final_path, music_path=music_path,
             title_card_path=title_card_path, end_card_path=end_card_path)

    # Custom thumbnail (optional -- needs a verified channel, else skipped).
    try:
        make_thumbnail_image(story["title"], thumbnail_path)
        print(f"[{index}] Thumbnail generated")
    except Exception as e:
        print(f"[{index}] Thumbnail failed ({e}), uploading without it")
        thumbnail_path = None

    if not upload:
        print(f"[{index}] LOCAL MODE: video saved to {final_path} (not uploaded)")
        return

    title, description = build_title_and_description(story)
    video_id = upload_video(
        final_path,
        title=title,
        description=description,
        tags=["gaming", "esports", "gamingnews", "shorts"],
        thumbnail_path=thumbnail_path,
    )
    try:
        send_video_notification(title, video_id)
    except Exception as e:
        print(f"[{index}] Notification failed ({e}), ignoring.")


def main():
    import sys
    upload = "--local" not in sys.argv

    stories = get_fresh_stories(config.VIDEOS_PER_RUN)
    if not stories:
        print("No fresh stories found this run -- nothing to upload.")
        return

    for i, story in enumerate(stories, start=1):
        try:
            process_story(story, i, upload=upload)
        except Exception:
            print(f"[{i}] FAILED, skipping this story:")
            traceback.print_exc()


if __name__ == "__main__":
    main()

