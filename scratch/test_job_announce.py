import sys
import os
import time
import json
from unittest.mock import patch, MagicMock

# Adjust path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from Uploader_Modules.hotness_poll_engine import PollSchedulerDaemon, HotnessPollState

def test_job_announce():
    print("=== Testing job_announce() ===")
    
    # 1. Write a fresh schedule file
    os.makedirs("The_json", exist_ok=True)
    fresh_sched = {
        "session_date": "2026-06-04",
        "written_at": time.time(), # fresh
        "post_a": {"actress": "Disha Patani Test", "video_path": "downloads/mock_disha.mp4"},
        "post_b": {"actress": "Avneet Kaur Test", "video_path": "downloads/mock_avneet.mp4"}
    }
    with open("The_json/hotness_poll_schedule.json", "w", encoding="utf-8") as f:
        json.dump(fresh_sched, f, indent=2)

    # Mock broadcast and video send
    with patch("Uploader_Modules.hotness_poll_engine.broadcast") as mock_broadcast, \
         patch("Uploader_Modules.hotness_poll_engine._bot_send_video", return_value=True) as mock_send_video, \
         patch("Uploader_Modules.hotness_poll_engine.pick_two_reels", return_value=(None, None)) as mock_pick:

        print("\n--- Running with FRESH schedule JSON ---")
        PollSchedulerDaemon.job_announce()
        
        # Check output
        print("Broadcast calls count:", mock_broadcast.call_count)
        for call in mock_broadcast.call_args_list:
            print("Broadcasted Text sample:\n", call[0][0][:200] + "...")
        print("Video send calls count:", mock_send_video.call_count)
        for call in mock_send_video.call_args_list:
            print("Video Sent:", call[0][1], "caption:", call[1].get("caption", ""))

    # 2. Write a stale schedule file (>4 hours ago)
    stale_sched = {
        "session_date": "2026-06-04",
        "written_at": time.time() - 5 * 3600, # 5 hours ago (stale)
        "post_a": {"actress": "Stale Disha", "video_path": "downloads/stale_disha.mp4"},
        "post_b": {"actress": "Stale Avneet", "video_path": "downloads/stale_avneet.mp4"}
    }
    with open("The_json/hotness_poll_schedule.json", "w", encoding="utf-8") as f:
        json.dump(stale_sched, f, indent=2)

    with patch("Uploader_Modules.hotness_poll_engine.broadcast") as mock_broadcast, \
         patch("Uploader_Modules.hotness_poll_engine._bot_send_video", return_value=True) as mock_send_video, \
         patch("Uploader_Modules.hotness_poll_engine.pick_two_reels", return_value=("downloads/fallback_a.mp4", "downloads/fallback_b.mp4")) as mock_pick:

        print("\n--- Running with STALE schedule JSON ---")
        PollSchedulerDaemon.job_announce()
        
        print("pick_two_reels called:", mock_pick.called)
        print("Video send calls count:", mock_send_video.call_count)
        for call in mock_send_video.call_args_list:
            print("Video Sent:", call[0][1])

    # Clean up
    if os.path.exists("The_json/hotness_poll_schedule.json"):
        os.remove("The_json/hotness_poll_schedule.json")

if __name__ == "__main__":
    test_job_announce()
