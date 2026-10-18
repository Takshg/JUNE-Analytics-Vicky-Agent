"""Investor-prep pack (the Appendix G flow): compute -> draft -> audit -> revise (<= 2) -> done.

The audit notes are kept and shown to the founder, like Appendix H's "Audit notes".
If no LLM is configured, a deterministic pack is built from the claim check instead.
"""
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .. import audit as auditor
from .. import claims, data, metrics
from ..llm import clean, get_llm
from ..prompts import PACK_DRAFT, PACK_REVISE, RULES, vicky_system
from ..tools import fact_sheet, scenario_facts

MAX_REVISIONS = 2
LONG_TIMEOUT = 90  # a full pack is one long generation (~25s per call on the free tier)


class PackState(TypedDict, total=False):
    claims: list
    scenarios: list
    draft: str
    audit: dict
    audit_log: list  # every audit round, for the "Audit notes" section
    revisions: int


def _compute(state: PackState):
    return {"claims": claims.check_all(), "scenarios": scenario_facts(), "audit_log": [], "revisions": 0}


def _claims_text(cs: list) -> str:
    return "\n".join(f"- {c['claim']} -> {c['data_shows']} [{c['status']}]" for c in cs)


def _scenarios_text(ss: list) -> str:
    return "\n".join(
        f"- {s['scenario']}: ARR at Mar 2028 ${s['arr_mar_2028'] / 1e6:.2f}M; cash runs out {s['cash_out_month'] or 'after 2030'}; "
        f"runway after a Jan 2027 close {s['runway_after_close_months']} months" for s in ss)


def _draft(state: PackState):
    prompt = PACK_DRAFT.format(rules=RULES, claims=_claims_text(state["claims"]),
                               scenarios=_scenarios_text(state["scenarios"]), facts=fact_sheet(),
                               missing="; ".join(data.company()["missing_data"]))
    text = get_llm(temperature=0.3, timeout=LONG_TIMEOUT).invoke([SystemMessage(vicky_system()), HumanMessage(prompt)]).content
    return {"draft": clean(text)}


def _audit(state: PackState):
    r = auditor.audit(state["draft"], extra_known=[state["scenarios"], state["claims"]])
    result = {"round": len(state["audit_log"]) + 1, "passed": r.passed, "issues": r.issues, "summary": r.summary()}
    return {"audit": result, "audit_log": [*state["audit_log"], result]}


def _route(state: PackState):
    log = state["audit_log"]
    stuck = len(log) > 1 and auditor.same_issues(log[-1], log[-2])  # the last revision fixed nothing
    if not state["audit"]["passed"] and state["revisions"] < MAX_REVISIONS and not stuck:
        return "revise"
    return END


def _revise(state: PackState):
    issues = auditor.revision_brief(state["audit"]["issues"])
    text = get_llm(temperature=0.1, timeout=LONG_TIMEOUT).invoke([SystemMessage(vicky_system()),
                                            HumanMessage(PACK_REVISE.format(issues=issues, pack=state["draft"]))]).content
    return {"draft": clean(text), "revisions": state["revisions"] + 1}


def build():
    g = StateGraph(PackState)
    g.add_node("compute", _compute)
    g.add_node("draft_pack", _draft)
    g.add_node("audit_pack", _audit)
    g.add_node("revise", _revise)
    g.add_edge(START, "compute")
    g.add_edge("compute", "draft_pack")
    g.add_edge("draft_pack", "audit_pack")
    g.add_conditional_edges("audit_pack", _route, {"revise": "revise", END: END})
    g.add_edge("revise", "audit_pack")
    return g.compile()


def run() -> dict:
    out = build().invoke({})
    return {"markdown": out["draft"], "audit_log": out["audit_log"], "claims": out["claims"],
            "scenarios": out["scenarios"], "source": "llm"}


def deterministic() -> dict:
    """Fallback pack with no LLM: built straight from the claim check and metrics."""
    m = metrics.get
    cs = claims.check_all()
    ss = scenario_facts()
    failing = [c for c in cs if c["status"] in (claims.FIX, claims.REMOVE)]
    md = [
        "## Readiness",
        f"Not ready for a lead investor yet. {len(failing)} of the {len(cs)} deck claims need fixing before a first "
        "meeting and the rest need rewording. The business is stronger than some claims suggest: growth and capital "
        "efficiency are real.",
        "## Top three questions you will be asked",
        f"1. \"Your deck says 1% churn. The data says {m('logo_churn_12m').display()} a month over the last year. Which is it?\" (historical)",
        f"2. \"Growth was about {m('cmgr_12m').display()} a month over the year but {m('cmgr_3m').display()} from July to September. What happened?\" (historical)",
        f"3. \"How long does $4M last if growth stays at what you've actually done?\" ({ss[1]['runway_after_close_months']} months on historical drivers vs "
        f"{ss[0]['runway_after_close_months']} on the plan; forecast)",
        "## Strengths",
        f"- Capital efficient: burn multiple {m('burn_multiple').display()} ({m('burn_multiple_ex_sred').display()} without SR&ED). (historical; David Sacks definition)",
        f"- Non-dilutive funding: {m('srred_total').display()} of SR&ED refunds received. (historical)",
        f"- Monthly-plan customers past six months churn at about {m('mature_churn_monthly_plans').display()} a month. (reported in pack)",
        "## Weaknesses",
        f"- Gross margin is {m('gross_margin_incl_cs').display()} once customer success is counted, not 92%. (historical)",
        f"- Net revenue retention about {m('nrr').display()}. (reported in pack)",
        f"- Northern Comfort Group is {m('ncg_share_of_mrr').display()} of MRR and renews March 2027. (historical)",
        f"- Fully loaded CAC {m('cac_fully_loaded').display()}, payback about {m('cac_payback_months').value:.0f} months. (historical)",
        "- No finance function, CRM, pipeline or win/loss data. (founder-provided)",
        "## Next actions before the first meeting",
        "1. Rebuild the forecast with a three-month rep ramp, 2% churn and Northern Comfort flat at 260 seats; keep the current plan as upside.",
        "2. Move customer success into cost of revenue and restate gross margin.",
        "3. Recalculate CAC with all sales and marketing costs.",
        "4. Hold spending at today's level until a term sheet is signed.",
        "5. Build a bottom-up market size with sourced business counts.",
        "6. Set up a CRM so pipeline and win/loss data exist when investors ask.",
    ]
    text = "\n\n".join(md)
    r = auditor.audit(text, extra_known=[ss, cs])
    return {"markdown": text, "claims": cs, "scenarios": ss, "source": "deterministic",
            "audit_log": [{"round": 1, "passed": r.passed, "issues": r.issues, "summary": r.summary()}]}
