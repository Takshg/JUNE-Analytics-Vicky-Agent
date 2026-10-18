"""Start here: readiness in plain words (no score out of 100) and the "Your fix path" domino chain."""
from pathlib import Path

import pytest

from vicky import journey

ROOT = Path(__file__).resolve().parent.parent
ALL_FIXED = {"cash_cliff": 4.5, "churn": 4.1, "growth_slowing": 4.0, "deferred_revenue": 4.0, "srred_guess": 4.2,
             "annual_repricing": 4.4}


def statuses(steps):
    return [s["status"] for s in steps]


# --- (a) fix-path order and statuses ---------------------------------------------------------

def test_fix_path_order():
    assert [s["key"] for s in journey.fix_path({})] == ["survive", "deck", "growth", "forecast", "meeting"]
    assert [s["roadblocks"] for s in journey.fix_path({})][:4] == [
        ["cash_cliff"], ["churn"], ["growth_slowing"], ["deferred_revenue", "srred_guess", "annual_repricing"]]


def test_fix_path_no_practice():
    steps = journey.fix_path({})
    assert statuses(steps) == ["first", "next", "next", "next", "next"]
    assert steps[0]["practice_rb"] == "cash_cliff" and not any(s["latest"] for s in steps)


def test_fix_path_one_step_done():
    steps = journey.fix_path({"cash_cliff": 4.3}, latest="cash_cliff")
    assert statuses(steps) == ["done", "first", "next", "next", "next"]
    assert steps[0]["latest"] and steps[1]["practice_rb"] == "churn"


def test_fix_path_all_done_leaves_the_partner_meeting_as_first():
    steps = journey.fix_path(ALL_FIXED, latest="annual_repricing")
    assert statuses(steps) == ["done", "done", "done", "done", "first"]
    assert steps[3]["latest"] and steps[4]["practice_rb"] is None


def test_below_four_is_not_done():
    assert statuses(journey.fix_path({"cash_cliff": 3.9}))[0] == "first"


def test_later_step_done_out_of_order_stays_done():
    steps = journey.fix_path({"growth_slowing": 4.5})
    assert statuses(steps) == ["first", "next", "done", "next", "next"]


def test_deck_step_done_when_no_claims_need_fixing():
    steps = journey.fix_path({"cash_cliff": 4.2}, n_claims_to_fix=0)
    assert statuses(steps)[:3] == ["done", "done", "first"]


def test_grouped_forecast_step_needs_all_three():
    partial = {**ALL_FIXED, "srred_guess": 3.0}
    steps = journey.fix_path(partial)
    assert steps[3]["status"] == "first" and steps[3]["practice_rb"] == "srred_guess"


def test_latest_only_marked_on_a_done_step():
    steps = journey.fix_path({"churn": 3.5}, latest="churn")
    assert not any(s["latest"] for s in steps)


def test_one_figure_per_tile_with_its_source():
    steps = journey.fix_path({})
    assert steps[0]["figure"] == journey.roadblock("cash_cliff").figure
    assert steps[1]["figure"] == f"{len(journey.claims_to_fix())} claims to fix"
    assert steps[1]["prov"] == "founder_claim" and steps[4]["prov"] is None


# --- readiness in plain words ----------------------------------------------------------------

@pytest.mark.parametrize("best,level,icon", [
    ({}, "Getting ready", "○"),
    ({"cash_cliff": 4.2}, "Almost there", "◐"),
    ({"cash_cliff": 4.2, "growth_slowing": 4.0}, "Almost there", "◐"),
    ({"cash_cliff": 4.2, "growth_slowing": 4.0, "churn": 4.6}, "Ready for the partner meeting", "✓"),
])
def test_readiness_levels(best, level, icon):
    rv = journey.readiness_view(best)
    assert rv["level"] == level and rv["rows"][2]["icon"] == icon


def test_readiness_rows_strengths_first():
    rows = journey.readiness_view({})["rows"]
    assert rows[0]["key"].startswith("Your business is strong") and rows[0]["n"] == len(journey.strengths())
    assert rows[1]["n"] == len(journey.claims_to_fix()) == 6
    assert rows[2]["n"] == 0


def test_readiness_bar():
    assert journey.readiness_view({})["bar"] == round(40 + 20 * journey.deck_health())
    full = {"cash_cliff": 4.2, "growth_slowing": 4.0, "churn": 4.6}
    assert journey.readiness_view(full)["bar"] == round(80 + 20 * journey.deck_health())


# --- (b) the Start here page renders in English and French -----------------------------------

def _start(lang_fr: bool, best: dict | None = None, latest: str | None = None):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["nav"] = "Start here"
    at.session_state["lang_fr"] = lang_fr
    if best is not None:
        at.session_state["best"] = best
    if latest:
        at.session_state["latest_fix"] = latest
    return at.run()


@pytest.mark.parametrize("lang_fr,level,title", [(False, "Getting ready", "Your fix path"),
                                                  (True, "En préparation", "Votre parcours de corrections")])
def test_start_here_renders(lang_fr, level, title):
    at = _start(lang_fr)
    assert not at.exception
    html = "\n".join(m.value for m in at.markdown)
    assert level in html and title in html
    assert "/100" not in html
    assert html.count("<li aria-label=") == 5 and 'role="progressbar"' in html


def test_start_here_after_a_fix_shows_done_and_latest():
    at = _start(False, best={"cash_cliff": 4.3}, latest="cash_cliff")
    assert not at.exception
    html = "\n".join(m.value for m in at.markdown)
    assert "Almost there" in html and "Latest fix" in html
    assert 'aria-label="Step 1 of 5, Fixed: Survive the raise"' in html
    assert 'aria-label="Step 2 of 5, First fix: Fix the deck numbers"' in html
    assert any(b.label.startswith("Practise this →") and "Fix the deck numbers" in b.label for b in at.button)
