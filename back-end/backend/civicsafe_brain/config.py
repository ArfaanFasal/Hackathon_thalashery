import os
from pathlib import Path

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BASE_DIR / ".env")


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    # Latency: skip extra LLM pass on assistant replies (default off = faster)
    polish_chat: bool = _truthy("CIVIC_POLISH", "0")
    # Latency: skip OpenAI-generated greeting on session start (default on = faster)
    fast_opening: bool = _truthy("CIVIC_FAST_OPENING", "1")
    # Latency: Whisper only; set TRANSCRIBE_TRANSLATE=1 for Malayalam etc. → English pass
    transcribe_translate: bool = _truthy("TRANSCRIBE_TRANSLATE", "0")


settings = Settings()
