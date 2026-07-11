import sys
from unittest.mock import MagicMock, patch
# Mock mistralai if not installed to prevent mock patch/import failure
try:
    import mistralai
except ImportError:
    sys.modules['mistralai'] = MagicMock()
    sys.modules['mistralai.client'] = MagicMock()

from connectors.groq_connector import call_groq
from connectors.mistral import call_mistral
from connectors.gemini import call_gemini
from connectors.qwen_hf import call_qwen
import os

@patch.dict(os.environ, {"GROQ_API_KEY": "test_key"})
@patch('connectors.groq_connector.OpenAI')
def test_groq_connector(mock_openai):
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.return_value.choices = [
        type('obj', (object,), {'message': type('obj', (object,), {'content': 'Test groq response'})})
    ]
    mock_client.chat.completions.create.return_value.usage = type('obj', (object,), {'total_tokens': 12})
    
    result = call_groq("Hello")
    assert result["answer"] == "Test groq response"
    assert result["tokens_used"] == 12

@patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
@patch('mistralai.client.Mistral')
def test_mistral_connector(mock_mistral):
    # Mocking the client structure
    mock_client = mock_mistral.return_value
    mock_client.chat.complete.return_value.choices = [
        type('obj', (object,), {'message': type('obj', (object,), {'content': 'Test mistral response'})})
    ]
    mock_client.chat.complete.return_value.usage = type('obj', (object,), {'total_tokens': 15})

    result = call_mistral("Hello")
    assert result["answer"] == "Test mistral response"
    assert result["tokens_used"] == 15

@patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
@patch('google.genai.Client')
def test_gemini_connector(mock_genai):
    mock_client = mock_genai.return_value
    mock_client.models.generate_content.return_value.text = "Test gemini response"
    
    result = call_gemini("Hello")
    assert result["answer"] == "Test gemini response"
    assert result["tokens_used"] == 0

@patch.dict(os.environ, {"HF_TOKEN": "test_key"})
@patch('connectors.qwen_hf.InferenceClient')
def test_qwen_connector(mock_hf):
    mock_client = mock_hf.return_value
    mock_client.chat.completions.create.return_value.choices = [
        type('obj', (object,), {'message': type('obj', (object,), {'content': 'Test qwen response'})})
    ]
    mock_client.chat.completions.create.return_value.usage = type('obj', (object,), {'total_tokens': 20})

    result = call_qwen("Hello")
    assert result["answer"] == "Test qwen response"
    assert result["tokens_used"] == 20
