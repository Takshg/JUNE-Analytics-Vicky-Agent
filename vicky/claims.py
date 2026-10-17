"""Checks each claim in the founders' draft deck against the metrics engine. No LLM involved."""
from . import data, forecast, metrics

FIX, REWORD, REMOVE, UPSIDE, OK = "Fix", "Reword", "Remove or source", "Show as upside", "Supported"


def _check(claim: dict) -> dict:
    m = metrics.get
    cid = claim["id"]
    if cid == "arr":
        shows = f"{m('arr').display()} (MRR {m('mrr').display()} x 12). The claim is total revenue x 12, which includes one-time onboarding fees."
        status, fix = FIX, f"\"{m('arr').display()} ARR\", with onboarding fees ({m('onboarding_ltm').display()} last 12 months) shown separately."
        keys = ["arr", "arr_incl_onboarding"]
    elif cid == "growth":
        shows = f"About {m('cmgr_12m').display()} a month over 12 months ({m('cmgr_12m_ex_ncg').display()} without Northern Comfort), but {m('cmgr_3m').display()} over the last 3 months."
        status, fix = REWORD, "\"MRR grew ~9% a month compounded over the last 12 months\", and be ready to explain the slowdown to ~5%."
        keys = ["cmgr_12m", "cmgr_3m", "cmgr_12m_ex_ncg"]
    elif cid == "gross_margin":
        shows = f"{m('gross_margin_booked').display()} as booked, but {m('gross_margin_incl_cs').display()} once customer success salaries are counted in cost of revenue."
        status, fix = FIX, "Move customer success into cost of revenue and quote ~74%, explaining the restatement."
        keys = ["gross_margin_booked", "gross_margin_incl_cs"]
    elif cid == "churn":
        shows = f"{m('logo_churn_12m').display()} a month over 12 months; {m('logo_churn_6m').display()} over the last 6."
        status, fix = FIX, "Quote 2.0% (12 months) and 1.6% (6 months) and show the early-life churn plan."
        keys = ["logo_churn_12m", "logo_churn_6m"]
    elif cid == "nrr":
        shows = f"About {m('nrr').display()} NRR and {m('grr').display()} gross retention (stated in the pack; not recomputed here)."
        status, fix = FIX, "Quote ~88% NRR, say what is driving it, and what you're doing to raise it."
        keys = ["nrr", "grr"]
    elif cid == "cac":
        shows = (f"{m('cac_marketing_only').display()} counts marketing programs only. Fully loaded CAC is {m('cac_fully_loaded').display()}, "
                 f"payback about {m('cac_payback_months').value:.0f} months on a margin that includes support.")
        status, fix = FIX, "Quote fully loaded CAC (~$3,200) and ~9-10 month payback."
        keys = ["cac_fully_loaded", "cac_marketing_only", "cac_payback_months"]
    elif cid == "tam":
        shows = "No source or method given. The data pack has no market sizing."
        status, fix = REMOVE, "Build bottom-up: trades businesses with 3-30 technicians (Statistics Canada, US Census Bureau) x seats x price."
        keys = []
    elif cid == "ncg":
        shows = f"Northern Comfort is {m('ncg_share_of_mrr').display()} of MRR at 260 seats. The 600-seat expansion is verbal; nothing is signed. Renews March 2027."
        status, fix = UPSIDE, "Keep the base plan at 260 seats and show the expansion as upside."
        keys = ["ncg_share_of_mrr"]
    elif cid == "runway":
        hist = forecast.summarize(forecast.historical_drivers())
        shows = (f"About {m('plan_runway_after_close').value:.0f} months on the founders' own plan; "
                 f"about {hist['runway_after_close_months']} months on historical drivers (Vicky scenario model). "
                 f"The plan reaches {m('plan_arr_end').display()} ARR by March 2028, only if every assumption holds.")
        status, fix = REWORD, "\"~22 months on our plan, ~17 if growth stays at historical rates; here are the milestones and where we'd slow hiring.\""
        keys = ["plan_runway_after_close", "plan_arr_end"]
    else:
        raise ValueError(cid)
    return {
        "id": cid, "claim": claim["claim"], "data_shows": shows, "status": status, "suggested_fix": fix,
        "why_investors_care": claim["why"], "question_id": claim["question"],
        "evidence": [metrics.get(k).to_dict() for k in keys],
    }


def check_all() -> list[dict]:
    return [_check(c) for c in data.pack("deck_claims")]


def check(claim_id: str) -> dict:
    return next(_check(c) for c in data.pack("deck_claims") if c["id"] == claim_id)
