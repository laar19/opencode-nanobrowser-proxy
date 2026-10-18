import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "").strip()
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1").strip()
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))

# Upstream OpenCode endpoints
OPENCODE_CHAT_ENDPOINT = os.getenv(
    "OPENCODE_CHAT_ENDPOINT",
    "https://opencode.ai/inference/go/openai/v1/chat/completions",
).strip()

OPENCODE_MODELS_ENDPOINT = os.getenv(
    "OPENCODE_MODELS_ENDPOINT",
    "https://opencode.ai/inference/go/v1/models",
).strip()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-v4.1-flash").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def mask_key(key: str) -> str:
    """Mask key for safe logging: e.g. sk-abc...xyz"""
    if not key:
        return "<not set>"
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}...{key[-4:]}"
