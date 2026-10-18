"""Hover definitions for Appendix I glossary terms (vicky.glossary)."""
import re

import pytest

from vicky import data
from vicky.glossary import SKIP, _names, glossify, glossify_sections


def wrapped(html: str) -> list[str]:
    return re.findall(r'<span class="gl" tabindex="0">([^<]+)', html)


def test_every_glossary_entry_is_findable():
    for entry in data.glossary():
        if entry in SKIP:
            continue
        for name in _names(entry):
            assert wrapped(glossify(f"About {name} here.")), (entry, name)


def test_tooltip_has_definition_and_example():
    out = glossify("Our burn multiple is 0.6.")
    assert "Net burn divided by net new ARR" in out
    assert "Tidewell: About 0.6 over the last 12 months" in out


def test_longest_name_wins():
    assert wrapped(glossify("CAC payback is 9 months.")) == ["CAC payback"]
    assert wrapped(glossify("Net new ARR was $830K.")) == ["Net new ARR"]


def test_burn_rate_aliases():
    assert wrapped(glossify("Monthly burn is $58K.")) == ["Monthly burn"]
    assert wrapped(glossify("Burn multiple and burn rate.")) == ["Burn multiple", "burn rate"]


def test_acronym_and_full_name_both_match():
    assert wrapped(glossify("NRR is 88%.")) == ["NRR"]
    assert wrapped(glossify("Net revenue retention is 88%.")) == ["Net revenue retention"]


def test_first_mention_only():
    assert wrapped(glossify("ARR rose. ARR is MRR x 12. ARR again.")) == ["ARR", "MRR"]


def test_shared_seen_set_spans_calls():
    seen = set()
    assert wrapped(glossify("ARR is up.", seen)) == ["ARR"]
    assert wrapped(glossify("ARR is still up.", seen)) == []


@pytest.mark.parametrize("text", ["a safe bet", "please be safe", "the sam we hired", "your logo", "a forecast"])
def test_everyday_words_untouched(text):
    assert glossify(text) == text


def test_plurals():
    assert wrapped(glossify("Two SAFEs and two valuation caps.")) == ["SAFEs", "valuation caps"]


def test_code_tags_and_links_untouched():
    text = 'Run `get_metrics(["arr"])`, see <span title="ARR">x</span> and [docs](https://x.io/arr-cac).'
    assert glossify(text) == text


def test_dollar_signs_escaped_in_tooltip():
    tip = glossify("ARR")
    assert "$1.29M" not in tip and "&#36;1.29M" in tip  # stops Streamlit reading it as LaTeX


def test_idempotent():
    once = glossify("Net new ARR, NRR, CAC payback and the valuation cap.")
    assert glossify(once) == once


def test_sections_reset_first_mention():
    md = "## Numbers\nARR is $1.29M.\n\n## Risks\nARR depends on churn."
    assert wrapped(glossify_sections(md)) == ["ARR", "ARR", "churn"]


def test_empty():
    assert glossify("") == "" and glossify_sections("") == ""
