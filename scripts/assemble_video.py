"""
Combines background clip + voiceover + optional background music + burned-in
captions into a final vertical Short using ffmpeg (must be installed --
it's preinstalled on GitHub's ubuntu-latest runners).
"""
import subprocess

import config


def get_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def assemble(background_path: str, audio_path: str, srt_path: str, output_path: str,
             music_path: str | None = None):
    audio_duration = get_duration_seconds(audio_path)
    target_duration = min(audio_duration + 0.5, config.MAX_DURATION_SECONDS)

    # Bold, boxed, large captions (the CapCut/TikTok look) -- much more
    # readable and eye-catching than small plain subtitle text, which is
    # one of the biggest silent killers of watch time on Shorts.
    caption_style = (
        "FontName=Arial,FontSize=20,Bold=1,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BackColour=&H80000000&,"
        "BorderStyle=4,Outline=1,Shadow=0,Alignment=2,MarginV=140"
    )

    if background_path.lower().endswith((".png", ".jpg", ".jpeg")):
        video_input = ["-loop", "1", "-i", background_path]
    else:
        video_input = ["-stream_loop", "-1", "-i", background_path]

    inputs = video_input + ["-i", audio_path]
    if music_path:
        inputs += ["-stream_loop", "-1", "-i", music_path]

    video_filter = (
        f"[0:v]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"subtitles={srt_path}:force_style='{caption_style}'[vout]"
    )

    if music_path:
        # Music sits well under the voice (constant low volume -- simple
        # and reliable) rather than full sidechain ducking, which keeps
        # this dependency-free and fast to render.
        audio_filter = (
            f"[2:a]volume={config.MUSIC_VOLUME}[music];"
            f"[1:a][music]amix=inputs=2:duration=first:dropout_transition=2:weights=1 1[aout]"
        )
        filter_complex = f"{video_filter};{audio_filter}"
        audio_map = ["-map", "[aout]"]
    else:
        filter_complex = video_filter
        audio_map = ["-map", "1:a:0"]

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-t", str(target_duration),
        "-filter_complex", filter_complex,
        "-map", "[vout]", *audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, check=True)
    return output_path


if __name__ == "__main__":
    assemble("test_bg.mp4", "test.mp3", "test.srt", "test_final.mp4")
    print("Wrote test_final.mp4")



if __name__ == "__main__":
    assemble("test_bg.mp4", "test.mp3", "test.srt", "test_final.mp4")
    print("Wrote test_final.mp4")
