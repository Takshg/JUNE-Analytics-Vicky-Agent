"""Pitch simulator: a persona-specific mock investor meeting.

setup -> open -> [founder_turn (interrupt) -> evaluate]* -> debrief
Each founder answer is fact-checked in code (vicky.audit) before the LLM scores it against the
persona's own rubric, so feedback on accuracy is grounded rather than the model's opinion.
If the founder uploaded a deck, each answer can point at a slide: the slide's text, its own audit and
any answer-vs-slide contradictions (vicky.deck, all in code) go to the evaluator with the answer.
"""
import uuid
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .. import audit as auditor
from .. import data
from .. import deck as decks
from ..llm import clean, get_llm, parse_json
from ..prompts import EVALUATOR, persona_system
from ..tools import scenario_facts

DIMENSIONS = ["accuracy", "evidence", "candor", "clarity"]


class PitchState(TypedDict, total=False):
    persona_key: str
    max_questions: int
    queue: list  # remaining questions: {"text", "why", "strong", "qid"}
    current: dict
    follow_ups: int
    transcript: list  # {"role": "investor"|"founder", "text"}
    turns: list  # scored turns
    done: bool
    debrief: dict
    deck: dict | None  # {"name", "slides": [{"n", "title", "text"}]}; images stay in the UI


def _questions_for(persona: dict, max_questions: int) -> list[dict]:
    qs = []
    for qid in persona["questions"]:
        q = data.question(qid)
        qs.append({"qid": qid, "text": q["question"], "why": q["why"], "strong": q["strong"]})
    for text in persona.get("extra_questions", []):
        qs.append({"qid": None, "text": text, "why": "Persona-specific question (Appendix E).",
                   "strong": "No reference answer in the pack. A strong answer is specific, uses real figures, and admits gaps."})
    # interleave persona-specific questions early so each persona feels different
    extras = [q for q in qs if q["qid"] is None]
    core = [q for q in qs if q["qid"] is not None]
    ordered = []
    while core or extras:
        if core:
            ordered.append(core.pop(0))
        if extras:
            ordered.append(extras.pop(0))
    return ordered[:max_questions]


def _setup(state: PitchState):
    persona = data.investor_profiles()[state["persona_key"]]
    queue = _questions_for(persona, state.get("max_questions", 4))
    return {"queue": queue[1:], "current": queue[0], "follow_ups": 0, "transcript": [], "turns": [], "done": False}


def _open(state: PitchState):
    persona = data.investor_profiles()[state["persona_key"]]
    prompt = (f"Open the meeting in character in 2-3 sentences (a brief greeting, then get to business), and ask "
              f"this question in your own words: \"{state['current']['text']}\"")
    text = get_llm(temperature=0.7).invoke([SystemMessage(persona_system(persona)), HumanMessage(prompt)]).content
    return {"transcript": [{"role": "investor", "text": clean(text)}]}


def _founder_turn(state: PitchState):
    reply = interrupt({"investor_said": state["transcript"][-1]["text"]})
    # resume value: plain text, or {"text", "slide"} when the founder points at a slide
    text, slide = (reply.get("text", ""), reply.get("slide")) if isinstance(reply, dict) else (reply, None)
    return {"transcript": [*state["transcript"], {"role": "founder", "text": text, "slide": slide}]}


def _fact_check(answer: str) -> dict:
    report = auditor.audit(answer, extra_known=scenario_facts())
    return {"passed": report.passed, "issues": report.issues, "summary": report.summary(),
            "numbers_checked": report.numbers_checked}


def _slide_review(answer: str, deck: dict | None, slide_no: int | None) -> dict | None:
    ctx = decks.slide_context(deck, slide_no)
    if not ctx:
        return None
    return {**ctx, "contradictions": decks.describe_contradictions(decks.contradictions(answer, ctx["text"]))}


def _slide_block(review: dict | None) -> str:
    if not review:
        return "The founder is not pointing at a slide."
    issues = "\n".join(f"- {i['type']}: '{i['text']}' ({i['detail']})" for i in review["check"]["issues"]) or \
        "- No problems found on this slide."
    contra = "\n".join(f"- {c}" for c in review["contradictions"]) or "- None."
    return (f"The founder is pointing at slide {review['n']} of {review['of']} (\"{review['title']}\"). Slide text:\n"
            f"{review['text']}\n\nAutomated check of this slide (deterministic, trust this):\n{issues}\n"
            f"Contradictions between the answer and the slide (deterministic, trust this):\n{contra}\n"
            f"If the slide contradicts the answer or states an unsupported claim, the investor notices and may push "
            f"on it, and \"improve\" says what to change on the slide. Judge accuracy on the spoken answer.")


def _evaluate(state: PitchState):
    persona = data.investor_profiles()[state["persona_key"]]
    answer = state["transcript"][-1]["text"]
    q = state["current"]
    fact = _fact_check(answer)
    slide = _slide_review(answer, state.get("deck"), state["transcript"][-1].get("slide"))
    fact_lines = "\n".join(f"- {i['type']}: '{i['text']}' ({i['detail']})" for i in fact["issues"]) or \
        ("- All figures the founder stated tie to the data." if fact["numbers_checked"] else "- The founder stated no figures.")
    can_follow = state["follow_ups"] < persona["follow_up_depth"] - 1
    next_q = state["queue"][0]["text"] if state["queue"] else "(no more questions: thank them and close the meeting)"
    prompt = EVALUATOR.format(
        persona_name=persona["name"], weights=persona["rubric_weights"], question=q["text"], why=q["why"],
        strong=q["strong"], answer=answer, fact_check=fact_lines, follow_ups=state["follow_ups"],
        max_follow_ups=persona["follow_up_depth"] - 1, next_question=next_q, slide=_slide_block(slide))
    history = "\n".join(f"{t['role'].upper()}: {t['text']}" for t in state["transcript"][-6:])
    raw = get_llm(temperature=0.4).invoke([SystemMessage(persona_system(persona)),
                                           HumanMessage(f"Recent conversation:\n{history}\n\n{prompt}")]).content
    result = parse_json(raw) or {
        "scores": {d: 3 for d in DIMENSIONS}, "went_well": "", "improve": "Evaluator output could not be parsed.",
        "stronger_answer": q["strong"], "decision": "next",
        "investor_reply": f"Let's move on. {next_q}"}
    scores = {d: max(1, min(5, int(result.get("scores", {}).get(d, 3)))) for d in DIMENSIONS}
    if fact["issues"]:  # a wrong number caps accuracy whatever the model thinks
        scores["accuracy"] = min(scores["accuracy"], 2)
    weights = persona["rubric_weights"]
    weighted = sum(scores[d] * weights[d] for d in DIMENSIONS)
    decision = "follow_up" if result.get("decision") == "follow_up" and can_follow else "next"
    turn = {"question": q["text"], "qid": q["qid"], "answer": answer, "scores": scores, "weighted": round(weighted, 2),
            "went_well": result.get("went_well", ""), "improve": result.get("improve", ""),
            "stronger_answer": result.get("stronger_answer", ""), "fact_check": fact, "decision": decision,
            "slide": slide and {k: slide[k] for k in ("n", "title", "check", "contradictions")}}
    update = {"turns": [*state["turns"], turn]}
    reply = result.get("investor_reply", "").strip()
    if decision == "follow_up":
        update.update(follow_ups=state["follow_ups"] + 1,
                      current={**q, "text": reply or q["text"], "why": f"Follow-up on: {q['text']}"})
    elif state["queue"]:
        update.update(current=state["queue"][0], queue=state["queue"][1:], follow_ups=0)
    else:
        update["done"] = True
    update["transcript"] = [*state["transcript"], {"role": "investor", "text": reply or next_q}]
    return update


def _route(state: PitchState):
    return "debrief" if state.get("done") else "founder_turn"


def _debrief(state: PitchState):
    persona = data.investor_profiles()[state["persona_key"]]
    turns = state["turns"]
    avg = {d: round(sum(t["scores"][d] for t in turns) / len(turns), 1) for d in DIMENSIONS}
    overall = round(sum(t["weighted"] for t in turns) / len(turns), 2)
    weakest = min(DIMENSIONS, key=lambda d: avg[d])
    wrong_numbers = sum(len(t["fact_check"]["issues"]) for t in turns)
    verdict = ("Would take a second meeting" if overall >= 4 else
               "Interested but unconvinced" if overall >= 3 else "Would pass for now")
    slides = {}
    for t in turns:
        s = t.get("slide")
        if s and (s["check"]["issues"] or s["contradictions"]):
            entry = slides.setdefault(s["n"], {"n": s["n"], "title": s["title"], "problems": []})
            entry["problems"] += [f"{i['type'].replace('_', ' ')}: {i['text']}" for i in s["check"]["issues"]]
            entry["problems"] += [f"contradiction: {c}" for c in s["contradictions"]]
    for entry in slides.values():
        entry["problems"] = list(dict.fromkeys(entry["problems"]))
    return {"debrief": {"persona": persona["name"], "overall": overall, "averages": avg, "weakest": weakest,
                        "verdict": verdict, "flagged_figures": wrong_numbers, "turns": len(turns),
                        "slides_flagged": sorted(slides.values(), key=lambda e: e["n"])}}


def build():
    g = StateGraph(PitchState)
    g.add_node("setup", _setup)
    g.add_node("open", _open)
    g.add_node("founder_turn", _founder_turn)
    g.add_node("evaluate", _evaluate)
    g.add_node("debrief", _debrief)
    g.add_edge(START, "setup")
    g.add_edge("setup", "open")
    g.add_edge("open", "founder_turn")
    g.add_edge("founder_turn", "evaluate")
    g.add_conditional_edges("evaluate", _route, {"founder_turn": "founder_turn", "debrief": "debrief"})
    g.add_edge("debrief", END)
    return g.compile(checkpointer=MemorySaver())


class PitchSession:
    """Thin wrapper the UI holds in session state."""

    def __init__(self, persona_key: str, max_questions: int = 4, deck: dict | None = None):
        self.graph = build()
        self.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        slides_only = {"name": deck["name"], "slides": deck["slides"]} if deck else None
        self.state = self.graph.invoke({"persona_key": persona_key, "max_questions": max_questions,
                                        "deck": slides_only}, self.config)

    def answer(self, text: str, slide: int | None = None) -> dict:
        founder = {"role": "founder", "text": text, "slide": slide}
        pending = self.graph.get_state(self.config)
        if pending.next == ("evaluate",):
            # The last attempt was recorded but its evaluation failed (rate limit, timeout): replace that
            # answer with this one and evaluate again, rather than scoring the failed text.
            transcript = [*pending.values["transcript"][:-1], founder]
            self.graph.update_state(self.config, {"transcript": transcript}, as_node="founder_turn")
            self.state = self.graph.invoke(None, self.config)
        else:
            self.state = self.graph.invoke(Command(resume={"text": text, "slide": slide}), self.config)
        return self.state

    @property
    def finished(self) -> bool:
        return bool(self.state.get("debrief"))
