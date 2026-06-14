"""
reused_content_analyzer/analyzer.py
-----------------------------------
Takes a video path, uploads the entire video to Gemini via the File API,
and asks Gemini to generate transformation/originality strategies to comply
with YouTube's Reused Content Policy.
"""

import json
import logging
import os
import time
from typing import Any, Dict
from google import genai
from google.genai import types

logger = logging.getLogger("reused_content_analyzer")


def get_gemini_client() -> genai.Client:
    """Retrieve Gemini API key and return a genai Client."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        # Load from Credentials/.env as fallback
        from dotenv import load_dotenv

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, "Credentials", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError(
            "Gemini API key not found in environment variables or Credentials/.env"
        )

    return genai.Client(api_key=api_key)


def analyze_reused_video(
    video_path: str, model_name: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """Uploads video to Gemini File API and returns YouTube Reused Content strategies."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    client = get_gemini_client()

    logger.info(f"📤 Uploading video to Gemini File API: {video_path}")
    uploaded_file = client.files.upload(file=video_path)
    logger.info(f"✅ Upload successful. File Name: {uploaded_file.name}")

    # Wait for the file to be processed
    # Videos can take a few seconds to process on Google's servers before they can be queried
    logger.info("⏳ Waiting for video file processing status...")
    max_wait = 120
    start_time = time.time()
    while True:
        file_info = client.files.get(name=uploaded_file.name)
        if file_info.state.name == "ACTIVE":
            logger.info("❇️ File is active and ready for analysis.")
            break
        elif file_info.state.name == "FAILED":
            raise RuntimeError(
                f"File processing failed on Gemini servers: {file_info.error.message}"
            )
        elif time.time() - start_time > max_wait:
            # Attempt cleanup on timeout
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
            raise TimeoutError(
                "Timed out waiting for video processing on Gemini servers."
            )

        logger.info("...waiting 5 seconds...")
        time.sleep(5)

    prompt = """
    Analyze this video and provide specific, actionable transformation strategies to comply with the YouTube Reused Content policy. 
    Focus on how a creator can add significant educational, commentary, or creative value to transform this clip into original content.
    
    Your response must be a valid JSON object containing:
    {
      "reused_content_risk": "high | medium | low",
      "risk_rationale": "reason for the risk rating",
      "transformation_strategies": [
         "strategy 1",
         "strategy 2"
      ],
      "creative_editing_suggestions": {
         "audio_narrative": "suggestions for voiceover or narration overlay",
         "visual_modifications": "suggestions for visual edits, zoom, crops, transitions, or text overlays",
         "pacing_changes": "how to alter pacing or order of events"
      }
    }
    Return ONLY the raw JSON object. Do not wrap in markdown block formatting.
    """

    try:
        logger.info(f"🧠 Querying model {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        logger.info("✅ Analysis generation complete.")

        # Parse output
        result_text = response.text or ""
        # Handle potential markdown wrapping
        if result_text.startswith("```"):
            lines = result_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            result_text = "\n".join(lines).strip()

        result_data = json.loads(result_text)
        return result_data

    except Exception as e:
        logger.error(f"❌ Error during Gemini analysis: {e}")
        raise e
    finally:
        # Always clean up the uploaded file to free Google API storage
        try:
            logger.info(
                f"🗑️ Deleting uploaded file from Gemini storage: {uploaded_file.name}"
            )
            client.files.delete(name=uploaded_file.name)
            logger.info("🗑️ Cleanup successful.")
        except Exception as cleanup_err:
            logger.warning(
                f"⚠️ Cleanup failed for file {uploaded_file.name}: {cleanup_err}"
            )
