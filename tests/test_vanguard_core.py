import pytest
import os
import json
from unittest.mock import MagicMock, patch

# Save the original exists function before any mock/patch decorators run
real_exists = os.path.exists
from Intelligence_Modules.gemini_governor import GeminiGovernor
from claw_vanguard.vanguard_director import VanguardDirector
from claw_vanguard.tool_system import ErrorClassifier

def test_error_classification():
    assert ErrorClassifier.classify("unknown encoder 'libx264'") == "codec"
    assert ErrorClassifier.classify("Invalid duration found") == "timing"
    assert ErrorClassifier.classify("No such file or directory: 'input.mp4'") == "file"
    assert ErrorClassifier.classify("something weird happened") == "unknown"

@patch("requests.post")
def test_ollama_fallback(mock_post):
    # Mock Gemini Failure
    gov = GeminiGovernor()
    
    # Mock Ollama Success
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"response": "Local AI Response"}
    
    # Trigger fallback (by making gemini call fail and bypassing orchestra)
    from Intelligence_Modules.router_orchestra import orchestra
    with patch.object(orchestra, 'route', return_value=None):
        with patch.object(gov, 'get_available_model', return_value=None):
            result = gov.generate("reasoning", "test prompt")
            assert result == "Local AI Response"
            assert mock_post.called

@patch("Intelligence_Modules.gemini_governor.GeminiGovernor.generate")
@patch("claw_vanguard.vanguard_director.vanguard_tools.execute")
@patch("google.genai.Client")
@patch("os.path.exists")
@patch("os.path.getsize")
def test_director_turn_limit(mock_getsize, mock_exists, mock_client_class, mock_execute, mock_generate):
    director = VanguardDirector()
    
    # Mock exists check to return True when verifying the output file exists
    def side_effect_exists(path):
        if "clip.mp4" in str(path) or "output.mp4" in str(path):
            return True
        return real_exists(path)
    mock_exists.side_effect = side_effect_exists
    mock_getsize.return_value = 10 * 1024 * 1024 # 10 MB
    
    # Mock genai client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_file = MagicMock()
    mock_file.name = "mock_file"
    mock_file.uri = "https://gemini/file/mock_file"
    # Mock active state
    mock_state = MagicMock()
    mock_state.name = "ACTIVE"
    mock_file.state = mock_state
    
    mock_client.files.upload.return_value = mock_file
    mock_client.files.get.return_value = mock_file
    
    # Mock Successful Steps
    mock_generate.side_effect = [
        "Plan",        # Turn 1
        '{"ok": true, "reason": "Looks good", "confidence": 0.9}' # Turn 3
    ]
    
    # Mock compile_video result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output = "output.mp4"
    mock_result.error_type = None
    mock_execute.return_value = mock_result
    
    result = director.execute_mission("Fashion", "Test Request", input_paths=["clip.mp4"])
    
    assert result.success == True
    # Ensure mission_dashboard exists
    assert os.path.exists("logs/mission_dashboard.json")
    
    # Verify file upload and delete were called
    mock_client.files.upload.assert_called_once()
    mock_client.files.delete.assert_called_once_with(name="mock_file")

def test_vanguard_md_structure():
    assert os.path.exists("claw_vanguard/VANGUARD.md")
    with open("claw_vanguard/VANGUARD.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "Winning Styles" in content
        assert "Failed Patterns" in content
        assert "Rules" in content

@patch("Intelligence_Modules.gemini_governor.GeminiGovernor.begin_video_session")
@patch("Intelligence_Modules.gemini_governor.GeminiGovernor.generate")
@patch("claw_vanguard.vanguard_director.vanguard_tools.execute")
@patch("google.genai.Client")
@patch("os.path.exists")
@patch("os.path.getsize")
def test_director_repair_budget_reset(mock_getsize, mock_exists, mock_client_class, mock_execute, mock_generate, mock_begin_session):
    director = VanguardDirector()
    
    # Mock exists check
    def side_effect_exists(path):
        if "clip.mp4" in str(path) or "output.mp4" in str(path):
            return True
        return real_exists(path)
    mock_exists.side_effect = side_effect_exists
    mock_getsize.return_value = 10 * 1024 * 1024
    
    # Mock genai client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_file = MagicMock()
    mock_file.name = "mock_file"
    mock_file.uri = "https://gemini/file/mock_file"
    mock_state = MagicMock()
    mock_state.name = "ACTIVE"
    mock_file.state = mock_state
    mock_client.files.upload.return_value = mock_file
    mock_client.files.get.return_value = mock_file
    
    # Mock first compile output (success=True but fails visual audit ok=False)
    mock_result_1 = MagicMock()
    mock_result_1.success = True
    mock_result_1.output = "output.mp4"
    mock_result_1.error_type = None
    
    # Mock second compile output (repaired, success=True)
    mock_result_2 = MagicMock()
    mock_result_2.success = True
    mock_result_2.output = "output.mp4"
    mock_result_2.error_type = None
    
    mock_execute.side_effect = [mock_result_1, mock_result_2]
    
    # Mock generate to return a failed visual audit in Turn 3
    mock_generate.side_effect = [
        '{"ok": false, "reason": "Watermark detected", "adjustments": "Remove watermark", "confidence": 0.9}' # Turn 3 visual verify
    ]
    
    result = director.execute_mission("Fashion", "Test Request", input_paths=["clip.mp4"])
    
    # Ensure compile_video was executed twice (Turn 2, Turn 4)
    assert mock_execute.call_count == 2
    
    # Ensure begin_video_session was called twice (start of mission, and start of Turn 4 Repair)
    assert mock_begin_session.call_count == 2
    
    # First call uses original mission_id
    call_args_1 = mock_begin_session.call_args_list[0][0]
    # Second call uses retry mission_id
    call_args_2 = mock_begin_session.call_args_list[1][0]
    
    assert "retry_1" in call_args_2[0]
