"""
Converts script text to speech (free, via edge-tts) and produces an
.srt caption file using edge-tts's word-boundary timing so captions are
burned in perfectly synced.
"""
import asyncio
import edge_tts

import config


def _ms_to_srt_time(ms: float) -> str:
    total_ms = int(ms)
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


async def _synthesize(text: str, audio_path: str, srt_path: str):
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


def generate_voiceover(text: str, audio_path: str, srt_path: str):
    """Writes an mp3 to audio_path and an .srt to srt_path."""
    asyncio.run(_synthesize(text, audio_path, srt_path))


if __name__ == "__main__":
    generate_voiceover(
        "This is a test of the gaming news voiceover pipeline.",
        "test.mp3",
        "test.srt",
    )
    print("Wrote test.mp3 and test.srt")
