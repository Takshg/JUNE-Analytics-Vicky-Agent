"""Pitch simulator: a persona-specific mock investor meeting.

setup -> open -> [founder_turn (interrupt) -> evaluate]* -> debrief
Each founder answer is fact-checked in code (vicky.audit) before the LLM scores it against the
persona's own rubric, so feedback on accuracy is grounded rather than the model's opinion.
"""
import uuid
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .. import audit as auditor
from .. import data
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
    answer = interrupt({"investor_said": state["transcript"][-1]["text"]})
    return {"transcript": [*state["transcript"], {"role": "founder", "text": answer}]}


def _fact_check(answer: str) -> dict:
    report = auditor.audit(answer, extra_known=scenario_facts())
    return {"passed": report.passed, "issues": report.issues, "summary": report.summary(),
            "numbers_checked": report.numbers_checked}


def _evaluate(state: PitchState):
    persona = data.investor_profiles()[state["persona_key"]]
    answer = state["transcript"][-1]["text"]
    q = state["current"]
    fact = _fact_check(answer)
    fact_lines = "\n".join(f"- {i['type']}: '{i['text']}' ({i['detail']})" for i in fact["issues"]) or \
        ("- All figures the founder stated tie to the data." if fact["numbers_checked"] else "- The founder stated no figures.")
    can_follow = state["follow_ups"] < persona["follow_up_depth"] - 1
    next_q = state["queue"][0]["text"] if state["queue"] else "(no more questions: thank them and close the meeting)"
    prompt = EVALUATOR.format(
        persona_name=persona["name"], weights=persona["rubric_weights"], question=q["text"], why=q["why"],
        strong=q["strong"], answer=answer, fact_check=fact_lines, follow_ups=state["follow_ups"],
        max_follow_ups=persona["follow_up_depth"] - 1, next_question=next_q)
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
            "stronger_answer": result.get("stronger_answer", ""), "fact_check": fact, "decision": decision}
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
    return {"debrief": {"persona": persona["name"], "overall": overall, "averages": avg, "weakest": weakest,
                        "verdict": verdict, "flagged_figures": wrong_numbers, "turns": len(turns)}}


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

    def __init__(self, persona_key: str, max_questions: int = 4):
        self.graph = build()
        self.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        self.state = self.graph.invoke({"persona_key": persona_key, "max_questions": max_questions}, self.config)

    def answer(self, text: str) -> dict:
        self.state = self.graph.invoke(Command(resume=text), self.config)
        return self.state

    @property
    def finished(self) -> bool:
        return bool(self.state.get("debrief"))
