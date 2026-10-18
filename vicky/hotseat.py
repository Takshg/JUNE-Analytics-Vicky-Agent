"""Vicky's Partner Meeting (formerly "Hot Seat"): three investors at once, a clock, and investors who walk out.

In a real raise the partner meeting is the last step: the founder pitches the whole partnership.

The panel takes turns. Each answer is scored (AI or rule-based, see vicky.practice). An investor
says "I'm out" when an answer trips their deal-breaker from Appendix E. The session ends with a
scorecard: who is still in, why each investor left, and a stronger answer to practise.

State is a plain dict so Streamlit can keep it in session_state.
"""
from . import data, practice

TIME_LIMIT_SECONDS = 45

PANEL = ["lead_seed_fund", "angel_operator", "skeptical_partner"]
# two rounds of questions per investor, chosen from each persona's Appendix E list
QUESTIONS = {
    "lead_seed_fund": [1, 10],
    "angel_operator": [3, 8],
    "skeptical_partner": [2, 9],
}

OUT_LINES = {
    "lead_seed_fund": "I'm out. I can't take a number to my partners that I can't trace back to your books.",
    "angel_operator": "I'm out for now. I need founders who know the story behind their own numbers.",
    "skeptical_partner": "I'm out. That fell apart on the first follow-up.",
}
STAY_LINES = {
    "lead_seed_fund": "Okay. That ties to the numbers.",
    "angel_operator": "Good, I like that you didn't dodge it.",
    "skeptical_partner": "Fine. Next.",
}


def _deal_breaker(persona_key: str, turn: dict) -> str | None:
    """Return why this investor walks out, or None if they stay."""
    s, w = turn["scores"], turn["weighted"]
    fact_issues = turn["fact_check"]["issues"]
    if persona_key == "lead_seed_fund":
        if fact_issues:
            return "Inflated metrics: a figure didn't tie to the data (" + ", ".join(i["text"] for i in fact_issues[:2]) + ")."
        if w < 2.8:
            return "Couldn't trace the answer to the history."
    if persona_key == "angel_operator":
        if s["accuracy"] <= 2 and s["evidence"] <= 2:
            return "Couldn't explain the number behind the story."
        if s["candor"] <= 2:
            return "Sounded like a bluff."
    if persona_key == "skeptical_partner":
        if s["candor"] <= 2:
            return "Didn't admit the obvious weak spot."
        if w < 3.2:
            return "The claim didn't survive one follow-up question."
    if turn.get("overtime"):
        return f"Took longer than {TIME_LIMIT_SECONDS} seconds and lost the room."
    return None


def new_session() -> dict:
    queue = []
    for round_ in range(2):
        for p in PANEL:
            queue.append({"persona": p, "qid": QUESTIONS[p][round_]})
    return {"queue": queue, "turns": [], "out": {}, "done": False}


def current(state: dict) -> dict | None:
    """The next question from an investor who is still in the room."""
    while state["queue"] and state["queue"][0]["persona"] in state["out"]:
        state["queue"].pop(0)
    if not state["queue"]:
        state["done"] = True
        return None
    nxt = state["queue"][0]
    persona = data.investor_profiles()[nxt["persona"]]
    return {**nxt, "name": persona["name"], "emoji": persona["emoji"], "question": practice.question(nxt["qid"])}


def submit(state: dict, answer: str, seconds: float, use_ai: bool = True, lang: str = "en") -> dict:
    cur = current(state)
    if cur is None:
        return {}
    turn = practice.score(cur["question"], answer, cur["persona"], use_ai=use_ai, lang=lang)
    turn["persona"], turn["seconds"] = cur["persona"], round(seconds)
    turn["overtime"] = seconds > TIME_LIMIT_SECONDS
    if turn["overtime"]:
        turn["scores"]["clarity"] = max(1, turn["scores"]["clarity"] - 1)
        turn["weighted"] = practice._weighted(turn["scores"], cur["persona"])
    reason = _deal_breaker(cur["persona"], turn)
    turn["walked_out"] = bool(reason)
    turn["reaction"] = OUT_LINES[cur["persona"]] if reason else STAY_LINES[cur["persona"]]
    if reason:
        state["out"][cur["persona"]] = reason
    state["turns"].append(turn)
    state["queue"].pop(0)
    current(state)  # updates done
    return turn


def scorecard(state: dict) -> dict:
    profiles = data.investor_profiles()
    still_in = [p for p in PANEL if p not in state["out"]]
    turns = state["turns"]
    avg = round(sum(t["weighted"] for t in turns) / len(turns), 2) if turns else 0
    weakest = min(turns, key=lambda t: t["weighted"]) if turns else None
    return {
        "still_in": [profiles[p]["name"] for p in still_in],
        "walked_out": [{"name": profiles[p]["name"], "emoji": profiles[p]["emoji"], "reason": r} for p, r in state["out"].items()],
        "average": avg,
        "verdict": ("All three want a second meeting" if len(still_in) == 3 else
                    "You kept part of the room" if still_in else "Everyone walked out. Fix the weakest answer and go again."),
        "weakest": weakest,
    }
