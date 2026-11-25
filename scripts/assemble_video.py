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
             music_path: str | None = None, title_card_path: str | None = None,
             end_card_path: str | None = None):
    audio_duration = get_duration_seconds(audio_path)
    title_extra = 0.0
    if title_card_path:
        title_extra = get_duration_seconds(title_card_path)
    if end_card_path:
        title_extra += get_duration_seconds(end_card_path)
    target_duration = min(audio_duration + title_extra + 0.5, config.MAX_DURATION_SECONDS)

    # Bold, boxed, large captions (the CapCut/TikTok look) -- much more
    # readable and eye-catching than small plain subtitle text, which is
    # one of the biggest silent killers of watch time on Shorts.
    caption_style = (
        "FontName=Arial,FontSize=26,Bold=1,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BackColour=&H80000000&,"
        "BorderStyle=4,Outline=1,Shadow=0,Alignment=2,MarginV=150"
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
        # Music is ducked under the voice (sidechain compression) so it
        # swells in the gaps and drops during speech -- the professional
        # "podcast/news" sound. Fully free (ffmpeg's sidechaincompress).
        audio_filter = (
            f"[1:a]asplit=2[voice1][voice2];"
            f"[2:a]volume={config.MUSIC_VOLUME}[music];"
            f"[voice2]highpass=f=200,"
            f"sidechaincompress=threshold={config.DUCK_THRESHOLD}:"
            f"ratio={config.DUCK_RATIO}:attack={config.DUCK_ATTACK}:"
            f"release={config.DUCK_RELEASE}[duck];"
            f"[music][duck]amix=inputs=2:duration=first:dropout_transition=2:weights=1 1[musicducked];"
            f"[voice1][musicducked]amix=inputs=2:duration=first:dropout_transition=2:weights=2 1[aout]"
        )
        filter_complex = f"{video_filter};{audio_filter}"
        audio_map = ["-map", "[aout]", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
    else:
        filter_complex = video_filter
        audio_map = ["-map", "1:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]

    # Render the main body, then concat [title card] + body + [end card].
    body_path = output_path.rsplit(".", 1)[0] + "_body.mp4"
    cmd_body = [
        "ffmpeg", "-y",
        *inputs,
        "-t", str(target_duration),
        "-filter_complex", filter_complex,
        "-map", "[vout]", *audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        body_path,
    ]
    subprocess.run(cmd_body, check=True)

    list_file = output_path.rsplit(".", 1)[0] + "_concat.txt"
    with open(list_file, "w") as f:
        if title_card_path:
            f.write(f"file '{title_card_path}'\n")
        f.write(f"file '{body_path}'\n")
        if end_card_path:
            f.write(f"file '{end_card_path}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c", "copy", output_path],
        check=True,
    )
    # Clean up intermediates so the output dir doesn't bloat across runs.
    import os
    for p in (list_file, body_path):
        try:
            os.remove(p)
        except OSError:
            pass
    return output_path


if __name__ == "__main__":
    assemble("test_bg.mp4", "test.mp3", "test.srt", "test_final.mp4")
    print("Wrote test_final.mp4")
