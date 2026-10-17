"""The engine must reproduce the figures in Appendix H (Example Vicky output) and Appendix D."""
import pytest

from vicky import audit, claims, forecast, metrics


def v(key):
    return metrics.get(key).value


@pytest.mark.parametrize("key,expected,tol", [
    ("mrr", 107_189, 0.5),
    ("arr", 1_286_268, 1),
    ("arr_incl_onboarding", 1_372_668, 1),
    ("onboarding_ltm", 108_600, 0.5),
    ("revenue_ltm", 1_001_816, 0.5),
    ("cmgr_12m", 0.09, 0.003),
    ("cmgr_3m", 0.05, 0.003),
    ("cmgr_12m_ex_ncg", 0.08, 0.003),
    ("ncg_share_of_mrr", 0.10, 0.005),
    ("net_new_arr_12m", 830_000, 1_000),
    ("gross_margin_booked", 0.92, 0.005),
    ("gross_margin_incl_cs", 0.74, 0.005),
    ("cac_fully_loaded", 3_200, 50),
    ("cac_marketing_only", 970, 5),
    ("logo_churn_12m", 0.020, 0.001),
    ("logo_churn_6m", 0.016, 0.001),
    ("burn_monthly", 58_000, 1_000),
    ("runway_months", 8.3, 0.2),
    ("net_burn_12m", 514_000, 1_000),
    ("burn_multiple", 0.6, 0.05),
    ("burn_multiple_ex_sred", 0.8, 0.05),
    ("srred_total", 278_700, 0.5),
    ("plan_runway_after_close", 22, 0.6),
    ("plan_arr_end", 5_112_000, 1),
])
def test_metric_matches_pack(key, expected, tol):
    assert v(key) == pytest.approx(expected, abs=tol)


def test_cac_payback_9_to_10_months():
    assert 9 <= v("cac_payback_months") <= 10


def test_every_metric_has_provenance_and_formula():
    for m in metrics.registry().values():
        assert m.provenance in {metrics.HISTORICAL, metrics.FORECAST, metrics.REPORTED}
        assert m.formula and m.ref


def test_founders_plan_model_tracks_appendix_c():
    s = forecast.summarize(forecast.founders_plan())
    assert s["arr_mar_2028"] == pytest.approx(5_112_000, rel=0.02)
    assert s["runway_after_close_months"] in (21, 22)


def test_historical_drivers_shorten_runway():
    s = forecast.summarize(forecast.historical_drivers())
    assert s["runway_after_close_months"] in (16, 17, 18)


def test_round_slipping_to_april_runs_out_in_march():
    s = forecast.with_overrides(forecast.founders_plan(), seed_month="2027-04")
    assert forecast.summarize(s)["cash_out_month"] == "2027-03"


def test_holding_spend_survives_a_slip():
    s = forecast.with_overrides(forecast.founders_plan(), seed_month="2027-04", hold_spend_until_close=True)
    out = forecast.summarize(s)
    assert out["cash_out_month"] is None or out["cash_out_month"] > "2027-04"


def test_claims_statuses_match_appendix_h():
    status = {c["id"]: c["status"] for c in claims.check_all()}
    assert status == {
        "arr": claims.FIX, "growth": claims.REWORD, "gross_margin": claims.FIX, "churn": claims.FIX,
        "nrr": claims.FIX, "cac": claims.FIX, "tam": claims.REMOVE, "ncg": claims.UPSIDE, "runway": claims.REWORD,
    }


def test_audit_flags_wrong_number_claim_and_valuation():
    r = audit.audit("Churn is 1% a month. Burn multiple is 2.5x. We recommend a valuation of $12M.")
    types = {i["type"] for i in r.issues}
    assert {"claim_as_fact", "unsupported_number", "valuation_or_advice"} <= types


def test_audit_passes_grounded_text():
    r = audit.audit("ARR is $1.29M (MRR $107,189 x 12). Churn was 2.0% a month; the deck says 1%. "
                    "Fully loaded CAC is about $3,200, with payback of about 9 months.")
    assert r.passed, r.issues
