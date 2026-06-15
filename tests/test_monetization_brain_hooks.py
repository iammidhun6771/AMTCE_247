import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Setup path for imports
sys.path.append(os.getcwd())

from Intelligence_Modules.monetization_brain import MonetizationStrategist
from Text_Modules.overlay_engine import VIRAL_HOOKS


class TestMonetizationBrainHooks:
    @patch("Text_Modules.overlay_engine._save_viral_hook_memory")
    @patch("Text_Modules.overlay_engine._load_viral_hook_memory")
    def test_gemini_generates_viral_hook(self, mock_load, mock_save):
        """Verify that when Gemini returns a viral hook, it is used."""
        mock_load.return_value = []
        brain = MonetizationStrategist()
        brain.router = MagicMock()
        
        # Mock Gemini response with custom viral_hook
        mock_response = {
            "items": [
                {
                    "item_name": "Red Cotton Saree",
                    "category": "Saree",
                    "confidence": 0.9,
                    "narration": {
                        "color": "red",
                        "garment_type": "saree",
                        "fit": "regular",
                        "material": "cotton",
                        "pattern": "plain",
                        "occasion": "party"
                    }
                }
            ],
            "generated_hashtags": ["#saree"],
            "generated_title": "Red Saree Dance",
            "telegram_hook": "Telegram Hook",
            "instagram_hook": "Instagram Hook",
            "youtube_hook": "Youtube Hook",
            "community_comment_hook": "Community Comment",
            "viral_hook": "Custom Gemini Hook 🥵🔥"
        }
        brain.router.generate.return_value = json.dumps(mock_response)
        
        res = brain.analyze_content(
            title="VIRAL Mrunal Saree Dance",
            duration=15.0,
            niche_category="fashion"
        )
        
        assert res["approved"] is True
        assert res["overlay_data"][0]["viral_hook"] == "Custom Gemini Hook 🥵🔥"
        
        # Verify that generate was called and prompt contains examples
        called_args = brain.router.generate.call_args[1]["prompt"]
        prompt_text = called_args[0] if isinstance(called_args, list) else called_args
        assert "viral_hook" in prompt_text
        assert "rotated examples" in prompt_text

    @patch("Text_Modules.overlay_engine._save_viral_hook_memory")
    @patch("Text_Modules.overlay_engine._load_viral_hook_memory")
    def test_gemini_missing_viral_hook_fallback(self, mock_load, mock_save):
        """Verify fallback to select_viral_hook if Gemini does not return viral_hook."""
        mock_load.return_value = []
        brain = MonetizationStrategist()
        brain.router = MagicMock()
        
        # Mock Gemini response WITHOUT viral_hook
        mock_response = {
            "items": [
                {
                    "item_name": "Red Cotton Saree",
                    "category": "Saree",
                    "confidence": 0.9,
                    "narration": {
                        "color": "red",
                        "garment_type": "saree",
                        "fit": "regular",
                        "material": "cotton",
                        "pattern": "plain",
                        "occasion": "party"
                    }
                }
            ],
            "generated_hashtags": ["#saree"],
            "generated_title": "Red Saree Dance",
            "telegram_hook": "Telegram Hook",
            "instagram_hook": "Instagram Hook",
            "youtube_hook": "Youtube Hook",
            "community_comment_hook": "Community Comment"
        }
        brain.router.generate.return_value = json.dumps(mock_response)
        
        res = brain.analyze_content(
            title="VIRAL Mrunal Saree Dance",
            duration=15.0,
            niche_category="fashion"
        )
        
        assert res["approved"] is True
        # Since it was missing, we fell back to select_viral_hook.
        hook_obtained = res["overlay_data"][0]["viral_hook"]
        assert len(hook_obtained) > 0
        assert "{name}" not in hook_obtained
