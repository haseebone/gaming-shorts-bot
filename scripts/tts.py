"""
Converts script text to speech, with automatic fallback across FOUR free
providers, because Microsoft's edge-tts service has a well-known history
of periodic outages/blocks that are outside our control (see
https://github.com/rany2/edge-tts/issues -- this has recurred repeatedly
since 2024 and is unrelated to anything in this project).

Order of attempts:
  1. edge-tts   -- best quality, natural AI voice, free
  2. Piper      -- offline neural voice (en_US-lessac-medium), free, MIT
                   licensed, sounds far more natural than a robotic
                   fallback and never depends on any API being up, so
                   it's the "still sounds good" safety net.
  3. gTTS       -- Google Translate's free voice, in case Piper's model
                   file somehow isn't available in a given run.
  4. espeak-ng  -- offline, always installed, always works, robotic voice.
                   The absolute last resort so the channel never goes a
                   day without a video even if everything else fails.

Only edge-tts gives free word-by-word timing for captions. For the other
three we estimate caption timing by spreading words evenly across the
measured audio duration -- less perfectly synced, but still readable.
"""
import asyncio
import subprocess
import wave
import contextlib
import os

import edge_tts
from gtts import gTTS

import config


def _ms_to_srt_time(ms: float) -> str:
    total_ms = int(ms)
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def _write_estimated_srt(text: str, audio_duration_seconds: float, srt_path: str):
    """Splits the script into ~6-word caption chunks spread evenly across
    the audio's actual duration (measured via ffprobe elsewhere)."""
    words = text.split()
    chunk_size = 6
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    if not chunks:
        chunks = [text]

    per_chunk_ms = (audio_duration_seconds * 1000) / len(chunks)
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            start_ms = i * per_chunk_ms
            end_ms = (i + 1) * per_chunk_ms
            f.write(f"{i + 1}\n")
            f.write(f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}\n")
            f.write(f"{chunk}\n\n")


def _get_wav_duration(path: str) -> float:
    with contextlib.closing(wave.open(path, "r")) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _get_mp3_duration_via_ffprobe(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def _try_edge_tts(text: str, audio_path: str, srt_path: str):
    communicate = edge_tts.Communicate(text, voice=config.TTS_VOICE)
    submaker = edge_tts.SubMaker()

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(submaker.get_srt())


def _try_piper(text: str, audio_path: str, srt_path: str):
    model_path = config.PIPER_MODEL_PATH
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Piper voice model not found at {model_path} -- the workflow's "
            "'Download Piper voice model' step should have fetched it."
        )

    result = subprocess.run(
        ["piper", "--model", model_path, "--output_file", audio_path],
        input=text, text=True, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"piper exited with an error: {result.stderr}")

    duration = _get_wav_duration(audio_path)
    _write_estimated_srt(text, duration, srt_path)


def _try_gtts(text: str, audio_path: str, srt_path: str):
    tts = gTTS(text=text, lang="en", tld="com")  # tld="com" = US-accented endpoint
    tts.save(audio_path)
    duration = _get_mp3_duration_via_ffprobe(audio_path)
    _write_estimated_srt(text, duration, srt_path)


def _try_espeak(text: str, audio_path: str, srt_path: str):
    # espeak-ng writes .wav directly; ffmpeg (in assemble_video.py) can
    # take .wav input just as easily as .mp3.
    subprocess.run(
        ["espeak-ng", "-v", "en-us", "-s", "165", "-w", audio_path, text],
        check=True,
    )
    duration = _get_wav_duration(audio_path)
    _write_estimated_srt(text, duration, srt_path)


def _move_if_different_extension(written_path: str, requested_path: str):
    if written_path != requested_path:
        import shutil
        shutil.move(written_path, requested_path)


def generate_voiceover(text: str, audio_path: str, srt_path: str):
    """Tries Piper, then edge-tts, then gTTS, then espeak-ng.

    Piper goes first (not edge-tts) because Microsoft's edge-tts
    handshake has been failing with a 403 on a recurring, ongoing basis
    industry-wide (see github.com/rany2/edge-tts/issues -- still
    unresolved as of the most recent reports), so trying it first just
    means eating a failed request on nearly every run before falling
    back anyway. Piper is a solid offline neural voice and never
    depends on any external API being up.

    Raises only if all four fail."""
    try:
        piper_audio_path = audio_path.rsplit(".", 1)[0] + ".wav"
        _try_piper(text, piper_audio_path, srt_path)
        _move_if_different_extension(piper_audio_path, audio_path)
        print("[tts] Used Piper (offline neural voice)")
        return
    except Exception as e:
        print(f"[tts] Piper failed ({e}), trying edge-tts")

    try:
        asyncio.run(_try_edge_tts(text, audio_path, srt_path))
        print("[tts] Used edge-tts")
        return
    except Exception as e:
        print(f"[tts] edge-tts failed ({e}), falling back to gTTS")

    try:
        _try_gtts(text, audio_path, srt_path)
        print("[tts] Used gTTS")
        return
    except Exception as e:
        print(f"[tts] gTTS failed ({e}), falling back to espeak-ng (offline, last resort)")

    espeak_audio_path = audio_path.rsplit(".", 1)[0] + ".wav"
    _try_espeak(text, espeak_audio_path, srt_path)
    _move_if_different_extension(espeak_audio_path, audio_path)
    print("[tts] Used espeak-ng (offline fallback)")


if __name__ == "__main__":
    generate_voiceover(
        "This is a test of the gaming news voiceover pipeline.",
        "test.mp3",
        "test.srt",
    )
    print("Wrote test.mp3 and test.srt")



if __name__ == "__main__":
    generate_voiceover(
        "This is a test of the gaming news voiceover pipeline.",
        "test.mp3",
        "test.srt",
    )
    print("Wrote test.mp3 and test.srt")
