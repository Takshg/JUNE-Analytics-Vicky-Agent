"""A founder's pitch deck (PDF) for the pitch simulator.

load() turns the PDF into slides: text for the evaluator and a PNG for the viewer.
check_slide() audits a slide's figures and claims in code; contradictions() finds topics where the
founder's spoken answer and the slide they point at give different numbers.
"""
import re

import pymupdf

from . import audit as auditor
from .tools import scenario_facts

MAX_PAGES = 40
MAX_BYTES = 25 * 1024 * 1024
MAX_SLIDE_CHARS = 1500  # per slide, in the evaluator prompt
RENDER_WIDTH = 1100  # px

# topics where a slide and an answer can disagree on a number
TOPICS = {
    "ARR": r"\barr\b|annual recurring",
    "MRR": r"\bmrr\b|monthly recurring",
    "growth": r"grow|grew|growth|\bmom\b|month over month",
    "churn": r"churn",
    "gross margin": r"gross margin|\bmargin\b",
    "NRR": r"\bnrr\b|net revenue retention|net retention",
    "CAC": r"\bcac\b|acquisition cost",
    "runway": r"runway",
    "burn": r"\bburn\b",
    "TAM": r"\btam\b|addressable market|market size",
}


class DeckError(ValueError):
    """A deck that can't be used, with a message fit for the founder."""


def load(pdf: bytes, name: str = "deck.pdf") -> dict:
    """Read a PDF deck. Returns {"name", "slides": [{"n", "title", "text"}], "images": [png bytes]}."""
    if len(pdf) > MAX_BYTES:
        raise DeckError(f"The deck is over {MAX_BYTES // (1024 * 1024)} MB. Export a smaller PDF.")
    try:
        doc = pymupdf.open(stream=pdf, filetype="pdf")
    except Exception as e:
        raise DeckError("That file couldn't be read as a PDF. Export the deck as PDF and try again.") from e
    if doc.needs_pass:
        raise DeckError("The PDF is password-protected. Export an unprotected copy.")
    if doc.page_count == 0:
        raise DeckError("The PDF has no pages.")
    slides, images = [], []
    for i, page in enumerate(doc):
        if i >= MAX_PAGES:
            break
        text = re.sub(r"[ \t]+", " ", page.get_text("text")).strip()
        text = re.sub(r"\n{2,}", "\n", text)
        text = re.sub(r"(?<![.!?:])\n(?=[a-z])", " ", text)  # rejoin lines a text box wrapped mid-sentence
        title = next((ln.strip() for ln in text.splitlines() if ln.strip()), f"Slide {i + 1}")
        slides.append({"n": i + 1, "title": title[:80], "text": text})
        zoom = RENDER_WIDTH / page.rect.width
        images.append(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
    return {"name": name, "slides": slides, "images": images, "truncated": doc.page_count > MAX_PAGES}


def check_slide(text: str) -> dict:
    """Audit a slide like any other text: unsupported figures and founder claims stated as fact."""
    if not text.strip():
        return {"passed": True, "issues": [], "summary": "No text on this slide (image only).", "numbers_checked": 0}
    report = auditor.audit(text, extra_known=scenario_facts())
    return {"passed": report.passed, "issues": report.issues, "summary": report.summary(),
            "numbers_checked": report.numbers_checked}


def _figures_by_topic(text: str) -> dict[str, set]:
    """{topic: {(kind, value)}} for each line/sentence that names a topic and states a figure."""
    out = {}
    for chunk in re.split(r"\n|(?<=[.!?;])\s+", text):
        low = chunk.lower()
        found = [t for t, pat in TOPICS.items() if re.search(pat, low)]
        if not found:
            continue
        figs = set()
        for m in auditor.NUM_RE.finditer(chunk):
            parsed = auditor._to_value(m)
            if parsed and parsed[1]:
                figs.add(parsed)
        for t in found:
            if figs:
                out.setdefault(t, set()).update(figs)
    return out


def _close(a: float, b: float, kind: str) -> bool:
    if kind == "%":
        return abs(a - b) <= 0.3  # percentage points
    return abs(a - b) <= 0.03 * max(abs(a), abs(b))


def contradictions(answer: str, slide_text: str) -> list[dict]:
    """Topics where the answer and the slide both state a figure of the same kind and none agree."""
    said, shown = _figures_by_topic(answer), _figures_by_topic(slide_text)
    out = []
    for topic in said.keys() & shown.keys():
        for kind in {k for _, k in said[topic]} & {k for _, k in shown[topic]}:
            a = sorted(v for v, k in said[topic] if k == kind)
            s = sorted(v for v, k in shown[topic] if k == kind)
            if not any(_close(x, y, kind) for x in a for y in s):
                # a sentence naming two topics ("ARR is $1.29M: MRR of $107,189 x 12") lends both figures to
                # each; report only the founder's figure nearest the slide's
                nearest = min(a, key=lambda x: min(abs(x - y) for y in s))
                out.append({"topic": topic, "kind": kind, "said": [nearest], "slide": s})
    return out


def _fmt(v: float, kind: str) -> str:
    if kind == "%":
        return f"{v:g}%"
    if kind == "$":
        return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v:,.0f}"
    if kind == "x":
        return f"{v:g}x"
    return f"{v:g} months"


def describe_contradictions(items: list[dict]) -> list[str]:
    return [f"{c['topic']}: the founder said {', '.join(_fmt(v, c['kind']) for v in c['said'])} but the slide shows "
            f"{', '.join(_fmt(v, c['kind']) for v in c['slide'])}" for c in items]


def slide_context(deck: dict | None, slide_no: int | None) -> dict | None:
    """The referenced slide's text plus its code check, for the evaluator. None if no deck or slide."""
    if not deck or not slide_no:
        return None
    slides = deck["slides"]
    if not 1 <= slide_no <= len(slides):
        return None
    s = slides[slide_no - 1]
    return {"n": s["n"], "of": len(slides), "title": s["title"], "text": s["text"][:MAX_SLIDE_CHARS],
            "check": check_slide(s["text"])}
