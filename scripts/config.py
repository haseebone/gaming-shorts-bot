"""
Central config. Edit this file to change news sources, video count,
or targeting -- no other code changes needed.
"""

# Free RSS feeds covering game news + esports/tournament results.
# Add/remove feeds freely -- the script just needs a valid RSS/Atom URL.
RSS_FEEDS = [
    "https://www.ign.com/rss/articles/feed",
    "https://www.eurogamer.net/feed",
    "https://www.gamespot.com/feeds/game-news/",
    "https://www.pcgamer.com/rss/",
    "https://www.rockpapershotgun.com/feed",
    "https://liquipedia.net/dota2/index.php?title=Special:RecentChanges&feed=rss",
]

# How many Shorts to produce and upload per run.
# Set to 1 -- the workflow now triggers 5x/day at spread-out US times
# instead of making 2 videos in one burst, so viewers see a fresh video
# throughout the day instead of two at once.
VIDEOS_PER_RUN = 1

# Vertical short specs (YouTube Shorts requirement: <= 3 min / 180s, 9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
# Hard cap = the maximum YouTube Shorts length. Scripts are written to fill
# up to this when the story is rich enough (never truncating a good answer).
MAX_DURATION_SECONDS = 180
# Comfortable target length for a typical news short. Longer, richer stories
# can go all the way up to MAX_DURATION_SECONDS.
TARGET_DURATION_SECONDS = 75

# Background music volume relative to the voiceover (0.0-1.0). Kept low
# so it never competes with narration -- just adds energy underneath it.
MUSIC_VOLUME = 0.12
MUSIC_DIR = "music"

# edge-tts voice. Use an American English voice to match US targeting.
# Christopher = deep, energetic, great for gaming/news commentary.
# Full list: run `edge-tts --list-voices` locally.
TTS_VOICE = "en-US-ChristopherNeural"
# Slight speed boost for a punchier, more energetic delivery (percent string
# edge-tts accepts, e.g. "+8%", "-5%", "10%"). Empty string = normal pace.
TTS_RATE = "+8%"

# Offline neural fallback voice (used if edge-tts is down). Downloaded by
# the workflow into this path before the pipeline runs -- see
# .github/workflows/daily-upload.yml.
PIPER_MODEL_PATH = "voices/en_US-lessac-medium.onnx"

# YouTube upload metadata targeting a US audience.
YOUTUBE_CATEGORY_ID = "20"  # Gaming
DEFAULT_LANGUAGE = "en"
DEFAULT_AUDIO_LANGUAGE = "en-US"
PRIVACY_STATUS = "public"  # or "private" while testing

# Pexels search terms used as a *fallback* background when a story has no
# obvious visual keyword. Keep these generic/neutral -- never a game title
# or character name, since we only want free stock footage here.
FALLBACK_VISUAL_QUERIES = [
    "esports arena crowd",
    "gaming setup neon",
    "video game controller closeup",
    "computer keyboard gaming",
]

OUTPUT_DIR = "output"
STATE_FILE = "state/posted_links.json"  # tracks which stories were already made into videos

# Title-card: a ~2.5s branded opening with the story title, so sound-off
# viewers instantly know what the video is about (big retention win).
TITLE_CARD_SECONDS = 2.5
TITLE_CARD_BRAND = "GAMING NEWS"

# Thumbnail upload is attempted but never fatal -- it needs a verified
# channel, otherwise it's skipped with a warning.
THUMBNAIL_PATH = "thumbnail.jpg"
