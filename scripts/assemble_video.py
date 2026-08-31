"""
Combines background clip + voiceover + burned-in captions into a final
vertical Short using ffmpeg (must be installed -- it's preinstalled on
GitHub's ubuntu-latest runners).
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


def assemble(background_path: str, audio_path: str, srt_path: str, output_path: str):
    audio_duration = get_duration_seconds(audio_path)
    target_duration = min(audio_duration + 0.5, config.MAX_DURATION_SECONDS)

    vf = (
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"subtitles={srt_path}:force_style="
        "'FontName=Arial,FontSize=16,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BorderStyle=1,Outline=2,Alignment=2,MarginV=120'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", background_path,
        "-i", audio_path,
        "-t", str(target_duration),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
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
