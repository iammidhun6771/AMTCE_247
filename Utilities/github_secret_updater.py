import os
import sys
import json
import logging
import base64
import urllib.request
import urllib.parse
from typing import Optional

logger = logging.getLogger("github_secret_updater")

# Map local credential directory folder names to GitHub Secret names
SECRET_MAP = {
    "Fashion": "TOKEN_JSON",
    "Fashion_01": "TOKEN_JSON_01",
    "Fashion_02": "TOKEN_JSON_02",
    "Fashion_03": "TOKEN_JSON_03",
    "Fashion_04": "TOKEN_JSON_04",
    "NSFW": "TOKEN_JSON_ADULT",
    "NSFW_01": "TOKEN_JSON_ADULT_01",
    "NSFW_02": "TOKEN_JSON_ADULT_02",
    "NSFW_03": "TOKEN_JSON_ADULT_03",
    "General_Fallback": "TOKEN_JSON",
}

DEFAULT_REPO = os.getenv("GITHUB_REPOSITORY", "swargawasal/AMTCE_247")

def resolve_secret_name(token_path: str) -> str:
    """
    Resolves a local token.json filepath to its corresponding GitHub Secret name.
    """
    normalized = os.path.normpath(token_path).replace("\\", "/")
    parts = normalized.split("/")
    
    # Check if inside Credentials/social_media/<niche>/token.json
    if "social_media" in parts:
        try:
            idx = parts.index("social_media")
            if idx + 1 < len(parts):
                niche_folder = parts[idx + 1]
                if niche_folder in SECRET_MAP:
                    return SECRET_MAP[niche_folder]
                # Dynamic matching for Fashion_XX / NSFW_XX
                if niche_folder.startswith("Fashion"):
                    return f"TOKEN_JSON{niche_folder.replace('Fashion', '')}"
                if niche_folder.startswith("NSFW"):
                    return f"TOKEN_JSON_ADULT{niche_folder.replace('NSFW', '')}"
        except ValueError:
            pass
            
    # Default fallback root token
    return "TOKEN_JSON"

def sync_token_to_github_secret(token_path: str, token_content: Optional[str] = None) -> bool:
    """
    Encrypts and updates the specified YouTube token in GitHub Repository Secrets using GH_PAT.
    """
    pat_token = os.getenv("GH_PAT") or os.getenv("GH_TOKEN")
    if not pat_token:
        logger.debug("[SECRET_SYNC] GH_PAT not present in environment. Skipping remote secret sync.")
        return False
        
    secret_name = resolve_secret_name(token_path)
    
    if not token_content:
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    token_content = f.read()
            except Exception as e:
                logger.error(f"[SECRET_SYNC] Failed to read token file {token_path}: {e}")
                return False
        else:
            logger.error(f"[SECRET_SYNC] Token file does not exist: {token_path}")
            return False

    # Validate JSON content before pushing
    try:
        json.loads(token_content)
    except Exception as je:
        logger.error(f"[SECRET_SYNC] Invalid JSON payload for {secret_name}: {je}")
        return False

    repo = DEFAULT_REPO
    logger.info(f"🔑 [SECRET_SYNC] Syncing updated {secret_name} to GitHub repo '{repo}'...")

    try:
        # 1. Fetch Repo Public Key for Encryption
        key_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
        req = urllib.request.Request(key_url, headers={
            "Authorization": f"token {pat_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AMTCE-Bot"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            key_data = json.loads(resp.read().decode("utf-8"))

        public_key_b64 = key_data["key"]
        key_id = key_data["key_id"]

        # 2. Encrypt using PyNaCl
        try:
            from nacl import encoding, public
            public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
            sealed_box = public.SealedBox(public_key)
            encrypted = sealed_box.encrypt(token_content.encode("utf-8"))
            encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")
        except ImportError:
            logger.warning("[SECRET_SYNC] PyNaCl not installed. Unable to encrypt secret in Python.")
            return False

        # 3. PUT Request to Update Secret
        secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
        payload = json.dumps({"encrypted_value": encrypted_b64, "key_id": key_id}).encode("utf-8")
        put_req = urllib.request.Request(secret_url, data=payload, headers={
            "Authorization": f"token {pat_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "AMTCE-Bot"
        }, method="PUT")

        with urllib.request.urlopen(put_req, timeout=15) as put_resp:
            if put_resp.status in (201, 204):
                logger.info(f"✅ [SECRET_SYNC] Successfully updated GitHub Secret '{secret_name}'!")
                return True
            else:
                logger.warning(f"⚠️ [SECRET_SYNC] Secret update returned status {put_resp.status}")
    except Exception as e:
        logger.warning(f"⚠️ [SECRET_SYNC] Failed to update GitHub Secret '{secret_name}': {e}")
        
    return False
