"""The metrics engine. Every number Vicky states comes from here, never from the LLM.

Each metric carries its formula, its inputs and its provenance, so the UI can show the
calculation and the auditor can check LLM text against it.
"""
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from . import data

# Provenance kinds
HISTORICAL = "historical"
FORECAST = "forecast"
FOUNDER_CLAIM = "founder_claim"
REPORTED = "reported_in_pack"
PUBLIC = "public_source"

IS_REF = "01_income_statement_monthly_actuals.csv"
LTM = ("2025-10", "2026-09")  # last twelve closed months
LAST_MONTH = "2026-09"


@dataclass
class Metric:
    key: str
    label: str
    value: float
    unit: str  # "$", "%", "x", "months", "count"
    formula: str
    provenance: str
    ref: str
    inputs: dict = field(default_factory=dict)
    note: str = ""

    def display(self) -> str:
        return fmt(self.value, self.unit)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["display"] = self.display()
        return d


def fmt(value: float, unit: str) -> str:
    if unit == "$":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        if abs(value) >= 10_000:
            return f"${value / 1000:,.0f}K"
        return f"${value:,.0f}"
    if unit == "%":
        return f"{value * 100:.1f}%"
    if unit == "x":
        return f"{value:.2f}x"
    if unit == "months":
        return f"{value:.1f} months"
    return f"{value:,.0f}"


def _ltm(df):
    return df.loc[LTM[0]:LTM[1]]


def _cmgr(start: float, end: float, months: int) -> float:
    return (end / start) ** (1 / months) - 1


def _months_between(start: str, end: str) -> int:
    y1, m1 = map(int, start.split("-"))
    y2, m2 = map(int, end.split("-"))
    return (y2 - y1) * 12 + (m2 - m1)


def _logo_churn(quarters: list[str]) -> tuple[float, dict]:
    """Monthly logo churn = churned customers / (months x average customer base).

    The average base uses quarter-end counts from the quarter before the window through
    the last quarter in it (only quarterly customer counts are available).
    """
    cs = data.quarterly("customers_seats_quarterly")
    labels = list(cs.index)
    first = labels.index(quarters[0])
    base_points = cs["customers_end"].iloc[first - 1: labels.index(quarters[-1]) + 1]
    churned = int(cs.loc[quarters, "churned_customers"].sum())
    months = 3 * len(quarters)
    avg_base = float(base_points.mean())
    return churned / (months * avg_base), {
        "churned_customers": churned,
        "months": months,
        "average_customers": round(avg_base, 1),
        "quarters": ", ".join(quarters),
    }


@lru_cache
def registry() -> dict[str, Metric]:
    df = data.income_statement()
    co = data.company()
    ltm = _ltm(df)
    mrr = df["subscription_revenue"]
    reg: dict[str, Metric] = {}

    def add(m: Metric):
        reg[m.key] = m

    # --- Revenue and growth -------------------------------------------------
    add(Metric("mrr", "MRR, September 2026", mrr[LAST_MONTH], "$",
               "Subscription revenue in September 2026", HISTORICAL, IS_REF))
    add(Metric("arr", "ARR (MRR x 12)", mrr[LAST_MONTH] * 12, "$",
               "September 2026 MRR x 12, excluding one-time onboarding fees", HISTORICAL, IS_REF,
               {"mrr": mrr[LAST_MONTH]}))
    total_rev_sep = df.loc[LAST_MONTH, "total_revenue"]
    add(Metric("arr_incl_onboarding", "Total revenue x 12 (the deck's method)", total_rev_sep * 12, "$",
               "September 2026 total revenue x 12, which wrongly includes one-time onboarding fees",
               HISTORICAL, IS_REF,
               {"total_revenue_sep": total_rev_sep,
                "onboarding_sep": df.loc[LAST_MONTH, "onboarding_services_revenue"]}))
    add(Metric("onboarding_ltm", "Onboarding fees, last 12 months", ltm["onboarding_services_revenue"].sum(), "$",
               "Sum of onboarding services revenue, Oct 2025 - Sep 2026", HISTORICAL, IS_REF))
    add(Metric("revenue_ltm", "Total revenue, last 12 months", ltm["total_revenue"].sum(), "$",
               "Sum of total revenue, Oct 2025 - Sep 2026", HISTORICAL, IS_REF))
    add(Metric("cmgr_12m", "MRR growth, compounded monthly (12 months)", _cmgr(mrr["2025-09"], mrr[LAST_MONTH], 12), "%",
               "(MRR Sep 2026 / MRR Sep 2025)^(1/12) - 1", HISTORICAL, IS_REF,
               {"mrr_sep_2025": mrr["2025-09"], "mrr_sep_2026": mrr[LAST_MONTH]}))
    add(Metric("cmgr_3m", "MRR growth, compounded monthly (Jul - Sep 2026)", _cmgr(mrr["2026-06"], mrr[LAST_MONTH], 3), "%",
               "(MRR Sep 2026 / MRR Jun 2026)^(1/3) - 1", HISTORICAL, IS_REF,
               {"mrr_jun_2026": mrr["2026-06"], "mrr_sep_2026": mrr[LAST_MONTH]}))
    ncg = co["largest_customer"]
    ncg_mrr = ncg["seats"] * ncg["price_per_seat"]
    add(Metric("ncg_mrr", "Northern Comfort Group MRR", ncg_mrr, "$",
               "260 seats x $40", HISTORICAL, "Appendix A"))
    add(Metric("cmgr_12m_ex_ncg", "MRR growth excluding Northern Comfort (12 months)",
               _cmgr(mrr["2025-09"], mrr[LAST_MONTH] - ncg_mrr, 12), "%",
               "((MRR Sep 2026 - NCG MRR) / MRR Sep 2025)^(1/12) - 1", HISTORICAL, f"{IS_REF}, Appendix A",
               {"ncg_mrr": ncg_mrr}))
    add(Metric("ncg_share_of_mrr", "Northern Comfort Group share of MRR", ncg_mrr / mrr[LAST_MONTH], "%",
               "NCG MRR / September 2026 MRR", HISTORICAL, f"{IS_REF}, Appendix A",
               {"ncg_mrr": ncg_mrr, "mrr": mrr[LAST_MONTH]},
               note="Renews March 2027. The 600-seat expansion is verbal only; nothing is signed."))
    net_new_arr = (mrr[LAST_MONTH] - mrr["2025-09"]) * 12
    add(Metric("net_new_arr_12m", "Net new ARR, last 12 months", net_new_arr, "$",
               "(MRR Sep 2026 - MRR Sep 2025) x 12", HISTORICAL, IS_REF))

    # --- Margin and unit economics -----------------------------------------
    rev, gp, cs_sal = ltm["total_revenue"].sum(), ltm["gross_profit"].sum(), ltm["customer_success_salaries"].sum()
    add(Metric("gross_margin_booked", "Gross margin as booked (12 months)", gp / rev, "%",
               "Gross profit / revenue, with hosting, SMS and card fees as cost of revenue", HISTORICAL, IS_REF,
               {"gross_profit": gp, "revenue": rev}))
    add(Metric("gross_margin_incl_cs", "Gross margin including customer success (12 months)", (gp - cs_sal) / rev, "%",
               "(Gross profit - customer success salaries) / revenue", HISTORICAL, IS_REF,
               {"gross_profit": gp, "customer_success_salaries": cs_sal, "revenue": rev},
               note="Most SaaS investors count customer support in cost of revenue."))
    cs_q = data.quarterly("customers_seats_quarterly")
    ltm_quarters = ["Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026"]
    new_customers = int(cs_q.loc[ltm_quarters, "new_customers"].sum())
    sm_cols = ["sales_salaries", "sales_commissions", "marketing_salaries", "marketing_programs"]
    sm = ltm[sm_cols].sum().sum()
    add(Metric("new_customers_ltm", "New customers, last 12 months", new_customers, "count",
               "Sum of new customers, Q4 2025 - Q3 2026", HISTORICAL, "Appendix B customers and seats"))
    add(Metric("cac_fully_loaded", "CAC, fully loaded", sm / new_customers, "$",
               "(Sales salaries + commissions + marketing salaries + marketing programs, 12 months) / new customers",
               HISTORICAL, f"{IS_REF}, Appendix B", {"sales_and_marketing": sm, "new_customers": new_customers}))
    add(Metric("cac_marketing_only", "CAC, marketing programs only (the deck's method)",
               ltm["marketing_programs"].sum() / new_customers, "$",
               "Marketing programs (12 months) / new customers", HISTORICAL, f"{IS_REF}, Appendix B",
               {"marketing_programs": ltm["marketing_programs"].sum(), "new_customers": new_customers}))
    rep = data.pack("reported_metrics")
    mrr_new = rep["mrr_per_new_customer"]["value"]
    payback = (sm / new_customers) / (mrr_new * reg["gross_margin_incl_cs"].value)
    add(Metric("cac_payback_months", "CAC payback", payback, "months",
               "Fully loaded CAC / (MRR per new customer x gross margin incl. customer success)",
               HISTORICAL, f"{IS_REF}, Appendix D Q6",
               {"cac": round(sm / new_customers), "mrr_per_new_customer": mrr_new},
               note="MRR per new customer ($458) is stated in the pack; it needs customer-level data to recompute."))

    # --- Churn ---------------------------------------------------------------
    churn12, in12 = _logo_churn(ltm_quarters)
    add(Metric("logo_churn_12m", "Monthly logo churn (12 months)", churn12, "%",
               "Churned customers / (12 x average customers)", HISTORICAL, "Appendix B customers and seats", in12))
    churn6, in6 = _logo_churn(["Q2 2026", "Q3 2026"])
    add(Metric("logo_churn_6m", "Monthly logo churn (last 6 months)", churn6, "%",
               "Churned customers / (6 x average customers)", HISTORICAL, "Appendix B customers and seats", in6,
               note="Six months is a short window; show both numbers rather than calling it a trend."))

    # --- Cash, burn and runway ----------------------------------------------
    cash = co["snapshot_2026_09_30"]["cash"]
    add(Metric("cash", "Cash in the bank, Sep 30 2026", cash, "$", "Balance sheet", HISTORICAL, "Appendix B snapshot"))
    last6 = df.loc["2026-04":LAST_MONTH]
    burn = -(last6["net_income"] - last6["other_income_srred_credit"]).mean()
    add(Metric("burn_monthly", "Monthly burn (Apr - Sep 2026, excl. SR&ED)", burn, "$",
               "Average monthly net loss excluding SR&ED credits, Apr - Sep 2026", HISTORICAL, IS_REF,
               note="Uses net loss as a proxy for cash burn; monthly cash flow was not provided."))
    add(Metric("runway_months", "Runway at current burn", cash / burn, "months",
               "Cash / monthly burn", HISTORICAL, f"Appendix B, {IS_REF}", {"cash": cash, "burn": round(burn)}))
    bs = data.quarterly("balance_sheet")
    safe_ltm = 500_000  # Feb 2026 SAFE extension, the only financing in the window
    net_burn = (bs.loc["cash", "sep_30_2025_k"] - bs.loc["cash", "sep_30_2026_k"]) * 1000 + safe_ltm
    add(Metric("net_burn_12m", "Net burn, last 12 months", net_burn, "$",
               "Cash Sep 2025 - cash Sep 2026 + SAFE raised in between", HISTORICAL, "Appendix B balance sheet",
               {"safe_raised": safe_ltm}))
    add(Metric("burn_multiple", "Burn multiple (12 months)", net_burn / net_new_arr, "x",
               "Net burn / net new ARR (David Sacks)", HISTORICAL, "Appendix B; definition: sacks_burn",
               {"net_burn": net_burn, "net_new_arr": net_new_arr}))
    srred_ltm = ltm["other_income_srred_credit"].sum()
    add(Metric("burn_multiple_ex_sred", "Burn multiple excluding SR&ED", (net_burn + srred_ltm) / net_new_arr, "x",
               "(Net burn + SR&ED received) / net new ARR", HISTORICAL, "Appendix B; definition: sacks_burn",
               {"srred_received": srred_ltm}))
    srred_total = sum(f["amount"] for f in co["funding"] if "SR&ED" in f["source"])
    add(Metric("srred_total", "SR&ED refunds received to date", srred_total, "$",
               "Sum of SR&ED refunds", HISTORICAL, "Appendix A funding"))

    # --- Founders' forecast ---------------------------------------------------
    fc = data.quarterly("forecast_quarterly")
    end_cash = fc.loc["Q1 2028", "ending_cash_k"] * 1000
    end_burn = -(fc.loc["Q1 2028", "net_income_k"] + fc.loc["Q1 2028", "equipment_k"]) * 1000 / 3
    months_after_plan = end_cash / end_burn
    plan_runway = _months_between("2027-01", "2028-03") + months_after_plan
    add(Metric("plan_runway_after_close", "Runway after a Jan 2027 close (founders' plan)", plan_runway, "months",
               "Months from Jan 2027 to Mar 2028, plus Mar 2028 cash / Q1 2028 monthly burn", FORECAST,
               "Appendix C forecast", {"ending_cash_mar_2028": end_cash, "monthly_burn_q1_2028": round(end_burn)},
               note="Cash runs out around November 2028 on the founders' own plan, not 24 months."))
    add(Metric("plan_arr_end", "ARR at March 2028 (founders' plan)", fc.loc["Q1 2028", "ending_mrr_k"] * 12_000, "$",
               "Ending MRR Q1 2028 x 12", FORECAST, "Appendix C forecast"))

    # --- Reported in pack, not recomputable -------------------------------
    for key, r in rep.items():
        if key in reg or key == "mrr_per_new_customer":
            continue
        unit = r.get("unit", "%")
        add(Metric(key, r["label"], r["value"], unit, "Stated in the data pack", REPORTED, r["ref"],
                   note="Not recomputed: needs customer-level files (05/06) that were not provided."
                   + (f" {r['detail']}" if r.get("detail") else "")))
    add(Metric("mrr_per_new_customer", rep["mrr_per_new_customer"]["label"], mrr_new, "$",
               "Stated in the data pack", REPORTED, rep["mrr_per_new_customer"]["ref"],
               note="Not recomputed: needs customer-level files (05/06) that were not provided."))
    return reg


def get(key: str) -> Metric:
    return registry()[key]


def as_table() -> list[dict]:
    return [m.to_dict() for m in registry().values()]
