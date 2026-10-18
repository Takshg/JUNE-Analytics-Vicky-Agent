"""Offer round (vicky.offers): bounded offers, terms in code, audited debrief, no AI needed."""
import json
from pathlib import Path

import pytest
from langchain_core.globals import set_llm_cache
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from vicky import offers

ROOT = Path(__file__).resolve().parent.parent
ASK = (4_000_000, 20.0)  # founder's ask in these tests: $20M post-money


# --- Bounds and terms ------------------------------------------------------------------------

def test_cheque_ranges_come_from_the_pack():
    assert offers.cheque_range("lead_seed_fund") == (1_500_000, 3_000_000)
    assert offers.cheque_range("angel_operator") == (25_000, 150_000)
    assert offers.cheque_range("government_fund") == offers.CO_INVEST
    assert offers.cheque_range("skeptical_partner") is None
    assert "skeptical_partner" not in offers.investors()


def test_band_is_anchored_on_the_safe_caps():
    assert offers._caps() == [10_000_000, 15_000_000]
    assert offers.post_money_band() == (6_000_000, 30_000_000)


def test_validate_clamps_and_records():
    o = offers.validate({"money": "$9,000,000", "equity": "60%"}, "strategic_investor", *ASK)
    assert o["money"] == 1_000_000
    post = o["money"] / (o["equity"] / 100)
    assert 6_000_000 <= post <= 30_100_000
    assert len(o["adjusted"]) == 2


def test_validate_missing_equity_uses_founders_valuation():
    o = offers.validate({"money": 2_000_000}, "lead_seed_fund", *ASK)
    assert o["equity"] == 10.0 and o["adjusted"]


def test_validate_keeps_a_fair_offer_untouched():
    o = offers.validate({"money": 2_500_000, "equity": 15, "condition": "board seat"}, "lead_seed_fund", *ASK)
    assert (o["money"], o["equity"], o["adjusted"]) == (2_500_000, 15, [])


def test_terms():
    t = offers.terms({"money": 2_400_000, "equity": 15}, *ASK)
    assert round(t["post_money"]) == 16_000_000 and round(t["pre_money"]) == 13_600_000
    assert round(t["vs_ask"], 2) == -0.2 and t["share_of_raise"] == 0.6
    assert t["vs_caps"] == [(10_000_000, "above"), (15_000_000, "above")]


def test_fallback_offers_are_in_bounds():
    offs = offers.fallback_offers(offers.DEFAULT_INVESTORS, *ASK)
    assert [o["persona"] for o in offs] == offers.DEFAULT_INVESTORS
    for o in offs:
        lo, hi = offers.cheque_range(o["persona"])
        assert lo <= o["money"] <= hi and o["source"] == "rules"


# --- Generation and debrief with a fake LLM --------------------------------------------------

@pytest.fixture
def fake_llm(monkeypatch):
    set_llm_cache(None)

    def install(*replies):
        model = GenericFakeChatModel(messages=iter([AIMessage(r) for r in replies]))
        monkeypatch.setattr(offers, "get_llm", lambda **kw: model)
    return install


def test_generate_validates_ai_offers(fake_llm):
    fake_llm(json.dumps({"offers": [
        {"persona": "lead_seed_fund", "money": 2_500_000, "equity": 18, "condition": "board seat", "pitch": "p", "why": "w"},
        {"persona": "angel_operator", "money": 900_000, "equity": 4, "pitch": "p", "why": "w"},  # above the cheque
    ]}))
    offs = offers.generate(["lead_seed_fund", "angel_operator"], *ASK)
    assert [o["source"] for o in offs] == ["ai", "ai"]
    assert offs[1]["money"] == 150_000 and offs[1]["adjusted"]


def test_generate_falls_back_when_an_investor_is_missing(fake_llm):
    fake_llm(json.dumps({"offers": [{"persona": "lead_seed_fund", "money": 2_000_000, "equity": 15}]}))
    offs = offers.generate(["lead_seed_fund", "angel_operator"], *ASK)
    assert {o["source"] for o in offs} == {"rules"}


def test_generate_without_ai():
    assert {o["source"] for o in offers.generate(offers.DEFAULT_INVESTORS, *ASK, use_ai=False)} == {"rules"}


def test_debrief_is_audited_and_revised_once(fake_llm):
    offs = offers.fallback_offers(["lead_seed_fund", "angel_operator"], *ASK)
    bad = "Taking $2,400,000 for 15% raises 60% of the $4,000,000 target. You should raise at a valuation of $16M."
    fake_llm(bad, bad)  # the revision repeats the problem: the audit result is still shown to the founder
    d = offers.debrief({"kind": "accept", "index": 0}, offs, *ASK)
    assert d["source"] == "ai" and not d["audit"]["passed"]
    assert "valuation_or_advice" in {i["type"] for i in d["audit"]["issues"]}


def test_debrief_without_ai_describes_every_offer():
    offs = offers.fallback_offers(offers.DEFAULT_INVESTORS, *ASK)
    d = offers.debrief({"kind": "walk"}, offs, *ASK, use_ai=False)
    assert d["source"] == "rules" and d["text"].startswith("You walked away") and d["text"].count("post-money") == 4


@pytest.mark.parametrize("decision,start", [
    ({"kind": "accept", "index": 0}, "accepted The lead seed fund"),
    ({"kind": "counter", "index": 0, "money": 2_400_000, "equity": 14}, "countered The lead seed fund"),
    ({"kind": "walk"}, "walked away"),
    ({"kind": "timeout"}, "ran out of time"),
])
def test_describe_decision(decision, start):
    offs = offers.fallback_offers(["lead_seed_fund"], *ASK)
    assert offers.describe_decision(decision, offs, *ASK).startswith(start)


# --- Investor reactions (decided in code) ----------------------------------------------------

def _offs():
    return offers.fallback_offers(offers.DEFAULT_INVESTORS, *ASK)  # lead $2.4M for 15% = $16M post


def _by(reacts):
    return {r["persona"]: r for r in reacts}


def test_accepting_the_lead_brings_in_the_government_fund_at_the_leads_price():
    r = _by(offers.reactions({"kind": "accept", "index": 0}, _offs()))
    assert r["lead_seed_fund"]["outcome"] == "deal"
    gov = r["government_fund"]
    assert gov["outcome"] == "co_invest" and gov["money"] == 800_000 and gov["equity"] == 5.0  # $800K at $16M post
    assert r["strategic_investor"]["outcome"] == r["angel_operator"]["outcome"] == "pass"
    summary = offers.round_summary(list(r.values()))
    assert summary["raised"] == 3_200_000 and summary["share"] == 0.8 and summary["equity_sold"] == 20.0


@pytest.mark.parametrize("equity,outcome", [
    (16.0, "deal"),     # better for the investor than their own offer
    (14.3, "deal"),     # 4.9% above their valuation: within half the lead's 10% flexibility
    (13.8, "halfway"),  # 8.7% above: within flexibility
    (12.0, "firm"),     # 25% above: within 3x flexibility
    (11.0, "withdraw"), # 36% above
])
def test_counter_outcomes_for_the_lead(equity, outcome):
    r = _by(offers.reactions({"kind": "counter", "index": 0, "money": 2_400_000, "equity": equity}, _offs()))
    assert r["lead_seed_fund"]["outcome"] == outcome


def test_halfway_terms_split_the_valuation():
    lead = _by(offers.reactions({"kind": "counter", "index": 0, "money": 2_400_000, "equity": 13.8}, _offs()))["lead_seed_fund"]
    asked, theirs = 2_400_000 / 0.138, 16_000_000
    assert abs(lead["money"] / (lead["equity"] / 100) - (asked + theirs) / 2) / theirs < 0.01


def test_counter_outside_the_cheque_keeps_the_founders_valuation():
    angel = _by(offers.reactions({"kind": "counter", "index": 3, "money": 500_000, "equity": 2.5}, _offs()))["angel_operator"]
    assert angel["money"] == 150_000 and angel["note"].startswith("can only invest")
    assert angel["equity"] == 0.8  # $150K at the founder's $20M valuation


@pytest.mark.parametrize("kind,outcome", [("walk", "door_open"), ("timeout", "waiting")])
def test_walk_and_timeout(kind, outcome):
    reacts = offers.reactions({"kind": kind}, _offs())
    assert {r["outcome"] for r in reacts} == {outcome} and offers.round_summary(reacts)["raised"] == 0


def test_voice_uses_templates_without_ai():
    voiced = offers.voice(offers.reactions({"kind": "walk"}, _offs()), "walked away", use_ai=False)
    assert all(v["line"] == offers.TEMPLATE_LINES["door_open"] and v["voice"] == "rules" for v in voiced)


def test_voice_keeps_ai_lines_that_pass_the_audit(fake_llm):
    fake_llm(json.dumps({"replies": [
        {"persona": "lead_seed_fund", "line": "Done. Let's draft the term sheet this week."},
        {"persona": "government_fund", "line": "We'll match it, and the company is worth $90M."},  # fails the audit
    ]}))
    voiced = _by(offers.voice(offers.reactions({"kind": "accept", "index": 0}, _offs()), "accepted the lead"))
    assert voiced["lead_seed_fund"]["voice"] == "ai"
    assert voiced["government_fund"]["voice"] == "rules"
    assert voiced["government_fund"]["line"] == offers.TEMPLATE_LINES["co_invest"]


def test_debrief_includes_how_investors_responded():
    offs = _offs()
    d = offers.debrief({"kind": "accept", "index": 0}, offs, *ASK, use_ai=False)
    assert "Joins the round" in d["text"] and "Committed if these close: $3,200,000 (80% of the target)" in d["text"]


# --- App -------------------------------------------------------------------------------------

def test_app_offer_round_end_to_end_without_ai(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["nav"] = "Offer round"
    at.session_state["use_ai"] = False
    at.run()
    assert not at.exception
    next(n for n in at.number_input if n.label.startswith("For this much equity")).set_value(20.0).run()
    next(b for b in at.button if b.label == "Bring in the offers").click().run()
    assert not at.exception and len(at.session_state["offer_round"]["offers"]) == 4
    at.radio[0].set_value(("walk", None)).run()
    next(b for b in at.button if b.label == "Lock in my decision").click().run()
    assert not at.exception
    rnd = at.session_state["offer_round"]
    assert rnd["decision"]["kind"] == "walk" and rnd["debrief"]["source"] == "rules"
    assert {r["outcome"] for r in rnd["reactions"]} == {"door_open"}


def test_debrief_revision_fixes_a_flagged_figure(fake_llm):
    offs = offers.fallback_offers(["lead_seed_fund"], *ASK)
    fake_llm("Taking $2,400,000 for 15% leaves $77,777,777 unspent.", "Taking $2,400,000 for 15% raises 60% of the target.")
    d = offers.debrief({"kind": "accept", "index": 0}, offs, *ASK)
    assert d["audit"]["passed"] and "77,777,777" not in d["text"]


def test_debrief_states_equity_comparisons_for_a_counter():
    d = offers.debrief({"kind": "counter", "index": 0, "money": 2_400_000, "equity": 13.8}, _offs(), *ASK, use_ai=False)
    assert "14.4% is more equity than the founder's counter of 13.8%" in d["text"]
    assert "Agreed so far (excluding offers the founder hasn't accepted): $800,000" in d["text"]
