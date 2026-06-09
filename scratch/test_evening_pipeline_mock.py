import sys
import os
import time
import hashlib
from unittest.mock import patch, MagicMock

# Adjust path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Actress_Modules.actress_scheduler import run_evening_pipeline
from Actress_Modules.actress_ledger import get_ledger

def test_mock_evening_pipeline():
    print("Starting mock evening pipeline test...")

    # Mock get_source_accounts to return a list of channels/accounts
    mock_accounts = ["disha_patani", "avneet_kaur", "kartik_aaryan"]

    # Mock reels returned by apify_scrape_actress_accounts
    mock_reels = [
        {
            "videoUrl": "http://mock-instagram/disha_reels/1.mp4",
            "shortcode": "DISHA123",
            "ownerUsername": "disha_patani",
            "isPinned": False
        },
        {
            "videoUrl": "http://mock-instagram/avneet_reels/2.mp4",
            "shortcode": "AVNEET456",
            "ownerUsername": "avneet_kaur",
            "isPinned": False
        },
        {
            "videoUrl": "http://mock-instagram/kartik_reels/3.mp4",
            "shortcode": "KARTIK789",
            "ownerUsername": "kartik_aaryan",
            "isPinned": False
        },
        {
            "videoUrl": "http://mock-instagram/disha_reels/pinned.mp4",
            "shortcode": "PINNED123",
            "ownerUsername": "disha_patani",
            "isPinned": True  # Should be skipped as pinned
        },
        {
            "videoUrl": "http://mock-instagram/avneet_reels/already_seen.mp4",
            "shortcode": "DZIVsrbDHI0",  # Seen in test_avoid_list
            "ownerUsername": "avneet_kaur",
            "isPinned": False  # Should be skipped as seen shortcode
        }
    ]

    sched_path = "The_json/hotness_poll_schedule.json"
    if os.path.exists(sched_path):
        try:
            os.remove(sched_path)
        except Exception:
            pass

    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)

    def mock_download_video(url):
        print(f"[MOCK] download_video called for url: {url}")
        url_hash = hashlib.md5(url.encode()).hexdigest()
        dest_path = f"downloads/mock_{url_hash}.mp4"
        with open(dest_path, "wb") as f:
            f.write(b"MOCK VIDEO BYTES " + url.encode())
        return dest_path, None

    def mock_resolve_channel(ig_id, reel):
        print(f"[MOCK] resolve_channel called for @{ig_id}")
        if ig_id == "disha_patani":
            return "General_Fallback", "Disha Patani", False
        elif ig_id == "avneet_kaur":
            return "General_Fallback", "Avneet Kaur", False
        else:
            return "Paparazzi", "Kartik Aaryan", False

    # Mock dependencies
    with patch("Actress_Modules.channel_router.get_source_accounts", return_value=mock_accounts), \
         patch("Download_Modules.apify_downloader.apify_scrape_actress_accounts", return_value=mock_reels), \
         patch("Download_Modules.downloader.download_video", side_effect=mock_download_video), \
         patch("Actress_Modules.channel_router.resolve_channel", side_effect=mock_resolve_channel), \
         patch("Actress_Modules.actress_scheduler._auto_publish_clip") as mock_auto_publish:

        # Run pipeline
        run_evening_pipeline()

    # Verify if schedule json was written
    if os.path.exists(sched_path):
        print("\nSuccess! hotness_poll_schedule.json was created.")
        with open(sched_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            print(json.dumps(data, indent=2))
    else:
        print("\nFailure: hotness_poll_schedule.json was not created.")

if __name__ == "__main__":
    test_mock_evening_pipeline()
