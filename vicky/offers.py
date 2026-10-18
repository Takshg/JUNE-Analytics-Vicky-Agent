"""Offer round: investors make offers, the founder decides on the clock, then a debrief.

Numbers are code: each offer is kept inside the persona's cheque range (Appendix E) and a simulation band anchored
on Tidewell's own SAFE caps, and every term (implied pre/post-money, vs the founder's ask, share of the raise) is
computed here. The AI only writes the investors' pitches and Vicky's debrief, and the debrief is audited.
Offers are role-play by investor archetypes, not a valuation view: Vicky never says which offer to take.
"""
import math
import re

from langchain_core.messages import HumanMessage, SystemMessage

from . import audit as auditor
from . import data, i18n
from .llm import clean, get_llm, parse_json
from .prompts import RULES, vicky_system

TIME_LIMIT_SECONDS = 90
DEFAULT_INVESTORS = ["lead_seed_fund", "strategic_investor", "government_fund", "angel_operator"]
CO_INVEST = (250_000, 1_000_000)  # government fund "co-invests beside a private lead": no range in the pack

# per persona: (share of the ask they put in, their valuation vs the founder's ask, condition) for offers without AI
FALLBACK = {
    "lead_seed_fund": (0.60, 0.80, "board seat and a 10% option pool top-up before the round"),
    "strategic_investor": (0.15, 0.90, "right of first refusal if Tidewell is ever sold"),
    "government_fund": (0.20, 1.00, "conditional on a private lead investor closing first"),
    "angel_operator": (0.03, 1.00, ""),
}
FALLBACK_PITCH = {
    "lead_seed_fund": ("We'll lead and set the terms, and help you build the Series A story.",
                       "Growth and capital efficiency are real; retention needs work."),
    "strategic_investor": ("Our distributor channel puts Tidewell in front of thousands of contractors.",
                           "The product fits the customers we already sell to."),
    "government_fund": ("We match a private lead and back Canadian software jobs and IP.",
                        "Toronto team, Canadian IP, a credible lead in sight."),
    "angel_operator": ("I've run B2B sales; I'll help your account executives close faster.",
                       "The founders know their product and learn fast."),
}


def _caps() -> list[float]:
    """SAFE valuation caps from the pack (Appendix A): the only valuation reference points we have."""
    caps = [float(m.group(1)) * 1e6 for f in data.company()["funding"]
            if (m := re.search(r"\$([\d.]+)M valuation cap", f["terms"]))]
    return sorted(caps)


def post_money_band() -> tuple[float, float]:
    """Simulation guardrail, not a valuation view: 0.6x the lowest SAFE cap to 2x the highest."""
    caps = _caps()
    return 0.6 * caps[0], 2 * caps[-1]


def cheque_range(persona_key: str) -> tuple[float, float] | None:
    text = data.investor_profiles()[persona_key]["cheque"]
    m = re.search(r"\$([\d.]+)\s*([KM])\s*to\s*\$([\d.]+)\s*([KM])", text)
    if m:
        unit = {"K": 1e3, "M": 1e6}
        return float(m.group(1)) * unit[m.group(2)], float(m.group(3)) * unit[m.group(4)]
    return CO_INVEST if "co-invest" in text.lower() else None  # None: doesn't write cheques


def investors() -> list[str]:
    return [k for k in data.investor_profiles() if cheque_range(k)]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def validate(raw: dict, persona_key: str, ask_money: float, ask_equity: float) -> dict:
    """Keep an offer inside the persona's cheque and the post-money band. Records every adjustment."""
    lo, hi = cheque_range(persona_key)
    notes = []
    try:
        money = float(str(raw.get("money", "")).replace(",", "").replace("$", ""))
    except ValueError:
        money = hi
        notes.append("amount unreadable")
    if not lo <= money <= hi:
        notes.append(f"amount moved into the cheque range (${lo:,.0f} to ${hi:,.0f})")
        money = _clamp(money, lo, hi)
    ask_post = ask_money / (ask_equity / 100)
    try:
        equity = float(str(raw.get("equity", "")).replace("%", ""))
    except ValueError:
        equity = None
    if not equity or equity <= 0:
        equity = money / ask_post * 100
        notes.append("equity missing: set at the founder's valuation")
    band_lo, band_hi = post_money_band()
    eq_lo, eq_hi = money / band_hi * 100, money / band_lo * 100
    if not eq_lo <= equity <= eq_hi:
        notes.append("equity kept inside the simulation band")
        equity = _clamp(equity, eq_lo, eq_hi)
    # round to 0.1% without leaving the band (16.67% -> 16.7% would dip under the post-money floor)
    equity = _clamp(round(equity, 1), math.ceil(eq_lo * 10) / 10, math.floor(eq_hi * 10) / 10)
    return {"persona": persona_key, "money": round(money, -3), "equity": equity,
            "condition": str(raw.get("condition") or "")[:200], "pitch": str(raw.get("pitch") or "")[:300],
            "why": str(raw.get("why") or "")[:300], "adjusted": notes}


def fallback_offers(personas: list[str], ask_money: float, ask_equity: float) -> list[dict]:
    ask_post = ask_money / (ask_equity / 100)
    out = []
    for k in personas:
        share, value, cond = FALLBACK[k]
        money = share * ask_money
        pitch, why = FALLBACK_PITCH[k]
        out.append(validate({"money": money, "equity": money / (ask_post * value) * 100, "condition": cond,
                             "pitch": pitch, "why": why}, k, ask_money, ask_equity) | {"source": "rules"})
    return out


OFFERS_PROMPT = """It's the end of Tidewell's seed pitch. The founders asked for ${ask_money:,.0f} for {ask_equity:g}%.
Each investor below now makes ONE offer, in character. Investors may offer less money, ask for more equity, or add
a condition (board seat, milestone tranche, right of first refusal, co-invest condition). Stay inside each cheque.

INVESTORS:
{investors}

Tidewell's real numbers are in the system prompt. Base each pitch on what that investor cares about.
Reply with ONLY a JSON object:
{{"offers": [{{"persona": "<key>", "money": <number>, "equity": <percent number>, "condition": "<short or empty>",
  "pitch": "<what they bring, 1 sentence, in their voice>", "why": "<what made them offer, 1 sentence>"}}]}}"""


def generate(personas: list[str], ask_money: float, ask_equity: float, use_ai: bool = True,
             lang: str = "en") -> list[dict]:
    """One AI call for every investor's offer; code validates each one. Falls back to rule-based offers."""
    if use_ai:
        profiles = data.investor_profiles()
        lines = "\n".join(f"- {k}: {profiles[k]['name']}. {profiles[k]['who']} Cheque: {profiles[k]['cheque']}. "
                          f"Cares about: {', '.join(profiles[k]['cares_about'])}." for k in personas)
        prompt = OFFERS_PROMPT.format(ask_money=ask_money, ask_equity=ask_equity, investors=lines)
        try:
            reply = get_llm(temperature=0.6).invoke([SystemMessage(vicky_system()),
                                                     HumanMessage(prompt + i18n.ai_instruction(lang))]).content
            raw = {o.get("persona"): o for o in (parse_json(reply) or {}).get("offers", []) if isinstance(o, dict)}
            if all(k in raw for k in personas):
                return [validate(raw[k], k, ask_money, ask_equity) | {"source": "ai"} for k in personas]
        except Exception:
            pass  # rate limit, bad JSON: the round still runs on rule-based offers
    return fallback_offers(personas, ask_money, ask_equity)


def terms(offer: dict, ask_money: float, ask_equity: float) -> dict:
    """Mechanics of an offer, computed in code."""
    post = offer["money"] / (offer["equity"] / 100)
    ask_post = ask_money / (ask_equity / 100)
    raise_amount = data.company()["raise"]["amount"]
    return {"post_money": post, "pre_money": post - offer["money"], "vs_ask": post / ask_post - 1,
            "share_of_raise": offer["money"] / raise_amount,
            "vs_caps": [(cap, "above" if post > cap else "below") for cap in _caps()]}


def describe(offer: dict, t: dict) -> str:
    caps = ", ".join(f"{pos} the ${cap / 1e6:.0f}M SAFE cap" for cap, pos in t["vs_caps"])
    return (f"${offer['money']:,.0f} for {offer['equity']:g}%"
            + (f" ({offer['condition']})" if offer.get("condition") else "")
            + f": implies ${t['post_money'] / 1e6:.1f}M post-money (${t['pre_money'] / 1e6:.1f}M pre-money), "
              f"{t['vs_ask'] * 100:+.0f}% vs the founders' ask, {t['share_of_raise'] * 100:.0f}% of the "
              f"${data.company()['raise']['amount'] / 1e6:.0f}M raise; {caps}")


def describe_decision(decision: dict, offers: list[dict], ask_money: float, ask_equity: float) -> str:
    profiles = data.investor_profiles()
    if decision["kind"] == "accept":
        o = offers[decision["index"]]
        return f"accepted {profiles[o['persona']]['name']}'s offer: {describe(o, terms(o, ask_money, ask_equity))}"
    if decision["kind"] == "counter":
        o = {"money": decision["money"], "equity": decision["equity"], "condition": ""}
        to = profiles[offers[decision["index"]]["persona"]]["name"]
        return f"countered {to} with {describe(o, terms(o, ask_money, ask_equity))}"
    if decision["kind"] == "timeout":
        return "ran out of time without deciding"
    return "walked away from every offer"



# How far each investor will move off their own valuation when countered. Simulation settings matched to each
# archetype's style (Appendix E: the lead "sets the terms", angels "give a lot of time"), not market data.
FLEX = {"lead_seed_fund": 0.10, "strategic_investor": 0.15, "government_fund": 0.20, "angel_operator": 0.25}
OUTCOME_LABEL = {"deal": "Deal", "halfway": "Meets you halfway", "firm": "Holds firm", "withdraw": "Withdraws",
                 "co_invest": "Joins the round", "pass": "Passes", "door_open": "Door stays open",
                 "waiting": "Waiting for an answer"}
TEMPLATE_LINES = {
    "deal": "We have a deal. Let's get the term sheet drafted.",
    "halfway": "I can't go all the way there, but I'll meet you in the middle.",
    "firm": "My offer stands as it is. Let me know if you change your mind.",
    "withdraw": "That's too far from where I am. I'll step back from this one.",
    "co_invest": "With a lead in place, we'll come in beside them on the same terms.",
    "pass": "You've chosen your partner. Good luck with the round.",
    "door_open": "Understood. If your plans change, my door is open.",
    "waiting": "I need an answer before I take this to my partners.",
}


def _post(money: float, equity: float) -> float:
    return money / (equity / 100)


def _at_post(persona: str, money: float, post: float) -> dict:
    return {"persona": persona, "money": round(money, -3), "equity": round(money / post * 100, 1)}


def reactions(decision: dict, offers: list[dict]) -> list[dict]:
    """How each investor responds to the founder's decision. The outcome is decided here, in code; the AI only
    voices it. Each item: {"persona", "outcome", "money", "equity", "note"} (terms are None without a deal)."""
    kind, idx = decision["kind"], decision.get("index")
    out = []
    lead_deal = None
    for i, o in enumerate(offers):
        k = o["persona"]
        r = {"persona": k, "outcome": "pass", "money": None, "equity": None, "note": ""}
        if kind == "walk":
            r["outcome"] = "door_open"
        elif kind == "timeout":
            r["outcome"] = "waiting"
        elif i == idx and kind == "accept":
            r.update(outcome="deal", money=o["money"], equity=o["equity"])
        elif i == idx and kind == "counter":
            lo, hi = cheque_range(k)
            # the founder's proposed valuation is what's negotiated; an amount outside the cheque is scaled to fit
            asked, theirs = _post(decision["money"], decision["equity"]), _post(o["money"], o["equity"])
            money = _clamp(decision["money"], lo, hi)
            if money != decision["money"]:
                r["note"] = f"can only invest ${lo:,.0f} to ${hi:,.0f}"
            gap, flex = asked / theirs - 1, FLEX.get(k, 0.10)
            if gap <= flex / 2:
                r.update(outcome="deal", **{key: v for key, v in _at_post(k, money, asked).items() if key != "persona"})
            elif gap <= flex:
                mid = _at_post(k, money, (asked + theirs) / 2)
                r.update(outcome="halfway", money=mid["money"], equity=mid["equity"])
            elif gap <= 3 * flex:
                r.update(outcome="firm", money=o["money"], equity=o["equity"])
            else:
                r["outcome"] = "withdraw"
        out.append(r)
        if r["outcome"] in ("deal", "halfway") and k == "lead_seed_fund":
            lead_deal = r
    if lead_deal:  # the government fund co-invests beside a private lead (Appendix E), at the lead's price
        price = _post(lead_deal["money"], lead_deal["equity"])
        for r, o in zip(out, offers):
            if r["persona"] == "government_fund" and r["outcome"] == "pass":
                r.update(outcome="co_invest", **{k_: v for k_, v in _at_post("government_fund", o["money"], price).items()
                                                 if k_ != "persona"})
    return out


def round_summary(reacts: list[dict]) -> dict:
    """Money committed if the deals on the table close. "agreed" excludes halfway offers the founder hasn't taken."""
    committed = [r for r in reacts if r["outcome"] in ("deal", "halfway", "co_invest")]
    raised = sum(r["money"] for r in committed)
    target = data.company()["raise"]["amount"]
    return {"raised": raised, "target": target, "share": raised / target,
            "equity_sold": round(sum(r["equity"] for r in committed), 1),
            "agreed": sum(r["money"] for r in committed if r["outcome"] != "halfway")}


REPLIES_PROMPT = """The founders just responded to investor offers. Write each investor's reply, in character, 1-2
sentences. The OUTCOME and TERMS are decided; do not change them or mention valuation. Don't restate the terms or
write any numbers, in digits or words: the terms are shown next to your reply.

{lines}

Reply with ONLY a JSON object: {{"replies": [{{"persona": "<key>", "line": "<reply>"}}]}}"""


def voice(reacts: list[dict], decision_text: str, use_ai: bool = True, lang: str = "en") -> list[dict]:
    """Adds a "line" to each reaction: AI-written in the investor's voice, audited, else a template."""
    profiles = data.investor_profiles()
    lines = {}
    if use_ai:
        desc = "\n".join(
            f"- {r['persona']} ({profiles[r['persona']]['name']}, style: {' '.join(profiles[r['persona']]['style'].split())}): "
            f"OUTCOME {OUTCOME_LABEL[r['outcome']]}"
            + (f", TERMS ${r['money']:,.0f} for {r['equity']:g}%" if r["money"] else "")
            + (f", note: {r['note']}" if r["note"] else "") for r in reacts)
        try:
            reply = get_llm(temperature=0.6).invoke([HumanMessage(
                f"The founder {decision_text}.\n\n" + REPLIES_PROMPT.format(lines=desc) + i18n.ai_instruction(lang))]).content
            got = {x.get("persona"): str(x.get("line", ""))[:280] for x in (parse_json(reply) or {}).get("replies", [])
                   if isinstance(x, dict)}
            known = [f"${r['money']:,.0f} for {r['equity']:g}%" for r in reacts if r["money"]]
            lines = {k: v for k, v in got.items() if v and auditor.audit(v, extra_known=known).passed}
        except Exception:
            pass
    return [r | {"line": lines.get(r["persona"]) or TEMPLATE_LINES[r["outcome"]],
                 "voice": "ai" if r["persona"] in lines else "rules"} for r in reacts]


DEBRIEF_PROMPT = """Offer round debrief. The founders asked for ${ask_money:,.0f} for {ask_equity:g}%.

OFFERS (terms computed in code):
{offers}

THE FOUNDER {decision}.
HOW THE INVESTORS RESPONDED (decided in code; "Meets you halfway" is a revised offer the founder hasn't accepted
yet, so count it as on the table, not raised):
{responses}

In under 180 words, for the founders: explain what their decision means in practice (ownership given up, money
raised against the ${raise_amount:,.0f} target, the conditions they took on), and the trade-offs between the offers
(money vs equity vs conditions vs who leads). Explain what a SAFE cap means for these valuations in one sentence.
{rules_reminder}
Do NOT say which offer to take, whether the decision was right, or what Tidewell is worth. Use only figures above."""


def debrief(decision: dict, offers: list[dict], ask_money: float, ask_equity: float, reacts: list[dict] | None = None,
            use_ai: bool = True, lang: str = "en") -> dict:
    """Vicky explains the trade-offs. Audited; falls back to a rule-based summary without AI."""
    profiles = data.investor_profiles()
    offer_lines = [f"- {profiles[o['persona']]['name']}: {describe(o, terms(o, ask_money, ask_equity))}" for o in offers]
    said = describe_decision(decision, offers, ask_money, ask_equity)
    known = [o | terms(o, ask_money, ask_equity) for o in offers] + [{"ask": ask_money, "eq": ask_equity}]
    if decision.get("money"):
        known.append(decision | terms({"money": decision["money"], "equity": decision["equity"]}, ask_money, ask_equity))
    reacts = reacts if reacts is not None else reactions(decision, offers)
    summary = round_summary(reacts)
    response_lines = [f"- {profiles[r['persona']]['name']}: {OUTCOME_LABEL[r['outcome']]}"
                      + (f" at ${r['money']:,.0f} for {r['equity']:g}%" if r["money"] else "") for r in reacts]
    response_lines.append(f"Committed if these close: ${summary['raised']:,.0f} ({summary['share'] * 100:.0f}% of the "
                          f"target), {summary['equity_sold']:g}% of the company. Agreed so far (excluding offers the "
                          f"founder hasn't accepted): ${summary['agreed']:,.0f}")
    if decision["kind"] == "counter":  # comparisons the model got backwards in testing, worked out here
        for r in reacts:
            if r["money"] and r["outcome"] in ("deal", "halfway") and r["equity"] != decision["equity"]:
                more = "more" if r["equity"] > decision["equity"] else "less"
                response_lines.append(f"{profiles[r['persona']]['name']}'s {r['equity']:g}% is {more} equity than "
                                      f"the founder's counter of {decision['equity']:g}%")
    known += [summary] + offer_lines + response_lines  # formatted lines carry units ("7.2%"), so the audit can tie them
    if use_ai:
        prompt = DEBRIEF_PROMPT.format(ask_money=ask_money, ask_equity=ask_equity, offers="\n".join(offer_lines),
                                       decision=said.upper()[:1] + said[1:], responses="\n".join(response_lines),
                                       raise_amount=data.company()["raise"]["amount"],
                                       rules_reminder=RULES.splitlines()[0])
        try:
            msgs = [SystemMessage(vicky_system()), HumanMessage(prompt + i18n.ai_instruction(lang))]
            text = clean(get_llm().invoke(msgs).content)
            report = auditor.audit(text, extra_known=known)
            if not report.passed:  # one revision, as in Ask Vicky and the prep pack
                fix = (f"An independent audit of your debrief found:\n{auditor.revision_brief(report.issues)}\n\n"
                       f"Rewrite the debrief applying each FIX. Change nothing else. Output only the debrief.\n\n"
                       f"DEBRIEF:\n{text}")
                text = clean(get_llm(temperature=0.1).invoke([SystemMessage(vicky_system()), HumanMessage(fix)]).content)
                report = auditor.audit(text, extra_known=known)
            return {"text": text, "source": "ai", "audit": {"passed": report.passed, "issues": report.issues,
                                                             "summary": report.summary()}}
        except Exception:
            pass
    text = (f"You {said}.\n\n" + "\n".join(response_lines) + "\n\n" + "\n".join(offer_lines)
            + "\n\nA SAFE cap is the highest valuation at which a SAFE converts: if the round prices below a cap, "
              "those SAFE holders convert at the round price and own more of the company.")
    return {"text": text, "source": "rules", "audit": None}
