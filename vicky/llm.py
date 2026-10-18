"""LLM factory. Any OpenAI-compatible endpoint works (OpenRouter free models by default; Groq
or Gemini by changing .env). Responses are cached in SQLite so demo replays cost nothing."""
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
GOOGLE = "generativelanguage.googleapis.com"
# (default model, fallbacks) per provider. OpenRouter applies fallbacks server-side; for others the client does.
DEFAULTS = {
    # 0.5s for a simple reply vs ~30s queue for nemotron-3.5-lightning; free tier is 50 requests/day
    "openrouter": ("nvidia/nemotron-3-super-120b-a12b:free", "xingchen-agi/xing4.0-29b-a4b:free"),
    # Google AI Studio free tier. Flash models (3.5-3.8) allow only ~20 requests/day each; Flash-Lite ~500.
    # Measured on the real flows: 3.5-flash-lite ~3s, all JSON valid; 3.1-flash-lite slower; gemma ~25s.
    "google": ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite,gemma-4-26b-a4b-it"),
}


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


def _provider() -> str:
    return "google" if GOOGLE in os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL) else "openrouter"


def model_name() -> str:
    return os.getenv("LLM_MODEL", DEFAULTS[_provider()][0])


def fallback_models() -> list[str]:
    return [m for m in os.getenv("LLM_FALLBACK_MODELS", DEFAULTS[_provider()][1]).split(",") if m]


@lru_cache
def get_llm(temperature: float = 0.3, timeout: int = 30):
    """timeout is per call; raise it only for long documents (the prep pack)."""
    if os.getenv("LLM_CACHE", "1") == "1":
        set_llm_cache(SQLiteCache(database_path=str(ROOT / ".llm_cache.sqlite")))
    if _provider() == "openrouter":
        return _chat(model_name(), temperature, timeout)
    # client-side fallbacks: try the next model when one is overloaded or rate-limited
    primary, *rest = [model_name(), *fallback_models()]
    llm = _chat(primary, temperature, timeout)
    return llm.with_fallbacks([_chat(m, temperature, timeout) for m in rest]) if rest else llm


def _chat(model: str, temperature: float, timeout: int, cache: bool | None = None) -> ChatOpenAI:
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    extra_body = {}
    if "openrouter.ai" in base_url:
        if fallback_models():
            extra_body["models"] = [model, *fallback_models()]
        # Free models are reasoning models; hidden thinking added ~70s per call in testing. Off unless asked for.
        if os.getenv("LLM_REASONING", "off").lower() != "on":
            extra_body["reasoning"] = {"enabled": False}
    extra = {}
    if GOOGLE in base_url and model.startswith("gemini") and os.getenv("LLM_REASONING", "off").lower() != "on":
        # Gemini thinks by default (12s for a one-word reply on 3.8 flash). "low" is accepted by every Gemini
        # thinking model; "minimal" isn't, Pro models may reject "none", and Gemma rejects the parameter.
        extra["reasoning_effort"] = "low"
    return ChatOpenAI(
        base_url=base_url,
        api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        model=model,
        temperature=temperature,
        max_retries=1,  # fail fast: a stuck free-tier call used to hang for up to ~4.5 minutes
        timeout=timeout,
        extra_body=extra_body or None,
        default_headers={"HTTP-Referer": "https://juneanalytics.ai", "X-Title": "Vicky AI Pitch Coach"},
        cache=cache,
        **extra,
    )


def explain_error(e: Exception) -> str:
    """One plain sentence for the founder about why an AI call failed. The app appends what to do next."""
    text, kind = str(e), type(e).__name__
    low = text.lower()
    endpoint = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    if "429" in text or "ratelimit" in kind.lower() or "free-models-per-day" in low or "resource_exhausted" in low:
        return "The AI's free daily quota is used up or it's rate-limited."
    if "404" in text or "notfound" in kind.lower():
        return (f"The AI model \"{model_name()}\" isn't available at {endpoint}: LLM_MODEL in .env doesn't match "
                f"LLM_BASE_URL.")
    if "401" in text or "403" in text or "authentication" in kind.lower() or "permission" in kind.lower():
        return f"The API key was rejected by {endpoint}: check that the key in .env belongs to that provider."
    if "503" in text or "unavailable" in low or "overloaded" in low or "high demand" in low:
        return "The AI model is overloaded right now; try again in a minute."
    if "timeout" in kind.lower() or "timed out" in low:
        return "The AI model didn't reply in time."
    return f"The AI call failed ({kind})."


def check_connection() -> tuple[bool, str]:
    """Send one tiny request, bypassing the cache (a cached reply would falsely say the AI is reachable)."""
    if not configured():
        return False, "No API key in .env (LLM_API_KEY or OPENROUTER_API_KEY)."
    start = time.perf_counter()
    try:
        _chat(model_name(), 0, 30, cache=False).invoke("Reply with exactly: OK")
    except Exception as e:
        return False, explain_error(e)
    return True, f"Connected: {model_name()} replied in {time.perf_counter() - start:.1f}s."
