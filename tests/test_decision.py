"""Ask Vicky's hierarchical decision model: policy gate, intents, plan validation, and the full graph
with a fake LLM (no network, no API key)."""
import json
from pathlib import Path

import pytest
from langchain_core.globals import set_llm_cache
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from vicky import decision
from vicky.graphs import coach

ROOT = Path(__file__).resolve().parent.parent


# --- Level 1: policy gate --------------------------------------------------------------------

@pytest.mark.parametrize("q,rule", [
    ("What valuation should we raise at?", "valuation"),
    ("How much is Tidewell worth?", "valuation"),
    ("What's a fair valuation for us?", "valuation"),
    ("Should I invest in Tidewell?", "investment_advice"),
    ("Would you invest?", "investment_advice"),
    ("Should we accept the term sheet?", "investment_advice"),
    ("What is Jobber's churn?", "competitor_data"),
    ("What's the ARR of ServiceTitan?", "competitor_data"),
])
def test_gate_blocks(q, rule):
    assert decision.gate(q)["rule"] == rule


@pytest.mark.parametrize("q", [
    "How does a valuation cap work?",
    "What is a SAFE?",
    "Why will we win against Jobber?",
    "What is our churn?",
    "What does dilution mean for us?",
])
def test_gate_allows(q):
    assert decision.gate(q) is None


# --- Level 2: heuristic intents --------------------------------------------------------------

@pytest.mark.parametrize("q,intent", [
    ("What is our ARR and how is it calculated?", "explain_metric"),
    ("Our deck says churn is 1%. Is that defensible?", "challenge_claim"),
    ("What if churn stays at 2% and the round slips to April?", "what_if"),
    ("What happens if Northern Comfort leaves?", "what_if"),
    ("What does burn multiple mean?", "concept"),
    ("What is a SAFE?", "concept"),
    ("How should I answer an investor asking about our gross margin?", "investor_prep"),
    ("Why will we win against Jobber?", "investor_prep"),
    ("Why can't you compute cohort churn?", "missing_data"),
    ("What valuation should we raise at?", "policy_boundary"),
    ("Tell me about the team", "general"),
])
def test_heuristic_intent(q, intent):
    assert decision.heuristic_intent(q)[0] == intent


def test_topic_maps():
    assert decision.claim_ids("Our deck says churn is 1%") == ["churn"]
    assert decision.question_ids("How dependent are we on Northern Comfort?")[0] == 9
    assert "logo_churn_12m" in decision.metric_keys("what is our churn")
    assert decision.glossary_term("How does a valuation cap work?") == "Valuation cap"
    assert decision.glossary_term("explain NRR") == "Net revenue retention (NRR)"


# --- Level 3: scenario arguments -------------------------------------------------------------

@pytest.mark.parametrize("q,expected", [
    ("What if churn stays at 2%?", {"monthly_churn": 0.02}),
    ("what if we have 1.5% monthly churn", {"monthly_churn": 0.015}),
    ("What if reps take a 4-month ramp?", {"ae_ramp_months": 4}),
    ("what if the ramp takes 3 months", {"ae_ramp_months": 3}),
    ("What if the round slips to April?", {"seed_month": "2027-04"}),
    ("What if the round slips 3 months?", {"seed_month": "2027-04"}),
    ("What if we close the round in June 2028?", {"seed_month": "2028-06"}),
    ("What if Northern Comfort doesn't renew?", {"ncg_renewal_seats": 0}),
    ("What if we lose our largest customer?", {"ncg_renewal_seats": 0}),
    ("What if we freeze hiring until close?", {"hold_spend_until_close": True}),
    ("What if only 50% of customers accept the price increase?", {"price_increase_uptake": 0.5}),
    ("What if growth continues at historical rates?", {"base": "Historical drivers"}),
    ("What if things go badly?", {}),
])
def test_scenario_args(q, expected):
    assert decision.scenario_args(q) == expected


def test_scenario_args_combined():
    args = decision.scenario_args("What if churn stays at 2% and the round slips to April and we hold spending?")
    assert args == {"monthly_churn": 0.02, "seed_month": "2027-04", "hold_spend_until_close": True}


# --- Level 3: plan validation ----------------------------------------------------------------

def _names(plan):
    return [c["name"] for c in plan["tools"]]


def test_validate_adds_required_tool():
    plan, notes = decision.validate_plan({"intent": "challenge_claim", "tools": []}, "Is our deck's churn claim fair?")
    assert plan["tools"] == [{"name": "check_deck_claim", "args": {"claim_id": "churn"}}]
    assert any("required for challenge_claim" in n["decision"] and n["by"] == "code" for n in notes)


def test_validate_falls_back_on_bad_intent():
    plan, notes = decision.validate_plan({"intent": "nonsense"}, "What is our gross margin?")
    assert plan["intent"] == "explain_metric"
    assert notes[0]["by"] == "fallback"


def test_validate_drops_unknown_tools_and_fixes_args():
    proposal = {"intent": "what_if", "tools": [
        {"name": "delete_everything", "args": {}},
        {"name": "run_scenario", "args": {"monthly_churn": 3, "seed_month": "April", "colour": "red"}},
    ]}
    plan, notes = decision.validate_plan(proposal, "what if churn is 3% and we close in June?")
    assert plan["tools"] == [{"name": "run_scenario", "args": {"monthly_churn": 0.03, "seed_month": "2027-06"}}]
    decisions = " ".join(n["decision"] for n in notes)
    assert "delete_everything" in decisions and "colour" in decisions


def test_question_text_beats_planner_reading():
    proposal = {"intent": "what_if", "tools": [{"name": "run_scenario", "args": {"monthly_churn": 0.025}}]}
    plan, _ = decision.validate_plan(proposal, "What if churn is 2%?")
    assert plan["tools"][0]["args"]["monthly_churn"] == 0.02


def test_validate_repairs_bad_keys_and_ids():
    proposal = {"intent": "explain_metric", "tools": [
        {"name": "get_metrics", "args": {"keys": ["churn_rate"]}},
        {"name": "check_deck_claim", "args": {"claim_id": "made_up"}},
        {"name": "get_investor_question", "args": {"question_id": 99}},
    ]}
    plan, _ = decision.validate_plan(proposal, "what is our churn?")
    args = {c["name"]: c["args"] for c in plan["tools"]}
    assert "logo_churn_12m" in args["get_metrics"]["keys"]
    assert args["check_deck_claim"] == {"claim_id": "churn"}
    assert args["get_investor_question"] == {"question_id": 3}


def test_validate_caps_tool_count():
    proposal = {"intent": "general", "tools": [{"name": "get_investor_question", "args": {"question_id": i}}
                                               for i in range(1, 9)]}
    plan, notes = decision.validate_plan(proposal, "help me prepare")
    assert len(plan["tools"]) == decision.MAX_TOOLS
    assert any("trimmed" in n["decision"] for n in notes)


def test_investor_prep_gets_a_source():
    plan, _ = decision.validate_plan(None, "How should I answer an investor asking about our gross margin?")
    assert _names(plan) == ["get_investor_question", "find_sources"]


def test_general_without_metrics_uses_company_facts():
    plan, _ = decision.validate_plan(None, "Tell me about the team")
    assert _names(plan) == ["company_facts"]


def test_every_planned_tool_runs():
    """Whatever the validator emits must be callable without error."""
    for q in ["What is our ARR?", "Our deck says churn is 1%", "What if the round slips to April?",
              "What is a SAFE?", "How should I answer the gross margin question?", "Why can't you compute NRR?",
              "Why will we beat Jobber?", "Tell me about the team"]:
        plan, _ = decision.validate_plan(None, q)
        for call in plan["tools"]:
            out = decision.TOOLS[call["name"]].invoke(call["args"])
            assert isinstance(out, str) and out, (q, call)


# --- Reasoning parser ------------------------------------------------------------------------

def test_split_reasoning():
    steps, answer = coach.split_reasoning(
        "<think>scratch</think>**REASONING:**\n1. First.\n2) Second.\n3. Third.\n**ANSWER:**\nThe answer.")
    assert steps == ["First.", "Second.", "Third."]
    assert answer == "The answer."


def test_split_reasoning_without_format():
    assert coach.split_reasoning("Just an answer.") == ([], "Just an answer.")


def test_split_reasoning_keeps_word_answer_inside_steps():
    steps, answer = coach.split_reasoning("REASONING:\n1. A strong answer cites data.\nANSWER: Cite the data.")
    assert steps == ["A strong answer cites data."] and answer == "Cite the data."


# --- Full graph with a fake LLM --------------------------------------------------------------

@pytest.fixture
def fake_llm(monkeypatch):
    set_llm_cache(None)  # a cache would replay one test's replies in another
    calls = []

    def install(*replies):
        model = GenericFakeChatModel(messages=iter([AIMessage(r) for r in replies]))
        monkeypatch.setattr(coach, "get_llm", lambda **kw: calls.append(kw) or model)
        return calls
    return install


def _plan_json(intent, tools):
    return json.dumps({"intent": intent, "why": "test", "tools": tools})


def test_graph_llm_plan(fake_llm):
    calls = fake_llm(
        "<think>hmm</think>```json\n" + _plan_json("what_if", [{"name": "run_scenario", "args": {"monthly_churn": 2}}])
        + "\n```",
        "REASONING:\n1. Churn changes.\n2. Run the scenario.\n3. Runway shortens.\nANSWER:\nThis is a forecast.")
    r = coach.ask([], "What if churn stays at 2%?")
    assert r["intent"] == "what_if"
    assert r["tool_calls"] == [{"name": "run_scenario", "args": {"monthly_churn": 0.02}}]
    assert r["reasoning"] == ["Churn changes.", "Run the scenario.", "Runway shortens."]
    assert r["answer"] == "This is a forecast."
    assert r["audit"]["passed"] and not r["revised"]
    assert [t["by"] for t in r["decision_trace"]][:2] == ["code", "llm"]
    assert len(calls) == 2  # plan + answer


def test_graph_policy_skips_planner(fake_llm):
    calls = fake_llm("REASONING:\n1. Valuation request.\nANSWER:\nI can't recommend a valuation, but here is how caps work.")
    r = coach.ask([], "What valuation should we raise at?")
    assert r["intent"] == "policy_boundary" and r["policy"]["rule"] == "valuation"
    assert {c["name"] for c in r["tool_calls"]} == {"get_investor_question", "lookup_glossary"}
    assert not any(t["level"].startswith("2") for t in r["decision_trace"])
    assert len(calls) == 1  # answer only


def test_graph_planner_without_json_falls_back(fake_llm):
    fake_llm("I think this is about margins.", "Gross margin is explained here.")
    r = coach.ask([], "What is our gross margin?")
    assert r["intent"] == "explain_metric"
    assert r["decision_trace"][1]["by"] == "fallback (no JSON)"
    assert r["tool_calls"][0]["name"] == "get_metrics"
    assert r["reasoning"] == [] and r["answer"] == "Gross margin is explained here."


def test_graph_planner_error_falls_back(fake_llm, monkeypatch):
    answer_model = GenericFakeChatModel(messages=iter([AIMessage("REASONING:\n1. x\nANSWER:\nok")]))

    class Broken:
        def invoke(self, _):
            raise TimeoutError("rate limited")

    monkeypatch.setattr(coach, "get_llm", lambda temperature=0.3: Broken() if temperature == 0 else answer_model)
    r = coach.ask([], "What is a SAFE?")
    assert r["intent"] == "concept" and r["decision_trace"][1]["by"] == "fallback (TimeoutError)"
    assert r["answer"] == "ok"


def test_graph_failed_audit_revises(fake_llm):
    fake_llm(_plan_json("explain_metric", [{"name": "get_metrics", "args": {"keys": ["arr"]}}]),
             "REASONING:\n1. ARR.\nANSWER:\nARR is $7,777,777.",
             "REASONING:\n1. ARR.\nANSWER:\nARR is MRR times twelve, from the closed September month.")
    r = coach.ask([], "What is our ARR?")
    assert r["revised"]
    assert [a["passed"] for a in r["audit_history"]] == [False, True]
    assert "7,777,777" not in r["answer"]


def test_graph_passes_history_to_planner(monkeypatch):
    set_llm_cache(None)
    model = GenericFakeChatModel(messages=iter([AIMessage(_plan_json("what_if", [])), AIMessage("ok")]))
    seen = []

    class Spy:
        def invoke(self, msgs):
            seen.append(msgs)
            return model.invoke(msgs)

    monkeypatch.setattr(coach, "get_llm", lambda **kw: Spy())
    coach.ask([HumanMessage("What if churn stays at 2%?"), AIMessage("Runway shortens.")], "and at 3%?")
    assert "What if churn stays at 2%?" in seen[0][0].content  # planner prompt
    assert any(m.content == "Runway shortens." for m in seen[1])  # answer call gets the chat history


# --- App smoke test --------------------------------------------------------------------------

def test_app_ask_vicky_renders_decision_details(fake_llm, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    fake_llm(_plan_json("what_if", [{"name": "run_scenario", "args": {"monthly_churn": 0.02, "ae_ramp_months": 3}}]),
             "REASONING:\n1. Two drivers.\n2. Scenario.\n3. Shorter runway.\nANSWER:\nRunway shortens versus the plan.")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["nav"] = "Ask Vicky"  # the app navigates with a segmented control, not tabs
    at.run()
    assert not at.exception
    next(b for b in at.button if "churn stays at 2%" in b.label).click().run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    for title in ("How Vicky decided", "How Vicky reasoned", "Evidence (1 tool result)"):
        assert any(title in label for label in labels), title
    assert any("What-if scenario" in m.value for m in at.markdown)


# --- Revision briefs -------------------------------------------------------------------------

def test_revision_brief_gives_an_action_per_issue():
    from vicky import audit
    report = audit.audit("Each customer contributes $343,219 a month.")
    brief = audit.revision_brief(report.issues)
    assert "$343,219" in brief and "DELETE this figure" in brief


def test_same_issues_detects_no_progress():
    from vicky import audit
    a = {"issues": [{"type": "unsupported_number", "text": "$343"}]}
    b = {"issues": [{"type": "unsupported_number", "text": "$343"}]}
    c = {"issues": []}
    assert audit.same_issues(a, b) and not audit.same_issues(a, c)
