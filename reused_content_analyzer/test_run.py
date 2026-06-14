import os
import sys
import logging
from pprint import pprint

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reused_content_analyzer.analyzer import analyze_reused_video

logging.basicConfig(level=logging.INFO)

def main():
    video_path = os.path.join("downloads", "Amy.mp4")
    if not os.path.exists(video_path):
        print(f"Error: Sample video {video_path} not found.")
        sys.exit(1)
        
    print(f"Starting analysis on {video_path}...")
    try:
        results = analyze_reused_video(video_path, model_name="gemini-2.5-flash")
        print("\n--- RESULTS ---")
        pprint(results)
    except Exception as e:
        print(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
