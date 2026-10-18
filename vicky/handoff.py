"""When a human should take over.

Vicky prepares founders; she doesn't negotiate terms, value the company or file taxes. When a
founder's question reaches one of those moments, the app says so and points to a person.
This is deterministic (keyword rules), so it can't be talked out of it.
"""
import re

from . import decision

# Taksh Girdhar's policy gate (vicky.decision.gate) backs up these rules, so Ask Vicky and the hand-off card agree.
GATE_WHO = {
    "valuation": ("a June CPA and a startup lawyer", "Vicky explains how valuation, dilution and SAFE conversion work, but won't "
                  "suggest what the company is worth. Set your expectations with people who know your full situation."),
    "investment_advice": ("your advisors (June's team, your lawyer, founders who've raised)",
                          "Vicky doesn't give investment advice. She can lay out the trade-offs so you can decide."),
}

RULES = [
    {"id": "valuation", "patterns": [r"\bvaluation", r"\bpre-?money\b", r"\bpost-?money\b", r"\bwhat (are|is) we worth\b",
                                     r"\bprice (the|our) round\b", r"\bhow much (equity|of the company)\b"],
     "who": "a June CPA and a startup lawyer",
     "why": "Vicky explains how valuation, dilution and SAFE conversion work, but won't suggest what the company is worth. "
            "Set your expectations with people who know your full situation."},
    {"id": "term_sheet", "patterns": [r"\bterm ?sheet\b", r"\bliquidation preference\b", r"\bboard seat\b", r"\bpro[- ]?rata\b",
                                      r"\bright of first refusal\b", r"\brofr\b", r"\binformation rights\b",
                                      r"\banti-?dilution\b", r"\bprotective provisions\b", r"\bshould (we|i) (sign|accept)\b"],
     "who": "a startup lawyer, with a June CPA on the numbers",
     "why": "Term sheets are legal documents. Have a lawyer review every term before you sign."},
    {"id": "tax", "patterns": [r"\bfile (the|our|a)? ?(sr&ed|srred|tax)", r"\bsr&ed claim\b", r"\btax (return|filing)\b",
                               r"\baudit(ed)? (statements|financials)\b", r"\bhst\b|\bgst\b"],
     "who": "a June CPA",
     "why": "Tax claims and audited statements need a qualified accountant."},
    {"id": "advice", "patterns": [r"\bshould (we|i) (take|raise from|choose|pick) (this|that|the) investor\b",
                                  r"\bshould i invest\b", r"\bis (this|it) a good (deal|investment)\b"],
     "who": "your advisors (June's team, your lawyer, founders who've raised)",
     "why": "Vicky doesn't give investment advice. She can lay out the trade-offs so you can decide."},
]


def needs_human(text: str) -> dict | None:
    """Return the first matching hand-off rule for this text, or None."""
    low = (text or "").lower()
    for rule in RULES:  # the specific rules first: a term sheet needs a lawyer, not just "no advice"
        if any(re.search(p, low) for p in rule["patterns"]):
            return {"id": rule["id"], "who": rule["who"], "why": rule["why"]}
    hit = decision.gate(text or "")  # then Taksh Girdhar's policy gate catches the phrasings the rules miss
    if hit and hit["rule"] in GATE_WHO:
        who, why = GATE_WHO[hit["rule"]]
        return {"id": hit["rule"], "who": who, "why": why}
    return None
