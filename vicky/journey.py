"""The founder journey: where you are -> what's in the way -> where you want to be.

June told us founders are stressed and overloaded, so the first screen shows only:
three numbers, the goal, the top three roadblocks (at least one a blind spot the founder
probably doesn't know about) and a readiness score that rises as they practise.

Everything here is computed in code from the metrics engine and the scenario model.
No LLM is involved, and every figure carries its provenance.
"""
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from . import data, forecast, metrics

HIST, FCST, CLAIM, REPORTED = metrics.HISTORICAL, metrics.FORECAST, metrics.FOUNDER_CLAIM, metrics.REPORTED

GOAL_ARR = 5_000_000  # founders' stated goal: "Series A at $5M ARR" (Appendix A)


@dataclass
class Fact:
    """One line of evidence: a plain sentence, its provenance and where it comes from."""
    text: str
    provenance: str
    ref: str


@dataclass
class Roadblock:
    id: str
    title: str  # plain language, no jargon
    impact: str  # one line: why it matters to the raise
    severity: str  # "high" | "medium"
    blind_spot: bool  # True if the deck and the founders' plan don't mention it
    facts: list = field(default_factory=list)
    what_to_do: list = field(default_factory=list)
    practice_qid: int = 0
    term: str = ""  # glossary key for the jargon pop-up
    rank: int = 0
    figure: str = ""  # the headline figure for the snapshot card
    figure_prov: str = HIST

    def to_dict(self) -> dict:
        return asdict(self)


def _m(key: str) -> metrics.Metric:
    return metrics.get(key)


def _money(v: float) -> str:
    return metrics.fmt(v, "$")


def _month_name(ym: str | None) -> str:
    if not ym:
        return "after 2030"
    y, mth = ym.split("-")
    return ["January", "February", "March", "April", "May", "June", "July", "August", "September",
            "October", "November", "December"][int(mth) - 1] + f" {y}"


def months_to_goal(monthly_growth: float, start_mrr: float | None = None, goal_arr: float = GOAL_ARR) -> float:
    """Months for MRR to reach goal_arr / 12 at a steady compounded monthly growth rate."""
    start = start_mrr if start_mrr is not None else _m("mrr").value
    if monthly_growth <= 0:
        return math.inf
    return math.log((goal_arr / 12) / start) / math.log(1 + monthly_growth)


@lru_cache
def scenarios() -> dict:
    """The scenario runs the journey relies on (all FORECAST)."""
    fp = forecast.founders_plan()
    runs = {
        "plan": fp,
        "historical": forecast.historical_drivers(),
        "slip_april": forecast.with_overrides(fp, name="Round slips to April", seed_month="2027-04"),
        "slip_april_hold": forecast.with_overrides(fp, name="Slips to April, spending held", seed_month="2027-04",
                                                   hold_spend_until_close=True),
        "no_srred": forecast.with_overrides(fp, name="No SR&ED refund", srred_amount=0),
        "churn_2pct": forecast.with_overrides(fp, name="Churn stays at 2%", monthly_churn=0.02),
        "ncg_flat": forecast.with_overrides(fp, name="Northern Comfort stays at 260 seats", ncg_renewal_seats=260,
                                            ncg_renewal_fee=0),
        "ncg_leaves": forecast.with_overrides(fp, name="Northern Comfort leaves", ncg_renewal_seats=0,
                                              ncg_renewal_fee=0),
        "ramp_3": forecast.with_overrides(fp, name="3-month rep ramp", ae_ramp_months=3),
        "partial_reprice": forecast.with_overrides(fp, name="Only 75% of customers repriced", price_increase_uptake=0.75),
    }
    out = {}
    for key, s in runs.items():
        df = forecast.run(s)
        summary = forecast.summarize(s, df)
        reached = df.index[df["arr"] >= GOAL_ARR]
        summary["goal_month"] = reached[0] if len(reached) else None
        summary["opex_oct_2026"] = float(df.loc["2026-10", "opex"])
        out[key] = summary
    return out


def where_you_are() -> list[dict]:
    """The three numbers a founder should know by heart (all historical)."""
    return [
        {**_m("arr").to_dict(), "label": "Recurring revenue, per year", "term": "ARR (annual recurring revenue)"},
        {**_m("cmgr_3m").to_dict(), "label": "Monthly growth, last 3 months",
         "term": "CMGR (compound monthly growth rate)", "sub": f"{_m('cmgr_12m').display()} over the last 12 months"},
        {**_m("runway_months").to_dict(), "label": "Months of cash left", "term": "Runway", "sub": f"{_m('cash').display()} in the bank, burning {_m('burn_monthly').display()}/month"},
    ]


def goal() -> dict:
    """Where the founders want to be, and what the data says about getting there."""
    sc = scenarios()
    g12, g3 = _m("cmgr_12m").value, _m("cmgr_3m").value
    hist = sc["historical"]
    return {
        "label": "Series A at $5M ARR",
        "provenance": CLAIM,
        "ref": "Appendix A, the founders' goal",
        "plan_month": sc["plan"]["goal_month"],
        "plan_arr_mar_2028": sc["plan"]["arr_mar_2028"],
        "months_at_12m_growth": months_to_goal(g12),
        "months_at_3m_growth": months_to_goal(g3),
        "historical_arr_mar_2028": hist["arr_mar_2028"],
        "historical_cash_out": hist["cash_out_month"],
        "historical_goal_month": hist["goal_month"],
        "cash_runs_out_first": bool(hist["cash_out_month"] and (not hist["goal_month"] or
                                                                 hist["cash_out_month"] < hist["goal_month"])),
    }


@lru_cache
def roadblocks() -> tuple:
    """Every roadblock, ranked. The first three are the founder's 'top three'."""
    sc = scenarios()
    co = data.company()
    snap = co["snapshot_2026_09_30"]
    ncg = co["largest_customer"]
    sep_opex = data.income_statement().loc[metrics.LAST_MONTH, "total_operating_expenses"]
    g = goal()
    plan, hist = sc["plan"], sc["historical"]
    srred_planned = forecast.founders_plan().srred_amount

    items = [
        Roadblock(
            "cash_cliff", "You could run out of cash before the round closes",
            "If the raise takes a few months longer than planned, the company runs out of money mid-raise.",
            "high", True,
            [Fact(f"{_m('cash').display()} in the bank, burning about {_m('burn_monthly').display()} a month: "
                  f"{_m('runway_months').display()} of cash.", HIST, "Appendix B, income statement"),
             Fact(f"The plan raises monthly spending from {_money(sep_opex)} (September) to "
                  f"{_money(sc['plan']['opex_oct_2026'])} in October, before the money lands.", FCST, "Appendix C forecast"),
             Fact(f"If the round slips to April 2027, the plan runs out of cash in "
                  f"{_month_name(sc['slip_april']['cash_out_month'])}.", FCST, "Vicky scenario model")],
            ["Hold spending at today's level until a term sheet is signed. In the model, that keeps the company "
             "alive through an April close.",
             "Start investor meetings in November as planned, and track every conversation."],
            11, "Runway"),
        Roadblock(
            "growth_slowing", "Growth has nearly halved, and the $5M goal depends on it",
            "Investors will see the slowdown in the first minute and ask why.",
            "high", False,
            [Fact(f"Monthly growth was {_m('cmgr_12m').display()} over 12 months but {_m('cmgr_3m').display()} "
                  f"over the last 3.", HIST, "Income statement"),
             Fact(f"At {_m('cmgr_12m').display()} a month, $5M ARR takes about {g['months_at_12m_growth']:.0f} months. "
                  f"At {_m('cmgr_3m').display()}, about {g['months_at_3m_growth']:.0f} months.", FCST,
                  "Compounding from September 2026 MRR"),
             Fact(f"On historical drivers the money runs out in {_month_name(hist['cash_out_month'])}, with ARR at "
                  f"{_money(hist['arr_mar_2028'])} in March 2028, before reaching $5M.", FCST, "Vicky scenario model")],
            ["Explain what happened from July to September. Use real reasons from customers, not guesses.",
             "Show the plan at your actual growth rate next to the plan at your target rate."],
            2, "CMGR (compound monthly growth rate)"),
        Roadblock(
            "churn", "You're losing customers twice as fast as your deck says",
            "Churn decides how hard growth has to work just to stand still.",
            "high", False,
            [Fact("The deck says monthly churn is around 1%.", CLAIM, "Appendix A deck"),
             Fact(f"The data says {_m('logo_churn_12m').display()} a month over 12 months, "
                  f"{_m('logo_churn_6m').display()} over the last 6.", HIST, "Appendix B customers"),
             Fact(f"With churn at 2%, the plan's March 2028 ARR falls from {_money(plan['arr_mar_2028'])} to "
                  f"{_money(sc['churn_2pct']['arr_mar_2028'])}.", FCST, "Vicky scenario model")],
            ["Quote 2.0% (12 months) and 1.6% (6 months). Never 1%.",
             "Show where churn happens: new monthly customers churn fastest, so the fix is the first 90 days."],
            3, "Churn (logo)"),
        Roadblock(
            "deferred_revenue", "Your forecast counts revenue as cash",
            "Some of next year's revenue was already paid. It won't bring in new cash.",
            "medium", True,
            [Fact(f"{_money(snap['deferred_revenue'])} of deferred revenue at September 30, 2026: customers paid "
                  f"up front for service not yet delivered, including {_money(ncg['unearned_at_2026_09_30'])} from "
                  f"Northern Comfort.", HIST, "Appendix B snapshot"),
             Fact("The founders' cash line is net income plus the raise. Receivables, payables and deferred revenue "
                  "are not modelled.", FCST, "Appendix C assumptions"),
             Fact(f"So cash can be overstated by up to {_money(snap['deferred_revenue'])}, depending on how many "
                  f"annual customers renew and prepay again.", FCST, "Vicky check")],
            ["Rebuild the cash line from collections (cash in) rather than revenue.",
             "Show annual renewals by month, starting with Northern Comfort in March 2027."],
            16, "Deferred revenue"),
        Roadblock(
            "srred_guess", f"The plan counts on a {_money(srred_planned)} tax refund that isn't filed",
            "Treating an uncertain refund as certain shortens the real runway.",
            "medium", True,
            [Fact(f"SR&ED refunds received so far: {_m('srred_total').display()} from two claims.", HIST,
                  "Appendix A funding"),
             Fact(f"The plan assumes {_money(srred_planned)} in July 2027 because 'R&D spend is up'. Nothing is filed.",
                  CLAIM, "Appendix C assumptions"),
             Fact(f"Without it, runway after a January close is about {sc['no_srred']['runway_after_close_months']} "
                  f"months instead of {plan['runway_after_close_months']}.", FCST, "Vicky scenario model")],
            ["Show the plan without the refund and treat it as upside.",
             "Ask a June CPA to estimate the claim from actual R&D salaries."],
            17, "SR&ED"),
        Roadblock(
            "annual_repricing", "The price increase hits customers you can't reprice yet",
            "A forecast that assumes every customer pays 20% more in January won't survive one question.",
            "medium", True,
            [Fact(f"The plan raises prices 20% for every customer in January 2027, with no extra churn.", CLAIM,
                  "Appendix C assumptions"),
             Fact(f"{co['pricing']['annual_prepay_customers']} customers prepay annually and can't be repriced "
                  f"until renewal; {co['pricing']['legacy_customers']} still pay the legacy "
                  f"${co['pricing']['legacy_price_per_seat']} price.", HIST, "Appendix A pricing"),
             Fact(f"If only 75% of customers are repriced, March 2028 ARR is {_money(sc['partial_reprice']['arr_mar_2028'])} "
                  f"instead of {_money(plan['arr_mar_2028'])}.", FCST, "Vicky scenario model")],
            ["Phase the increase in at each customer's renewal date.", "Plan for some customers to leave over it."],
            7, "Forecast"),
        Roadblock(
            "ncg", "One customer is 10% of revenue, and their renewal isn't signed",
            "If Northern Comfort leaves or stays flat, the growth story changes.",
            "medium", False,
            [Fact(f"Northern Comfort is {_m('ncg_share_of_mrr').display()} of MRR at {ncg['seats']} seats, renewing "
                  f"March 2027.", HIST, "Appendix A, income statement"),
             Fact("The plan assumes they expand to 600 seats. That's verbal only.", CLAIM, "Appendix C assumptions"),
             Fact(f"At 260 seats, March 2028 ARR is {_money(sc['ncg_flat']['arr_mar_2028'])}; if they leave, "
                  f"{_money(sc['ncg_leaves']['arr_mar_2028'])}.", FCST, "Vicky scenario model")],
            ["Keep them at 260 seats in the base plan and show 600 as upside.",
             "Ask their COO for a written expansion timeline before the first meeting."],
            9, "Logo"),
        Roadblock(
            "rep_ramp", "New salespeople won't close deals in their first month",
            "The hiring plan only works if new reps produce. This is where seed forecasts usually break.",
            "medium", False,
            [Fact("The plan assumes a new account executive closes 5 customers a month after 1 month.", CLAIM,
                  "Appendix C assumptions"),
             Fact("The two current reps took about 3 months to reach 4 to 5 a month.", REPORTED, "Appendix D Q8"),
             Fact(f"With a 3-month ramp, March 2028 ARR is {_money(sc['ramp_3']['arr_mar_2028'])}.", FCST,
                  "Vicky scenario model")],
            ["Use a 3-month ramp in the plan.", "Set up a CRM so you can show pipeline and win rates."],
            8, "Ramp"),
    ]
    figures = {
        "cash_cliff": (_m("runway_months").display().replace(" months", " mo"), HIST),
        "growth_slowing": (f"{_m('cmgr_12m').display()} → {_m('cmgr_3m').display()}", HIST),
        "churn": (f"1% → {_m('logo_churn_12m').display()}", HIST),
        "deferred_revenue": (_money(snap["deferred_revenue"]), HIST),
        "srred_guess": (_money(srred_planned), CLAIM),
        "annual_repricing": ("+20% for all", CLAIM),
        "ncg": (_m("ncg_share_of_mrr").display() + " of MRR", HIST),
        "rep_ramp": ("1 mo vs 3 mo", REPORTED),
    }
    for i, r in enumerate(items, start=1):
        r.rank = i
        r.figure, r.figure_prov = figures[r.id]
    return tuple(items)


def roadblock(rid: str) -> Roadblock:
    return next(r for r in roadblocks() if r.id == rid)


def top_three() -> list[Roadblock]:
    return list(roadblocks()[:3])


def strengths() -> list[dict]:
    """What's genuinely working. Founders need confidence, not only a list of problems."""
    return [
        {"title": "You grow without burning much cash", "figure": f"{_m('burn_multiple').value:.2f}x",
         "label": "Burn multiple (12 months)", "ref": "Balance sheet + income statement",
         "text": f"Every dollar of new recurring revenue cost about {_m('burn_multiple').value:.2f} dollars of burn over "
                 f"the last 12 months ({_m('burn_multiple_ex_sred').value:.2f} without the SR&ED refund). Lower is better.",
         "term": "Burn multiple", "provenance": HIST},
        {"title": "Real, recurring revenue", "figure": _m("arr").display(), "label": "Annual recurring revenue",
         "ref": "Income statement, Sep 2026 MRR × 12",
         "text": f"{_m('arr').display()} ARR, and {_m('net_new_arr_12m').display()} of it was added in the last 12 months.",
         "term": "Net new ARR", "provenance": HIST},
        {"title": "Customers who stay, stay", "figure": _m("mature_churn_monthly_plans").display() + "/mo",
         "label": "Churn after month 6 (monthly plans)", "ref": "Appendix D Q3",
         "text": f"Monthly-plan customers past their first six months churn at about "
                 f"{_m('mature_churn_monthly_plans').display()} a month.",
         "term": "Churn (logo)", "provenance": REPORTED},
        {"title": "Money that doesn't cost you ownership", "figure": _m("srred_total").display(),
         "label": "SR&ED refunds received", "ref": "Appendix A funding",
         "text": f"{_m('srred_total').display()} of SR&ED refunds received to date.",
         "term": "SR&ED", "provenance": HIST},
    ]


def weaknesses() -> list[dict]:
    """Areas likely to draw scrutiny (all from the books or the pack)."""
    return [
        {"text": "Largest customer's share of revenue", "figure": _m("ncg_share_of_mrr").display(), "prov": HIST,
         "ref": "Income statement + Appendix A (Northern Comfort, renews Mar 2027)"},
        {"text": "Gross margin once support is counted", "figure": _m("gross_margin_incl_cs").display(), "prov": HIST,
         "ref": "Income statement, last 12 months"},
        {"text": "Revenue kept from last year's customers (NRR)", "figure": _m("nrr").display(), "prov": REPORTED,
         "ref": "Appendix D Q4 (not recomputable from the files provided)"},
        {"text": "Months of cash left at today's burn", "figure": _m("runway_months").display().replace(" months", " mo"),
         "prov": HIST, "ref": "Balance sheet cash ÷ Apr–Sep 2026 burn"},
    ]


def next_actions() -> list[dict]:
    """What to do before the first investor meeting."""
    return [
        {"text": "Hold spending at today's level until a term sheet is signed", "prov": FCST,
         "ref": "Scenario: round slips to April 2027"},
        {"text": "Quote churn as 2.0% (12 months). Never 1%", "prov": HIST, "ref": "Appendix B customers"},
        {"text": "Explain the July–September slowdown with customer evidence", "prov": HIST,
         "ref": "Income statement, Jun–Sep 2026"},
        {"text": "Rebuild the forecast's cash line from collections", "prov": FCST, "ref": "Deferred revenue $181K"},
        {"text": "Show the plan without the $240K SR&ED refund", "prov": CLAIM, "ref": "Appendix C assumptions"},
        {"text": "Replace the $2B TAM with a bottom-up build", "prov": CLAIM, "ref": "Deck claim, Appendix A"},
    ]


def deck_health() -> float:
    """Share of the 9 deck claims that survive a first meeting (supported, reword or upside)."""
    from . import claims
    cs = claims.check_all()
    return sum(c["status"] in (claims.OK, claims.REWORD, claims.UPSIDE) for c in cs) / len(cs)


def readiness_score(best_scores: dict[str, float]) -> dict:
    """Readiness out of 100: 30 points for a deck that holds up, 70 for answers you've practised well."""
    deck = deck_health()
    practice = readiness(best_scores)["percent"] / 100
    score = round(30 * deck + 70 * practice)
    top_ready = {**best_scores, **{r.id: max(best_scores.get(r.id, 0), 4.5) for r in top_three()}}
    with_top3 = round(30 * deck + 70 * readiness(top_ready)["percent"] / 100)
    return {"score": score, "deck_points": round(30 * deck), "practice_points": score - round(30 * deck),
            "with_top3": with_top3, "max_in_app": round(30 * deck) + 70}


STAGES = [
    {"name": "Know your numbers", "human": False},
    {"name": "Fix your story", "human": False},
    {"name": "Practise the questions", "human": False},
    {"name": "Build your investor list", "human": False},
    {"name": "First meetings", "human": False},
    {"name": "Diligence and partner meeting", "human": True},
    {"name": "Term sheet and close", "human": True},
]


def readiness(best_scores: dict[str, float]) -> dict:
    """Investor-readiness from practice results.

    best_scores maps roadblock id -> best weighted practice score (1-5). A roadblock counts as
    ready at 4+, half-ready at 3+, and a little for trying. The top three count double.
    """
    total = earned = 0.0
    ready = 0
    for r in roadblocks():
        weight = 2.0 if r.rank <= 3 else 1.0
        total += weight
        s = best_scores.get(r.id)
        credit = 0.0 if s is None else 1.0 if s >= 4 else 0.5 if s >= 3 else 0.2
        earned += weight * credit
        ready += credit == 1.0
    pct = round(100 * earned / total)
    stage = 0 if not best_scores else 1 if pct < 50 else 2 if pct < 85 else 3
    return {"percent": pct, "ready": ready, "total": len(roadblocks()), "stage": stage}
