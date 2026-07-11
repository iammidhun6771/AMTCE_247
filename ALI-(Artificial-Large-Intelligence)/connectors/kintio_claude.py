import os
import json
import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger("SonOfAnton.KintioClaude")

STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Credentials",
    "kintio_state.json"
)

def _get_keys() -> List[str]:
    """Retrieves all Kintio keys from the environment."""
    keys_str = os.getenv("KINTIO_API_KEYS", "").strip()
    if not keys_str:
        return []
    return [k.strip() for k in keys_str.split(",") if k.strip()]

def _load_active_index(num_keys: int) -> int:
    """Loads the active key index from Credentials/kintio_state.json."""
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            idx = int(data.get("active_key_index", 0))
            if 0 <= idx < num_keys:
                return idx
    except Exception:
        pass
    return 0

def _save_active_index(idx: int):
    """Saves the active key index to Credentials/kintio_state.json."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"active_key_index": idx}, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save Kintio state: {e}")

def call_kintio_claude(
    prompt: str,
    system_prompt: str = "You are a strict validator.",
    model: str = "claude-3-5-sonnet-20241022"
) -> Dict[str, Any]:
    """
    Calls Claude via Kintio's Anthropic-compatible API proxy.
    Automatically rotates through keys in KINTIO_API_KEYS on failure.
    """
    keys = _get_keys()
    if not keys:
        return {"error": "No KINTIO_API_KEYS found in environment."}

    num_keys = len(keys)
    start_idx = _load_active_index(num_keys)
    
    # Try all keys starting from the last saved index
    for attempt in range(num_keys):
        idx = (start_idx + attempt) % num_keys
        api_key = keys[idx]
        
        logger.info(f"Using Kintio key index {idx}/{num_keys-1} for model {model}...")
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(
                "https://api.kintio.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Auto-rotate key on rate limits (429) or auth errors (401, 403)
            if response.status_code in (401, 403, 429):
                logger.warning(f"Kintio Key {idx} returned status {response.status_code}. Rotating key...")
                continue
                
            response.raise_for_status()
            res_data = response.json()
            
            content_list = res_data.get("content", [])
            answer = ""
            if content_list and isinstance(content_list, list):
                answer = content_list[0].get("text", "")
                
            if idx != start_idx:
                _save_active_index(idx)
                
            return {
                "answer": answer,
                "model_used": model,
                "tokens_used": res_data.get("usage", {}).get("total_tokens", 0)
            }
            
        except Exception as e:
            logger.warning(f"Error calling Kintio Claude with key {idx}: {e}")
            continue

    next_start = (start_idx + 1) % num_keys
    _save_active_index(next_start)
    return {"error": "All configured Kintio API keys failed or were rate-limited."}
