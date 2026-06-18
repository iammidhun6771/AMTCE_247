"""
hotness_poll_engine.py — AMTCE Hotness Poll System
====================================================
Replaces the old bid/deposit auction with a "Who's Hotter?" face-off where
users invest real ₹ on which post they think is hotter. Winners get a
proportional share of the losing side's pot.

Flow (daily, Mon–Sat):
  18:00 IST  → Announce face-off (2 reels posted)
  18:30 IST  → Poll opens — /vote A <amount> or /vote B <amount>
  20:45 IST  → War Mode alerts (15-min countdown)
  21:00 IST  → Poll closes, payouts calculated & announced

User commands:
  /vote A 100   — invest ₹100 on Post A being hotter
  /vote B 50    — invest ₹50 on Post B
  /mystats      — show your investment and live odds
  /pollstatus   — live vote counts and pot totals

Admin commands:
  /poll_start   — manually open poll
  /poll_stop    — manually close + settle poll
"""

import os
import json
import time
import logging
import threading
import urllib.request
import urllib.parse
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from contextlib import contextmanager

try:
    import schedule as _schedule
except ImportError:
    _schedule = None

logger = logging.getLogger("hotness_poll")
logger.setLevel(logging.INFO)

POLL_LEDGER_FILE   = "The_json/hotness_poll_ledger.json"
POLL_SCHEDULE_FILE = "The_json/hotness_poll_schedule.json"

# Minimum vote amount (₹)
MIN_VOTE_AMOUNT = 10.0

# Platform cut from the losing pot (%)
PLATFORM_CUT_PCT = 20.0

# Partial refund for losers (% of their investment returned)
LOSER_REFUND_PCT = 30.0


# ===========================================================================
# STATE
# ===========================================================================

class HotnessPollState:
    """
    Thread-safe singleton managing the lifecycle of one poll session.

    State schema:
    {
        "active": bool,
        "session_id": str,           # e.g. "2026-06-04"
        "post_a": {"label": str, "actress": str, "video_path": str},
        "post_b": {"label": str, "actress": str, "video_path": str},
        "votes": {
            "<user_id>": {
                "username": str,
                "side": "A" | "B",
                "amount": float,
                "verified": bool,
                "utr": str | null,
                "timestamp": float
            }
        },
        "pot_a": float,   # total verified ₹ on side A
        "pot_b": float,   # total verified ₹ on side B
        "winner_side": "A" | "B" | null,
        "settled": bool
    }
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    @contextmanager
    def safe_lock(self, timeout: float = 10.0):
        acquired = self._lock.acquire(timeout=timeout)
        try:
            if not acquired:
                raise TimeoutError("Poll system temporarily busy. Try again in a moment.")
            yield
        finally:
            if acquired:
                self._lock.release()

    def _init(self):
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(POLL_LEDGER_FILE):
            try:
                with open(POLL_LEDGER_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._blank_state()

    @staticmethod
    def _blank_state() -> dict:
        return {
            "active": False,
            "session_id": "",
            "post_a": {"label": "🔥 Post A", "actress": "", "video_path": ""},
            "post_b": {"label": "💥 Post B", "actress": "", "video_path": ""},
            "votes": {},
            "pot_a": 0.0,
            "pot_b": 0.0,
            "winner_side": None,
            "settled": False,
        }

    def save(self):
        os.makedirs(os.path.dirname(POLL_LEDGER_FILE), exist_ok=True)
        tmp = POLL_LEDGER_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp, POLL_LEDGER_FILE)

    # ---- pot helpers -------------------------------------------------------

    def _recalc_pots(self):
        """Recalculate pot_a / pot_b from verified votes. Must hold lock."""
        pot_a = pot_b = 0.0
        for v in self.state["votes"].values():
            if v.get("verified"):
                if v["side"] == "A":
                    pot_a += v["amount"]
                else:
                    pot_b += v["amount"]
        self.state["pot_a"] = pot_a
        self.state["pot_b"] = pot_b

    # ---- public API --------------------------------------------------------

    def register_vote(self, user_id: str, username: str, side: str, amount: float) -> str:
        """
        Stage 1: register intent before payment.
        Returns: "OK" or error string.
        """
        side = side.upper()
        if side not in ("A", "B"):
            return "❌ Invalid side. Use /vote A or /vote B."
        if amount < MIN_VOTE_AMOUNT:
            return f"❌ Minimum vote amount is ₹{MIN_VOTE_AMOUNT:.0f}."

        with self.safe_lock():
            if not self.state.get("active"):
                return "❌ No poll is active right now. Check back at 7 PM IST!"
            if self.state.get("settled"):
                return "❌ This poll has already been settled."

            uid = str(user_id)
            if uid in self.state["votes"]:
                existing = self.state["votes"][uid]
                if existing.get("verified"):
                    return (
                        f"✅ You already voted ₹{existing['amount']:.0f} for "
                        f"Post {existing['side']}. You can't change a verified vote."
                    )
                # Unverified → allow update
                self.state["votes"][uid] = {
                    "username": username,
                    "side": side,
                    "amount": amount,
                    "verified": False,
                    "utr": None,
                    "timestamp": time.time(),
                }
            else:
                self.state["votes"][uid] = {
                    "username": username,
                    "side": side,
                    "amount": amount,
                    "verified": False,
                    "utr": None,
                    "timestamp": time.time(),
                }
            self.save()
        return "OK"

    def verify_vote(self, user_id: str, utr: str, amount_paid: float) -> str:
        """
        Stage 2: Admin or Gemini-OCR confirms screenshot payment.
        """
        with self.safe_lock():
            uid = str(user_id)
            if uid not in self.state["votes"]:
                return "❌ No pending vote found for this user."
            vote = self.state["votes"][uid]
            if abs(vote["amount"] - amount_paid) > 2:
                return (
                    f"❌ Payment mismatch. Expected ₹{vote['amount']:.0f}, "
                    f"got ₹{amount_paid:.0f}."
                )
            vote["verified"] = True
            vote["utr"] = utr
            self._recalc_pots()
            self.save()
        return "OK"

    def get_live_status(self) -> dict:
        with self.safe_lock():
            votes_a = sum(1 for v in self.state["votes"].values() if v["side"] == "A" and v["verified"])
            votes_b = sum(1 for v in self.state["votes"].values() if v["side"] == "B" and v["verified"])
            return {
                "active": self.state["active"],
                "session_id": self.state["session_id"],
                "post_a_label": self.state["post_a"]["label"],
                "post_b_label": self.state["post_b"]["label"],
                "votes_a": votes_a,
                "votes_b": votes_b,
                "pot_a": self.state["pot_a"],
                "pot_b": self.state["pot_b"],
                "total_pot": self.state["pot_a"] + self.state["pot_b"],
            }

    def get_user_stats(self, user_id: str) -> Optional[dict]:
        with self.safe_lock():
            uid = str(user_id)
            v = self.state["votes"].get(uid)
            if not v:
                return None
            my_side_pot = self.state[f"pot_{v['side'].lower()}"]
            other_pot   = self.state["pot_b"] if v["side"] == "A" else self.state["pot_a"]
            # Expected winning if my side wins (proportional share of loser pot minus platform cut)
            loser_pool = other_pot * (1 - PLATFORM_CUT_PCT / 100) * (1 - LOSER_REFUND_PCT / 100)
            my_share   = (v["amount"] / my_side_pot * loser_pool) if my_side_pot > 0 else 0
            return {
                "side": v["side"],
                "amount": v["amount"],
                "verified": v["verified"],
                "expected_win": my_share + v["amount"],  # original back + winnings
            }


# ===========================================================================
# PAYOUT CALCULATOR
# ===========================================================================

class PollResultCalculator:
    """
    Determines the winning side and calculates payouts.

    Winning side = whichever side has MORE total verified ₹ invested.
    (More money = crowd believes more strongly in that side.)
    """

    @staticmethod
    def settle(state: HotnessPollState) -> dict:
        with state.safe_lock():
            pot_a = state.state["pot_a"]
            pot_b = state.state["pot_b"]

            if pot_a == 0 and pot_b == 0:
                state.state["settled"] = True
                state.state["active"] = False
                state.save()
                return {"status": "cancelled", "reason": "No verified votes."}

            # Tie: side with more individual voters wins; if still equal → A
            if pot_a >= pot_b:
                winner_side = "A"
                loser_pot   = pot_b
                winner_label = state.state["post_a"]["label"]
            else:
                winner_side = "B"
                loser_pot   = pot_a
                winner_label = state.state["post_b"]["label"]

            platform_take    = loser_pot * (PLATFORM_CUT_PCT / 100)
            loser_refund_pool = loser_pot * (LOSER_REFUND_PCT / 100)
            winner_prize_pool = loser_pot - platform_take - loser_refund_pool

            # Per-winner payout (proportional to their investment)
            winner_pot = pot_a if winner_side == "A" else pot_b
            payouts = []
            for uid, v in state.state["votes"].items():
                if not v.get("verified"):
                    continue
                if v["side"] == winner_side:
                    share = (v["amount"] / winner_pot) * winner_prize_pool if winner_pot > 0 else 0
                    payouts.append({
                        "user_id": uid,
                        "username": v["username"],
                        "side": v["side"],
                        "invested": v["amount"],
                        "payout": round(v["amount"] + share, 2),
                        "status": "winner",
                    })
                else:
                    refund = round(v["amount"] * (LOSER_REFUND_PCT / 100), 2)
                    payouts.append({
                        "user_id": uid,
                        "username": v["username"],
                        "side": v["side"],
                        "invested": v["amount"],
                        "payout": refund,
                        "status": "loser_refund",
                    })

            state.state["winner_side"]  = winner_side
            state.state["settled"]      = True
            state.state["active"]       = False
            state.save()

        return {
            "status": "success",
            "winner_side": winner_side,
            "winner_label": winner_label,
            "pot_a": pot_a,
            "pot_b": pot_b,
            "platform_revenue": round(platform_take, 2),
            "payouts": payouts,
        }


# ===========================================================================
# TELEGRAM HELPERS
# ===========================================================================

def _bot_send(chat_id: str, text: str, parse_mode: str = "HTML"):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return
    def _bg():
        try:
            url  = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id, "text": text, "parse_mode": parse_mode
            }).encode()
            urllib.request.urlopen(url, data=data, timeout=10)
        except Exception as e:
            logger.error("Telegram send error: %s", e)
    threading.Thread(target=_bg, daemon=True).start()


def _bot_send_video(chat_id: str, video_path: str, caption: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id or not os.path.exists(video_path):
        return False
    try:
        boundary = "AMTCE_POLL_BOUNDARY"
        with open(video_path, "rb") as vf:
            video_data = vf.read()
        fname = os.path.basename(video_path)
        body  = b""
        for name, value in [("chat_id", chat_id), ("caption", caption), ("parse_mode", "HTML")]:
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{name}"\r\n\r\n{value}\r\n'
            ).encode()
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="video"; filename="{fname}"\r\nContent-Type: video/mp4\r\n\r\n'
        ).encode() + video_data + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        logger.error("send_video error: %s", e)
        return False


def _group_id() -> str:
    return os.getenv("TELEGRAM_GROUP_ID", os.getenv("TELEGRAM_ADMIN_ID", ""))


def _admin_id() -> str:
    return os.getenv("TELEGRAM_ADMIN_ID", "")


def broadcast(msg: str, admin_only: bool = False):
    cid = _admin_id() if admin_only else _group_id()
    _bot_send(cid, msg)


# ===========================================================================
# REEL PICKER
# ===========================================================================

def pick_two_reels() -> Tuple[Optional[str], Optional[str]]:
    """
    Pick two distinct actress reels from the output ledger.
    Returns (path_a, path_b) — either may be None if not enough clips.
    """
    ledger_path = "The_json/output_batch_state.json"
    candidates: List[Tuple[str, str, float]] = []  # (actress, path, updated_at)

    if os.path.exists(ledger_path):
        try:
            with open(ledger_path) as f:
                ledger = json.load(f)
            for actress, data in ledger.items():
                updated_at = data.get("updated_at", 0)
                for fpath in data.get("files", []):
                    if os.path.exists(fpath):
                        candidates.append((actress, fpath, updated_at))
        except Exception:
            pass

    # Also scan Processed Shorts
    ps_dir = "Processed Shorts"
    if os.path.isdir(ps_dir):
        for fname in os.listdir(ps_dir):
            if fname.lower().endswith(".mp4"):
                fpath = os.path.join(ps_dir, fname)
                candidates.append((fname.split("_")[0], fpath, os.path.getmtime(fpath)))

    if not candidates:
        return None, None

    # Sort newest first, deduplicate by actress
    candidates.sort(key=lambda x: x[2], reverse=True)
    seen_actresses: set = set()
    unique: List[Tuple[str, str, float]] = []
    for actress, path, ts in candidates:
        if actress not in seen_actresses:
            seen_actresses.add(actress)
            unique.append((actress, path, ts))
        if len(unique) >= 2:
            break

    if len(unique) == 0:
        return None, None
    if len(unique) == 1:
        return unique[0][1], None

    return unique[0][1], unique[1][1]


# ===========================================================================
# SCHEDULER DAEMON
# ===========================================================================

class PollSchedulerDaemon:
    """Daily face-off scheduler."""

    _thread: Optional[threading.Thread] = None
    _stop   = threading.Event()

    @classmethod
    def start_background_polling(cls):
        if cls._thread and cls._thread.is_alive():
            return
        cls._stop.clear()
        cls._thread = threading.Thread(target=cls._run, daemon=True, name="HotnessPollDaemon")
        cls._thread.start()
        logger.info("🔥 HotnessPollDaemon started.")

    @classmethod
    def _run(cls):
        if _schedule is None:
            logger.error("❌ 'schedule' package not available — HotnessPollDaemon disabled.")
            return

        _schedule.every().day.at("13:30").do(cls.job_open_poll)  # 7:00 PM IST — poll opens
        _schedule.every().day.at("15:30").do(cls.job_close_poll) # 9:00 PM IST — poll closes

        while not cls._stop.is_set():
            _schedule.run_pending()
            time.sleep(30)

    # ---- scheduled jobs ---------------------------------------------------

    @classmethod
    def job_open_poll(cls):
        """7 PM IST — Pick two reels, open the poll, post both videos, send ONE message."""
        if datetime.now().weekday() == 6:
            return  # Skip Sunday

        poll = HotnessPollState()

        # --- Pick contenders (schedule JSON first, fallback to ledger) ---
        path_a = path_b = actress_a = actress_b = None

        if os.path.exists(POLL_SCHEDULE_FILE):
            try:
                with open(POLL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    sched = json.load(f)
                if time.time() - sched.get("written_at", 0) < 4 * 3600:
                    post_a = sched.get("post_a", {})
                    post_b = sched.get("post_b", {})
                    path_a    = post_a.get("video_path")
                    actress_a = post_a.get("actress")
                    path_b    = post_b.get("video_path")
                    actress_b = post_b.get("actress")
                    logger.info("[POLL] Loaded schedule: A=%s B=%s", actress_a, actress_b)
            except Exception as e:
                logger.error("[POLL] Schedule read error: %s", e)

        if not path_a or not path_b:
            fb_a, fb_b = pick_two_reels()
            if not path_a:
                path_a    = fb_a
                actress_a = os.path.splitext(os.path.basename(path_a))[0].split("_")[0] if path_a else "Actress A"
            if not path_b:
                path_b    = fb_b
                actress_b = os.path.splitext(os.path.basename(path_b))[0].split("_")[0] if path_b else "Actress B"

        # --- Reset state and open ---
        with poll.safe_lock():
            poll.state.update({
                "session_id": datetime.now().strftime("%Y-%m-%d"),
                "post_a": {"label": f"A: {actress_a}", "actress": actress_a or "", "video_path": path_a or ""},
                "post_b": {"label": f"B: {actress_b}", "actress": actress_b or "", "video_path": path_b or ""},
                "votes": {}, "pot_a": 0.0, "pot_b": 0.0,
                "winner_side": None, "settled": False, "active": True,
            })
            poll.save()

        upi_id = os.getenv("UPI_ID", "your-upi@bank")

        # --- Post both videos first (so the message lands after) ---
        if path_a and os.path.exists(path_a):
            _bot_send_video(_group_id(), path_a, caption=f"Option A — {actress_a}")
        if path_b and os.path.exists(path_b):
            _bot_send_video(_group_id(), path_b, caption=f"Option B — {actress_b}")

        # --- ONE clean poll message ---
        msg = (
            f"🗳️ <b>Who's hotter? Vote now! (7 PM – 9 PM only)</b>\n\n"
            f"Option A — <b>{actress_a}</b>\n"
            f"Option B — <b>{actress_b}</b>\n\n"
            f"Reply with /vote A or /vote B and the amount (min ₹{MIN_VOTE_AMOUNT:.0f})\n"
            f"Example: <code>/vote A 50</code>\n\n"
            f"Pay to UPI: <code>{upi_id}</code> then send screenshot here.\n"
            f"Winners split the losing pot. Poll closes at 9 PM."
        )
        broadcast(msg)



    @classmethod
    def job_close_poll(cls):
        """9 PM IST — Settle and post ONE result message."""
        if datetime.now().weekday() == 6:
            return
        poll   = HotnessPollState()
        result = PollResultCalculator.settle(poll)

        if result["status"] == "cancelled":
            broadcast("Poll closed. No verified votes tonight.")
            return

        winner_label = result["winner_label"]
        payouts = result["payouts"]
        winners = [p for p in payouts if p["status"] == "winner"]
        winner_names = ", ".join(f"@{p['username']}" for p in winners) or "—"

        msg = (
            f"Poll closed. <b>{winner_label}</b> wins!\n\n"
            f"Winners: {winner_names}\n"
            f"Payouts will be sent via UPI within 24 hours."
        )
        broadcast(msg)
        broadcast(
            f"SETTLE: {len(payouts)} payouts. Revenue ₹{result['platform_revenue']:.2f}",
            admin_only=True
        )

    # ---- manual triggers (for run_ci_mode / admin commands) ---------------

    @classmethod
    def trigger_announce(cls):
        pass  # Announce step removed — open poll does everything at 7 PM

    @classmethod
    def trigger_open(cls):
        cls.job_open_poll()

    @classmethod
    def trigger_close(cls):
        cls.job_close_poll()


# ===========================================================================
# PAYMENT VERIFICATION (Gemini Vision OCR — reused from auction engine)
# ===========================================================================

def verify_payment_screenshot(image_path: str) -> dict:
    """
    Use Gemini Vision to extract UTR + amount from a UPI payment screenshot.
    Returns {"status": "success", "utr": str, "amount": float} or {"status": "error", ...}
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or not os.path.exists(image_path):
        return {"status": "error", "message": "Missing API key or image path."}
    try:
        try:
            import google.generativeai as genai
        except ImportError:
            import google.genai as genai
        from PIL import Image
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Extract UPI payment details from this screenshot. "
            "Return ONLY valid JSON: "
            '{"utr_number": "string", "amount": float, "payer_name": "string"}'
        )
        img = Image.open(image_path)
        resp = model.generate_content([prompt, img])
        raw = resp.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        data["status"] = "success"
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}
