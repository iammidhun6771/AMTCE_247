import json
import os
import unittest
from unittest.mock import MagicMock, patch

from reused_content_analyzer import analyze_reused_video, get_gemini_client


class TestReusedContentAnalyzer(unittest.TestCase):

    def test_file_not_found(self):
        """Should raise FileNotFoundError if the video path does not exist."""
        with self.assertRaises(FileNotFoundError):
            analyze_reused_video("non_existent_file.mp4")

    @patch("reused_content_analyzer.analyzer.get_gemini_client")
    @patch("os.path.exists")
    def test_analyze_reused_video_success(self, mock_exists, mock_get_client):
        """Should successfully upload, analyze and clean up the video."""
        mock_exists.return_value = True

        # Mock genai Client and methods
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock files.upload
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "files/test-file-123"
        mock_uploaded_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test-file-123"
        mock_client.files.upload.return_value = mock_uploaded_file

        # Mock files.get to return ACTIVE state
        mock_file_info = MagicMock()
        mock_file_info.state.name = "ACTIVE"
        mock_client.files.get.return_value = mock_file_info

        # Mock models.generate_content response
        mock_response = MagicMock()
        expected_json = {
            "reused_content_risk": "medium",
            "risk_rationale": "High visual similarity to stock clips.",
            "transformation_strategies": [
                "Add a picture-in-picture commentary track",
                "Introduce narrative transitions"
            ],
            "creative_editing_suggestions": {
                "audio_narrative": "Record a custom educational voiceover",
                "visual_modifications": "Apply zoom adjustments",
                "pacing_changes": "Vary the playback speeds"
            }
        }
        mock_response.text = json.dumps(expected_json)
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        result = analyze_reused_video("mock_video.mp4")

        # Assertions
        self.assertEqual(result, expected_json)
        mock_client.files.upload.assert_called_once_with(file="mock_video.mp4")
        mock_client.files.get.assert_called_with(name="files/test-file-123")
        mock_client.models.generate_content.assert_called_once()
        mock_client.files.delete.assert_called_once_with(name="files/test-file-123")

    @patch("reused_content_analyzer.analyzer.get_gemini_client")
    @patch("os.path.exists")
    def test_analyze_reused_video_cleanup_on_error(self, mock_exists, mock_get_client):
        """Should attempt file cleanup even if model generation fails."""
        mock_exists.return_value = True

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "files/error-file-123"
        mock_client.files.upload.return_value = mock_uploaded_file

        mock_file_info = MagicMock()
        mock_file_info.state.name = "ACTIVE"
        mock_client.files.get.return_value = mock_file_info

        # Force generate_content to throw an exception
        mock_client.models.generate_content.side_effect = RuntimeError("API rate limit exceeded")

        with self.assertRaises(RuntimeError):
            analyze_reused_video("error_video.mp4")

        # Cleanup should still be called
        mock_client.files.delete.assert_called_once_with(name="files/error-file-123")


if __name__ == "__main__":
    unittest.main()
