"""vicky.llm helpers the app relies on: plain-English errors and the connection check."""
import pytest

from vicky import llm


class FakeError(Exception):
    pass


class RateLimitError(Exception):
    pass


@pytest.mark.parametrize("error,expected", [
    (FakeError("Error code: 429 - Rate limit exceeded: free-models-per-day"), "free daily quota"),
    (RateLimitError("slow down"), "free daily quota"),
    (FakeError("Error code: 429 RESOURCE_EXHAUSTED"), "free daily quota"),
    (FakeError("Error code: 404 - models/x is not found"), "doesn't match LLM_BASE_URL"),
    (FakeError("Error code: 401 - Missing Authentication header"), "key was rejected"),
    (FakeError("Error code: 503 - This model is currently experiencing high demand"), "overloaded"),
    (TimeoutError("Request timed out."), "didn't reply in time"),
    (FakeError("something odd"), "failed (FakeError)"),
])
def test_explain_error(error, expected):
    msg = llm.explain_error(error)
    assert expected in msg and msg.endswith(".")


def test_check_connection_success(monkeypatch):
    class OK:
        def invoke(self, _):
            return "OK"

    monkeypatch.setattr(llm, "configured", lambda: True)
    monkeypatch.setattr(llm, "_chat", lambda *a, **kw: OK())
    ok, msg = llm.check_connection()
    assert ok and msg.startswith(f"Connected: {llm.model_name()} replied in")


def test_check_connection_bypasses_cache(monkeypatch):
    seen = {}

    def fake_chat(model, temperature, timeout, cache=None):
        seen["cache"] = cache
        raise FakeError("Error code: 401 - bad key")

    monkeypatch.setattr(llm, "configured", lambda: True)
    monkeypatch.setattr(llm, "_chat", fake_chat)
    ok, msg = llm.check_connection()
    assert not ok and "key was rejected" in msg and seen["cache"] is False


def test_check_connection_without_key(monkeypatch):
    monkeypatch.setattr(llm, "configured", lambda: False)
    assert llm.check_connection() == (False, "No API key in .env (LLM_API_KEY or OPENROUTER_API_KEY).")
