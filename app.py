"""Vicky, June Analytics' AI venture capitalist. Run: uv run streamlit run app.py"""
import random

import altair as alt
import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from vicky import claims, data, forecast, llm, metrics
from vicky.audit import audit

st.set_page_config(page_title="Vicky · AI VC by June", page_icon="assets/june_logo.png", layout="wide")

PROV = {
    "historical": ("Historical", "#1f7a4d", "#e3f4ea"),
    "forecast": ("Forecast", "#8a5a00", "#fdf1d8"),
    "founder_claim": ("Founder claim", "#9b1c1c", "#fbe4e4"),
    "reported_in_pack": ("Reported in pack", "#3b4a9b", "#e6e9fa"),
    "public_source": ("Public source", "#555", "#eee"),
}
STATUS_COLOR = {claims.FIX: "#9b1c1c", claims.REWORD: "#8a5a00", claims.REMOVE: "#9b1c1c",
                claims.UPSIDE: "#3b4a9b", claims.OK: "#1f7a4d"}

st.markdown("""<style>
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.72rem;font-weight:600;margin-left:4px}
.kpi{border:1px solid #e5e5e0;border-radius:10px;padding:12px 14px;background:#fff;height:100%}
.kpi .v{font-size:1.55rem;font-weight:700;margin:2px 0}
.kpi .l{font-size:0.82rem;color:#555}
.claim{border-left:4px solid;padding:6px 12px;margin-bottom:10px;background:#fafaf8;border-radius:4px}
.small{font-size:0.82rem;color:#555}
</style>""", unsafe_allow_html=True)


def badge(prov: str) -> str:
    label, fg, bg = PROV.get(prov, (prov, "#555", "#eee"))
    return f'<span class="badge" style="color:{fg};background:{bg}">{label}</span>'


def kpi(key: str, label: str | None = None, sub: str = ""):
    m = metrics.get(key)
    st.markdown(f'<div class="kpi"><div class="l">{label or m.label}{badge(m.provenance)}</div>'
                f'<div class="v">{m.display()}</div><div class="small">{sub}</div></div>', unsafe_allow_html=True)
    with st.popover("Show calculation", width="stretch"):
        show_metric(m)


def show_metric(m: metrics.Metric):
    st.markdown(f"**{m.label}** = **{m.display()}** {badge(m.provenance)}", unsafe_allow_html=True)
    st.markdown(f"Formula: {m.formula}")
    if m.inputs:
        st.json({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.inputs.items()})
    st.caption(f"Source: {m.ref}")
    if m.note:
        st.info(m.note)


def render_audit(entries: list[dict], title="Audit notes"):
    with st.expander(f"🔎 {title}: {entries[-1]['summary']}", expanded=not entries[-1]["passed"]):
        for e in entries:
            label = f"Round {e['round']}: " if "round" in e else ""
            st.markdown(f"**{label}{e['summary']}**")
            for i in e["issues"]:
                st.markdown(f"- `{i['type']}` **{i['text']}**: {i['detail']}  \n  <span class='small'>“{i['sentence'][:220]}”</span>",
                            unsafe_allow_html=True)
        if len(entries) > 1:
            st.success("Issues found by the audit were sent back to Vicky and fixed before you saw this.")


def need_llm() -> bool:
    if llm.configured():
        return True
    st.warning("No LLM key configured. Add `OPENROUTER_API_KEY` to `.env` (free at openrouter.ai/keys) and restart. "
               "The dashboard, claim check and scenario lab work without it.")
    return False


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.image("assets/june_logo_wide.png", width=120)
    st.markdown("### Vicky · AI venture capitalist")
    co = data.company()
    st.markdown(f"**{co['name']}**  \nRaising **${co['raise']['amount'] / 1e6:.0f}M seed**, target close "
                f"{co['raise']['target_close']}")
    st.divider()
    st.markdown("**Every figure is labelled**")
    st.markdown(" ".join(badge(k) for k in ["historical", "forecast", "founder_claim", "reported_in_pack"]),
                unsafe_allow_html=True)
    st.caption("Actuals: Oct 2024 to Sep 2026. Forecast: Oct 2026 to Mar 2028. CAD. Tidewell is fictional; all data is synthetic.")
    st.divider()
    if llm.configured():
        st.caption(f"LLM: `{llm.model_name()}` (calculations never come from the LLM)")
    else:
        st.caption("LLM: not configured")
    st.caption("Vicky explains how investors think. She does not give investment advice or recommend valuations.")

st.title("Get investor-ready with Vicky")
st.caption("Analyze the numbers → prepare the founder → simulate the pitch. Calculations run in code; "
           "the AI explains them, and an independent audit checks every figure it writes.")

tabs = st.tabs(["📊 Numbers", "🧾 Deck claim check", "📋 Investor prep pack", "💬 Ask Vicky",
                "🎤 Pitch simulator", "🧪 Scenario lab"])

# ---------------------------------------------------------------- 1. dashboard
with tabs[0]:
    st.subheader("Snapshot at September 30, 2026")
    r1 = st.columns(4)
    with r1[0]:
        kpi("arr", "ARR", "MRR × 12, no one-time fees")
    with r1[1]:
        kpi("cmgr_12m", "MRR growth / month (12 mo)", f"Last 3 months: {metrics.get('cmgr_3m').display()}")
    with r1[2]:
        kpi("gross_margin_incl_cs", "Gross margin incl. support", f"As booked: {metrics.get('gross_margin_booked').display()}")
    with r1[3]:
        kpi("logo_churn_12m", "Logo churn / month", f"Last 6 months: {metrics.get('logo_churn_6m').display()}")
    r2 = st.columns(4)
    with r2[0]:
        kpi("cac_fully_loaded", "CAC, fully loaded", f"Payback ≈ {metrics.get('cac_payback_months').value:.1f} months")
    with r2[1]:
        kpi("burn_monthly", "Monthly burn", "Apr–Sep 2026, excl. SR&ED")
    with r2[2]:
        kpi("runway_months", "Runway today", f"Cash {metrics.get('cash').display()}")
    with r2[3]:
        kpi("burn_multiple", "Burn multiple", f"Excl. SR&ED: {metrics.get('burn_multiple_ex_sred').display()}")
    r3 = st.columns(4)
    with r3[0]:
        kpi("nrr", "Net revenue retention", "Not recomputable from the files provided")
    with r3[1]:
        kpi("ncg_share_of_mrr", "Largest customer share", "Northern Comfort, renews Mar 2027")
    with r3[2]:
        kpi("plan_runway_after_close", "Runway after raise (plan)", "Deck says 24 months")
    with r3[3]:
        kpi("plan_arr_end", "ARR Mar 2028 (plan)", "Founders' forecast")

    st.subheader("MRR: actuals vs the founders' plan vs historical drivers")
    hist = data.income_statement()["subscription_revenue"].rename("MRR").to_frame()
    hist["series"] = "Actual (historical)"
    fp = forecast.run(forecast.founders_plan()).loc[:"2028-03", ["mrr"]].rename(columns={"mrr": "MRR"})
    fp["series"] = "Founders' plan (forecast)"
    hd = forecast.run(forecast.historical_drivers()).loc[:"2028-03", ["mrr"]].rename(columns={"mrr": "MRR"})
    hd["series"] = "Historical drivers (forecast)"
    chart_df = pd.concat([hist, fp, hd]).reset_index(names="month")
    chart_df["month"] = pd.to_datetime(chart_df["month"])
    chart = alt.Chart(chart_df).mark_line(point=alt.OverlayMarkDef(size=18)).encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("MRR:Q", title="MRR (CAD)", axis=alt.Axis(format="$,.0s")),
        color=alt.Color("series:N", title=None, scale=alt.Scale(
            domain=["Actual (historical)", "Founders' plan (forecast)", "Historical drivers (forecast)"],
            range=["#111111", "#d08c00", "#3b4a9b"]), legend=alt.Legend(orient="top")),
        strokeDash=alt.condition(alt.datum.series == "Actual (historical)", alt.value([1, 0]), alt.value([5, 4])),
        tooltip=["series", alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("MRR:Q", format="$,.0f")],
    ).properties(height=320)
    st.altair_chart(chart, width="stretch")
    st.caption("Historical drivers: 2% churn, 3-month rep ramp, 4.5 deals per rep, Northern Comfort flat at 260 seats, "
               "price rise phased in. Spending follows the founders' plan in both forecasts.")

    with st.expander("All metrics, with formulas and sources"):
        tbl = pd.DataFrame(metrics.as_table())[["label", "display", "provenance", "formula", "ref", "note"]]
        st.dataframe(tbl, hide_index=True, width="stretch")
    with st.expander("What's missing from the data (and what would fill the gap)"):
        for item in data.company()["missing_data"]:
            st.markdown(f"- {item}")

# ---------------------------------------------------------------- 2. claims
with tabs[1]:
    st.subheader("Would your deck survive a first meeting?")
    cs = claims.check_all()
    failing = sum(c["status"] in (claims.FIX, claims.REMOVE) for c in cs)
    st.markdown(f"**{failing} of {len(cs)} claims need fixing** and the rest need rewording or reframing. "
                "This check is deterministic: no AI involved, every figure traces to the data.")
    for c in cs:
        color = STATUS_COLOR[c["status"]]
        st.markdown(
            f'<div class="claim" style="border-color:{color}"><b>“{c["claim"]}”</b>{badge("founder_claim")} '
            f'<span class="badge" style="color:#fff;background:{color}">{c["status"]}</span><br>'
            f'<b>What the data shows:</b> {c["data_shows"]}<br><b>Say instead:</b> {c["suggested_fix"]}<br>'
            f'<span class="small"><b>Why investors care:</b> {c["why_investors_care"]}</span></div>',
            unsafe_allow_html=True)
        if c["evidence"]:
            with st.popover("Evidence"):
                for e in c["evidence"]:
                    show_metric(metrics.get(e["key"]))

# ---------------------------------------------------------------- 3. prep pack
with tabs[2]:
    st.subheader("Investor prep pack")
    st.caption("Pipeline: compute metrics and checks in code → Vicky drafts the pack → independent audit checks every "
               "figure, claim and benchmark → Vicky revises (up to 2 rounds) → you see the result plus the audit notes.")
    c1, c2 = st.columns([1, 3])
    run_llm = c1.button("Generate with Vicky", type="primary", disabled=not llm.configured())
    run_det = c2.button("Generate without AI (deterministic)")
    if run_llm:
        from vicky.graphs import prep_pack
        with st.status("Building your pack…", expanded=True) as status:
            st.write("Computing metrics, claim checks and scenarios…")
            try:
                st.session_state.pack = prep_pack.run()
                status.update(label="Pack ready", state="complete")
            except Exception as e:  # free-tier rate limits etc.
                status.update(label="LLM call failed; showing the deterministic pack", state="error")
                st.error(f"{type(e).__name__}: {e}")
                st.session_state.pack = prep_pack.deterministic()
    if run_det:
        from vicky.graphs import prep_pack
        st.session_state.pack = prep_pack.deterministic()
    pack = st.session_state.get("pack")
    if pack:
        st.markdown(pack["markdown"])
        render_audit(pack["audit_log"])
        st.download_button("Download pack (.md)", pack["markdown"], file_name="tidewell_investor_prep_pack.md")
    elif not llm.configured():
        need_llm()

# ---------------------------------------------------------------- 4. ask vicky
with tabs[3]:
    st.subheader("Ask Vicky about your numbers")
    st.caption("Vicky uses tools (metrics, claim check, scenarios, glossary, sources) and every answer is audited before you see it.")
    if need_llm():
        st.session_state.setdefault("chat", [])
        examples = ["What's our real ARR and why isn't it $1.37M?", "Explain burn multiple like I'm an engineer",
                    "What if churn stays at 2% and reps take 3 months to ramp?", "What valuation should we raise at?",
                    "Why will we beat Jobber?"]
        ex_cols = st.columns(len(examples))
        picked = None
        for col, ex in zip(ex_cols, examples):
            if col.button(ex, width="stretch"):
                picked = ex
        for turn in st.session_state.chat:
            with st.chat_message(turn["role"], avatar="assets/june_logo.png" if turn["role"] == "assistant" else None):
                st.markdown(turn["content"])
                if turn.get("meta"):
                    meta = turn["meta"]
                    if meta["tool_calls"]:
                        st.caption("Tools used: " + ", ".join(f"`{t['name']}`" for t in meta["tool_calls"]))
                    render_audit([{**a, "round": i + 1} for i, a in enumerate(meta["audit_history"])], "Answer audit")
        q = st.chat_input("Ask about ARR, churn, runway, CAC, SAFEs…") or picked
        if q:
            from vicky.graphs import coach
            st.session_state.chat.append({"role": "user", "content": q})
            history = []
            for t in st.session_state.chat[:-1][-8:]:
                history.append(HumanMessage(t["content"]) if t["role"] == "user" else AIMessage(t["content"]))
            with st.spinner("Vicky is checking the numbers…"):
                try:
                    res = coach.ask(history, q)
                    st.session_state.chat.append({"role": "assistant", "content": res["answer"], "meta": res})
                except Exception as e:
                    st.session_state.chat.append({"role": "assistant", "content": f"⚠️ LLM call failed: {type(e).__name__}: {e}"})
            st.rerun()
        if st.session_state.chat and st.button("Clear chat"):
            st.session_state.chat = []
            st.rerun()

# ---------------------------------------------------------------- 5. pitch sim
with tabs[4]:
    st.subheader("Practise the pitch")
    if need_llm():
        profiles = data.investor_profiles()
        sess = st.session_state.get("pitch")
        if not sess:
            cols = st.columns(len(profiles))
            for col, (key, p) in zip(cols, profiles.items()):
                with col:
                    st.markdown(f"### {p['emoji']}\n**{p['name']}**")
                    st.caption(p["who"])
                    st.markdown(f"<span class='small'><b>Cares about:</b> {', '.join(p['cares_about'])}<br>"
                                f"<b>Says no when:</b> {', '.join(p['says_no_when'])}</span>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 1, 1])
            choice = c1.selectbox("Investor", list(profiles), format_func=lambda k: f"{profiles[k]['emoji']} {profiles[k]['name']}")
            n_q = c2.slider("Questions", 2, 5, 3)
            if c3.button("🎲 Random investor"):
                choice = random.choice(list(profiles))
                st.session_state.random_choice = choice
            choice = st.session_state.pop("random_choice", choice)
            if st.button("Start meeting", type="primary"):
                from vicky.graphs.pitch import PitchSession
                with st.spinner("The investor is taking a seat…"):
                    try:
                        st.session_state.pitch = PitchSession(choice, n_q)
                        st.session_state.pitch_persona = choice
                    except Exception as e:
                        st.error(f"LLM call failed: {type(e).__name__}: {e}")
                st.rerun()
            st.caption("Investor types are archetypes from the data pack (Appendix E), not real firms or people.")
        else:
            p = profiles[st.session_state.pitch_persona]
            state = sess.state
            st.markdown(f"**In the room:** {p['emoji']} {p['name']}. {p['style']}")
            turns = iter(state.get("turns", []))
            for t in state["transcript"]:
                if t["role"] == "investor":
                    with st.chat_message("investor", avatar=p["emoji"]):
                        st.markdown(t["text"])
                else:
                    with st.chat_message("founder", avatar="🧑‍💻"):
                        st.markdown(t["text"])
                    turn = next(turns, None)
                    if turn:
                        with st.expander(f"Feedback: {turn['weighted']:.1f}/5 (weighted for this investor)", expanded=False):
                            sc = st.columns(4)
                            for col, (d, s) in zip(sc, turn["scores"].items()):
                                col.metric(d.capitalize(), f"{s}/5")
                            fc = turn["fact_check"]
                            if fc["issues"]:
                                st.error("Fact check: " + "; ".join(f"**{i['text']}**: {i['detail']}" for i in fc["issues"]))
                            elif fc["numbers_checked"]:
                                st.success(f"Fact check: {fc['summary']}")
                            else:
                                st.info("Fact check: no figures stated. Investors expect a number.")
                            if turn["went_well"]:
                                st.markdown(f"**Went well:** {turn['went_well']}")
                            st.markdown(f"**Improve:** {turn['improve']}")
                            st.markdown(f"**A stronger answer:** {turn['stronger_answer']}")
                            sa = audit(turn["stronger_answer"])
                            if not sa.passed:
                                st.caption("⚠️ The suggested answer contains a figure the audit couldn't verify: "
                                           + ", ".join(i["text"] for i in sa.issues))
            if sess.finished:
                d = state["debrief"]
                st.divider()
                st.subheader(f"Debrief: {d['verdict']}")
                cols = st.columns(5)
                cols[0].metric("Overall (weighted)", f"{d['overall']:.1f}/5")
                for col, (k, val) in zip(cols[1:], d["averages"].items()):
                    col.metric(k.capitalize(), f"{val}/5")
                st.markdown(f"Weakest dimension: **{d['weakest']}**. Figures flagged by the fact check: **{d['flagged_figures']}**.")
                st.caption("Each investor type weights the dimensions differently (Appendix E).")
            else:
                ans = st.chat_input("Your answer…")
                if ans:
                    with st.spinner("The investor is thinking…"):
                        try:
                            sess.answer(ans)
                        except Exception as e:
                            st.error(f"LLM call failed: {type(e).__name__}: {e}")
                    st.rerun()
            if st.button("End / new meeting"):
                del st.session_state["pitch"]
                st.rerun()

# ---------------------------------------------------------------- 6. scenario lab
with tabs[5]:
    st.subheader("Scenario lab: stress-test the forecast")
    st.caption("Everything here is FORECAST. Revenue is rebuilt from drivers; spending follows the founders' plan. "
               "The model reproduces the founders' plan to within about 1% of MRR each quarter.")
    preset = st.radio("Start from", list(forecast.PRESETS), horizontal=True)
    base = forecast.PRESETS[preset]()
    c1, c2, c3 = st.columns(3)
    churn = c1.slider("Monthly logo churn", 0.005, 0.04, base.monthly_churn, 0.0025, format="%.4f",
                      help="Historical: 2.0% (12 mo), 1.6% (6 mo). Plan: 1.0%")
    ramp = c1.slider("New AE ramp (months)", 1, 6, base.ae_ramp_months, help="Historical ≈ 3. Plan: 1")
    deals = c2.slider("Deals per ramped AE / month", 2.0, 7.0, float(base.ae_new_per_month), 0.5, help="Historical: 4 to 5")
    ncg_seats = c2.select_slider("Northern Comfort seats at renewal", [0, 260, 400, 600], base.ncg_renewal_seats,
                                 help="0 = they leave. Nothing is signed.")
    uptake = c3.slider("Share of base repriced in Jan 2027", 0.0, 1.0, base.price_increase_uptake, 0.05)
    seed_month = c3.selectbox("Seed round lands", ["2027-01", "2027-02", "2027-03", "2027-04", "2027-06"],
                              index=["2027-01", "2027-02", "2027-03", "2027-04", "2027-06"].index(base.seed_month))
    hold = c3.toggle("Hold spending until the round lands", value=base.hold_spend_until_close)
    custom = forecast.with_overrides(base, name="Your scenario", monthly_churn=churn, ae_ramp_months=ramp,
                                     ae_new_per_month=deals, ncg_renewal_seats=ncg_seats, price_increase_uptake=uptake,
                                     seed_month=seed_month, hold_spend_until_close=hold)
    rows = forecast.compare(forecast.founders_plan(), custom)
    k = st.columns(4)
    plan, mine = rows
    k[0].metric("ARR at Mar 2028", f"${mine['arr_mar_2028'] / 1e6:.2f}M",
                f"{(mine['arr_mar_2028'] - plan['arr_mar_2028']) / 1e6:+.2f}M vs plan")
    k[1].metric("Cash at Mar 2028", f"${mine['cash_mar_2028'] / 1e6:.2f}M",
                f"{(mine['cash_mar_2028'] - plan['cash_mar_2028']) / 1e6:+.2f}M vs plan")
    k[2].metric("Cash runs out", mine["cash_out_month"] or "after 2030")
    rw = mine["runway_after_close_months"]
    k[3].metric("Runway after close", f"{rw} months" if rw and rw > 0 else "—",
                None if not (rw and plan["runway_after_close_months"]) else f"{rw - plan['runway_after_close_months']:+d} vs plan")
    if mine["cash_out_before_close"]:
        st.error(f"⚠️ Cash runs out in {mine['cash_out_month']}, before the round lands in {seed_month}. "
                 "Try holding spending until the term sheet is signed.")
    if mine["arr_mar_2028"] < 5_000_000:
        st.warning(f"ARR at March 2028 is ${mine['arr_mar_2028'] / 1e6:.2f}M, short of the \"$5M ARR Series A\" goal.")
    sim = forecast.run(custom).loc[:"2029-06"]
    pl = forecast.run(forecast.founders_plan()).loc[:"2029-06"]
    cdf = pd.concat([pl[["cash"]].assign(series="Founders' plan"), sim[["cash"]].assign(series="Your scenario")]).reset_index(names="month")
    cdf["month"] = pd.to_datetime(cdf["month"])
    cash_chart = alt.Chart(cdf).mark_line().encode(
        x=alt.X("month:T", title=None), y=alt.Y("cash:Q", title="Cash (CAD)", axis=alt.Axis(format="$,.2s")),
        color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#d08c00", "#3b4a9b"]), legend=alt.Legend(orient="top")),
        tooltip=["series", alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("cash:Q", format="$,.0f")])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#9b1c1c", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((cash_chart + zero).properties(height=300), width="stretch")
    st.caption("After March 2028 the burn is held at its final-quarter level, as in the data pack's runway figures.")
