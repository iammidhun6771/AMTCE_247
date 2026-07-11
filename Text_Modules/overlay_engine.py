"""
Overlay Text Engine
--------------------
Generates short, punchy on-screen text (max 4 words) with memory-based
similarity guards so overlays stay fresh and independent from captions
or narration outputs.

Also provides select_viral_hook() as a mechanic-observation fallback,
and validate_viral_hook() for strict psychological validation.
"""

import json
import logging
import os
import random
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional

logger = logging.getLogger("overlay_engine")

# ─────────────────────────────────────────────────────────────────────────────
# MECHANIC-OBSERVATION FALLBACK POOL (20 Structurally Varied Fallbacks)
# ─────────────────────────────────────────────────────────────────────────────
_FALLBACK_STRUCTURES = [
    "Ye fabric drape manually set hoti hai 🤫",
    "Is cut ka naam cowl neckline hai — rare hai 😶",
    "Is drape ki tailoring details dekh rahe ho? 👀",
    "Ye silk stitch pattern machine se nahi bana 🤫",
    "Ye pattern silhouette perfect tailoring se banta hai 😶",
    "Fabric ka grain shine dekh tune? 👀",
    "Hemline ka stitch design custom made hai zaroor 👁️",
    "Tailoring border pe Resham work kiya gaya hai 😶",
    "Gota patti design ka work is suit ko unique banata hai 🤫",
    "Is structured fit ki boning details pe dhyan gaya? 👀",
    "Ye fabric weave handwoven loom se bana hai 😏",
    "Is draping ka symmetry ratio perfect match hai 👁️",
    "Zari work ki thread-count purity high hai 🤫",
    "Is fabric ka grain texture crepe cotton blend hai 😶",
    "Neckline cutout design custom pattern hai 👀",
    "Is silhouette drape ka fall fluid georgette hai 😏",
    "Brocade work ki weaving detail dekh rahe ho? 👁️",
    "Is neck detail ka design handwoven cut hai 🤫",
    "Asymmetric silhouette ka alignment expert tailored hai 😶",
    "Tailor ne drape angle perfect design kiya hai 👀",
]

VIRAL_HOOKS: List[str] = _FALLBACK_STRUCTURES

_VIRAL_HOOK_MEMORY_PATH = "The_json/viral_hook_memory.json"
_VIRAL_HOOK_MAX_MEMORY = 50

MEMORY_PATH = "The_json/overlay_memory.json"
MAX_MEMORY = 100
SIMILARITY_THRESHOLD = 0.8

NEGATIVE_WORDS_FALLBACK = [
    "effortless", "stunning", "beautiful", "chic", "elegant",
    "sexy", "hot", "camera", "video", "clip", "shows"
]

OVERLAY_POOLS: Dict[str, List[str]] = {
    "attitude": [
        "Own the moment",
        "Main character stance",
        "Command the room",
        "Lead with presence",
        "Move like you mean it",
    ],
    "luxury": [
        "Quiet power",
        "Calm authority",
        "Understated shine",
        "Soft luxe",
        "Rare air energy",
    ],
    "minimal": [
        "Less noise",
        "Clean lines only",
        "Signal over noise",
        "Sharp and simple",
        "More presence",
    ],
    "statement": [
        "Icon in motion",
        "Own your frame",
        "Nothing accidental",
        "Signature move",
        "Attention follows",
    ],
}


def _load_negative_words() -> List[str]:
    cfg_path = "The_json/caption_prompt.json"
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                words = data.get("negative_words", [])
                if isinstance(words, list) and words:
                    return [w.lower() for w in words if isinstance(w, str)]
    except Exception:
        pass
    return NEGATIVE_WORDS_FALLBACK


def _load_memory() -> List[str]:
    if not os.path.exists(MEMORY_PATH):
        return []
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data][-MAX_MEMORY:]
    except Exception:
        pass
    return []


def _save_memory(memory: List[str]) -> None:
    try:
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory[-MAX_MEMORY:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[OVERLAY] memory_save_failed: {e}")


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def generate_overlay_text(
    caption_text: Optional[str] = None,
    narration_text: Optional[str] = None,
    mood: Optional[str] = None,
) -> str:
    pool_name = mood if mood in OVERLAY_POOLS else "statement"
    pool = OVERLAY_POOLS[pool_name]
    memory = _load_memory()
    negative = _load_negative_words()
    
    for text in random.sample(pool, len(pool)):
        if any(w in text.lower() for w in negative):
            continue
        if not any(_similarity(text, prev) > SIMILARITY_THRESHOLD for prev in memory):
            memory.append(text)
            _save_memory(memory)
            return text
    
    fallback = pool[0]
    memory.append(fallback)
    _save_memory(memory)
    return fallback


__all__ = ["generate_overlay_text", "select_viral_hook", "validate_viral_hook", "VIRAL_HOOKS"]


def validate_viral_hook(hook: str) -> bool:
    """
    Strict psychological validator enforcing:
    1. 4 to 9 words max (emojis stripped before counting)
    2. No bhai, no yaar, no explicit terms
    3. No generic filler subjects: vibe, entry, feel, scene
    """
    if not hook or not isinstance(hook, str):
        return False
    
    # Strip emojis before counting words
    emoji_pattern = re.compile(
        "[𐀀-􏿿"
        "😀-🙏"
        "🌀-🗿"
        "🚀-🛿"
        "🇠-🇿"
        "]+", flags=re.UNICODE
    )
    hook_no_emoji = emoji_pattern.sub("", hook).strip()
    words = hook_no_emoji.split()
    
    if len(words) > 9 or len(words) < 4:
        logger.warning(
            f"[HOOK_VALIDATION] Rejected (word count {len(words)} not in 4-9): '{hook}'"
        )
        return False
    
    hook_lower = hook.lower()
    forbidden = [
        "bhai", "yaar", "sexy", "hot", "body", 
        "skin", "nude", "gorgeous", "stunning"
    ]
    for f_word in forbidden:
        if re.search(rf"\b{re.escape(f_word)}\b", hook_lower):
            logger.warning(
                f"[HOOK_VALIDATION] Rejected (forbidden: '{f_word}'): '{hook}'"
            )
            return False
    
    generic_patterns = [
        r"\bvibe\b", r"\bentry\b", r"\bfeeling?\b", r"\bscene\b"
    ]
    for pattern in generic_patterns:
        if re.search(pattern, hook_lower):
            logger.warning(
                f"[HOOK_VALIDATION] Rejected (generic filler): '{hook}'"
            )
            return False
    
    return True


def _load_viral_hook_memory() -> List[str]:
    if not os.path.exists(_VIRAL_HOOK_MEMORY_PATH):
        return []
    try:
        with open(_VIRAL_HOOK_MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data][-_VIRAL_HOOK_MAX_MEMORY:]
    except Exception:
        pass
    return []


def _save_viral_hook_memory(memory: List[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_VIRAL_HOOK_MEMORY_PATH), exist_ok=True)
        with open(_VIRAL_HOOK_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory[-_VIRAL_HOOK_MAX_MEMORY:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[VIRAL_HOOK] memory_save_failed: {e}")


def select_viral_hook(context: Optional[Dict] = None) -> str:
    """
    Fallback only — Gemini should be primary.
    These are structurally sound gap-hooks, not content templates.
    They reference camera/fabric/styling mechanics, not specific visuals.
    Acceptable as fallback because they are observation-framed, not desire-bait.
    """
    ctx = context or {}
    memory = _load_viral_hook_memory()

    recent_memory = memory[-10:]

    for hook in _FALLBACK_STRUCTURES:
        too_similar = any(
            _similarity(hook, prev) > 0.60
            for prev in recent_memory
        )
        if not too_similar:
            memory.append(hook)
            _save_viral_hook_memory(memory)
            logger.info(f"[VIRAL_HOOK] fallback_selected='{hook}'")
            return hook

    # Absolute last resort
    selected = _FALLBACK_STRUCTURES[0]
    memory.append(selected)
    _save_viral_hook_memory(memory)
    return selected
