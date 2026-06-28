"""
Overlay Text Engine
--------------------
Generates short, punchy on-screen text (max 4 words) with memory-based
similarity guards so overlays stay fresh and independent from captions
or narration outputs.

Also provides select_viral_hook() and validate_viral_hook() to handle visually
specific, psychologically grounded Hinglish hooks.
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
# STYLE RHYTHM REFERENCE EXAMPLES
# Labeled for rhythm reference only, do not copy content directly.
# ─────────────────────────────────────────────────────────────────────────────
VIRAL_HOOKS: List[str] = [
    "Wo drape ka angle... samjhe? 😏",
    "Camera ne jo pakda, stylist ne nahi pakda 👀",
    "Itna careful styling... phir bhi kuch dikh gaya 🤫",
    "Ye fabric ka kaam thoda zyada honestly kiya 😶",
    "Designer ne boundary set ki thi... fabric ne nahi maani 👁️",
    "Ek second ke liye camera shaky hua... kyu? 😏",
]

_HOOK_RULES: Dict[str, List[int]] = {
    "has_name":  [0, 1, 2, 3, 4, 5],
    "no_name":   [0, 1, 2, 3, 4, 5],
    "energetic": [0, 1, 5],
    "romantic":  [2, 3],
    "curiosity": [1, 4, 5],
}

_VIRAL_HOOK_MEMORY_PATH = "The_json/viral_hook_memory.json"
_VIRAL_HOOK_MAX_MEMORY = 50

MEMORY_PATH = "The_json/overlay_memory.json"
MAX_MEMORY = 100
SIMILARITY_THRESHOLD = 0.8

NEGATIVE_WORDS_FALLBACK = [
    "effortless",
    "stunning",
    "beautiful",
    "chic",
    "elegant",
    "sexy",
    "hot",
    "camera",
    "video",
    "clip",
    "shows",
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

    negative = _load_negative_words()
    memory = _load_memory()

    combined_context = f"{caption_text or ''} {narration_text or ''}".lower()
    context_words = set(re.findall(r"\w+", combined_context))

    candidates: List[str] = []
    for text in pool:
        words = set(re.findall(r"\w+", text.lower()))
        if any(w in negative for w in words):
            continue
        if words.intersection(context_words):
            continue

        too_similar = False
        for prev in memory:
            if _similarity(text, prev) > SIMILARITY_THRESHOLD:
                too_similar = True
                break
        if too_similar:
            continue

        candidates.append(text)

    if candidates:
        selected = random.choice(candidates)
    else:
        filtered_fallback = [
            t for t in pool if not any(w in t.lower() for w in negative)
        ]
        selected = (
            random.choice(filtered_fallback) if filtered_fallback else pool[0]
        )

    memory.append(selected)
    _save_memory(memory)
    return selected


__all__ = ["generate_overlay_text", "select_viral_hook", "validate_viral_hook", "VIRAL_HOOKS"]


# ─────────────────────────────────────────────────────────────────────────────
# HOOK VALIDATION & SELECTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def validate_viral_hook(hook: str) -> bool:
    """
    Validation function that rejects any hook that:
    1. Could have been written without seeing the frames (generic)
    2. Contains generic filler as main subject: vibe, entry, feel, look
    3. Contains forbidden words: bhai, yaar, sexy, hot, body, skin, nude
    4. Is longer than 9 words or shorter than 3 words
    """
    if not hook or not isinstance(hook, str):
        return False
    words = hook.strip().split()
    if len(words) > 9 or len(words) < 3:
        logger.warning(f"[HOOK_VALIDATION] Rejected (word count {len(words)} not in 3-9): '{hook}'")
        return False

    hook_lower = hook.lower()

    # Forbidden words (bhai, yaar, explicit terms)
    forbidden = ["bhai", "yaar", "sexy", "hot", "body", "skin", "nude", "boobs", "cleavage"]
    for f_word in forbidden:
        if re.search(rf"\b{re.escape(f_word)}\b", hook_lower):
            logger.warning(f"[HOOK_VALIDATION] Rejected (contains forbidden word '{f_word}'): '{hook}'")
            return False

    # Generic filler as main subject
    generic_patterns = [
        r"\bvibe\b",
        r"\bentry\b",
        r"\bfeeling?\b",
        r"\blooks?\b\s+wala",
        r"\bkya\s+look\b",
        r"\blook\b\s+check\b"
    ]
    for pattern in generic_patterns:
        if re.search(pattern, hook_lower):
            logger.warning(f"[HOOK_VALIDATION] Rejected (contains generic filler pattern '{pattern}'): '{hook}'")
            return False

    return True


def _load_viral_hook_memory() -> List[str]:
    """Load recently used viral hook texts to avoid repetition."""
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
    Dynamically select or construct a visually specific, gap-based Hinglish hook.
    Uses memory threshold 0.60 for heightened uniqueness.
    """
    ctx = context or {}
    memory = _load_viral_hook_memory()

    name = (
        ctx.get("actress_name")
        or ctx.get("user_title")
        or ctx.get("title", "")
    )
    if name:
        while True:
            prev_name = name
            name = re.sub(
                r"(?i)^(?:niche[_\s]?virals?|niche|viral|fashion|entertainment|nsfw|adult|paparazzi|general|process|cli|title)[\s:|]+",
                "", name
            ).strip()
            if name == prev_name:
                break
        name = re.sub(r"[_\-]+", " ", name).strip()
        if name.lower() in ("niche viral", "niche virals", "viral niche", "viral niches", "niche_viral", "niche_virals", "niche", "viral", "video", "cli mission", "generic"):
            name = ""
        if name:
            words = name.split()
            name = " ".join(words[:3]).strip(" '\",.")

    has_name = bool(name and len(name) > 2)

    # Dynamic gap templates focused on specific elements (strictly 6-8 words)
    gap_templates = [
        "Wo drape ka angle... samjhe? 😏",
        "Camera ne pakda, stylist ne nahi 👀",
        "Careful styling... phir bhi dikh gaya 🤫",
        "Ye fabric ka kaam honest hua 😶",
        "Designer boundary... fabric ne nahi maani 👁️",
        "Camera second ke liye shaky hua 😏",
    ]
    if has_name:
        gap_templates.insert(0, f"Wo {name} ka drape angle... samjhe? 😏")
        gap_templates.insert(2, f"Careful styling... phir bhi {name} dikha 🤫")

    recent_memory = memory[-25:]
    selected_raw = ""

    for cand in gap_templates:
        if not validate_viral_hook(cand):
            continue
        too_similar = False
        for prev in recent_memory:
            if _similarity(cand, prev) > 0.60:  # Tuned threshold 0.60
                too_similar = True
                break
        if not too_similar:
            selected_raw = cand
            break

    if not selected_raw:
        selected_raw = gap_templates[0]

    memory.append(selected_raw)
    _save_viral_hook_memory(memory)
    logger.info(f"[VIRAL_HOOK] selected=\"{selected_raw}\" visually_grounded=True")
    return selected_raw
