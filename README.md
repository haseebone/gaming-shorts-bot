# Gaming News Shorts Bot

Fully automated, 100% free pipeline that posts 5 vertical YouTube Shorts a
day, spread across US hours, covering game news and esports/tournament
results — no game footage, no copyrighted characters, no manual work
after setup.

## Why no game footage

Actual GTA (or any other game's) gameplay footage belongs to whoever
recorded it, and the game itself is copyrighted by its publisher.
Automatically downloading and reposting other people's gameplay isn't
legal and is exactly what YouTube's spam/reused-content policy targets —
it gets channels terminated, often fast. This bot instead does **original
commentary/news** with AI voiceover over free stock b-roll, which is a
real, sustainable, monetizable niche and has no copyright exposure.

## How it works

```
GitHub Actions (free, 5x/day cron)
  -> fetch_news.py       free RSS feeds (IGN, Eurogamer, GameSpot, etc.)
  -> generate_script.py  turns story into a ~50s narration script
  -> tts.py               free TTS with 4-way fallback (edge-tts -> Piper
                           offline neural voice -> gTTS -> espeak-ng) +
                           synced captions
  -> graphics.py          tournament/match-result stories -> original
                           scoreboard graphic (Pillow) + slow zoom (ffmpeg)
  -> stock_media.py       everything else -> free vertical b-roll (Pexels)
  -> assemble_video.py    ffmpeg combines audio + video + burned captions
  -> youtube_upload.py    uploads via YouTube Data API (free quota)
```

### Why the voiceover has 4 fallback layers

Microsoft's free edge-tts service has a well-documented history of
temporary outages/blocks (see github.com/rany2/edge-tts/issues) that are
outside our control — this is what caused your first run to fail. So
`tts.py` tries edge-tts first (best quality), then falls back to
**Piper** (a free offline neural voice — sounds far more natural than a
robotic voice and never depends on any API being up), then gTTS, and
finally offline `espeak-ng` as the absolute last resort. A temporary
outage at Microsoft no longer means either a missed upload or a
robotic-sounding video.

### Why tournament stories get a generated graphic instead of real clips

Broadcast/match footage belongs to the tournament organizer or platform
holder and is normally Content-ID fingerprinted, so reposting even a
short clip typically gets it claimed or struck almost immediately.
`graphics.py` detects result-style stories (wins/defeats/finals/score
patterns) and instead renders an original scoreboard card — team names
and score pulled from the article text, drawn from scratch with Pillow,
with a slow Ken Burns zoom applied via ffmpeg. No logos, no footage, no
IP risk. Non-tournament news still uses generic Pexels b-roll.

Nothing here costs money: GitHub Actions' free tier, edge-tts, Pexels'
free API, ffmpeg, and the YouTube Data API's free daily quota (10,000
units/day — an upload costs 1,600, so 2/day uses a small fraction of it).

## One-time setup

1. **Google Cloud project** → console.cloud.google.com → New Project.
2. **Enable YouTube Data API v3** under APIs & Services → Library.
3. **OAuth consent screen** → External → add yourself as a Test user
   (no Google verification needed for personal use).
4. **Create OAuth credentials** → Credentials → Create Credentials →
   OAuth client ID → **Desktop app** → download the JSON for your
   `client_id` / `client_secret`.
5. **Pexels API key** → pexels.com/api → free signup.
6. **Get your refresh token** — on your own machine:
   ```
   pip install google-auth-oauthlib
   python scripts/get_refresh_token.py YOUR_CLIENT_ID YOUR_CLIENT_SECRET
   ```
   Log in with the YouTube account you want the bot to post to. It
   prints a refresh token — copy it.
7. **Add GitHub repo secrets** (Settings → Secrets and variables →
   Actions):
   - `YT_CLIENT_ID`
   - `YT_CLIENT_SECRET`
   - `YT_REFRESH_TOKEN`
   - `PEXELS_API_KEY`
8. Push this repo to GitHub. The workflow in
   `.github/workflows/daily-upload.yml` runs automatically **5 times a
   day** at spread-out US hours (see the schedule comments in that file).
   You can also trigger it manually from the **Actions** tab
   (`workflow_dispatch`) to test it right away.

## Posting schedule (5 videos/day, spread across US hours)

`config.VIDEOS_PER_RUN = 1` and the workflow triggers 5 separate times a
day (9 AM, 12 PM, 3 PM, 6 PM, 9 PM US Eastern), so instead of two videos
landing at once, a fresh Short appears roughly every 3 hours during the
US day — morning commute, lunch, afternoon lull, after work/school, and
evening scroll. Want a different number of videos or times? Add/remove
`cron:` lines in `.github/workflows/daily-upload.yml` (each line = one
run = one video, since `VIDEOS_PER_RUN` is 1); GitHub cron times are
always in UTC, so convert your target US time to UTC first.

## Targeting a US audience

- `defaultAudioLanguage` is set to `en-US` and the voice is an American
  English TTS voice (`en-US-GuyNeural` in `config.py` — change to
  `en-US-JennyNeural` for a female voice, or see
  `edge-tts --list-voices`).
- Upload times are spread across US daytime/evening hours (see schedule
  above).
- YouTube's own recommendation system will further localize distribution
  based on viewer engagement — there's no upload-time "audience country"
  field beyond language/caption signals, so language + timing is what you
  control.

## Customizing content sources

Edit `RSS_FEEDS` in `scripts/config.py` to add/remove outlets, or narrow
it to specific games/esports scenes you care about. The pipeline doesn't
care what the feed covers as long as it's a valid RSS/Atom URL.

## If GTA 6 (or GTA 7 someday) launches

Nothing needs to change — this channel already covers *news about* every
game, so a GTA 6 launch just becomes one more story pulled from the RSS
feeds automatically, with zero manual intervention.

## Costs & limits to know about

- GitHub Actions free tier: 2,000 min/month for private repos (5
  runs/day at a few minutes each is well within that; public repos get
  unlimited minutes).
- YouTube Data API: 10,000 free units/day; each upload = 1,600 units, so
  5/day uses 8,000 — comfortably under the limit, but don't add a 6th run
  without checking the math.
- Pexels, edge-tts/gTTS/espeak-ng: free, no card required.
- Piper (the offline neural voice fallback) is free to run, but current
  releases are GPL-3.0 licensed (older MIT-era versions are unmaintained).
  Running it privately in your own automation, as this project does, is
  fine under GPL — the license terms mainly matter if you redistribute
  the software itself, which this setup doesn't do.
- If a story doesn't have a strong visual match, the bot falls back to
  generic gaming b-roll (setups, arenas, keyboards) rather than searching
  for a specific game's name/art, to stay clear of any brand/IP issues.
- The "already posted" tracking file (`scripts/state/posted_links.json`)
  is committed back into the repo automatically after each run, so it
  persists reliably across all 5 daily runs without needing any extra
  setup from you.
