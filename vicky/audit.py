"""A separate, deterministic check on anything the LLM writes.

1. Every $ / % / x / months figure in the text must tie to a number we know (metrics engine,
   data pack, scenario outputs). Anything else is flagged as unsupported.
2. Founder claims (1% churn, 110% NRR, ...) must not be stated as fact without attribution.
3. No valuation recommendations or investment advice.
4. Benchmarks must name a source.
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from . import data, metrics

NUM_RE = re.compile(
    r"(?P<cur>\$)?\s?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s?"
    r"(?P<suf>[kKmMbB](?![a-zA-Z])|million|billion)?\s?"
    r"(?P<unit>%|x(?![a-zA-Z]|\s?\d)|-?\s?months?\b)?"
)

ADVICE_PATTERNS = [
    r"\byou should (raise|price|value|set) (at|the round at|a valuation)",
    r"\b(recommend|suggest)\w* (a |an )?(pre-?money|post-?money)? ?valuation (of|at|around)",
    r"\b(pre|post)-?money (valuation )?(of|at|around) \$",
    r"\bvalu(ation|ed) (of|at) (about |around |roughly )?\$\d",
    r"\bcompany is worth \$",
    r"\b(you|investors) should (invest|buy|sell)\b",
    r"\bfair valuation\b",
]
BENCHMARK_PATTERNS = [r"\bbenchmark", r"\btop[- ]quartile", r"\bbest[- ]in[- ]class", r"\bindustry (average|standard|norm)",
                      r"\btypical (seed |saas |b2b )?(company|startup|saas)", r"\bmedian (seed|saas|startup)"]
ATTRIBUTION_WORDS = r"(deck|claim|claimed|says|said|plan|assum|forecast|target|founders?'|slide|states|quoted|weak answer|vs\.?|versus|not|as booked|verbal|upside)"

# founder claims that must not be stated as fact: (topic regex, value regex)
FOUNDER_CLAIMS = [
    (r"churn", r"\b1(\.0)?\s?%"),
    (r"\bnrr\b|net revenue retention", r"\b110\s?%"),
    (r"\barr\b|annual recurring", r"\$1\.37\s?m"),
    (r"\bcac\b|acquisition cost", r"\$970\b"),
    (r"runway", r"\b24\s?months"),
    (r"\btam\b|addressable", r"\$2\s?b"),
    (r"grow", r"\b10\s?%\s*(a month|month over month|mom|monthly)"),
    (r"gross margin", r"\b92\s?%"),  # true only as booked; investors count support in cost of revenue
    (r"northern comfort|\bncg\b", r"\b600[\s-]?seats?"),  # verbal, nothing signed
]


@dataclass
class AuditReport:
    passed: bool
    issues: list = field(default_factory=list)
    numbers_checked: int = 0
    numbers_verified: int = 0

    def summary(self) -> str:
        if self.passed:
            return f"Audit passed: {self.numbers_verified}/{self.numbers_checked} figures tie to the data."
        return f"Audit raised {len(self.issues)} issue(s); {self.numbers_verified}/{self.numbers_checked} figures tie to the data."


def _walk_numbers(obj, out: dict):
    """Collect numbers into out[kind]; bare numbers go to out["raw"]."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out["raw"].add(float(obj))
    elif isinstance(obj, str):
        for m in NUM_RE.finditer(obj):
            v = _to_value(m)
            if v is not None:
                value, kind = v
                out[kind or "raw"].add(value / 100 if kind == "%" else value)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk_numbers(v, out)


def _empty_known() -> dict:
    return {"raw": set(), "$": set(), "%": set(), "x": set(), "months": set()}


def _to_value(m: re.Match):
    try:
        v = float(m.group("num").replace(",", ""))
    except ValueError:
        return None
    suf = (m.group("suf") or "").lower()
    v *= {"k": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}.get(suf, 1)
    unit = (m.group("unit") or "").strip().lower()
    if unit == "%":
        kind = "%"
    elif unit == "x":
        kind = "x"
    elif "month" in unit:
        kind = "months"
    elif m.group("cur"):
        kind = "$"
    else:
        kind = None
    return v, kind


@lru_cache
def _pack_numbers() -> dict:
    known = _empty_known()
    for path in data.PACK_DIR.iterdir():
        if path.suffix == ".yaml":
            _walk_numbers(yaml.safe_load(path.read_text()), known)
        elif path.suffix == ".csv":
            df = data.quarterly(path.stem)
            for col in df.columns:
                for v in df[col]:
                    if isinstance(v, (int, float)):
                        known["raw"].add(float(v))
                        if col.endswith("_k"):
                            known["$"].add(float(v) * 1000)
    for m in metrics.registry().values():
        known[m.unit if m.unit in known else "raw"].add(float(m.value))
        _walk_numbers(m.inputs, known)
    return {k: frozenset(v) for k, v in known.items()}


def _matches(value: float, kind: str, known: dict) -> bool:
    if kind == "%":
        cands = known["%"] | {k for k in known["raw"] if abs(k) <= 5}
        return any(abs(value / 100 - k) <= 0.006 for k in cands)
    if kind == "x":
        return any(abs(value - k) <= 0.06 for k in known["x"] | {k for k in known["raw"] if abs(k) <= 10})
    if kind == "months":
        return any(abs(value - k) <= 1.0 for k in known["months"])
    # dollars: allow rounding such as "$3,200" vs 3,209 or "$1.29M"
    return any(k and abs(value - abs(k)) / abs(k) <= 0.035 for k in known["$"] | known["raw"])


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def audit(text: str, extra_known: list | dict | None = None) -> AuditReport:
    known = {k: set(v) for k, v in _pack_numbers().items()}
    if extra_known:
        _walk_numbers(extra_known, known)
    issues = []
    checked = verified = 0
    for sent in _sentences(text):
        low = sent.lower()
        for m in NUM_RE.finditer(sent):
            parsed = _to_value(m)
            if not parsed or parsed[1] is None:
                continue
            value, kind = parsed
            if kind == "months" and value > 60:
                continue
            checked += 1
            if _matches(value, kind, known):
                verified += 1
            else:
                issues.append({"type": "unsupported_number", "text": m.group(0).strip(), "sentence": sent.strip(),
                               "detail": "This figure doesn't tie to the data pack or the metrics engine."})
        for topic, value in FOUNDER_CLAIMS:
            if re.search(topic, low) and re.search(value, low) and not re.search(ATTRIBUTION_WORDS, low):
                issues.append({"type": "claim_as_fact", "text": re.search(value, low).group(0), "sentence": sent.strip(),
                               "detail": "A founder claim the data does not support is stated as fact."})
        for pat in ADVICE_PATTERNS:
            if re.search(pat, low):
                issues.append({"type": "valuation_or_advice", "text": re.search(pat, low).group(0), "sentence": sent.strip(),
                               "detail": "Vicky must not recommend a valuation or give investment advice."})
                break
        for pat in BENCHMARK_PATTERNS:
            if re.search(pat, low) and not _has_source(sent):
                issues.append({"type": "unsourced_benchmark", "text": re.search(pat, low).group(0), "sentence": sent.strip(),
                               "detail": "Benchmarks must name a public source (Appendix F)."})
                break
    return AuditReport(passed=not issues, issues=issues, numbers_checked=checked, numbers_verified=verified)


# What the reviser must do for each issue type. Without this, models "fix" an unsupported figure by
# keeping it and adding "the deck states", which misattributes it to the founders.
FIX_ACTIONS = {
    "unsupported_number": "DELETE this figure. Do not restate, reword or attribute it to anyone, and do not "
                          "calculate a replacement. Rewrite the sentence without it, or delete the sentence.",
    "claim_as_fact": "Attribute it to the founders, e.g. \"the deck says ...\", and give the figure the data shows.",
    "valuation_or_advice": "Remove the valuation or advice. You may explain how the mechanism works instead.",
    "unsourced_benchmark": "Name the public source (publisher) for the benchmark, or delete the benchmark.",
}


def revision_brief(issues: list[dict]) -> str:
    """Issues formatted for a revise prompt, each with the action that fixes it."""
    return "\n".join(f"- {i['type']}: '{i['text']}' in \"{i['sentence'][:200]}\"\n  FIX: {FIX_ACTIONS[i['type']]}"
                     for i in issues)


def same_issues(a: dict, b: dict) -> bool:
    """True if two audit results flag the same problems (a revision made no progress)."""
    key = lambda r: sorted((i["type"], i["text"]) for i in r["issues"])
    return key(a) == key(b)


def _has_source(sentence: str) -> bool:
    low = sentence.lower()
    if "http" in low or "appendix" in low:
        return True
    return any(s["publisher"].lower() in low or s["id"] in low for s in data.sources())
