"""LLM factory. Any OpenAI-compatible endpoint works (OpenRouter free models by default; Groq
or Gemini by changing .env). Responses are cached in SQLite so demo replays cost nothing."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"  # 0.5s simple reply vs ~30s queue for 3.5-lightning
# OpenRouter tries these in order server-side if the primary model is rate limited or down
DEFAULT_FALLBACKS = "xingchen-agi/xing4.0-29b-a4b:free"


def clean(text: str) -> str:
    """Strip <think>...</think> blocks that some reasoning models (e.g. Nemotron) put in content."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    return re.sub(r"^.*?</think>", "", text, flags=re.S).strip()


def parse_json(text: str) -> dict | None:
    """First JSON object in a model reply (tolerates prose or ```json fences around it)."""
    text = clean(text)
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
        start = text.find("{", start + 1)
    return None


def configured() -> bool:
    return bool(os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY"))


def model_name() -> str:
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


@lru_cache
def get_llm(temperature: float = 0.3, timeout: int = 30) -> ChatOpenAI:
    """timeout is per call; raise it only for long documents (the prep pack)."""
    if os.getenv("LLM_CACHE", "1") == "1":
        set_llm_cache(SQLiteCache(database_path=str(ROOT / ".llm_cache.sqlite")))
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    extra_body = {}
    if "openrouter.ai" in base_url:
        fallbacks = [m for m in os.getenv("LLM_FALLBACK_MODELS", DEFAULT_FALLBACKS).split(",") if m]
        if fallbacks:
            extra_body["models"] = [model_name(), *fallbacks]
        # Free models are reasoning models; hidden thinking added ~70s per call in testing. Off unless asked for.
        if os.getenv("LLM_REASONING", "off").lower() != "on":
            extra_body["reasoning"] = {"enabled": False}
    return ChatOpenAI(
        base_url=base_url,
        api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        model=model_name(),
        temperature=temperature,
        max_retries=1,  # fail fast: a stuck free-tier call used to hang for up to ~4.5 minutes
        timeout=timeout,
        extra_body=extra_body or None,
        default_headers={"HTTP-Referer": "https://juneanalytics.ai", "X-Title": "Vicky AI Pitch Coach"},
    )
