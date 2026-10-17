"""Driver-based monthly forecast, so founders can rerun the plan on different assumptions.

Revenue is built from drivers (new customers, churn, expansion, price, Northern Comfort).
Spending follows the founders' plan (Appendix C quarterly lines, split evenly by month and
held flat after March 2028), because the line-level hiring plan file was not provided.
Everything this module returns is FORECAST, never actual.
"""
from dataclasses import asdict, dataclass, field, replace

import pandas as pd

from . import data

START = "2026-10"
PLAN_END = "2028-03"  # last month of the founders' plan; burn is frozen after this
HORIZON_END = "2030-12"


def _month_range(start: str, end: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


def _quarter(month: str) -> str:
    p = pd.Period(month, freq="M")
    return f"Q{p.quarter} {p.year}"


def _months_between(start: str, end: str) -> int:
    return (pd.Period(end, freq="M") - pd.Period(start, freq="M")).n


@dataclass
class Scenario:
    name: str = "Founders' plan"
    monthly_churn: float = 0.01
    ae_new_per_month: float = 5
    ae_ramp_months: int = 1
    # existing reps are already ramped; planned hires by start month (3 / 5 / 6 AEs by quarter)
    existing_aes: int = 2
    ae_hires: dict = field(default_factory=lambda: {"2026-10": 1, "2027-03": 2, "2027-05": 1})
    inbound_start: float = 4
    inbound_growth: float = 0.03
    seats_per_new_customer: float = 10
    monthly_expansion: float = 0.01
    new_price: float = 45
    new_price_from_jan_2027: float = 54
    existing_price_increase: float = 0.20
    price_increase_uptake: float = 1.0  # share of the (non-NCG) base actually repriced in Jan 2027
    price_increase_extra_churn: float = 0.0  # one-time share of customers lost to the increase
    ncg_renewal_seats: int = 600  # 0 = Northern Comfort leaves at renewal
    ncg_renewal_fee: float = 20_000
    cost_of_revenue_pct: float = 0.12
    onboarding_fee: float = 900
    seed_amount: float = 4_000_000
    seed_month: str = "2027-01"
    srred_amount: float = 240_000
    srred_month: str = "2027-07"
    hold_spend_until_close: bool = False  # keep spending at Q4 2026 plan level until the round lands

    def to_dict(self) -> dict:
        return asdict(self)


def founders_plan() -> Scenario:
    return Scenario()


def historical_drivers() -> Scenario:
    """The founders' plan with drivers reset to what the history supports (Appendix B / D)."""
    return Scenario(
        name="Historical drivers",
        monthly_churn=0.02,  # 2.0% a month over the last 12 months
        ae_ramp_months=3,  # existing reps took ~3 months to reach 4-5 a month
        ae_new_per_month=4.5,  # "4 to 5 a month"
        ncg_renewal_seats=260,  # nothing signed; keep flat, show expansion as upside
        ncg_renewal_fee=0,
        price_increase_uptake=0.75,  # annual plans can't be repriced until renewal; phased in
        price_increase_extra_churn=0.03,
        monthly_expansion=0.004,  # expansion has been ~0.4% of starting MRR a month
    )


PRESETS = {"Founders' plan": founders_plan, "Historical drivers": historical_drivers}


def _plan_spend() -> pd.DataFrame:
    """Monthly operating spend and equipment from the founders' quarterly plan."""
    fc = data.quarterly("forecast_quarterly")
    cols = ["rnd_salaries_k", "sales_salaries_commissions_k", "marketing_k", "customer_success_k", "ga_k"]
    rows = {}
    for month in _month_range(START, HORIZON_END):
        q = _quarter(month)
        q = q if q in fc.index else "Q1 2028"  # hold the last planned quarter flat afterwards
        rows[month] = {
            "opex": fc.loc[q, cols].sum() * 1000 / 3,
            "equipment": -fc.loc[q, "equipment_k"] * 1000 / 3 if _quarter(month) in fc.index else 0.0,
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def run(s: Scenario) -> pd.DataFrame:
    co = data.company()
    snap = co["snapshot_2026_09_30"]
    ncg = co["largest_customer"]
    spend = _plan_spend()
    hold_opex = spend.loc[START, "opex"]

    ncg_mrr = ncg["seats"] * ncg["price_per_seat"]
    base_mrr = snap["mrr"] - ncg_mrr  # everything except Northern Comfort
    customers = snap["customers"] - 1
    cash = snap["cash"]
    hires = sorted((m, n) for m, n in s.ae_hires.items())
    rows = []
    for i, month in enumerate(_month_range(START, HORIZON_END)):
        # new customers: inbound plus account executives (ramping linearly)
        inbound = s.inbound_start * (1 + s.inbound_growth) ** i
        ae_capacity = s.existing_aes
        for hire_month, n in hires:
            if month >= hire_month:
                tenure = _months_between(hire_month, month)  # 0 in the hire month
                ae_capacity += n * min(1.0, tenure / max(s.ae_ramp_months, 1))
        new_customers = inbound + ae_capacity * s.ae_new_per_month
        price = s.new_price_from_jan_2027 if month >= "2027-01" else s.new_price

        churned_mrr = base_mrr * s.monthly_churn
        expansion_mrr = base_mrr * s.monthly_expansion
        new_mrr = new_customers * s.seats_per_new_customer * price
        churned_customers = customers * s.monthly_churn
        if month == "2027-01":
            base_mrr *= 1 + s.existing_price_increase * s.price_increase_uptake
            churned_mrr += base_mrr * s.price_increase_extra_churn
            churned_customers += customers * s.price_increase_extra_churn
        base_mrr += new_mrr + expansion_mrr - churned_mrr
        customers += new_customers - churned_customers

        onboarding = new_customers * s.onboarding_fee
        if month == ncg["renews"]:
            ncg_mrr = s.ncg_renewal_seats * ncg["price_per_seat"]
            onboarding += s.ncg_renewal_fee if s.ncg_renewal_seats else 0
        mrr = base_mrr + ncg_mrr
        revenue = mrr + onboarding

        opex = spend.loc[month, "opex"]
        if s.hold_spend_until_close and month < s.seed_month:
            opex = min(opex, hold_opex)
        cor = revenue * s.cost_of_revenue_pct
        srred = s.srred_amount if month == s.srred_month else 0.0
        net_income = revenue - cor - opex + srred
        if month > PLAN_END:
            # beyond the plan, hold monthly burn at its final-quarter level (as the pack does)
            net_income = frozen_net_income
        financing = s.seed_amount if month == s.seed_month else 0.0
        cash += net_income + financing - spend.loc[month, "equipment"]
        if month == PLAN_END:
            frozen_net_income = sum(r["net_income"] for r in rows[-2:]) / 3 + net_income / 3
        rows.append({
            "month": month, "mrr": mrr, "arr": mrr * 12, "customers": customers,
            "new_customers": new_customers, "revenue": revenue, "opex": opex,
            "net_income": net_income, "financing": financing, "cash": cash,
        })
    return pd.DataFrame(rows).set_index("month")


def summarize(s: Scenario, df: pd.DataFrame | None = None) -> dict:
    df = run(s) if df is None else df
    negative = df.index[df["cash"] < 0]
    cash_out = negative[0] if len(negative) else None
    runway_after_close = _months_between(s.seed_month, cash_out) if cash_out else None
    return {
        "scenario": s.name,
        "mrr_mar_2028": df.loc["2028-03", "mrr"],
        "arr_mar_2028": df.loc["2028-03", "arr"],
        "cash_mar_2028": df.loc["2028-03", "cash"],
        "cash_out_month": cash_out,
        "runway_after_close_months": runway_after_close,
        "cash_out_before_close": bool(cash_out and cash_out <= s.seed_month),
        "provenance": "forecast (Vicky scenario model on founders' spending plan)",
    }


def compare(*scenarios: Scenario) -> list[dict]:
    return [summarize(s) for s in scenarios]


def with_overrides(base: Scenario, **overrides) -> Scenario:
    valid = {k: v for k, v in overrides.items() if k in Scenario.__dataclass_fields__}
    return replace(base, **valid)
