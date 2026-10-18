"""Progressive jargon: founders see more investor-speak as they learn it.

June asked for pop-up answers so founders get exposure to the complex terms and get better with
them over time. Three levels:
  1 Plain English    "Months of cash left"           (hover/tap shows "Runway" and its meaning)
  2 Mixed            "Months of cash left (runway)"
  3 Investor-speak   "Runway"                        (hover/tap shows the plain meaning)
The level rises automatically as the founder passes quick term checks, or can be set by hand.

Analogies are written for Tidewell's founders, who are software engineers.
"""
import random

from . import data

LEVELS = {1: "Plain English", 2: "Mixed", 3: "Investor-speak"}

ANALOGIES = {
    "ARR (annual recurring revenue)": "Like counting only your recurring cron jobs, not one-off scripts.",
    "Burn rate": "Your monthly cash 'memory leak' before the next fundraise reboots the system.",
    "Burn multiple": "Efficiency ratio: cash spent per unit of new recurring revenue. Lower is a faster algorithm.",
    "CAC (customer acquisition cost)": "The full compute bill to acquire one customer, including salaries, not just ad spend.",
    "CAC payback": "How many months of profit before a new customer has paid back what it cost to win them.",
    "Churn (logo)": "Like a slow memory leak: you have to keep adding customers just to stay level.",
    "CMGR (compound monthly growth rate)": "The steady per-month growth that gets you from the first value to the last, like an average speed.",
    "Deferred revenue": "Prepaid credits: the cash is already in, but you still owe the service.",
    "Dilution": "Your share of the pie shrinks when new slices are created, even if the pie grows.",
    "Gross margin": "What's left of each dollar after the cost of running the service, like throughput after overhead.",
    "Net revenue retention (NRR)": "Run last year's customers through this year: do they produce more or less revenue?",
    "Runway": "Time until the battery hits zero at the current power draw.",
    "SAFE (simple agreement for future equity)": "A promise to give shares later, resolved when the priced round 'compiles'.",
    "Valuation cap": "The maximum price at which a SAFE converts into shares.",
    "Ramp": "Warm-up time before a new salesperson runs at full speed.",
    "Forecast": "A simulation of the future based on your assumptions, not a measurement.",
    "Logo": "Investor slang for one customer.",
    "SR&ED": "A Canadian tax refund for R&D work. Real money, but it arrives late and isn't guaranteed.",
    "Net new ARR": "How much your recurring revenue grew over the period, after losses.",
}


def entry(key: str) -> dict | None:
    g = data.glossary().get(key)
    if not g:
        return None
    short = key.split(" (")[0]
    return {"term": key, "short": short, "means": g["means"], "example": g["example"],
            "analogy": ANALOGIES.get(key, "")}


def auto_level(learned: int) -> int:
    """Plain English to start, Mixed after 3 terms learned, Investor-speak after 8."""
    return 1 if learned < 3 else 2 if learned < 8 else 3


def display_text(plain: str, key: str, level: int, label: bool = False) -> tuple[str, str]:
    """(text shown on screen, text shown in the pop-up) for this level.

    label=True is for metric labels, where the plain words must stay visible at every level so two
    metrics with the same jargon (e.g. two kinds of runway) remain distinguishable."""
    e = entry(key)
    if not e:
        return plain, ""
    jargon = e["short"]
    meaning = f"{e['means']} Tidewell: {e['example']}" + (f" Think of it as: {e['analogy']}" if e["analogy"] else "")
    if level >= 3:
        shown = f"{jargon}: {plain[0].lower() + plain[1:]}" if label else jargon
        return shown, f"In plain words: {plain[0].lower() + plain[1:]}. {meaning}"
    if level == 2:
        return f"{plain} ({jargon})", f"{jargon}: {meaning}"
    return plain, f"Investors call this {jargon}. {meaning}"


def quiz(key: str, seed: int | None = None) -> dict:
    """One multiple-choice question: which definition matches this term? Two distractors."""
    g = data.glossary()
    rng = random.Random(seed if seed is not None else key)
    others = [k for k in g if k != key]
    wrong = rng.sample(others, 2)
    options = [g[key]["means"]] + [g[w]["means"] for w in wrong]
    rng.shuffle(options)
    return {"term": key, "short": key.split(" (")[0], "options": options, "answer": g[key]["means"]}


def next_term(learned: set, prefer: list[str] | None = None) -> str | None:
    """The next term to learn: preferred terms first, then those with an analogy, then the rest."""
    g = data.glossary()
    order = [k for k in (prefer or []) if k in g] + [k for k in ANALOGIES if k in g] + list(g)
    return next((k for k in order if k not in learned), None)
