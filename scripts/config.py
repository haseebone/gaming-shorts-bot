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
VIDEOS_PER_RUN = 2

# Vertical short specs (YouTube Shorts requirement: <= 60s, 9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
MAX_DURATION_SECONDS = 58

# edge-tts voice. Use an American English voice to match US targeting.
# Full list: run `edge-tts --list-voices` locally.
TTS_VOICE = "en-US-GuyNeural"

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
