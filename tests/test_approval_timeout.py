import os
import sys
import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path to enable local module imports
sys.path.append(os.getcwd())

from main import auto_approve_timer, user_sessions

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_auto_approve_timer_success():
    user_id = 999999
    approval_timestamp = time.time()
    
    # Initialize session
    user_sessions[user_id] = {
        "state": "WAITING_FOR_APPROVAL",
        "approval_timestamp": approval_timestamp
    }
    
    mock_update = MagicMock()
    mock_update.effective_user.id = user_id
    mock_context = MagicMock()
    
    with patch("main.APPROVAL_TIMEOUT_SECS", 0.01), \
         patch("main._perform_upload", new_callable=AsyncMock) as mock_upload, \
         patch("main.safe_reply", new_callable=AsyncMock) as mock_reply:
         
        await auto_approve_timer(user_id, mock_update, mock_context, approval_timestamp)
        
        mock_reply.assert_called_once()
        assert "Timeout Expired" in mock_reply.call_args[0][1]
        mock_upload.assert_called_once_with(mock_update, mock_context)
    
    # Cleanup
    user_sessions.pop(user_id, None)


@pytest.mark.anyio
async def test_auto_approve_timer_cancelled_by_state_change():
    user_id = 999998
    approval_timestamp = time.time()
    
    # Session state changed to WAITING_FOR_TITLE_EXPANSION (user replied/interacted)
    user_sessions[user_id] = {
        "state": "WAITING_FOR_TITLE_EXPANSION",
        "approval_timestamp": approval_timestamp
    }
    
    mock_update = MagicMock()
    mock_update.effective_user.id = user_id
    mock_context = MagicMock()
    
    with patch("main.APPROVAL_TIMEOUT_SECS", 0.01), \
         patch("main._perform_upload", new_callable=AsyncMock) as mock_upload, \
         patch("main.safe_reply", new_callable=AsyncMock) as mock_reply:
         
        await auto_approve_timer(user_id, mock_update, mock_context, approval_timestamp)
        
        # Verify it cancelled and did NOT upload/reply
        mock_reply.assert_not_called()
        mock_upload.assert_not_called()
        
    # Cleanup
    user_sessions.pop(user_id, None)


@pytest.mark.anyio
async def test_auto_approve_timer_cancelled_by_timestamp_mismatch():
    user_id = 999997
    approval_timestamp = time.time()
    
    # Session exists, but timestamp is newer (e.g. user processed a new video in the meantime)
    user_sessions[user_id] = {
        "state": "WAITING_FOR_APPROVAL",
        "approval_timestamp": approval_timestamp + 100.0
    }
    
    mock_update = MagicMock()
    mock_update.effective_user.id = user_id
    mock_context = MagicMock()
    
    with patch("main.APPROVAL_TIMEOUT_SECS", 0.01), \
         patch("main._perform_upload", new_callable=AsyncMock) as mock_upload, \
         patch("main.safe_reply", new_callable=AsyncMock) as mock_reply:
         
        await auto_approve_timer(user_id, mock_update, mock_context, approval_timestamp)
        
        # Verify it cancelled and did NOT upload/reply
        mock_reply.assert_not_called()
        mock_upload.assert_not_called()
        
    # Cleanup
    user_sessions.pop(user_id, None)


@pytest.mark.anyio
async def test_auto_approve_timer_cancelled_by_session_deletion():
    user_id = 999996
    approval_timestamp = time.time()
    
    # Session is completely deleted (e.g. user manually rejected/approved)
    if user_id in user_sessions:
        del user_sessions[user_id]
        
    mock_update = MagicMock()
    mock_update.effective_user.id = user_id
    mock_context = MagicMock()
    
    with patch("main.APPROVAL_TIMEOUT_SECS", 0.01), \
         patch("main._perform_upload", new_callable=AsyncMock) as mock_upload, \
         patch("main.safe_reply", new_callable=AsyncMock) as mock_reply:
         
        await auto_approve_timer(user_id, mock_update, mock_context, approval_timestamp)
        
        # Verify it cancelled and did NOT upload/reply
        mock_reply.assert_not_called()
        mock_upload.assert_not_called()
