"""Score one founder answer to one investor question.

Two scorers, same output shape:
- ai_score: the persona's LLM evaluator (rich feedback, uses the investor's own rubric).
- rule_score: deterministic, no API call. Used when no key is configured, when the free tier is
  rate limited, or as a fallback if the AI call fails, so the demo never stalls.

Both start from the same code fact-check (vicky.audit): a wrong number caps accuracy no matter what.
"""
import re

from . import audit as auditor
from . import data, metrics

DIMENSIONS = ["accuracy", "evidence", "candor", "clarity"]
DEFAULT_PERSONA = "lead_seed_fund"

EVIDENCE_CUES = [r"\btimes\b", r"\bx\s?12\b", r"\bdivided\b", r"\bover the last\b", r"\bper (month|customer|seat)\b",
                 r"\bbecause\b", r"\bcalculat", r"\bfrom \$?\d", r"\bthat's\b", r"\bwhich (is|means)\b",
                 r"\bbased on\b", r"\bexcluding\b|\bleave out\b|\bwithout\b", r"\bsince\b",
                 r"\bwent from\b", r"\bassum", r"\bon (our|that|this) (plan|basis)\b", r"\bso\b", r"\bto get to\b",
                 r"\bmonths? (to|after|instead)\b", r"\bin (march|april|september|october|november|january)\b"]
CANDOR_CUES = [r"\bbut\b", r"\bhowever\b", r"\bthough\b", r"\bslow(ed|ing)?\b", r"\bweak", r"\bhonest", r"\bfair\b",
               r"\brisk", r"\bwe('re| are) fixing\b", r"\bnot (signed|certain|filed|yet)\b", r"\bhaven't\b",
               r"\bdon't (have|track|know)\b", r"\bisn't\b", r"\btarget, not\b", r"\bmissed\b", r"\bupside\b",
               r"\bworse\b", r"\bimprove\b", r"\bwe('ll| will)\b", r"\bshould\b", r"\blost\b",
               r"\bbetter\b", r"\bmost churn\b", r"\bslipped\b", r"\bif\b", r"\bonly\b"]
NUMBER_WORDS = r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half|a fifth|a third)\b"
BLUFF_CUES = [r"\bconfident\b", r"\bdefinitely\b", r"\bno problem\b", r"\bwon't happen\b", r"\bit won't\b",
              r"\bstrong interest\b", r"\bguarantee", r"\bbest (product|in)\b", r"\bnothing to worry\b",
              r"\bdon't worry\b", r"\beasily\b"]


def question(qid: int) -> dict:
    q = data.question(qid)
    return {"qid": qid, "text": q["question"], "why": q["why"], "strong": q["strong"],
            "weak": q.get("weak", ""), "metrics": q.get("metrics", [])}


def fact_check(answer: str) -> dict:
    from .tools import scenario_facts
    from .journey import scenarios
    report = auditor.audit(answer, extra_known=[scenario_facts(), list(scenarios().values())])
    return {"passed": report.passed, "issues": report.issues, "summary": report.summary(),
            "numbers_checked": report.numbers_checked}


def _hits(patterns: list[str], text: str) -> int:
    return sum(bool(re.search(p, text)) for p in patterns)


def _weighted(scores: dict, persona_key: str) -> float:
    w = data.investor_profiles()[persona_key]["rubric_weights"]
    return round(sum(scores[d] * w[d] for d in DIMENSIONS), 2)


def _right_figures(q: dict) -> str:
    keys = [k for k in q.get("metrics", []) if k in metrics.registry()]
    return "; ".join(f"{metrics.get(k).label} = {metrics.get(k).display()}" for k in keys[:3])


def rule_score(q: dict, answer: str, persona_key: str = DEFAULT_PERSONA) -> dict:
    """Deterministic scoring. Transparent rules, so the founder can see exactly why."""
    low = answer.lower()
    words = len(answer.split())
    fact = fact_check(answer)
    claim_issue = any(i["type"] == "claim_as_fact" for i in fact["issues"])
    if fact["issues"]:
        accuracy = 1 if claim_issue else 2
    elif fact["numbers_checked"]:
        accuracy = 5
    elif re.search(NUMBER_WORDS, low):
        accuracy = 4  # gives figures the audit can't check automatically (e.g. "three months", "4 or 5 a month")
    else:
        accuracy = 2
    evidence = 1 + min(4, _hits(EVIDENCE_CUES, low))
    if not fact["numbers_checked"] and not re.search(NUMBER_WORDS, low):
        evidence = min(evidence, 3)
    candor = max(1, min(5, 2 + min(3, _hits(CANDOR_CUES, low)) - _hits(BLUFF_CUES, low)))
    clarity = 5 if 20 <= words <= 110 else 4 if 12 <= words <= 160 else 3 if words > 160 else 2
    scores = {"accuracy": accuracy, "evidence": evidence, "candor": candor, "clarity": clarity}

    tips = []
    if accuracy <= 2:
        right = _right_figures(q)
        if fact["issues"]:
            bad = ", ".join(i["text"] for i in fact["issues"][:3])
            tips.append(f"Fix the numbers: {bad} doesn't match the data." + (f" Use: {right}." if right else ""))
        else:
            tips.append("Give the number. Investors expect a figure, not a feeling." + (f" Use: {right}." if right else ""))
    if evidence <= 2:
        tips.append("Say how you calculated it, in one line (for example, 'September MRR times 12').")
    if candor <= 2:
        tips.append("Name the weak spot yourself and say what you're doing about it. Bluffing ends meetings.")
    if clarity <= 3:
        tips.append("Keep it to three or four sentences." if words > 110 else "Say a little more: the number, how, the weak spot, the fix.")
    best = max(DIMENSIONS, key=lambda d: scores[d])
    praise = {"accuracy": "Your numbers tie to the data.", "evidence": "You showed how you got the number.",
              "candor": "You were upfront about the weak spot.", "clarity": "Short and clear."}
    return {
        "question": q["text"], "qid": q.get("qid"), "answer": answer, "scores": scores,
        "weighted": _weighted(scores, persona_key),
        "went_well": praise[best] if scores[best] >= 4 else "",
        "improve": " ".join(tips) or "Strong answer. Practise saying it out loud without notes.",
        "stronger_answer": q["strong"], "fact_check": fact, "method": "rule-based",
        "investor_reply": "",
    }


def ai_score(q: dict, answer: str, persona_key: str = DEFAULT_PERSONA, lang: str = "en") -> dict:
    """The persona's LLM evaluator, grounded by the same fact check."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from .llm import get_llm, parse_json
    from .prompts import EVALUATOR, persona_system

    persona = data.investor_profiles()[persona_key]
    fact = fact_check(answer)
    fact_lines = "\n".join(f"- {i['type']}: '{i['text']}' ({i['detail']})" for i in fact["issues"]) or \
        ("- All figures the founder stated tie to the data." if fact["numbers_checked"] else "- The founder stated no figures.")
    prompt = EVALUATOR.format(
        persona_name=persona["name"], weights=persona["rubric_weights"], question=q["text"], why=q["why"],
        strong=q["strong"], answer=answer, fact_check=fact_lines, follow_ups=0, max_follow_ups=0,
        next_question="(this is a single practice question: react in one sentence, no new question)",
        slide="The founder is not pointing at a slide.")
    if lang != "en":  # French mode: same JSON keys, the text values in Canadian French
        from .i18n import ai_instruction
        prompt += ai_instruction(lang) + " Keep the JSON keys in English."
    raw = get_llm(temperature=0.4).invoke([SystemMessage(persona_system(persona)), HumanMessage(prompt)]).content
    result = parse_json(raw)
    if not result or "scores" not in result:
        raise ValueError("The AI evaluator returned something that wasn't valid JSON.")
    scores = {d: max(1, min(5, int(result.get("scores", {}).get(d, 3)))) for d in DIMENSIONS}
    if fact["issues"]:
        scores["accuracy"] = min(scores["accuracy"], 2)
    stronger = result.get("stronger_answer") or q["strong"]
    if not auditor.audit(stronger).passed:  # never show a model answer with an unverifiable figure
        stronger = q["strong"]
    return {
        "question": q["text"], "qid": q.get("qid"), "answer": answer, "scores": scores,
        "weighted": _weighted(scores, persona_key), "went_well": result.get("went_well", ""),
        "improve": result.get("improve", ""), "stronger_answer": stronger, "fact_check": fact,
        "method": "ai", "investor_reply": result.get("investor_reply", ""),
    }


def score(q: dict, answer: str, persona_key: str = DEFAULT_PERSONA, use_ai: bool = True, lang: str = "en") -> dict:
    """AI feedback when available, otherwise (or on any failure) the rule-based scorer."""
    if use_ai:
        try:
            return ai_score(q, answer, persona_key, lang)
        except Exception as e:  # rate limits, timeouts, bad JSON: never stall the founder
            out = rule_score(q, answer, persona_key)
            out["fallback_reason"] = f"{type(e).__name__}: {str(e)[:160]}"
            return out
    return rule_score(q, answer, persona_key)
