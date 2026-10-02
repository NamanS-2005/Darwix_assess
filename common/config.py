"""Central configuration loaded from .env (repo root)."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip() or default   # empty value in .env = use default


GROQ_API_KEY = env("GROQ_API_KEY")
GEMINI_API_KEY = env("GEMINI_API_KEY")
LLM_PRIMARY = env("LLM_PRIMARY", "groq")

# Optional extra keys / providers (all OpenAI-compatible). Each adds its own quota to the fallback chain.
GROQ_API_KEY_2 = env("GROQ_API_KEY_2")
GEMINI_API_KEY_2 = env("GEMINI_API_KEY_2")
CEREBRAS_API_KEY = env("CEREBRAS_API_KEY")
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
OPENAI_API_KEY = env("OPENAI_API_KEY")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

MODELS = {
    "groq": {
        "agent": env("AGENT_MODEL_GROQ", "qwen/qwen3.8-27b,openai/gpt-oss-120b,openai/gpt-oss-20b"),
        "fast": env("FAST_MODEL_GROQ", "qwen/qwen3.8-27b,openai/gpt-oss-20b"),
        # simulated customers / judges use a different model (own 8k TPM bucket on the free tier, and no self-play bias)
        "sim": env("SIM_MODEL_GROQ", "openai/gpt-oss-120b,openai/gpt-oss-20b"),
        "signals": env("SIGNAL_MODEL_GROQ", "qwen/qwen3.8-27b,openai/gpt-oss-20b"),     # Q4 live signal tier
    },
    "gemini": {
        "agent": env("AGENT_MODEL_GEMINI", "gemini-3.5-flash,gemini-flash-lite-latest,gemini-3.1-flash-lite"),
        "fast": env("FAST_MODEL_GEMINI", "gemini-flash-lite-latest,gemini-3.1-flash-lite"),
        "sim": env("SIM_MODEL_GEMINI", "gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-3.5-flash"),
        "signals": env("SIGNAL_MODEL_GEMINI", "gemini-flash-lite-latest,gemini-3.1-flash-lite"),
    },
}
# Extra providers: second keys reuse the same model lists; others are configurable (comma-separated fallback order).
MODELS["groq2"] = dict(MODELS["groq"])
MODELS["gemini2"] = dict(MODELS["gemini"])
for _p, _default in (("cerebras", ""), ("openrouter", "qwen/qwen3.8-27b:free,google/gemma-4-31b-it:free"), ("openai", "")):
    _m = env(f"{_p.upper()}_MODELS", _default)
    MODELS[_p] = {t: env(f"{_p.upper()}_{t.upper()}_MODELS", _m) for t in ("agent", "fast", "sim", "signals")}

PROVIDERS = {  # name -> (api key, base url)
    "groq": (GROQ_API_KEY, "https://api.groq.com/openai/v1"),
    "groq2": (GROQ_API_KEY_2, "https://api.groq.com/openai/v1"),
    "cerebras": (CEREBRAS_API_KEY, "https://api.cerebras.ai/v1"),
    "openrouter": (OPENROUTER_API_KEY, "https://openrouter.ai/api/v1"),
    "openai": (OPENAI_API_KEY, "https://api.openai.com/v1"),
    "gemini": (GEMINI_API_KEY, "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "gemini2": (GEMINI_API_KEY_2, "https://generativelanguage.googleapis.com/v1beta/openai/"),
}
PROVIDER_ORDER = ["groq", "groq2", "cerebras", "openrouter", "openai", "gemini", "gemini2"]

EMBED_MODEL_GEMINI = env("EMBED_MODEL_GEMINI", "gemini-embedding-001")
ASR_MODEL = env("ASR_MODEL", "whisper-large-v3")
ASR_MODEL_FAST = env("ASR_MODEL_FAST", "whisper-large-v3-turbo")

VAPI_API_KEY = env("VAPI_API_KEY")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL").rstrip("/")
ESCALATION_WEBHOOK_URL = env("ESCALATION_WEBHOOK_URL")

APP_TZ = ZoneInfo(env("APP_TIMEZONE", "Asia/Kolkata"))


def now() -> datetime:
    return datetime.now(APP_TZ)
