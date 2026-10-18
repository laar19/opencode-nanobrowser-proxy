import json
import pytest
from fastapi.testclient import TestClient
import httpx
from unittest.mock import AsyncMock, patch

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import main as main_module
    from main import app, session_manager
    from session_manager import SessionManager
except (ImportError, ValueError):
    from opencode_proxy import main as main_module
    from opencode_proxy.main import app, session_manager
    from opencode_proxy.session_manager import SessionManager

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "endpoints" in data
    assert "api_key_configured" in data
    # Ensure raw API key is never in health check
    assert "sk-" not in json.dumps(data) or "..." in json.dumps(data)

def test_session_manager_stability():
    sm = SessionManager()

    # Initial conversation message
    conv_turn_1 = {
        "model": "deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": "You are a web assistant."},
            {"role": "user", "content": "Open python.org and read docs"},
        ],
    }
    session_1 = sm.get_or_create_session(body=conv_turn_1)
    assert session_1.startswith("ses_")

    # Turn 2: Assistant replied with a tool call and browser executed it
    conv_turn_2 = {
        "model": "deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": "You are a web assistant."},
            {"role": "user", "content": "Open python.org and read docs"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "open_tab"}}]},
            {"role": "tool", "tool_call_id": "call_1", "content": "Tab opened"},
        ],
    }
    session_2 = sm.get_or_create_session(body=conv_turn_2)
    # The session ID MUST be identical across multi-step turns of the same task!
    assert session_1 == session_2

    # Different conversation: should have a different session ID
    conv_different = {
        "model": "deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": "You are a web assistant."},
            {"role": "user", "content": "Search for latest news on Mars rover"},
        ],
    }
    session_diff = sm.get_or_create_session(body=conv_different)
    assert session_diff != session_1

    # Explicit session header provided: should be honored
    explicit_session = "ses_custom_nanobrowser_123"
    session_explicit = sm.get_or_create_session(explicit_header=explicit_session, body=conv_turn_1)
    assert session_explicit == explicit_session

def test_cors_preflight():
    response = client.options(
        "/v1/chat/completions",
        headers={
            "Origin": "chrome-extension://imbddededgmcgfhfpcjmijokokekbkal",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

@pytest.mark.asyncio
async def test_chat_completions_injection_and_forwarding():
    # Mock the upstream httpx client to inspect forwarded headers and body
    captured_request = {}

    async def mock_post(url, headers=None, json=None, **kwargs):
        captured_request["url"] = url
        captured_request["headers"] = headers
        captured_request["json"] = json
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "model": "deepseek-v4.1-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Mock success response"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    with patch.object(main_module.http_client, "post", side_effect=mock_post):
        payload = {
            "model": "deepseek-v4.1-flash",
            "messages": [{"role": "user", "content": "Test prompt"}],
            "stream": False,
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["choices"][0]["message"]["content"] == "Mock success response"

        # Verify critical headers injected by proxy
        assert captured_request["url"] == "https://opencode.ai/inference/go/openai/v1/chat/completions"
        assert "x-opencode-session" in captured_request["headers"]
        assert captured_request["headers"]["x-opencode-session"].startswith("ses_")
        assert captured_request["headers"]["User-Agent"] == "opencode-agent/1.0"
        assert "Authorization" in captured_request["headers"]

@pytest.mark.asyncio
async def test_models_forwarding():
    captured_request = {}

    async def mock_get(url, headers=None, **kwargs):
        captured_request["url"] = url
        captured_request["headers"] = headers
        return httpx.Response(
            status_code=200,
            json={
                "object": "list",
                "data": [
                    {"id": "deepseek-v4.1-flash", "object": "model"},
                    {"id": "deepseek-v4-pro", "object": "model"},
                ],
            },
        )

    with patch.object(main_module.http_client, "get", side_effect=mock_get):
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert captured_request["url"] == "https://opencode.ai/inference/go/v1/models"
        assert captured_request["headers"]["x-opencode-session"] == "ses_discovery"
        assert captured_request["headers"]["User-Agent"] == "opencode-agent/1.0"
