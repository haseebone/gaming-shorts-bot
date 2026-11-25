"""
Free Telegram notification when a video goes live.

All optional: if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID secrets are set, the
bot pings you with the new video link. If not set, this is a no-op.

Setup (1 minute, free):
  1. Open Telegram, message @BotFather -> /newbot -> copy the token.
  2. Message @userinfobot (or your bot) to get your chat id.
  3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as repo secrets.
"""
import os
import requests


def send_video_notification(title: str, video_id: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://youtube.com/shorts/{video_id}"
    text = (
        f"🎮 New short is live!\n\n"
        f"{title}\n\n"
        f"{url}"
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
            timeout=20,
        )
        resp.raise_for_status()
        print("[notify] Telegram notification sent.")
    except Exception as e:
        print(f"[notify] Telegram notification failed ({e}) -- ignoring.")


if __name__ == "__main__":
    send_video_notification("Test", "test_id")