"""
Overlay Text Engine
--------------------
Generates short, punchy on-screen text (max 4 words) with memory-based
similarity guards so overlays stay fresh and independent from captions
or narration outputs.

Also provides select_viral_hook() which intelligently picks a persuasive
Hindi/Hinglish hook from the VIRAL_HOOKS pool based on visual context
(actress name, niche category, content mood).  These hooks are placed as
text overlays in the same position as the fashion-scout caption lane.
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
# VIRAL HOOK POOL
# Persuasive Hinglish hooks for engagement-bait overlays.
# Placeholders:
#   {name}  → actress / user title resolved from context (falls back to "Bhai")
# ─────────────────────────────────────────────────────────────────────────────
VIRAL_HOOKS: List[str] = [
    # ── no-name / generic — high energy ──────────────────────────────────────
    "Just feel that heat 🥵🔥",                          # 0
    "Look at that walk, too clean 🤤",                                # 1
    "Bhai back profile is next level 😳",                          # 2
    "Vibe check: Out of this world 🚀✨",                          # 3
    "Aisi beauty is rare 🤫🥵",                               # 4
    "Can we appreciate this posture? 🥵",                                   # 5
    "Bhai content is too hot to handle 🌡️🔥",                  # 6
    "She knows exactly what she's doing 😏",                   # 7
    "That drop was completely illegal 😵🔥",                # 8
    "Just look at the way it fits her 🥵😍",           # 9
    "Absolute goddess energy ✨👑",                                    # 10
    "Le bhai, weekend mood set ho gaya 🙈🥵",                               # 11
    "The view gets better every second 😏🔥",                            # 12
    "Save krle, dynamic entry hai 🥵👉",                    # 13
    "Can't take my eyes off this walk 😱🔥",                         # 14
    "Aisi girlfriend to dream hoti hai 😍",              # 15
    "Iska attitude is purely addictive 🤫👀",                             # 16
    "That confidence is unmatched 🖤",                            # 17
    "Bhai pure beauty in one frame 😱🔥",              # 18
    "Vibe is purely therapeutic 🤤✨",                      # 19
    "Look at that drop, absolute banger 💥",                      # 20
    "Ek min ruk, look check kr ✋😏",                                   # 21
    "Scroll mat kar, look at the detail 👀",                       # 22
    "Ye dressing style is top tier 😵🔥",                  # 23
    "Outfit of the year, hands down 🤫",         # 24
    "Bhai kya look hai, absolute fire 🤯🔥",                          # 25
    # ── name-resolved hooks ───────────────────────────────────────────────────
    "Just feel that, {name}'s look 🥵",                                 # 26
    "Boom! {name}'s another banger 🔥",       # 27
    "{name} in this outfit is illegal 😳🥵",                                   # 28
    "Bhai {name} completely owned this walk 👑",       # 29
    "Save this to appreciate {name}'s vibe later 🥵",               # 30
    "{name} is setting the screen on fire 🤯🔥",  # 31
    # ── curiosity / tease ─────────────────────────────────────────────────────
    "The secret of this styling is below 🤫👇",           # 32
    "Wait for the slow-mo, it's worth it ⏱️🤯",             # 33
    "Behind the scenes is even crazier 😱👀",                     # 34
    "Only few noticed the detail at the end 😏",                 # 35
    "This transition is too smooth to be real 😵",                 # 36
    # ── romantic / soft ───────────────────────────────────────────────────────
    "Aisi beauty makes you believe in love 😍✨",              # 37
    "Kash aisi ek smile mujhe bhi mil jata 😢😍",             # 38
    "Pure elegance with a touch of magic 💘😢",                    # 39
]

# ─────────────────────────────────────────────────────────────────────────────
# HOOK SELECTION RULES
# Maps content signals → preferred hook indices (soft hints, not hard locks)
# ─────────────────────────────────────────────────────────────────────────────
_HOOK_RULES: Dict[str, List[int]] = {
    # When actress/title name is known — prefer hooks with {name} placeholder
    "has_name":  [26, 27, 28, 29, 30, 31],
    # Generic / no name
    "no_name":   [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
    # Energetic / party vibe
    "energetic": [2, 3, 6, 7, 11, 14, 15, 18, 26, 28, 31, 35, 36],
    # Romantic / soft vibe
    "romantic":  [8, 9, 20, 26, 27, 28, 30, 37, 38, 39],
    # Curiosity / tease
    "curiosity": [0, 1, 5, 12, 16, 17, 21, 22, 23, 24, 27, 29, 31, 32, 33, 34],
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
                return data.get("NEGATIVE_WORDS", []) or NEGATIVE_WORDS_FALLBACK
    except Exception:
        pass
    return NEGATIVE_WORDS_FALLBACK


NEGATIVE_PATTERNS = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in _load_negative_words()]


def _load_memory() -> List[str]:
    if not os.path.exists(MEMORY_PATH):
        return []
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data][-MAX_MEMORY:]
    except Exception as e:
        logger.warning(f"[OVERLAY_ENGINE] memory_load_failed: {e}")
    return []


def _save_memory(memory: List[str]) -> None:
    try:
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory[-MAX_MEMORY:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[OVERLAY_ENGINE] memory_save_failed: {e}")


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _too_similar(text: str, memory: List[str]) -> bool:
    return any(_similarity(text, prev) > SIMILARITY_THRESHOLD for prev in memory)


def _contains_negative(text: str) -> bool:
    lowered = text.lower()
    return any(p.search(lowered) for p in NEGATIVE_PATTERNS)


def _pick_theme(context: Optional[Dict]) -> str:
    ctx = context or {}
    for key in ("style_category", "persona", "vibe", "tone"):
        val = ctx.get(key)
        if isinstance(val, str) and val:
            return val.lower()
    return "attitude"


def _get_pool(theme: str) -> List[str]:
    if theme in OVERLAY_POOLS:
        return OVERLAY_POOLS[theme][:]
    # Map fuzzy themes to known buckets
    if "lux" in theme:
        return OVERLAY_POOLS["luxury"][:]
    if "minimal" in theme or "clean" in theme:
        return OVERLAY_POOLS["minimal"][:]
    if "statement" in theme:
        return OVERLAY_POOLS["statement"][:]
    return OVERLAY_POOLS["attitude"][:]


def _trim_to_four_words(text: str) -> str:
    words = text.split()
    return " ".join(words[:4]).strip()


def generate_overlay_text(context: Optional[Dict] = None) -> str:
    """
    Generate short overlay text independent of captions/narration.
    - Max 4 words
    - Avoid NEGATIVE_WORDS
    - Reject similarity > 0.8 against last 100 overlays
    """
    memory = _load_memory()
    theme = _pick_theme(context)
    pool = _get_pool(theme)
    
    candidate = None

    # 1. Use Stored Overlay Pools (No API Call)

    # 2. Fallback to Stored Pools
    if not candidate:
        logger.info("⚠️ Falling back to stored overlay pool.")
        random.shuffle(pool)
        for phrase in pool + OVERLAY_POOLS.get("attitude", []):
            text = _trim_to_four_words(phrase)
            if not text or _contains_negative(text) or _too_similar(text, memory):
                continue
            candidate = text
            break

    # 3. Last Resort
    if not candidate:
        candidate = "Own the moment"

    memory.append(candidate)
    memory = memory[-MAX_MEMORY:]
    _save_memory(memory)
    logger.info(f"[OVERLAY_ENGINE] overlay_generated=\"{candidate}\"")
    return candidate




__all__ = ["generate_overlay_text", "select_viral_hook", "VIRAL_HOOKS"]


# ─────────────────────────────────────────────────────────────────────────────
# VIRAL HOOK SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

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
    Intelligently select a viral Hinglish hook based on visual context.

    Context keys used:
        title          (str) : Video title — used to extract actress/subject name
        actress_name   (str) : Detected actress name (highest priority for name slot)
        niche_category (str) : Content niche, e.g. "fashion", "entertainment", "adult"
        energy_score   (float): Visual energy 0.0–1.0 from editing plan
        mood           (str) : "romantic" | "energetic" | "funny" | "curiosity"

    Returns:
        The selected hook string with {name} placeholder resolved.
    """
    ctx = context or {}
    memory = _load_viral_hook_memory()

    # ── 1. Resolve subject name ────────────────────────────────────────────
    name = (
        ctx.get("actress_name")
        or ctx.get("user_title")
        or ctx.get("title", "")
    )
    # Strip system prefixes iteratively and take first meaningful word group (≤3 words)
    if name:
        while True:
            prev_name = name
            name = re.sub(
                r"(?i)^(?:niche[_\s]?virals?|niche|viral|fashion|entertainment|nsfw|adult|paparazzi|general|process|cli|title)[\s:|]+",
                "", name
            ).strip()
            if name == prev_name:
                break
        
        # Remove file-name style underscores/dashes
        name = re.sub(r"[_\-]+", " ", name).strip()
        
        # Filter out generic/default values
        if name.lower() in ("niche viral", "niche virals", "viral niche", "viral niches", "niche_viral", "niche_virals", "niche", "viral", "video", "cli mission", "generic"):
            name = ""
            
        if name:
            # Keep max 3 words
            words = name.split()
            name = " ".join(words[:3]).strip(" '\",.")

    has_name = bool(name and len(name) > 2)

    # ── 2. Resolve mood / vibe ─────────────────────────────────────────────
    mood = ctx.get("mood", "")
    energy_raw = ctx.get("energy_score", 0.5)
    try:
        energy = float(energy_raw) if energy_raw is not None else 0.5
    except (TypeError, ValueError):
        energy = 0.5
    niche = str(ctx.get("niche_category", "")).lower()

    if not mood:
        if energy >= 0.70 or "party" in niche or "dance" in niche:
            mood = "energetic"
        elif "romantic" in niche or energy < 0.35:
            mood = "romantic"
        else:
            mood = "curiosity"

    # ── 3. Build candidate pool using rules ───────────────────────────────
    # We rank candidates by priority:
    # 1. Name-bearing hooks matching the mood
    # 2. Other name-bearing hooks
    # 3. Generic hooks matching the mood
    # 4. Remaining hooks
    name_indices = _HOOK_RULES["has_name"]
    other_indices = [i for i in range(len(VIRAL_HOOKS)) if i not in name_indices]

    mood_rule = _HOOK_RULES.get(mood, [])

    p1 = [i for i in name_indices if i in mood_rule]
    p2 = [i for i in name_indices if i not in mood_rule]
    p3 = [i for i in other_indices if i in mood_rule]
    p4 = [i for i in other_indices if i not in mood_rule]

    if has_name:
        candidate_indices = p1 + p2 + p3 + p4
    else:
        # If no name, name-bearing hooks fall back to "Bhai", so prioritize generic first
        candidate_indices = p3 + p4 + p1 + p2

    # Deduplicate while preserving order
    seen: set = set()
    ordered: List[int] = []
    for idx in candidate_indices:
        if idx not in seen:
            seen.add(idx)
            ordered.append(idx)

    # ── 4. Pick first hook not in recent memory ───────────────────────────
    selected_raw: str = ""
    # Limit memory check to the last 25 entries to ensure we don't block all 40 templates
    recent_memory = memory[-25:]
    for idx in ordered:
        hook = VIRAL_HOOKS[idx]
        resolved = hook.replace("{name}", name) if has_name else hook.replace("{name}", "Bhai")
        
        # Smart similarity comparison to avoid cross-actress blocking
        too_similar = False
        for prev in recent_memory:
            if "{name}" in hook:
                parts = hook.split("{name}")
                prefix = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                
                prev_lower = prev.lower()
                prefix_lower = prefix.lower()
                suffix_lower = suffix.lower()
                
                # If the previous resolved hook matches this template's prefix and suffix, block it
                if prev_lower.startswith(prefix_lower) and (not suffix_lower or prev_lower.endswith(suffix_lower)):
                    too_similar = True
                    break
            
            # Direct similarity check for resolved strings (handles both generic and name-resolved hooks)
            if _similarity(resolved, prev) > 0.75:
                too_similar = True
                break
                    
        if not too_similar:
            selected_raw = resolved
            break

    # Last resort: any random hook
    if not selected_raw:
        hook = random.choice(VIRAL_HOOKS)
        selected_raw = hook.replace("{name}", name) if has_name else hook.replace("{name}", "Bhai")

    # ── 5. Save to memory ─────────────────────────────────────────────────
    memory.append(selected_raw)
    _save_viral_hook_memory(memory)
    logger.info(f"[VIRAL_HOOK] selected=\"{selected_raw}\" mood={mood} has_name={has_name}")
    return selected_raw


