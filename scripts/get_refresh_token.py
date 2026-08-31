"""
RUN THIS ONCE, ON YOUR OWN COMPUTER (not in GitHub Actions).

It opens your browser, has you log into the Google/YouTube account you
want the bot to upload to, and prints a refresh_token. Copy that value
into the YT_REFRESH_TOKEN GitHub secret and you never need to run this
again.

Usage:
    python scripts/get_refresh_token.py YOUR_CLIENT_ID YOUR_CLIENT_SECRET
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    if len(sys.argv) != 3:
        print("Usage: python get_refresh_token.py CLIENT_ID CLIENT_SECRET")
        sys.exit(1)

    client_id, client_secret = sys.argv[1], sys.argv[2]

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n=== SUCCESS ===")
    print("Add this as the YT_REFRESH_TOKEN secret in your GitHub repo:\n")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
