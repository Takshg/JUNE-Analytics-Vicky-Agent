"""Pitch deck upload (vicky.deck) and the pitch simulator using the slide the founder points at."""
import json
from pathlib import Path

import pymupdf
import pytest
from langchain_core.globals import set_llm_cache
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from vicky import deck
from vicky.graphs import pitch

ROOT = Path(__file__).resolve().parent.parent

SLIDES = [
    ("Tidewell", "Scheduling and dispatch for HVAC and plumbing teams"),
    ("Traction", "$1.37M ARR\nGrowing 10% month over month\nMonthly logo churn around 1%"),
    ("The ask", "$4M seed\n24 months of runway"),
]


def make_pdf(slides=SLIDES, blank_last=False) -> bytes:
    doc = pymupdf.open()
    for title, body in slides:
        page = doc.new_page(width=960, height=540)
        page.insert_text((60, 80), title, fontsize=36)
        page.insert_text((60, 160), body, fontsize=22)
    if blank_last:
        doc.new_page(width=960, height=540)
    return doc.tobytes()


@pytest.fixture(scope="module")
def sample():
    return deck.load(make_pdf(), "tidewell.pdf")


# --- Loading ---------------------------------------------------------------------------------

def test_load_reads_text_titles_and_images(sample):
    assert [s["title"] for s in sample["slides"]] == ["Tidewell", "Traction", "The ask"]
    assert "Monthly logo churn around 1%" in sample["slides"][1]["text"]
    assert len(sample["images"]) == 3 and all(img.startswith(b"\x89PNG") for img in sample["images"])
    assert not sample["truncated"]


def test_load_blank_slide_has_placeholder_title():
    d = deck.load(make_pdf(blank_last=True))
    assert d["slides"][-1] == {"n": 4, "title": "Slide 4", "text": ""}


def test_load_caps_pages(monkeypatch):
    monkeypatch.setattr(deck, "MAX_PAGES", 2)
    d = deck.load(make_pdf())
    assert len(d["slides"]) == 2 and d["truncated"]


@pytest.mark.parametrize("data,message", [
    (b"not a pdf", "couldn't be read as a PDF"),
    (b"", "couldn't be read as a PDF"),
])
def test_load_rejects_bad_files(data, message):
    with pytest.raises(deck.DeckError, match=message):
        deck.load(data)


def test_load_rejects_huge_files(monkeypatch):
    monkeypatch.setattr(deck, "MAX_BYTES", 10)
    with pytest.raises(deck.DeckError, match="over"):
        deck.load(make_pdf())


# --- Checks ----------------------------------------------------------------------------------

def test_check_slide_flags_founder_claims(sample):
    check = deck.check_slide(sample["slides"][1]["text"])
    assert not check["passed"]
    assert {i["type"] for i in check["issues"]} == {"claim_as_fact"}
    assert len(check["issues"]) == 3  # $1.37M ARR, 10% MoM, ~1% churn


def test_check_slide_blank():
    assert deck.check_slide("")["passed"]


def test_contradiction_reports_nearest_figure(sample):
    found = deck.contradictions("Our ARR is $1.29M: September MRR of $107,189 times 12.", sample["slides"][1]["text"])
    assert deck.describe_contradictions(found) == ["ARR: the founder said $1.29M but the slide shows $1.37M"]


def test_growth_contradiction_with_past_tense(sample):
    found = deck.contradictions("MRR grew about 9% a month over the last 12 months.", sample["slides"][1]["text"])
    assert deck.describe_contradictions(found) == ["growth: the founder said 9% but the slide shows 10%"]


def test_contradictions_found(sample):
    found = deck.contradictions("Churn is 2.0% a month and ARR is $1.29M.", sample["slides"][1]["text"])
    assert {c["topic"] for c in found} == {"churn", "ARR"}
    text = " ".join(deck.describe_contradictions(found))
    assert "said 2% but the slide shows 1%" in text and "said $1.29M but the slide shows $1.37M" in text


@pytest.mark.parametrize("answer", [
    "Churn is about 1% a month.",          # agrees with the slide
    "Our team is great.",                  # no figures
    "Churn is roughly 1.2% a month.",      # within 0.3 points
    "Gross margin is 74%.",                # topic not on the slide
])
def test_no_contradiction(sample, answer):
    assert deck.contradictions(answer, sample["slides"][1]["text"]) == []


def test_slide_context_bounds(sample):
    assert deck.slide_context(None, 1) is None
    assert deck.slide_context(sample, None) is None
    assert deck.slide_context(sample, 9) is None
    ctx = deck.slide_context(sample, 2)
    assert (ctx["n"], ctx["of"], ctx["title"]) == (2, 3, "Traction") and not ctx["check"]["passed"]


# --- Pitch simulator with a deck -------------------------------------------------------------

EVAL = json.dumps({"scores": {"accuracy": 4, "evidence": 3, "candor": 4, "clarity": 4}, "went_well": "Clear.",
                   "improve": "Fix the churn figure on slide 2.", "stronger_answer": "Churn is 2.0% a month.",
                   "decision": "next", "investor_reply": "Thanks. Next question."})


@pytest.fixture
def spy_llm(monkeypatch):
    set_llm_cache(None)
    prompts = []

    def install(*replies):
        model = GenericFakeChatModel(messages=iter([AIMessage(r) for r in replies]))

        class Spy:
            def invoke(self, msgs):
                prompts.append("\n".join(m.content for m in msgs))
                return model.invoke(msgs)

        monkeypatch.setattr(pitch, "get_llm", lambda **kw: Spy())
        return prompts
    return install


def test_pitch_answer_with_slide(sample, spy_llm):
    prompts = spy_llm("Hello, let's start. What is your ARR?", EVAL, EVAL)
    sess = pitch.PitchSession("lead_seed_fund", max_questions=2, deck=sample)
    assert "images" not in sess.state["deck"]  # images stay in the UI, not the graph state
    sess.answer("Churn is 2.0% a month.", slide=2)
    evaluator = prompts[1]
    assert "pointing at slide 2 of 3" in evaluator and "Monthly logo churn around 1%" in evaluator
    assert "said 2% but the slide shows 1%" in evaluator
    turn = sess.state["turns"][0]
    assert turn["slide"]["n"] == 2 and turn["slide"]["contradictions"]
    assert sess.state["transcript"][1] == {"role": "founder", "text": "Churn is 2.0% a month.", "slide": 2}
    # a contradiction with the slide doesn't cap accuracy: the spoken figure is the right one
    assert turn["scores"]["accuracy"] == 4


def test_pitch_answer_without_slide(sample, spy_llm):
    prompts = spy_llm("Hello. What is your ARR?", EVAL, EVAL)
    sess = pitch.PitchSession("lead_seed_fund", max_questions=2, deck=sample)
    sess.answer("ARR is $1.29M.")
    assert "not pointing at a slide" in prompts[1]
    assert sess.state["turns"][0]["slide"] is None


def test_pitch_without_deck_still_works(spy_llm):
    spy_llm("Hello. What is your ARR?", EVAL, EVAL)
    sess = pitch.PitchSession("lead_seed_fund", max_questions=2)
    sess.answer("ARR is $1.29M.")
    assert sess.state["deck"] is None and sess.state["turns"][0]["slide"] is None


def test_debrief_lists_problem_slides(sample, spy_llm):
    spy_llm("Hello. What is your ARR?", EVAL, EVAL, EVAL)
    sess = pitch.PitchSession("lead_seed_fund", max_questions=2, deck=sample)
    sess.answer("Churn is 2.0% a month.", slide=2)
    sess.answer("We need $4M.", slide=1)  # slide 1 has no problems
    assert sess.finished
    flagged = sess.state["debrief"]["slides_flagged"]
    assert [s["n"] for s in flagged] == [2]
    assert any(p.startswith("contradiction: churn") for p in flagged[0]["problems"])


# --- App -------------------------------------------------------------------------------------

def test_app_meeting_shows_slide_viewer(sample, spy_llm, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    spy_llm("Hello. What is your ARR?", EVAL)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["pitch"] = pitch.PitchSession("lead_seed_fund", max_questions=2, deck=sample)
    at.session_state["pitch_persona"] = "lead_seed_fund"
    at.session_state["pitch_deck"] = sample
    at.run()
    assert not at.exception
    picker = next(s for s in at.selectbox if s.label == "Slide you're referencing")
    picker.set_value(2).run()
    assert not at.exception
    assert any("pointing at slide 2" in c.placeholder for c in at.chat_input)


def test_sample_decks_draft_flags_all_nine_claims_corrected_is_clean():
    flags = {}
    for version in ("draft", "corrected"):
        d = deck.load((ROOT / "assets" / "sample_deck" / f"tidewell_deck_{version}.pdf").read_bytes())
        flags[version] = {s["n"]: [i["text"] for i in deck.check_slide(s["text"])["issues"]] for s in d["slides"]}
    draft = {n: f for n, f in flags["draft"].items() if f}
    assert sorted(draft) == [4, 5, 6, 7, 8, 11]
    assert sum(len(f) for f in draft.values()) == 9  # the 9 Appendix A claims
    assert not any(flags["corrected"].values())


def test_verbal_expansion_is_attributed():
    from vicky import audit
    assert audit.audit("Northern Comfort has a verbal 600-seat expansion.").passed
    assert not audit.audit("Northern Comfort Group is expanding to 600 seats next year.").passed


def test_failed_turn_rolls_back_so_retry_scores_new_answer(monkeypatch):
    set_llm_cache(None)
    replies = iter(["Hello. What is your ARR?", RuntimeError("rate limited"), EVAL])

    class Flaky:
        def invoke(self, msgs):
            r = next(replies)
            if isinstance(r, Exception):
                raise r
            return AIMessage(r)

    monkeypatch.setattr(pitch, "get_llm", lambda **kw: Flaky())
    sess = pitch.PitchSession("lead_seed_fund", max_questions=2)
    with pytest.raises(RuntimeError):
        sess.answer("FIRST attempt")
    sess.answer("SECOND attempt")
    founder = [t["text"] for t in sess.state["transcript"] if t["role"] == "founder"]
    assert founder == ["SECOND attempt"]
    assert sess.state["turns"][0]["answer"] == "SECOND attempt"
