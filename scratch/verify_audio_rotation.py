import sys
import os
import json
import logging

# Set up clean logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("verify_rotation")

# Add the project root to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def main():
    logger.info("Initializing AudioPoolManager...")
    from Audio_Modules.audio_pool_manager import AudioPoolManager
    
    # Initialize the pool manager
    apm = AudioPoolManager(base_dir="Original_audio")
    
    # Check metadata status
    metadata = apm._load_metadata()
    files = metadata.get("files", metadata)
    num_registered = len(files)
    logger.info(f"Number of registered audio files in metadata: {num_registered}")
    
    if num_registered < 70:
        logger.error(f"❌ Failed! Only registered {num_registered} files, expected >= 70.")
        sys.exit(1)
    
    logger.info("✅ All active files have been successfully registered in pool_metadata.json!")
    
    # Test selecting the best audio
    logger.info("Testing BGM selection (select_best_audio)...")
    selected_path = apm.select_best_audio(
        video_bpm=120.0,
        video_energy=0.8,
        exclude_filenames=set()
    )
    
    if not selected_path:
        logger.error("❌ Failed! No audio file was selected.")
        sys.exit(1)
        
    selected_name = os.path.basename(selected_path)
    logger.info(f"✅ Success! Selected BGM track: {selected_name}")
    
    # Confirm it was moved to cooldown
    cooldown_file = os.path.join("Original_audio", "cooldown", selected_name)
    if os.path.exists(cooldown_file):
        logger.info(f"✅ Success! Track correctly moved to cooldown: {cooldown_file}")
        
        # Clean up by moving it back to active for the user's workspace
        active_dest = os.path.join("Original_audio", "active", selected_name)
        os.rename(cooldown_file, active_dest)
        logger.info(f"Restored {selected_name} back to active/ for workspace cleanliness.")
        
        # Re-save metadata with usage count reset to 0 to keep the repository clean
        meta = apm._get_file_metadata(selected_name)
        if meta:
            meta["usage_count"] = 0
            meta["last_used"] = 0
            apm._save_metadata()
            logger.info("Reset usage count in metadata.")
    else:
        logger.error(f"❌ Failed! Selected file was not moved to cooldown.")
        sys.exit(1)
        
    logger.info("🎉 All audio rotation logic verification tests passed successfully!")

if __name__ == "__main__":
    main()
