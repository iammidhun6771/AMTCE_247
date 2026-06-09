"""
auth_tiktok.py — One-time TikTok OAuth 2.0 Authorization Helper (PKCE)
=======================================================================
Run this script ONCE to authorize AMTCE to post to TikTok on your behalf.

Usage:
    python scripts/auth_tiktok.py [--niche NICHE_NAME]

What it does:
  1. Reads TIKTOK_CLIENT_KEY + TIKTOK_CLIENT_SECRET from Credentials/.env
  2. Generates a PKCE code_verifier + code_challenge (SHA256, required by TikTok)
  3. Opens the TikTok OAuth consent page in your browser
  4. Starts a local HTTP server on http://localhost:8080/callback
  5. Captures the authorization code from the redirect
  6. Exchanges code + code_verifier for access_token + refresh_token
  7. Saves them to tiktok_token_store.json (path based on --niche flag)

After this, AMTCE manages token refreshes automatically.

Scopes requested:
  video.upload    — required for FILE_UPLOAD source
  video.publish   — required for DIRECT_POST mode
  user.info.basic — for profile identification

NOTE: Unaudited apps can only publish with privacy_level=SELF_ONLY.
      Submit your app for audit on TikTok Developer Portal to enable public posts.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("auth_tiktok")

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE  = os.path.join(_REPO_ROOT, "Credentials", ".env")

# ── TikTok endpoints ──────────────────────────────────────────────────────────
_AUTH_URL   = "https://www.tiktok.com/v2/auth/authorize/"
_TOKEN_URL  = "https://open.tiktokapis.com/v2/oauth/token/"
_REDIRECT   = "http://localhost:8080/callback"
_SCOPES     = "video.upload,video.publish,user.info.basic"

# Shared state between server and main thread
_auth_code: str | None = None
_server_done = threading.Event()


# ── PKCE helpers ──────────────────────────────────────────────────────────────

def _generate_pkce_pair() -> tuple[str, str]:
    """
    Generate a PKCE code_verifier and code_challenge (S256 method).
    TikTok requires PKCE for all OAuth 2.0 flows.

    Returns:
        (code_verifier, code_challenge)
    """
    # code_verifier: 43-128 chars, URL-safe random string
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")

    # code_challenge = BASE64URL(SHA256(code_verifier))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


# ── Local callback server ─────────────────────────────────────────────────────

class _CallbackHandler(BaseHTTPRequestHandler):
    """Tiny HTTP handler that captures the OAuth callback code."""

    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _auth_code = params["code"][0]
            self._send_html(
                "<h1 style='color:#22c55e'>✅ Authorization Successful!</h1>"
                "<p>You can close this tab and return to AMTCE.</p>"
                "<p style='color:#64748b;font-size:14px'>Tokens are being saved...</p>"
            )
            logger.info("✅ Authorization code captured.")
        elif "error" in params:
            error = params.get("error", ["unknown"])[0]
            desc  = params.get("error_description", [error])[0]
            self._send_html(
                f"<h1 style='color:#ef4444'>❌ Authorization Failed</h1>"
                f"<p><strong>{error}</strong>: {desc}</p>"
                f"<p>Check the terminal for more info.</p>"
            )
            logger.error("❌ OAuth error: %s — %s", error, desc)

        _server_done.set()

    def _send_html(self, body: str):
        html = (
            "<html><head><style>"
            "body{font-family:system-ui,sans-serif;padding:60px;background:#0f172a;color:#f1f5f9}"
            "h1{margin-bottom:12px}"
            "p{color:#94a3b8;font-size:16px;line-height:1.6}"
            "</style></head>"
            f"<body>{body}</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):  # Suppress default request logging
        pass


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env() -> dict:
    """Parse key=value pairs from Credentials/.env."""
    env = {}
    if not os.path.exists(_ENV_FILE):
        return env
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _token_file_path(niche: str | None) -> str:
    """Resolve where to save the token store for this niche."""
    if niche:
        return os.path.join(
            _REPO_ROOT, "Credentials", "social_media", niche, "tiktok_token_store.json"
        )
    return os.path.join(_REPO_ROOT, "Credentials", "tiktok_token_store.json")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="One-time TikTok OAuth setup for AMTCE (with PKCE)"
    )
    parser.add_argument(
        "--niche",
        default=None,
        help=(
            "AMTCE niche folder name (e.g. General_Fallback, Fashion_Style). "
            "Leave blank to save to root Credentials/tiktok_token_store.json."
        ),
    )
    args = parser.parse_args()

    # Load credentials from .env
    env = _load_env()
    client_key    = env.get("TIKTOK_CLIENT_KEY", os.getenv("TIKTOK_CLIENT_KEY", ""))
    client_secret = env.get("TIKTOK_CLIENT_SECRET", os.getenv("TIKTOK_CLIENT_SECRET", ""))

    if not client_key or not client_secret:
        logger.error(
            "TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in Credentials/.env"
        )
        sys.exit(1)

    # ── Generate PKCE pair ────────────────────────────────────────────────────
    code_verifier, code_challenge = _generate_pkce_pair()
    logger.info("🔐 PKCE code_challenge generated (S256 method)")

    # Build the authorization URL (with PKCE)
    state = f"amtce_{int(time.time())}"
    auth_params = urlencode({
        "client_key":             client_key,
        "scope":                  _SCOPES,
        "response_type":          "code",
        "redirect_uri":           _REDIRECT,
        "state":                  state,
        "code_challenge":         code_challenge,
        "code_challenge_method":  "S256",
    })
    auth_url = f"{_AUTH_URL}?{auth_params}"

    # Start local callback server in background
    try:
        server = HTTPServer(("localhost", 8080), _CallbackHandler)
    except OSError as e:
        logger.error(
            "❌ Could not start callback server on port 8080: %s\n"
            "   Is another process using port 8080? Kill it and try again.", e
        )
        sys.exit(1)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    logger.info("🌐 Opening TikTok OAuth consent page…")
    logger.info("   URL: %s", auth_url)
    webbrowser.open(auth_url)

    logger.info("⏳ Waiting for authorization callback on http://localhost:8080/callback …")
    logger.info("   (You have 5 minutes to complete authorization in your browser)")
    _server_done.wait(timeout=300)   # 5 min timeout
    server.shutdown()

    if not _auth_code:
        logger.error("❌ No authorization code received (timeout or user denied).")
        sys.exit(1)

    # ── Exchange authorization code for tokens (with code_verifier) ───────────
    logger.info("🔄 Exchanging authorization code for tokens…")
    resp = requests.post(
        _TOKEN_URL,
        data={
            "client_key":     client_key,
            "client_secret":  client_secret,
            "code":           _auth_code,
            "grant_type":     "authorization_code",
            "redirect_uri":   _REDIRECT,
            "code_verifier":  code_verifier,   # ← PKCE verifier (required by TikTok)
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    if payload.get("error"):
        logger.error("❌ Token exchange failed: %s", payload)
        sys.exit(1)

    data = payload.get("data", payload)

    if not data.get("access_token"):
        logger.error("❌ No access_token in response: %s", payload)
        sys.exit(1)

    token_store = {
        "access_token":             data["access_token"],
        "refresh_token":            data.get("refresh_token", ""),
        "open_id":                  data.get("open_id", ""),
        "scope":                    data.get("scope", _SCOPES),
        "expires_in":               data.get("expires_in", 86400),
        "refresh_token_expires_in": data.get("refresh_token_expires_in", 2592000),
        "obtained_at":              int(time.time()),
        "client_key":               client_key,
    }

    # Save tokens
    out_path = _token_file_path(args.niche)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(token_store, f, indent=2)

    logger.info("✅ Token store saved to: %s", out_path)
    logger.info("🎉 AMTCE is now authorized to post to TikTok!")
    logger.info(
        "   Note: Unaudited apps use SELF_ONLY privacy. "
        "Submit your app for TikTok audit to enable public posts."
    )
    logger.info("   open_id: %s", token_store.get("open_id", "—"))


if __name__ == "__main__":
    main()
