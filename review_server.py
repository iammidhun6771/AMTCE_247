"""
review_server.py — AMTCE Live Editorial Interruption Server
=============================================================
Flask backend that powers the AMTCE Content Studio Panel.

Run this alongside main.py to enable editorial review mode:
    python review_server.py

Endpoints:
  GET  /                      — Serve the Studio UI
  GET  /api/review-queue      — All clips currently awaiting review
  GET  /api/status            — AMTCE health stats
  POST /api/approve/<id>      — Approve clip with optional edits
  POST /api/reject/<id>       — Reject and delete clip
  GET  /api/logs              — SSE stream of live AMTCE log lines
  GET  /api/video/<filename>  — Serve video file for preview

ENV Flags (Credentials/.env):
  EDITORIAL_REVIEW_MODE=on    — Clips pause for review before publish (default: off)
  STUDIO_PORT=7862            — Port for the Studio Panel server (default: 7862)
"""

from __future__ import annotations

import glob
import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_file,
    send_from_directory,
)

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv("Credentials/.env", override=False)
except ImportError:
    pass

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO_ROOT         = os.path.dirname(os.path.abspath(__file__))
REVIEW_QUEUE_FILE  = os.path.join(_REPO_ROOT, "review_queue.json")
PUBLISH_QUEUE_FILE = os.path.join(_REPO_ROOT, "publish_queue.json")
LOG_FILE           = os.path.join(_REPO_ROOT, "logs", "amtce_main.log")

# ── Config ────────────────────────────────────────────────────────────────────
STUDIO_PORT = int(os.getenv("STUDIO_PORT", "7862"))

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_server")

# SSE broadcast queue (all connected clients share this)
_sse_queue: queue.Queue = queue.Queue(maxsize=500)

# ── Review Queue helpers ──────────────────────────────────────────────────────

def _load_review_queue() -> list:
    if not os.path.exists(REVIEW_QUEUE_FILE):
        return []
    try:
        with open(REVIEW_QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_review_queue(queue_data: list) -> None:
    with open(REVIEW_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2)


def _get_item(review_id: str):
    q = _load_review_queue()
    for item in q:
        if item.get("id") == review_id:
            return item, q
    return None, q


# ── Log tail → SSE ───────────────────────────────────────────────────────────

def _tail_log_file():
    """Background thread: tail the AMTCE log file and push lines to SSE queue."""
    # Wait for log file to appear
    while not os.path.exists(LOG_FILE):
        time.sleep(2)

    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        # Jump to end of file
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                line = line.rstrip()
                if line:
                    try:
                        _sse_queue.put_nowait(line)
                    except queue.Full:
                        pass  # Drop oldest if buffer full
            else:
                time.sleep(0.2)


threading.Thread(target=_tail_log_file, daemon=True, name="LogTailer").start()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the Studio UI HTML."""
    panel_path = os.path.join(_REPO_ROOT, "amtce_studio_panel.html")
    if os.path.exists(panel_path):
        return send_file(panel_path)
    return "<h1>amtce_studio_panel.html not found</h1><p>Place it next to review_server.py</p>", 404


@app.route("/api/review-queue")
def get_review_queue():
    """Return the full review queue with clip metadata."""
    items = _load_review_queue()
    # Add file-exists check to each item
    for item in items:
        vp = item.get("video_path", "")
        if not os.path.isabs(vp):
            vp = os.path.join(_REPO_ROOT, vp)
        item["file_exists"] = os.path.exists(vp)
    return jsonify(items)


@app.route("/api/status")
def get_status():
    """Return AMTCE system health and queue stats."""
    review_q  = _load_review_queue()
    publish_q = []
    if os.path.exists(PUBLISH_QUEUE_FILE):
        try:
            with open(PUBLISH_QUEUE_FILE, "r", encoding="utf-8") as f:
                publish_q = json.load(f)
        except Exception:
            pass

    pending   = [i for i in review_q if i.get("status") == "PENDING_REVIEW"]
    approved  = [i for i in review_q if i.get("status") == "APPROVED"]
    rejected  = [i for i in review_q if i.get("status") == "REJECTED"]

    # Read EDITORIAL_REVIEW_MODE live from .env
    editorial_mode = os.getenv("EDITORIAL_REVIEW_MODE", "off").lower() in ("on", "yes", "true", "1")

    return jsonify({
        "editorial_review_mode": editorial_mode,
        "review_queue": {
            "total":    len(review_q),
            "pending":  len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
        },
        "publish_queue_depth": len(publish_q),
        "send_to_tiktok": os.getenv("SEND_TO_TIKTOK", "off").lower() in ("on", "yes", "true", "1"),
        "send_to_youtube": True,  # Always on
        "send_to_instagram": True,
        "server_time": int(time.time()),
    })


@app.route("/api/approve/<review_id>", methods=["POST"])
def approve_clip(review_id: str):
    """
    Approve a clip for publishing, with optional edits.
    Body (JSON, all optional):
      {
        "title": "...",
        "caption": "...",
        "hashtags": "...",
        "platforms": {"youtube": true, "instagram": true, "tiktok": false}
      }
    """
    item, q = _get_item(review_id)
    if not item:
        return jsonify({"error": f"Item {review_id} not found"}), 404

    body = request.get_json(silent=True) or {}

    # Apply edits
    if "title"    in body: item["title"]    = body["title"]
    if "caption"  in body: item["caption"]  = body["caption"]
    if "hashtags" in body: item["hashtags"] = body["hashtags"]
    if "platforms" in body: item["platforms"] = body["platforms"]

    item["status"]      = "APPROVED"
    item["approved_at"] = int(time.time())

    _save_review_queue(q)

    # Push SSE notification
    try:
        _sse_queue.put_nowait(f"✅ [STUDIO] Clip APPROVED: {item.get('actress_title', review_id)}")
    except queue.Full:
        pass

    logger.info("✅ [STUDIO] Approved: %s", review_id)
    return jsonify({"status": "approved", "id": review_id})


@app.route("/api/reject/<review_id>", methods=["POST"])
def reject_clip(review_id: str):
    """Reject a clip — marks it REJECTED and deletes the video file."""
    item, q = _get_item(review_id)
    if not item:
        return jsonify({"error": f"Item {review_id} not found"}), 404

    # Delete the actual video file
    vp = item.get("video_path", "")
    if not os.path.isabs(vp):
        vp = os.path.join(_REPO_ROOT, vp)
    deleted = False
    if os.path.exists(vp):
        try:
            os.remove(vp)
            deleted = True
            logger.info("🗑️ [STUDIO] Deleted rejected clip: %s", vp)
        except Exception as e:
            logger.warning("⚠️ [STUDIO] Could not delete clip: %s", e)

    item["status"]      = "REJECTED"
    item["rejected_at"] = int(time.time())
    _save_review_queue(q)

    try:
        _sse_queue.put_nowait(f"🗑️ [STUDIO] Clip REJECTED: {item.get('actress_title', review_id)}")
    except queue.Full:
        pass

    logger.info("🗑️ [STUDIO] Rejected: %s (deleted=%s)", review_id, deleted)
    return jsonify({"status": "rejected", "id": review_id, "file_deleted": deleted})


@app.route("/api/logs")
def stream_logs():
    """Server-Sent Events stream of live AMTCE log lines."""
    def generate():
        yield "data: 🎬 AMTCE Studio Panel connected — live log stream active\n\n"
        while True:
            try:
                line = _sse_queue.get(timeout=15)
                # Escape for SSE
                safe_line = line.replace("\n", " ").replace("\r", "")
                yield f"data: {safe_line}\n\n"
            except queue.Empty:
                # Heartbeat to keep connection alive
                yield ": heartbeat\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/video/<path:filename>")
def serve_video(filename: str):
    """Serve a video file from the repo root for preview in the UI."""
    # Security: only serve .mp4 files from known safe directories
    safe_dirs = [
        "Processed Shorts",
        "downloads",
        "First_Shots",
        "Influencer_Output",
        "temp",
    ]
    for safe_dir in safe_dirs:
        candidate = os.path.join(_REPO_ROOT, safe_dir, filename)
        if os.path.exists(candidate) and filename.lower().endswith(".mp4"):
            return send_file(candidate, mimetype="video/mp4")

    # Try absolute lookup from repo root
    candidate = os.path.join(_REPO_ROOT, filename)
    if os.path.exists(candidate) and filename.lower().endswith(".mp4"):
        return send_file(candidate, mimetype="video/mp4")

    return jsonify({"error": "Video not found"}), 404


# ── CORS (so GitHub Pages static UI can talk to local server) ────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return "", 200


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║        🎬  AMTCE CONTENT STUDIO PANEL SERVER            ║
╠══════════════════════════════════════════════════════════╣
║  Studio UI  → http://localhost:{STUDIO_PORT}                   ║
║  Review API → http://localhost:{STUDIO_PORT}/api/review-queue  ║
║  Log Stream → http://localhost:{STUDIO_PORT}/api/logs          ║
╠══════════════════════════════════════════════════════════╣
║  Set EDITORIAL_REVIEW_MODE=on in Credentials/.env       ║
║  to pause clips for review before auto-publish fires.   ║
╚══════════════════════════════════════════════════════════╝
""")
    app.run(
        host="0.0.0.0",
        port=STUDIO_PORT,
        debug=False,
        threaded=True,
        use_reloader=False,
    )
