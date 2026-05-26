"""Dataset loader for Phase-1 RAG prototype.

Hardcoded small dataset of editing patterns. Supports optional clearing of the
collection, stable IDs to avoid duplicates, and light normalization to align
query and stored text for retrieval.
"""

from __future__ import annotations

import re
import time
from typing import Dict, List


# Selective normalization to avoid semantic collapse of distinct fields
# We only lowercase and clean whitespace, preserving specific labels like 'high' and 'fast'.
def normalize_text(text: str) -> str:
    """Lowercase and clean whitespace while preserving distinct semantic tokens."""
    normalized = text.lower().strip()
    # collapse repeated whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


DATASET: List[Dict[str, str]] = [
    # --- FITNESS (7) ---
    {
        "category": "fitness", "energy": "high", "pace": "fast",
        "hook": "explosive box jump with frame freeze on peak",
        "strategy": "open on the peak freeze frame then reverse to the jump — makes viewer lean forward. Beat drops lock to each rep start. Kinetic text slams like a punch on impact frames. Speed ramp: slow entering the move, snap to normal on landing. Never hold a static shot longer than 0.8s. Close on a hero slow-mo of sweat or muscle tension — earns the save."
    },
    {
        "category": "fitness", "energy": "high", "pace": "fast",
        "hook": "heavy barbell slam with vibration glitch",
        "strategy": "cut on the impact — not before, not after. Aggressive match cuts across angles so it feels like the weight is hitting from everywhere. Stack foley: iron clank + bass thud layered. Flash frame at peak force. Text overlay burns in white then fades — never static. End on a tight face shot: determination sells the product."
    },
    {
        "category": "fitness", "energy": "medium", "pace": "steady",
        "hook": "yoga flow from warrior to balance pose",
        "strategy": "breath-synced cuts — cut on the exhale, hold on the inhale. 2-3s per pose minimum so the viewer can absorb the form. Slow dissolves between poses feel like the movement itself. Minimal text — single word cues like HOLD, BREATHE. Warm amber grade. End on stillness: a 3s wide shot with no cut earns more shares than any effect."
    },
    {
        "category": "fitness", "energy": "medium", "pace": "steady",
        "hook": "healthy meal prep assembly montage",
        "strategy": "cut on action — knife meets board, oil hits pan. Foley is everything: the chop, the sizzle, the pour. Keep each shot 1.5-2.5s. Tactile colour pop grading makes food look edible. Steady lo-fi beat under the cuts ties it together without dominating. End on the finished plate in natural light — wideshot then close on detail."
    },
    {
        "category": "fitness", "energy": "low", "pace": "slow",
        "hook": "silhouette stretch in golden hour window light",
        "strategy": "treat this like a short film not a workout video. Open wide, let the light do the talking. Cuts should be invisible — long cross-dissolves that feel like breathing. No text in the first 4 seconds. Let the silence breathe then bring in a single piano note. The product is the feeling: slow pull-out on the final shot rewards patience."
    },
    {
        "category": "fitness", "energy": "low", "pace": "slow",
        "hook": "meditation close-up with breathing-rhythm text",
        "strategy": "text appears and disappears with the breath cycle — on-screen for 2s, off for 3s. Never more than 3 words. Oceanic slow zoom in at 0.02x speed feels meditative not lazy. Soft vocal pad under the audio. Hard cuts are banned here — every transition should be imperceptible. End before the viewer expects it: leave them wanting one more breath."
    },
    {
        "category": "fitness", "energy": "high", "pace": "fast",
        "hook": "MMA combination ending in a knockout",
        "strategy": "POV angle on the first punch, cut mid-combination to the opponent's reaction. Never show the full combo in one shot — fragment it: jab from angle A, cross from angle B, hook from C. Glitch effect only on impact, not randomly. Ultra-high cut density — average 0.5s per shot in the combo. Silence for 1 frame on the KO then boom. Audience rewind rate is your metric."
    },

    # --- FASHION / INDIAN FASHION (14) ---
    {
        "category": "fashion", "energy": "high", "pace": "fast",
        "hook": "outfit reveal via spin — saree or lehenga hem in motion",
        "strategy": "open on the feet and slowly pan up — reveal the full look at the beat drop. Snap cuts between angles: front, side, back, detail. Fabric in motion is the hero: never cut while it's still. Speed ramp the spin itself — slow into it, fast through it, slow out. High saturation grade makes the colour pop. End tight on jewellery or face — it's the memory anchor."
    },
    {
        "category": "fashion", "energy": "high", "pace": "fast",
        "hook": "walk towards camera on street with confident eye contact",
        "strategy": "aggressive bass-driven sync — cut lands every time a foot hits the ground. High-contrast urban grade. Pull focus from background to face on approach. Text burns in like a watermark: the item name, the price. Never cut away from the eyes before they reach the lens — that connection is worth 3 seconds of hold time. End on a freeze frame."
    },
    {
        "category": "fashion", "energy": "high", "pace": "fast",
        "hook": "dance reveal — classical or Bollywood move in ethnic wear",
        "strategy": "sync the first cut to the tabla or dhol hit. Keep cuts inside the movement — never cut between moves, always in the middle of motion so it feels continuous. Wide for context, tight for expression, detail for fabric. Slow-mo at the peak of the movement catches the fabric billowing. The audience should feel the music through the editing even without sound."
    },
    {
        "category": "fashion", "energy": "medium", "pace": "steady",
        "hook": "luxury jewellery catch light on a turn",
        "strategy": "the glint is the cut point — as the light hits the jewel, cut to the next angle. Selective focus: jewellery sharp, background soft. Never wide: this is intimate. No fast text. A single price reveal animates in like a product card — restrained. Upscale instrumental, nothing with lyrics. End tight on the piece: if it's a necklace the final frame is the pendant alone."
    },
    {
        "category": "fashion", "energy": "medium", "pace": "steady",
        "hook": "ethnic wear haul with multiple looks",
        "strategy": "each look gets exactly 3-4 seconds: wide establishing, medium body, one detail. Clean wipe or match-cut transitions between looks. Text bubble appears bottom-left with item name and price — stays for 2 seconds, out cleanly. Warm golden grade consistent across all looks so they feel like a collection not random clips. End on the best look, slightly longer hold."
    },
    {
        "category": "fashion", "energy": "low", "pace": "slow",
        "hook": "silk or chiffon fabric texture in soft natural light",
        "strategy": "macro is mandatory: start so close the viewer can't tell what they're looking at, then pull back to reveal. Move at the speed of luxury — 3-4s per shot minimum. No hard cuts: every transition is a slow dissolve or a gentle wipe. Single warm grade, slight film grain. No loud text — if there is text it fades in like mist. The price appears last, alone."
    },
    {
        "category": "fashion", "energy": "low", "pace": "slow",
        "hook": "black and white portrait — traditional wear on modern woman",
        "strategy": "monochrome demands that every frame be compositionally perfect — no hiding behind colour. Long cinematic holds of 4-5 seconds. A single colour element (red bindi, gold earring) breaks the monochrome for one cut — that's the money shot. Let silence hold for 2 seconds before any music. This is art direction, not content creation."
    },
    {
        "category": "fashion", "energy": "high", "pace": "fast",
        "hook": "colour powder or smoke bomb with outfit reveal",
        "strategy": "VFX layer: real smoke blended with colour grade that matches the outfit. The reveal is the story — build 2 seconds of anticipation (haze, feet, swirling fabric) then snap cut to the full look. Speed ramp through the smoke. Hyper-saturated grade: this is sensory overload on purpose. Strobing effect on the reveal beat only. End on a still: the smoke clearing to reveal her face."
    },
    {
        "category": "fashion", "energy": "medium", "pace": "steady",
        "hook": "behind-the-scenes getting ready — dupatta drape, bindi placement",
        "strategy": "sequence the getting-ready in reverse reveal order: start with a detail (bindi mirror reflection) and build to the full look. Each step is 2-3 seconds. The editing tells a story: anticipation → reveal → reaction. Sound design: jewellery clink, bangles, the rustle of fabric. End on the subject seeing herself in the mirror — cut before she turns back to camera."
    },
    {
        "category": "fashion", "energy": "high", "pace": "fast",
        "hook": "ramp walk on runway or terrace — heel strike to camera stare",
        "strategy": "the heel strike is the metronome: cut every time a heel hits. Three-angle coverage minimum: feet, full body, face. Never let the walk slow in the edit even if the source is slow — speed ramp to maintain the energy. The final beat drop lands on the camera stare. Freeze for exactly 1 second after the stare then black."
    },

    # --- MEME (6) ---
    {
        "category": "meme", "energy": "high", "pace": "fast",
        "hook": "extreme reaction zoom with thud SFX on face",
        "strategy": "the comedic formula: setup (1.5s normal) → sudden zoom (0.2s) → hold on face (0.5s) → reaction SFX. The zoom must overshoot and snap back for maximum comedy. Cut density should feel almost random — the chaos IS the joke. Silence for exactly 1 frame before the punchline audio. Retrigger the zoom on any secondary reaction: the laugh loop is the goal."
    },
    {
        "category": "meme", "energy": "high", "pace": "fast",
        "hook": "rapid-fire greenscreen chaos with unexpected context",
        "strategy": "cut every frame at the punchline. The joke lands in the edit — bad timing kills memes. Loud unexpected audio triggers work best when the visual is completely deadpan. Screen shake only on the biggest moment, not throughout. The last cut should be the most unexpected — end on a hard cut to silence. Leave 0 breathing room: the joke should feel like it ambushed them."
    },
    {
        "category": "meme", "energy": "medium", "pace": "steady",
        "hook": "relatable text bubble over perfectly timed deadpan stare",
        "strategy": "the hold IS the joke — resist the urge to cut. Let the subject stare into the camera for an uncomfortably long time. Elevator music that's slightly too cheerful. The text appears after a beat, not immediately. Irony-heavy UI overlays that look like real interfaces. End abruptly — no fade, no resolution. The audience completes the joke themselves."
    },
    {
        "category": "meme", "energy": "medium", "pace": "steady",
        "hook": "character skit with jump-cut dialogue",
        "strategy": "jump-cut mid-sentence to compress time — the subject should feel like they're always mid-thought. Pop sound on each cut: not a transition, a punctuation mark. Keep each talking-head shot under 2 seconds. Break the 4th wall exactly once — that's the viral moment. End on something that makes no narrative sense: absurdist is rewatchable."
    },
    {
        "category": "meme", "energy": "low", "pace": "slow",
        "hook": "nihilistic void slow zoom on blurry abstract",
        "strategy": "this format survives on contrast: extremely slow editing in a world of fast content. The discomfort of the hold time IS the joke. Distorted dark ambient audio, barely audible. Extra slow zoom — so slow the viewer questions if it's moving. Visual grain and compression artifacts are aesthetic here. No resolution: cut to black while the viewer is still waiting for something to happen."
    },
    {
        "category": "meme", "energy": "low", "pace": "slow",
        "hook": "wholesome heartwarming moment with unexpected kindness",
        "strategy": "the edit should feel like it was made with care — warmth is earned through pacing not effects. Soft high-pitched music that doesn't overstay its welcome. Gentle fades. A single text line appears after the moment — the emotion should land before the words do. Pastel grade. End on a hold that runs 1 second too long: that slight awkwardness makes it feel real."
    },

    # --- PODCAST (6) ---
    {
        "category": "podcast", "energy": "high", "pace": "fast",
        "hook": "heated debate — both speakers talking over each other",
        "strategy": "this is a fight in the edit: rapid speaker switches, never stay on one face more than 1.5 seconds when tensions are high. Reaction shots are the gold — cut away from the speaker to the other face on the best lines. Dynamic subtitles that slam in like punches. Never cut in dead air: the edit should feel like it's barely keeping up with the argument. End on the best reaction face."
    },
    {
        "category": "podcast", "energy": "high", "pace": "fast",
        "hook": "outrageous guest reaction to unexpected question",
        "strategy": "the setup is invisible: the audience must not know the punchline is coming. Cut away from the host right before the question lands — show the guest's face as they process. The hold on the guest's face before they respond is worth more than the response. Sound-bite triggers: a laugh that sounds like a honk, an involuntary gasp. The clip ends at the peak of the reaction, never after."
    },
    {
        "category": "podcast", "energy": "medium", "pace": "steady",
        "hook": "quotable insight with animated side-text reveal",
        "strategy": "let the speaker finish the sentence before cutting — the edit respects the thought. Kinetic typography animates in word by word, not letter by letter (too slow). Slow zoom toward the speaker as the point lands: 10% zoom over 3 seconds. Subtitles are editorial, not transcription — highlight only the most quotable phrase. Professional audio, clean reverb removal. The clip should make someone want to screenshot it."
    },
    {
        "category": "podcast", "energy": "medium", "pace": "steady",
        "hook": "personal story intercut with matching b-roll",
        "strategy": "match cuts on nouns: they say 'hospital' — cut to a corridor. They say 'my mother' — cut to a close hand holding. Return to the speaker for the emotional peak — never have them off-screen when the voice cracks. The b-roll should feel discovered not stock. Steady vocal-driven pacing: the story sets the rhythm, not the music."
    },
    {
        "category": "podcast", "energy": "low", "pace": "slow",
        "hook": "deep philosophical moment in moody low-key lighting",
        "strategy": "the environment is a character: shadows, a single lamp, a coffee cup. Let the framing breathe. Slow cinematic push-ins: 0.5% zoom per second, nearly imperceptible. Stay on the speaker's eyes — that's where the truth is. No background music until minute two: silence creates intimacy. The clip ends on an incomplete thought — the audience finishes it in their head."
    },
    {
        "category": "podcast", "energy": "low", "pace": "slow",
        "hook": "emotional guest story — voice breaks on a revelation",
        "strategy": "the edit should feel invisible — as if someone pressed record and walked away. Long holds: 4-5 seconds on a face saying nothing. Soft fade to near-black on the hardest moment, then back. No effects, no text, no music under the break — just silence and breathing. The payoff is the recovery: end on their face finding composure. That's a save."
    },

    # --- TRAVEL (7) ---
    {
        "category": "travel", "energy": "high", "pace": "fast",
        "hook": "drone plunge off cliff into turquoise water",
        "strategy": "the anticipation is half the video: 2 seconds of cliff edge, wind audio, camera looking down — then the plunge. Speed ramp into the fall, normal through the water impact. High-frequency soundscape: wind → silence → splash. Rapid cuts underwater then surface to daylight. End on a wide shot that contextualises the scale. The sequence should make the viewer's stomach drop."
    },
    {
        "category": "travel", "energy": "high", "pace": "fast",
        "hook": "hyperlapse through neon-lit city streets at night",
        "strategy": "motion blur between cuts makes the speed feel physical. Cut every 0.8-1.2 seconds, always in motion never static. Electronic sync track with a hard tempo. Colour grade: push the neons, crush the blacks. Show one static moment — a single face in a window — to contrast the speed. That contrast is what makes the speed feel fast. End on a rooftop wide: the city beneath."
    },
    {
        "category": "travel", "energy": "medium", "pace": "steady",
        "hook": "coffee on a high-altitude balcony at sunrise",
        "strategy": "the establishing wide shot earns everything that follows. Let the sunrise build for 3 seconds before cutting. Sequence: wide environment → medium hands with cup → detail steam → wide again with their face. Lofi beat that starts quiet and builds over 10 seconds. Warm daylight grade: slightly overexposed to feel like memory. No text in the first 5 seconds. Let the place speak."
    },
    {
        "category": "travel", "energy": "medium", "pace": "steady",
        "hook": "vibrant street market — colour, crowd, food, craft",
        "strategy": "the edit is sensory journalism: show something you can almost smell or taste. Match cuts on colour (red chilli → red dupatta → red doorway). Cut on sounds in the ambient audio — a drumbeat, a vendor's call. Warm cultural grade. Steady journey pacing: 2 seconds per shot, building from chaos to intimacy. End on one person's face — from the crowd to the individual."
    },
    {
        "category": "travel", "energy": "low", "pace": "slow",
        "hook": "rain on jungle leaves in macro slow motion",
        "strategy": "the slowest cuts earn the biggest dopamine on rewatch. Each droplet impact is a micro-event: give it 2 seconds. ASMR sound design mixed to -18 LUFS: present but not intrusive. No music — let the rain be the soundtrack. Alternating macro (leaf level) and wide (canopy) keeps spatial awareness. End on the sound of rain continuing after the video ends: leave 0.5s of black with audio."
    },
    {
        "category": "travel", "energy": "low", "pace": "slow",
        "hook": "sunset silhouette over sand dunes — golden hour last light",
        "strategy": "this is a postcard. Every frame should be frameable. Ultra-long cross-fades: 1.5 second transitions. Single ambient soundscape, no beat. The silhouette moves only once — that movement after stillness is the whole video. Colour grade: push orange and teal separation. No text. The price of this video is the patience to make nothing happen beautifully."
    },
    {
        "category": "travel", "energy": "medium", "pace": "steady",
        "hook": "3D animated route map connecting multiple destinations",
        "strategy": "the map is a bridge between emotion and information. Open on a destination shot, cut to the map path reveal, cut back to the next destination. Path animation should feel like a story arc not a loading screen. Clean vector style, path draws at medium speed. Informative text overlays with flight time, distance. Music builds as the map extends. End on the final destination — wide establishing shot."
    },

    # --- PRODUCT (7) ---
    {
        "category": "product", "energy": "high", "pace": "fast",
        "hook": "water impact on tech device in 4K slow motion",
        "strategy": "the droplet is the star: macro lens, perfect lighting, 240fps. The product is revealed through the water — not before. Each droplet impact lands on a beat. High-end commercial grade: cool tones, crisp blacks. Never show the full product until 3 seconds in — the anticipation adds perceived value. End on a static hero shot: product alone, clean background, a single text reveal."
    },
    {
        "category": "product", "energy": "high", "pace": "fast",
        "hook": "tech device assembly with mechanical stop-motion",
        "strategy": "every component snap is a cut point. The assembly sequence should feel inevitable — you know where it's going but you can't look away. Metallic foley layered with an electronic score. Speed: fast but not so fast the viewer misses the engineering. End on the completed product powering on. The screen glow is the payoff — hold for 2 seconds."
    },
    {
        "category": "product", "energy": "medium", "pace": "steady",
        "hook": "tactile unboxing — texture, weight, first feel",
        "strategy": "the edit should feel like the viewer is doing the unboxing. Every reveal is a moment: lift the lid, fold back the tissue, see the product for the first time. Cut on reveal not before. ASMR foley: cardboard texture, paper rustle, the satisfying thud of the product settling. White-room aesthetic. Each detail shot earns 3 seconds. End on the product in natural hand use — not posed."
    },
    {
        "category": "product", "energy": "medium", "pace": "steady",
        "hook": "lifestyle use — product integrated into aspirational daily routine",
        "strategy": "the product should feel discovered not advertised. Show the user first, the product second. Cut: person reaching for it → product close-up → person using it → result on their face. The product makes their life fractionally better — show that fraction. Soft transition dissolves. Bright airy grade. Minimal typography. The product name appears once, at the end."
    },
    {
        "category": "product", "energy": "high", "pace": "fast",
        "hook": "holographic UI spec reveal — floating data over device",
        "strategy": "the CGI overlays must feel diegetic — as if they really exist. High-frequency camera pans between angles: never static when showing specs. Data layers animate in sequence, not all at once. Energetic tech score: high BPM, clean electronic. Colour grade: blue and white dominance. End on a spec + price reveal with the product centred. Clean. Confident."
    },
    {
        "category": "product", "energy": "medium", "pace": "steady",
        "hook": "split-screen before/after or product comparison",
        "strategy": "the dividing line between sides is active — use a wipe, not a static split. Show equivalent angles on both sides: same camera height, same framing. The inferior option should be shown first. Informative callout icons animate in with subtle spring physics. Trust-building pace: 2-3s per comparison point. Corporate clean aesthetic. End with a single recommendation, not a tie."
    },
    {
        "category": "product", "energy": "low", "pace": "slow",
        "hook": "luxury leather or precious material in cinematic shadow",
        "strategy": "shadow is a design element here not a lighting failure. The product emerges from darkness slowly — a 3-second reveal. Macro texture shots at f/1.8: the stitching, the grain, the sheen. Never more than 30% of the frame. Prestigious grade: deep blacks, warm highlights, slight desaturation. No foley — silence sells luxury. The price appears alone on a dark background. That's the close."
    },
]


def _build_document(entry: Dict[str, str]) -> str:
    # EXACT requested format for Chroma embedding
    text = f"{entry['category']} {entry['energy']} {entry['pace']} editing: {entry['strategy']}, hook: {entry['hook']}"
    return normalize_text(text)


def load_dataset(collection, clear: bool = True) -> None:
    """Load the hardcoded dataset into the given Chroma collection."""

    try:
        print("[DEBUG] Entered load_dataset")
        
        if clear:
            print("[DEBUG] Clearing existing collection content...")
            try:
                # Use a timeout-safe check for existing IDs
                existing = collection.get()
                old_ids = existing.get("ids", []) or []
                if old_ids:
                    print(f"[DEBUG] Removing {len(old_ids)} existing items...")
                    collection.delete(ids=old_ids)
                    print("[DEBUG] Clear complete.")
                else:
                    print("[DEBUG] Collection is already empty.")
            except Exception as e:
                print(f"[DEBUG] Non-critical error during clear: {e}")

        documents = []
        metadatas = []
        ids = []

        print(f"[DEBUG] Preparing {len(DATASET)} items for insertion...")
        # Ensure iteration is finite
        for idx, entry in enumerate(DATASET):
            doc = _build_document(entry)
            documents.append(doc)
            metadatas.append(entry)
            # Ensure unique strings for IDs
            unique_id = f"pattern-{idx}-{int(time.time())}"
            ids.append(unique_id)
            print(f"  [DEBUG] Item {idx} prepared: {entry['category']} (ID: {unique_id})")

        print("[DEBUG] Executing collection.upsert()...")
        print("WARNING: Chroma insertion taking too long might mean it's downloading the embedding model.")
        
        start_ts = time.time()
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        end_ts = time.time()
        
        print(f"Dataset loaded successfully in {end_ts - start_ts:.2f}s")
        print("Execution continuing...")

    except Exception as e:
        print(f"Dataset loading error: {e}")
        import traceback
        traceback.print_exc()
        # Ensure we don't block forever
        print("Continuing despite loading error (some features might be degraded).")