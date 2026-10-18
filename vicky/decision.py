"""Hierarchical decision model for Ask Vicky. Everything here is code; the LLM planner in
vicky.graphs.coach only proposes, and validate_plan() decides what actually runs.

Level 1  policy gate        gate()              regex, no LLM
Level 2  intent             heuristic_intent()  keyword fallback for the LLM planner
Level 3  action plan        validate_plan()     checks the planner's tools/args, adds what the intent requires
"""
import calendar
import re

from . import data, metrics, tools

MAX_TOOLS = 4
SEED_TARGET = "2027-01"

# --- Level 1: policy gate --------------------------------------------------------------------

POLICY_RULES = [
    ("valuation", [
        r"\bwhat (valuation|pre-?money|post-?money|cap)\b.*\b(should|could|can|would)\b",
        r"\b(should|could|can) (we|i)\b.*\b(raise|ask for|set|price)\b.*\b(valuation|cap|pre-?money|post-?money)\b",
        r"\bhow much (are we|is tidewell|is the company|is it) worth\b",
        r"\b(value|valuation) (of|for) (tidewell|us|the company|our company)\b",
        r"\b(fair|right|good|reasonable) (valuation|cap|pre-?money|post-?money)\b",
        r"\bwhat (are we|is tidewell) worth\b",
    ], "Vicky does not recommend a valuation. She can explain how valuation, caps, dilution and SAFE "
       "conversion work, and what drives an investor's view (growth, retention, efficiency)."),
    ("investment_advice", [
        r"\bshould (i|we|investors?|someone|anyone) (invest|buy|sell)\b",
        r"\bis (tidewell|this|it) a good investment\b",
        r"\bwould you invest\b",
        r"\bshould (we|i) (accept|take|sign) (the|this|their|a)? ?(term ?sheet|offer|deal)\b",
    ], "Vicky does not give investment advice or tell founders which offer to accept. She can explain the "
       "terms and what each one means for the founders."),
    ("competitor_data", [
        r"\b(jobber|housecall pro|servicetitan)('s)?\b.*\b(revenue|arr|mrr|churn|pricing|price|customers|metrics|"
        r"numbers|margin|growth|valuation|funding)\b",
        r"\b(revenue|arr|mrr|churn|pricing|customers|metrics|numbers|margin|growth)\b.*\b(of|for|at) "
        r"(jobber|housecall pro|servicetitan)\b",
    ], "The data pack has no competitor figures, so Vicky won't quote any. She can help the founders frame "
       "their differentiation using Tidewell's own data."),
]


# what the boundary answer can still offer, per rule
POLICY_TOOLS = {
    "valuation": [{"name": "get_investor_question", "args": {"question_id": 15}},
                  {"name": "lookup_glossary", "args": {"term": "valuation cap"}}],
    "investment_advice": [{"name": "get_metrics", "args": {"keys": ["arr", "cmgr_12m", "burn_multiple", "runway_months"]}}],
    "competitor_data": [{"name": "get_investor_question", "args": {"question_id": 13}}],
}


def policy_plan(hit: dict) -> dict:
    return {"intent": "policy_boundary", "tools": POLICY_TOOLS[hit["rule"]], "why": f"policy gate: {hit['rule']}"}


def gate(question: str) -> dict | None:
    """Return the policy rule a question trips, or None if it may proceed."""
    q = question.lower()
    for rule, patterns, guidance in POLICY_RULES:
        for p in patterns:
            if re.search(p, q):
                return {"rule": rule, "pattern": p, "guidance": guidance}
    return None


# --- Level 2: intents ------------------------------------------------------------------------

INTENTS = {
    "explain_metric": {
        "description": "What a Tidewell number is, how it is calculated, or why it moved.",
        "required": ["get_metrics"],
        "playbook": "State the figure with its provenance label, show the calculation in one line from the tool "
                    "inputs, explain what it means in plain language, then say what an investor will read into it "
                    "and what the founders should do about it.",
    },
    "challenge_claim": {
        "description": "Whether a deck claim or a founder statement holds up against the data.",
        "required": ["check_deck_claim"],
        "playbook": "Quote the claim and attribute it to the deck. Compare it with what the data shows, name the "
                    "gap and why it matters to an investor, then give the corrected wording from the tool's "
                    "suggested fix.",
    },
    "what_if": {
        "description": "A hypothetical: change an assumption (churn, ramp, round timing, Northern Comfort, "
                       "spending) and see the effect on cash and runway.",
        "required": ["run_scenario"],
        "playbook": "Say which assumptions changed and that the results are FORECAST. Compare the scenario with "
                    "the founders' plan on runway, cash low point and ARR, using only the tool's numbers. End "
                    "with the decision this implies for the founders.",
    },
    "concept": {
        "description": "A finance or fundraising term or mechanism in general (SAFE, dilution, NRR, burn multiple).",
        "required": ["lookup_glossary"],
        "playbook": "Define the term in one or two plain sentences, then use Tidewell's own number or example "
                    "from the tools to make it concrete. Avoid jargon in the definition.",
    },
    "investor_prep": {
        "description": "How to answer an investor question, prepare for a meeting, or what investors will ask.",
        "required": ["get_investor_question"],
        "playbook": "Say why investors ask this question, contrast the weak and strong answer, then draft a "
                    "strong answer in the founders' voice using only tool numbers, with the caveat they should "
                    "volunteer before being asked.",
    },
    "missing_data": {
        "description": "Data that is not in the pack, or a figure that can't be computed from it.",
        "required": ["company_facts"],
        "playbook": "Say plainly that the figure is not in the data pack. Explain what file or data would fill "
                    "the gap, what can be said from the data that does exist, and how the founders should "
                    "answer an investor in the meantime.",
    },
    "policy_boundary": {
        "description": "A request for a valuation, investment advice or competitor figures.",
        "required": [],
        "playbook": "Decline the specific request in one sentence and say why. Then help with the closest thing "
                    "that is allowed: explain the mechanism or the drivers an investor looks at, using tool "
                    "numbers.",
    },
    "general": {
        "description": "Anything else about Tidewell, the raise or the founders' preparation.",
        "required": [],
        "playbook": "Answer directly using tool numbers, label provenance, and finish with one concrete next "
                    "step for the founders.",
    },
}


def catalog_text() -> str:
    """Intent catalog for the planner prompt."""
    return "\n".join(f"- {name}: {spec['description']}" for name, spec in INTENTS.items())


# One row per topic: what the question is about -> which data answers it.
# (regex, metric keys, deck claim id, Appendix D question id, find_sources topic)
TOPICS = [
    (r"\barr\b|annual recurring|run[- ]rate", ["arr", "arr_incl_onboarding", "mrr"], "arr", 1, "arr"),
    (r"\bmrr\b|monthly recurring", ["mrr", "arr"], "arr", 1, "arr"),
    (r"grow|growth|cmgr|month over month|\bmom\b", ["cmgr_12m", "cmgr_3m", "cmgr_12m_ex_ncg"], "growth", 2, "metrics"),
    (r"churn|cancel|retain|retention|lose customers", ["logo_churn_12m", "logo_churn_6m", "early_churn_monthly_plans",
                                                       "mature_churn_monthly_plans"], "churn", 3, "churn"),
    (r"\bnrr\b|net revenue retention|net retention|expansion", ["nrr", "grr"], "nrr", 4, "nrr"),
    (r"\bgrr\b|gross revenue retention", ["grr", "nrr"], "nrr", 4, "nrr"),
    (r"gross margin|\bmargin\b|cogs|cost of revenue", ["gross_margin_booked", "gross_margin_incl_cs"], "gross_margin", 5,
     "gross_margin"),
    (r"\bcac\b|acquisition cost|cost to (win|acquire)|payback", ["cac_fully_loaded", "cac_marketing_only",
                                                                 "cac_payback_months"], "cac", 6, "cac"),
    (r"price increase|pricing|\bprice\b", ["mrr"], None, 7, "saas"),
    (r"\bramp|account exec|\baes?\b|sales rep|quota", ["ae_ramp_months_actual", "new_customers_ltm"], None, 8, "efficiency"),
    (r"northern comfort|\bncg\b|largest customer|concentration", ["ncg_mrr", "ncg_share_of_mrr", "cmgr_12m_ex_ncg"],
     "ncg", 9, "smb"),
    (r"runway|run out|cash out|out of cash|how long.*(last|money)", ["cash", "burn_monthly", "runway_months",
                                                                     "plan_runway_after_close"], "runway", 10, "runway"),
    (r"\bburn\b(?! multiple)|spend(ing)? per month", ["burn_monthly", "net_burn_12m", "cash"], None, 10, "burn"),
    (r"burn multiple|capital efficien", ["burn_multiple", "burn_multiple_ex_sred", "net_new_arr_12m"], None, 14,
     "burn_multiple"),
    (r"use of funds|why \$?4 ?m|the raise|\$4 ?m|how much.*raise", ["cash", "plan_runway_after_close", "plan_arr_end"],
     None, 10, "seed"),
    (r"slip|delay|takes longer|later than|round (takes|is late)", ["runway_months", "plan_runway_after_close"], None, 11,
     "runway"),
    (r"\btam\b|\bsam\b|\bsom\b|addressable|market size", [], "tam", 12, "tam"),
    (r"compet|jobber|housecall|servicetitan|differentiat", [], None, 13, "market"),
    (r"\brisk|milestone|series a|what will (this|the) round", ["plan_arr_end", "plan_runway_after_close"], None, 14, "seed"),
    (r"sr&ed|sred|tax credit", ["srred_total", "burn_multiple_ex_sred"], None, None, "sred"),
    (r"onboarding fee", ["onboarding_ltm", "arr_incl_onboarding"], "arr", 1, "arr"),
    (r"\bsafe\b|dilution|valuation|\bcap\b|pre-?money|post-?money", [], None, 15, "safe"),
    (r"\bcash\b|bank", ["cash", "burn_monthly"], None, None, "cash"),
]


def topics(question: str) -> list[tuple]:
    q = question.lower()
    return [t for t in TOPICS if re.search(t[0], q)]


def metric_keys(question: str) -> list[str]:
    reg = metrics.registry()
    keys = [k for t in topics(question) for k in t[1]]
    return [k for k in dict.fromkeys(keys) if k in reg]


def claim_ids(question: str) -> list[str]:
    return list(dict.fromkeys(t[2] for t in topics(question) if t[2]))


def question_ids(question: str) -> list[int]:
    return list(dict.fromkeys(t[3] for t in topics(question) if t[3]))


def source_topics(question: str) -> list[str]:
    return list(dict.fromkeys(t[4] for t in topics(question) if t[4]))


def glossary_term(question: str) -> str | None:
    """Longest glossary entry named in the question, matched on its short name or acronym."""
    q = question.lower()
    best = None
    for entry in data.glossary():
        names = [entry.lower().split(" (")[0]]
        acronym = re.search(r"\(([^)]+)\)", entry)
        if acronym:
            names.append(acronym.group(1).lower())
        if any(re.search(rf"\b{re.escape(n)}\b", q) for n in names) and (not best or len(entry) > len(best)):
            best = entry
    return best


INTENT_RULES = [
    ("what_if", r"\bwhat if\b|\bwhat happens\b|\bsuppose\b|\bscenario\b|\bif (the |our )?(round|churn|ramp|we|northern|ncg)"
                r"|\bslips?\b|\bdelay|\bimagine\b|\bassum(e|ing) (churn|the round|a)"),
    ("challenge_claim", r"\bdeck\b|\bslide\b|\bclaim|\bis it (true|right|fair|accurate)\b|\bcan (we|i) (say|claim)\b"
                        r"|\bhold up\b|\bdefensible\b|\bbelieve (the|our)\b"),
    ("investor_prep", r"\binvestors?\b.*\b(ask|think|push|want|expect|react|worry)|\bhow (should|do) (we|i) (answer|respond|"
                      r"explain|pitch|present|handle)\b|\bprep(are)?\b|\bmeeting\b|\bpitch\b|\btough questions?\b"),
    ("missing_data", r"\bmissing\b|\bdon'?t have\b|\bnot in the (data|pack)\b|\bdata gap|\bcohort\b|\bcan(no|')?t (you )?"
                     r"(compute|calculate)\b|\bwhy (isn'?t|is there no)\b"),
    ("concept", r"\bwhat (is|are|does) (an? |the )?[\w&\- ]+ (mean|work)\b|\bwhat (is|are) (an? )?(safe|nrr|grr|cac|"
                r"tam|arr|mrr|burn multiple|dilution|cap table|option pool|valuation cap|pre-?money|post-?money|sr&ed)\b"
                r"|\bexplain (what|how)\b.*\b(works?|means?)\b|\bdefine\b|\bdefinition\b|\bin plain (english|language)\b"),
]


def heuristic_intent(question: str) -> tuple[str, str]:
    """Keyword fallback for the planner. Returns (intent, why)."""
    q = question.lower()
    if gate(question):
        return "policy_boundary", "policy gate matched"
    for intent, pattern in INTENT_RULES:
        m = re.search(pattern, q)
        if m:
            return intent, f"keyword '{m.group(0).strip()}'"
    if metric_keys(question):
        return "explain_metric", f"names a metric ({', '.join(metric_keys(question)[:2])})"
    if question_ids(question):
        return "investor_prep", f"matches likely investor question {question_ids(question)[0]}"
    if glossary_term(question):
        return "concept", f"glossary term '{glossary_term(question)}'"
    return "general", "no specific signal"


# --- Level 3: scenario arguments and plan validation -----------------------------------------

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})


def _add_months(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    y, m = divmod(y * 12 + m - 1 + n, 12)
    return f"{y}-{m + 1:02d}"


def scenario_args(question: str) -> dict:
    """run_scenario arguments named in a what-if question. Only what the founder actually said."""
    q = question.lower()
    args = {}
    churn = (re.search(r"churn\D{0,25}?(\d+(?:\.\d+)?)\s?%", q) or
             re.search(r"(\d+(?:\.\d+)?)\s?%\s*(?:monthly |a month |per month )?churn", q))
    if churn:
        args["monthly_churn"] = round(float(churn.group(1)) / 100, 4)
    ramp = (re.search(r"(\d+)[- ]months? ramp", q) or
            re.search(r"ramp\D{0,25}?(\d+)\s?months?", q))
    if ramp:
        args["ae_ramp_months"] = int(ramp.group(1))
    deals = re.search(r"(\d+(?:\.\d+)?)\s?(?:new )?(?:deals|customers|closes)\s?(?:a|per) month(?: per| each| an)? ?(?:ae|rep)",
                      q) or re.search(r"(?:ae|rep)s?\D{0,25}?(\d+(?:\.\d+)?)\s?(?:new )?(?:deals|customers)", q)
    if deals:
        args["ae_new_per_month"] = float(deals.group(1))
    uptake = re.search(r"(\d+)\s?%\s*(?:of (?:customers|the base) )?(?:accept|take|agree to)", q)
    if uptake:
        args["price_increase_uptake"] = round(float(uptake.group(1)) / 100, 4)

    slip = re.search(r"(?:slips?|delay(?:ed|s)?|late|later)\D{0,15}?(\d+)\s?months?", q) or \
        re.search(r"(\d+)\s?months?\s*(?:late|later|delay)", q)
    month = re.search(rf"\b({'|'.join(sorted(MONTHS, key=len, reverse=True))})\b\.?\s*(20\d\d)?", q)
    if slip:
        args["seed_month"] = _add_months(SEED_TARGET, int(slip.group(1)))
    elif month and re.search(r"round|close|seed|raise|funding|money|slip|land", q):
        m = MONTHS[month.group(1)]
        year = int(month.group(2)) if month.group(2) else (2026 if m >= 10 else 2027)
        args["seed_month"] = f"{year}-{m:02d}"

    if re.search(r"(northern comfort|\bncg\b|largest customer).{0,40}(leave|leaves|churn|walk|lose|lost|cancel|"
                 r"(don'?t|doesn'?t|not) renew)|(lose|lost|losing) (northern comfort|ncg|our largest customer)", q):
        args["ncg_renewal_seats"] = 0
    if re.search(r"\b(hold|freeze|pause|delay|wait on)\w*\b.{0,25}\b(spend|spending|hiring|hires|costs)", q):
        args["hold_spend_until_close"] = True
    if re.search(r"historical|current (rates|trends|drivers)|today'?s (rates|numbers)|if nothing changes", q):
        args["base"] = "Historical drivers"
    return args


TOOLS = {t.name: t for t in tools.ALL_TOOLS}
CLAIM_IDS = {"arr", "growth", "gross_margin", "churn", "nrr", "cac", "tam", "ncg", "runway", "all"}
SCENARIO_FIELDS = {"monthly_churn": float, "ae_ramp_months": int, "ae_new_per_month": float, "ncg_renewal_seats": int,
                   "price_increase_uptake": float, "seed_month": str, "hold_spend_until_close": bool, "base": str}
DEFAULT_METRICS = ["arr", "cmgr_12m", "burn_monthly", "runway_months"]


def _clean_args(name: str, args: dict, question: str) -> tuple[dict | None, str | None]:
    """Coerce one tool call's arguments. Returns (args, note); args None means drop the call."""
    args = dict(args or {})
    if name == "get_metrics":
        keys = args.get("keys") or []
        keys = [keys] if isinstance(keys, str) else list(keys)
        reg = metrics.registry()
        good = [k for k in keys if k in reg]
        if not good:
            return {"keys": metric_keys(question) or DEFAULT_METRICS}, f"unknown metric keys {keys}; used keyword map"
        return {"keys": good}, (f"dropped unknown keys {sorted(set(keys) - set(good))}" if len(good) < len(keys) else None)
    if name == "check_deck_claim":
        cid = str(args.get("claim_id", "")).lower().strip()
        if cid not in CLAIM_IDS:
            ids = claim_ids(question)
            return {"claim_id": ids[0] if ids else "all"}, f"unknown claim id '{cid}'; used keyword map"
        return {"claim_id": cid}, None
    if name == "run_scenario":
        out, dropped, rescaled = {}, [], []
        for k, v in args.items():
            typ = SCENARIO_FIELDS.get(k)
            if typ is None or v is None:
                dropped.append(k)
                continue
            try:
                v = (str(v).lower() in ("true", "1", "yes")) if typ is bool else typ(v)
            except (TypeError, ValueError):
                dropped.append(k)
                continue
            if k in ("monthly_churn", "price_increase_uptake") and v > 1:
                v = round(v / 100, 4)  # planner gave a percent
                rescaled.append(k)
            if k == "seed_month" and not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", v):
                dropped.append(k)
                continue
            if k == "base" and v not in ("Founders' plan", "Historical drivers"):
                v = "Historical drivers" if "hist" in v.lower() else "Founders' plan"
            out[k] = v
        # what the founder literally said wins over the planner's reading of it
        parsed = scenario_args(question)
        changed = [k for k in parsed if out.get(k) != parsed[k]]
        out.update(parsed)
        notes = []
        if dropped:
            notes.append(f"dropped invalid args {dropped}")
        if rescaled:
            notes.append(f"read {rescaled} as percent")
        if changed:
            notes.append(f"set {changed} from the question text")
        return out, "; ".join(notes) or None
    if name == "get_investor_question":
        try:
            qid = int(args.get("question_id"))
        except (TypeError, ValueError):
            qid = 0
        if not 1 <= qid <= len(data.questions()):
            ids = question_ids(question)
            return ({"question_id": ids[0]}, f"invalid question id; used keyword map") if ids else (None, "no matching question")
        return {"question_id": qid}, None
    if name in ("lookup_glossary", "find_sources"):
        key = "term" if name == "lookup_glossary" else "topic"
        val = str(args.get(key) or "").strip()
        if not val:
            val = (glossary_term(question) if name == "lookup_glossary" else next(iter(source_topics(question)), None)) or ""
            if not val:
                return None, f"no {key} given or found"
            return {key: val}, f"{key} filled from the question"
        return {key: val}, None
    return {}, None  # list_metric_keys, company_facts take no arguments


def default_call(tool: str, question: str) -> dict | None:
    """The call code makes when an intent needs a tool the planner left out."""
    if tool == "get_metrics":
        return {"name": tool, "args": {"keys": metric_keys(question) or DEFAULT_METRICS}}
    if tool == "check_deck_claim":
        ids = claim_ids(question)
        return {"name": tool, "args": {"claim_id": ids[0] if ids else "all"}}
    if tool == "run_scenario":
        return {"name": tool, "args": scenario_args(question)}
    if tool == "lookup_glossary":
        term = glossary_term(question)
        return {"name": tool, "args": {"term": term}} if term else None
    if tool == "get_investor_question":
        ids = question_ids(question)
        return {"name": tool, "args": {"question_id": ids[0]}} if ids else None
    if tool == "find_sources":
        st = source_topics(question)
        return {"name": tool, "args": {"topic": st[0]}} if st else None
    if tool in ("company_facts", "list_metric_keys"):
        return {"name": tool, "args": {}}
    return None


def validate_plan(plan: dict | None, question: str) -> tuple[dict, list[dict]]:
    """Check a planner proposal and make it safe to run.

    plan: {"intent": str, "tools": [{"name", "args"}], "why": str} from the LLM, or None.
    Returns (plan, notes). Each note is {"level", "decision", "by"} for the decision trace.
    """
    notes = []
    plan = plan if isinstance(plan, dict) else {}
    intent = plan.get("intent")
    if intent not in INTENTS:
        intent, why = heuristic_intent(question)
        notes.append({"level": "intent", "decision": f"{intent} ({why})", "by": "fallback"})

    calls = []
    for call in plan.get("tools") or []:
        if not isinstance(call, dict) or call.get("name") not in TOOLS:
            notes.append({"level": "plan", "decision": f"dropped unknown tool {call!r:.60}", "by": "code"})
            continue
        args, note = _clean_args(call["name"], call.get("args") or {}, question)
        if args is None:
            notes.append({"level": "plan", "decision": f"dropped {call['name']}: {note}", "by": "code"})
            continue
        if note:
            notes.append({"level": "plan", "decision": f"{call['name']}: {note}", "by": "code"})
        new = {"name": call["name"], "args": args}
        if new not in calls:
            calls.append(new)

    for tool in INTENTS[intent]["required"]:
        if not any(c["name"] == tool for c in calls):
            call = default_call(tool, question)
            if call:
                calls.insert(0, call)
                notes.append({"level": "plan", "decision": f"added {tool}{call['args'] or ''}: required for {intent}",
                              "by": "code"})
    # an investor-prep answer that quotes expectations needs a source to cite
    if intent == "investor_prep" and not any(c["name"] == "find_sources" for c in calls):
        call = default_call("find_sources", question)
        if call:
            calls.append(call)
            notes.append({"level": "plan", "decision": f"added find_sources{call['args']}: cite investor expectations",
                          "by": "code"})

    if not calls and intent != "policy_boundary":
        call = default_call("get_metrics" if metric_keys(question) else "company_facts", question)
        calls.append(call)
        notes.append({"level": "plan", "decision": f"added {call['name']}{call['args'] or ''}: no tools planned",
                      "by": "code"})

    if len(calls) > MAX_TOOLS:
        notes.append({"level": "plan", "decision": f"trimmed {len(calls)} tool calls to {MAX_TOOLS}", "by": "code"})
        calls = calls[:MAX_TOOLS]
    return {"intent": intent, "tools": calls, "why": plan.get("why", "")}, notes


def heuristic_plan(question: str) -> dict:
    """A full plan with no LLM: used when the planner fails or returns nothing usable."""
    intent, why = heuristic_intent(question)
    return {"intent": intent, "tools": [], "why": f"keyword fallback: {why}"}
