"""
Converts script text to speech (free) and produces an .srt caption file.

Tries three engines in order, so a single service outage never blocks
the daily upload:

  1. edge-tts   - best quality, free, gives exact word-boundary timing
                  for perfectly synced captions. Occasionally rate-limited
                  or blocked (returns HTTP 403) since it's an unofficial API.
  2. gTTS       - free (Google Translate voice), no API key. Different
                  service/endpoint than edge-tts, so it's a real fallback,
                  not just a retry of the same thing. Captions are
                  estimated from audio duration (no word timing available).
  3. pyttsx3    - fully offline, no network call at all. Always works,
                  but robotic-sounding. Last resort so the run never fails.
                  Requires 'espeak' installed on the runner (apt package).

Whichever engine succeeds, generate_voiceover() writes the same two
outputs: an mp3/wav audio file and a matching .srt file.
"""
import asyncio
import subprocess
import sys

import config


def _ms_to_srt_time(ms: float) -> str:
    total_ms = int(ms)
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def _get_audio_duration_seconds(audio_path: str) -> float:
    """Uses ffprobe (already installed alongside ffmpeg) to get duration."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _write_estimated_srt(text: str, duration_seconds: float, srt_path: str):
    """
    Fallback caption generator for engines that don't give word timing.
    Splits the script into short chunks and spreads them evenly across
    the known audio duration, weighted by chunk length.
    """
    import re

    # Split into short caption-sized chunks (~6-8 words each)
    words = text.split()
    chunk_size = 7
    chunks = [
        " ".join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]
    if not chunks:
        chunks = [text]

    total_chars = sum(len(c) for c in chunks) or 1
    total_ms = duration_seconds * 1000
    srt_lines = []
    cursor_ms = 0.0
    for idx, chunk in enumerate(chunks, start=1):
        share = len(chunk) / total_chars
        chunk_ms = total_ms * share
        start_ms = cursor_ms
        end_ms = cursor_ms + chunk_ms
        cursor_ms = end_ms
        srt_lines.append(
            f"{idx}\n"
            f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}\n"
            f"{chunk}\n"
        )

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


async def _synthesize_edge_tts(text: str, audio_path: str, srt_path: str):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=config.TTS_VOICE)
    submaker = edge_tts.SubMaker()
    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    srt_text = submaker.get_srt()
    if not srt_text.strip():
        raise RuntimeError("edge-tts produced no captions/audio")

    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_text)


def _synthesize_gtts(text: str, audio_path: str, srt_path: str):
    from gtts import gTTS

    tts = gTTS(text=text, lang="en")
    tts.save(audio_path)
    duration = _get_audio_duration_seconds(audio_path)
    _write_estimated_srt(text, duration, srt_path)


def _synthesize_pyttsx3(text: str, audio_path: str, srt_path: str):
    import pyttsx3

    # pyttsx3 needs a .wav path (no direct mp3 support offline)
    wav_path = audio_path.rsplit(".", 1)[0] + ".wav"
    engine = pyttsx3.init()
    engine.save_to_file(text, wav_path)
    engine.runAndWait()

    if wav_path != audio_path:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, audio_path],
            check=True, capture_output=True,
        )

    duration = _get_audio_duration_seconds(audio_path)
    _write_estimated_srt(text, duration, srt_path)


def generate_voiceover(text: str, audio_path: str, srt_path: str):
    """
    Writes audio to audio_path and captions to srt_path.
    Tries edge-tts, then gTTS, then pyttsx3 (offline), in that order.
    Raises only if all three fail.
    """
    errors = []

    try:
        print("[tts] Trying edge-tts...")
        asyncio.run(_synthesize_edge_tts(text, audio_path, srt_path))
        print("[tts] edge-tts succeeded.")
        return
    except Exception as e:
        print(f"[tts] edge-tts failed: {e}", file=sys.stderr)
        errors.append(("edge-tts", e))

    try:
        print("[tts] Trying gTTS fallback...")
        _synthesize_gtts(text, audio_path, srt_path)
        print("[tts] gTTS succeeded.")
        return
    except Exception as e:
        print(f"[tts] gTTS failed: {e}", file=sys.stderr)
        errors.append(("gTTS", e))

    try:
        print("[tts] Trying pyttsx3 offline fallback...")
        _synthesize_pyttsx3(text, audio_path, srt_path)
        print("[tts] pyttsx3 succeeded.")
        return
    except Exception as e:
        print(f"[tts] pyttsx3 failed: {e}", file=sys.stderr)
        errors.append(("pyttsx3", e))

    raise RuntimeError(
        "All TTS engines failed: "
        + "; ".join(f"{name}: {err}" for name, err in errors)
    )


if __name__ == "__main__":
    generate_voiceover(
        "This is a test of the gaming news voiceover pipeline.",
        "test.mp3",
        "test.srt",
    )
    print("Wrote test.mp3 and test.srt")
