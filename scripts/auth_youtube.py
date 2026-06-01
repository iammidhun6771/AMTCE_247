import os
import sys
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import urllib.request
import urllib.parse
import argparse
import json as _json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"
]

DEFAULT_CLIENT_SECRET_FILE = "Credentials/client_secret.json"
DEFAULT_TOKEN_FILE = "Credentials/token.json"

# File that main.py's /ytcode or /yturl command will write to
AUTH_CODE_FILE = "Credentials/yt_auth_code.txt"


def _send_telegram(message: str, token: str, admin_id: str, button_url: str = None):
    """Send a Telegram message with optional inline URL button."""
    try:
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": admin_id,
            "text": message,
            "parse_mode": "HTML",
        }
        if button_url:
            payload["reply_markup"] = _json.dumps({
                "inline_keyboard": [
                    [{"text": "🔗 Sign in with Google", "url": button_url}]
                ]
            })
        data = urllib.parse.urlencode(payload).encode("utf-8")
        urllib.request.urlopen(api_url, data=data, timeout=10)
        print("📡 Telegram notification sent.")
        return True
    except Exception as te:
        print(f"⚠️ Telegram send failed: {te}")
        return False


def _get_telegram_creds():
    """Get Telegram bot token and admin ID from environment."""
    try:
        from dotenv import load_dotenv
        for env_path in ["Credentials/.env", ".env"]:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=False)
                break
    except ImportError:
        pass
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = (
        os.getenv("TELEGRAM_ADMIN_ID")
        or os.getenv("TELEGRAM_OWNER_CHAT_ID")
        or (os.getenv("ADMIN_IDS", "").split(",")[0].strip() if os.getenv("ADMIN_IDS") else None)
    )
    return token, admin_id


def _extract_code_from_input(raw: str) -> str:
    """
    Extract just the auth code from either:
      - A bare code:  4/0AX...
      - A full URL:   http://localhost/?code=4/0AX...&scope=...
    """
    raw = raw.strip()
    if raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        qs = urllib.parse.parse_qs(parsed.query)
        code = qs.get("code", [None])[0]
        if code:
            return code
    return raw


def authenticate(client_secret_file=None, token_file=None):
    print("🚀 Starting YouTube Authentication...")

    secret_path = client_secret_file or DEFAULT_CLIENT_SECRET_FILE
    token_path = token_file or DEFAULT_TOKEN_FILE
    tg_token, tg_admin = _get_telegram_creds()

    # ── Missing client_secret guard ──────────────────────────────────────────
    if not os.path.exists(secret_path):
        msg = (
            f"❌ <b>YouTube Auth FAILED</b>\n\n"
            f"<b>client_secret.json</b> missing at:\n"
            f"<code>{secret_path}</code>\n\n"
            f"Download from Google Cloud Console → APIs &amp; Services → Credentials\n"
            f"and add it as the <b>CLIENT_SECRET_JSON</b> GitHub Secret."
        )
        print(f"❌ Error: {secret_path} not found!")
        if tg_token and tg_admin:
            _send_telegram(msg, tg_token, tg_admin)
        return

    # ── DEMO credential guard ─────────────────────────────────────────────────
    try:
        with open(secret_path, 'r', encoding='utf-8') as f:
            raw = f.read()
            if "DEMO_CLIENT_ID" in raw or "DEMO_CLIENT_SECRET" in raw:
                print(f"❌ Error: {secret_path} contains placeholder DEMO credentials!")
                return
    except Exception:
        pass

    # ── Detect headless / CI environment ────────────────────────────────────
    is_headless = (
        os.getenv("GITHUB_ACTIONS") == "true"
        or os.getenv("CI") == "true"
        or os.getenv("HEADLESS_AUTH") == "true"
        or not sys.stdin.isatty()
    )

    if not is_headless:
        # ── Local PC: open browser, redirect caught automatically ────────────
        try:
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            creds = flow.run_local_server(
                port=0,
                access_type='offline',
                prompt='consent',
                open_browser=True
            )
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"✅ Authentication successful! Token saved to {token_path}")
            return
        except Exception as e:
            print(f"ℹ️ Browser auth failed, switching to headless mode: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # HEADLESS MODE
    # Strategy: Generate auth URL, send to Telegram, poll for the code
    # that the user pastes back via /ytcode or /yturl Telegram command.
    # The user can paste either:
    #   a) The full broken localhost URL from their browser bar
    #   b) Just the code= value if they prefer
    # ─────────────────────────────────────────────────────────────────────────

    # Try OOB redirect first (cleaner — shows code on Google's own page)
    auth_url = None
    use_oob = False
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            secret_path, SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        use_oob = True
        print("ℹ️ Using OOB redirect flow.")
    except Exception:
        # Fallback to standard localhost redirect
        flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        print("ℹ️ Using localhost redirect flow.")

    print(f"\n🔗 AUTHORIZE HERE:\n{auth_url}\n")

    # Send to Telegram
    if tg_token and tg_admin:
        if use_oob:
            instructions = (
                f"🔐 <b>YouTube Re-Auth Required</b>\n\n"
                f"1️⃣ Tap <b>Sign in with Google</b> below\n"
                f"2️⃣ Pick your account &amp; allow access\n"
                f"3️⃣ Google will show a <b>code on screen</b>\n"
                f"4️⃣ Send it here as:\n<code>/ytcode PASTE_CODE_HERE</code>"
            )
        else:
            instructions = (
                f"🔐 <b>YouTube Re-Auth Required</b>\n\n"
                f"1️⃣ Tap <b>Sign in with Google</b> below\n"
                f"2️⃣ Pick your account &amp; allow access\n"
                f"3️⃣ Browser will show a broken localhost page — that's normal\n"
                f"4️⃣ <b>Copy the full URL</b> from your browser bar\n"
                f"5️⃣ Send it here as:\n<code>/ytcode PASTE_FULL_URL_HERE</code>\n\n"
                f"<i>(You can paste the whole URL — the bot extracts the code automatically)</i>"
            )
        _send_telegram(instructions, tg_token, tg_admin, button_url=auth_url)
        # Also send raw URL so user can long-press copy on phone
        _send_telegram(f"🔗 Auth URL:\n{auth_url}", tg_token, tg_admin)
    else:
        print("⚠️ No TELEGRAM_BOT_TOKEN/TELEGRAM_ADMIN_ID — cannot send notification.")

    # ── Poll for auth code file (written by /ytcode bot command) ─────────────
    print("⏳ Waiting for you to authorize (polling for up to 10 minutes)...")
    deadline = time.time() + 600  # 10 min

    while time.time() < deadline:
        if os.path.exists(AUTH_CODE_FILE):
            try:
                with open(AUTH_CODE_FILE, "r", encoding="utf-8") as f:
                    raw_input = f.read().strip()
                os.remove(AUTH_CODE_FILE)

                code = _extract_code_from_input(raw_input)
                print(f"📥 Auth code received. Exchanging for token...")

                flow.fetch_token(code=code)
                creds = flow.credentials

                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

                print(f"✅ Token saved to {token_path}!")
                if tg_token and tg_admin:
                    _send_telegram(
                        "✅ <b>YouTube Authorized!</b>\n\nToken saved. Uploads will resume automatically.",
                        tg_token, tg_admin
                    )
                return

            except Exception as e:
                print(f"❌ Failed to exchange code for token: {e}")
                if tg_token and tg_admin:
                    _send_telegram(
                        f"❌ <b>Auth Failed</b>\n\nCould not exchange code:\n<code>{e}</code>\n\n"
                        f"Please try again — send /ytcode with the code from the Google page.",
                        tg_token, tg_admin
                    )
                # Reset deadline to give user another chance
                deadline = time.time() + 300

        time.sleep(5)

    # Timed out
    print("❌ Timed out waiting for YouTube authorization (10 min).")
    if tg_token and tg_admin:
        _send_telegram(
            "⏱️ YouTube auth timed out after 10 minutes.\n"
            "Uploads will be skipped this cycle.\n\n"
            "The bot will try again on next scheduled run.",
            tg_token, tg_admin
        )


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    parser = argparse.ArgumentParser(description="AMTCE YouTube Authentication Script")
    parser.add_argument("--secret", help="Path to client_secret.json")
    parser.add_argument("--token", help="Path to save token.json")
    args = parser.parse_args()

    authenticate(client_secret_file=args.secret, token_file=args.token)
