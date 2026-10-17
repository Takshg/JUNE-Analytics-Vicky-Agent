"""Tools the agents call. Each returns data computed in code, with provenance attached."""
import json

from langchain_core.tools import tool

from . import claims, data, forecast, metrics


def fact_sheet() -> str:
    """Compact list of every metric, given to the LLM so it never has to invent a number."""
    lines = []
    for m in metrics.registry().values():
        note = f" NOTE: {m.note}" if m.note else ""
        lines.append(f"- {m.key}: {m.label} = {m.display()} [{m.provenance}; {m.ref}]{note}")
    return "\n".join(lines)


def scenario_facts() -> list[dict]:
    """Founders' plan vs historical drivers, used as known numbers by the auditor."""
    return forecast.compare(forecast.founders_plan(), forecast.historical_drivers())


def _dump(obj) -> str:
    return json.dumps(obj, default=lambda o: float(o) if hasattr(o, "__float__") else str(o), indent=1)


@tool
def get_metrics(keys: list[str]) -> str:
    """Get Tidewell metrics by key, with formula, inputs and provenance (historical, forecast or
    reported_in_pack). Call list_metric_keys first if unsure of the key."""
    reg = metrics.registry()
    out = {k: reg[k].to_dict() for k in keys if k in reg}
    missing = [k for k in keys if k not in reg]
    if missing:
        out["_missing"] = f"No metric for {missing}. Say the data is not available rather than estimating."
    return _dump(out)


@tool
def list_metric_keys() -> str:
    """List every available metric key and its label."""
    return "\n".join(f"{m.key}: {m.label}" for m in metrics.registry().values())


@tool
def check_deck_claim(claim_id: str) -> str:
    """Check one claim from the founders' deck against the data. claim_id is one of:
    arr, growth, gross_margin, churn, nrr, cac, tam, ncg, runway. Use 'all' for every claim."""
    if claim_id == "all":
        return _dump([{k: c[k] for k in ("claim", "data_shows", "status", "suggested_fix")} for c in claims.check_all()])
    return _dump(claims.check(claim_id))


@tool
def run_scenario(monthly_churn: float | None = None, ae_ramp_months: int | None = None,
                 ae_new_per_month: float | None = None, ncg_renewal_seats: int | None = None,
                 price_increase_uptake: float | None = None, seed_month: str | None = None,
                 hold_spend_until_close: bool | None = None, base: str = "Founders' plan") -> str:
    """Rerun the 18-month forecast with different assumptions and compare with the founders' plan.
    monthly_churn as a fraction (0.02 = 2%). seed_month as 'YYYY-MM'. ncg_renewal_seats 0 means
    Northern Comfort leaves. base is "Founders' plan" or "Historical drivers". Results are FORECAST."""
    overrides = {k: v for k, v in locals().items() if v is not None and k != "base"}
    start = forecast.PRESETS.get(base, forecast.founders_plan)()
    s = forecast.with_overrides(start, name="Custom scenario", **overrides)
    return _dump({"overrides": overrides, "results": forecast.compare(forecast.founders_plan(), s)})


@tool
def lookup_glossary(term: str) -> str:
    """Plain-English definition of a finance or fundraising term, with Tidewell's example."""
    g = data.glossary()
    t = term.lower()
    hits = {k: v for k, v in g.items() if t in k.lower() or k.lower().split(" (")[0] in t}
    return _dump(hits or {"_missing": f"'{term}' is not in the glossary."})


@tool
def find_sources(topic: str) -> str:
    """Public sources (Appendix F) to cite for an investor expectation or benchmark, e.g. 'burn',
    'churn', 'tam', 'safe', 'deck', 'canada', 'runway'. Cite the publisher and URL."""
    t = topic.lower()
    hits = [s for s in data.sources() if any(t in x or x in t for x in s["topics"]) or t in s["about"].lower()]
    return _dump([{k: s[k] for k in ("publisher", "title", "url", "about")} for s in hits[:5]] or
                 {"_missing": "No source in the pack for this topic. Do not quote a benchmark."})


@tool
def get_investor_question(question_id: int) -> str:
    """One of the 15 likely investor questions (Appendix D) with why investors ask it and a weak vs
    strong answer."""
    return _dump(data.question(question_id))


@tool
def company_facts() -> str:
    """Tidewell's company facts: product, pricing, team, funding, the raise, use of funds, hiring
    plan, bookkeeping policies, and the data that is MISSING from the pack."""
    return _dump(data.company())


ALL_TOOLS = [get_metrics, list_metric_keys, check_deck_claim, run_scenario, lookup_glossary,
             find_sources, get_investor_question, company_facts]
