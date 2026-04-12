"""
app/services/calendar_auth.py

Run this ONCE to authorize TDMS to access your Google Calendar.
It will open a browser window asking you to log into Google and
grant permission. After you approve, it saves a token.json file
that the app uses for all future calendar operations.

Usage (from the backend/ directory, with venv activated):
  python -m app.services.calendar_auth

You only need to run this once. If you later revoke access in your
Google account settings, delete token.json and run this again.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = "google_credentials.json"
TOKEN_FILE = "token.json"


def authorize():
    if not os.path.exists(CREDENTIALS_FILE):
        print(
            f"\n[Error] {CREDENTIALS_FILE} not found.\n"
            "Please download your OAuth credentials from Google Cloud Console:\n"
            "  1. Go to https://console.cloud.google.com\n"
            "  2. Select your TDMS project\n"
            "  3. APIs & Services → Credentials\n"
            "  4. Create OAuth 2.0 Client ID → Desktop App\n"
            "  5. Download JSON and save as: backend/google_credentials.json\n"
        )
        return

    print("[Calendar Auth] Starting OAuth flow — a browser window will open…")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # run_local_server opens your default browser and handles the redirect automatically
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"\n[Calendar Auth] Authorization successful! Token saved to: {TOKEN_FILE}")
    print("You can now use Google Calendar sync in TDMS.")


if __name__ == "__main__":
    authorize()
