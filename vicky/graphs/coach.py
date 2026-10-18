"""Ask Vicky: the founder asks finance questions, answered through a hierarchical decision model.

gate -> (plan) -> execute -> answer -> audit -> (revise -> audit) -> end

Level 1  gate     code only: valuation / investment advice / competitor data go to the boundary path
Level 2  plan     LLM planner returns JSON intent + tools; keyword fallback if it fails
Level 3  execute  vicky.decision.validate_plan checks the plan in code, then the tools run in code
answer            per-intent playbook; the model writes REASONING (numbered steps) then ANSWER
The audit is deterministic (vicky.audit); a failed audit triggers one revision with the issues.
2-3 LLM calls per question, and no reliance on the model's native tool calling.
"""
import json
import operator
import re
import time
from functools import wraps
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .. import audit as auditor
from .. import data, decision, metrics
from ..llm import clean, get_llm, parse_json
from ..prompts import ANSWER, CHAT_REVISE, PLANNER, vicky_system
from ..tools import ALL_TOOLS, scenario_facts

MAX_REVISIONS = 1
MAX_EVIDENCE_CHARS = 3500  # per tool result, to keep free-model prompts small


class CoachState(TypedDict, total=False):
    question: str
    history: list
    policy: dict | None
    plan: dict
    trace: list
    evidence: list
    raw: str
    reasoning: list
    answer: str
    audit: dict
    audit_history: list
    revisions: int
    timings: Annotated[list, operator.add]  # [{"step", "seconds"}], one per node run


def _history_text(history: list, turns: int = 4) -> str:
    lines = [f"{'Founder' if isinstance(m, HumanMessage) else 'Vicky'}: {m.content[:300]}" for m in history[-turns:]]
    return "\n".join(lines) or "(none)"


def _tool_catalog() -> str:
    out = []
    for t in ALL_TOOLS:
        args = ", ".join(t.args)
        out.append(f"- {t.name}({args}): {' '.join(t.description.split())[:220]}")
    return "\n".join(out)


def split_reasoning(text: str) -> tuple[list[str], str]:
    """Split a 'REASONING: ... ANSWER: ...' reply into (steps, answer). Tolerates markdown headers."""
    text = clean(text)
    parts = re.split(r"(?im)^[#*_\s]*answer[*_\s]*:[*_\s]*", text, maxsplit=1)
    if len(parts) < 2:
        return [], text.strip()
    head, answer = parts
    head = re.sub(r"(?im)^[#*_\s]*reasoning[*_\s]*:[*_\s]*", "", head)
    steps = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+[.)]\s+(.+)$", head)]
    if not steps:
        steps = [ln.strip("-* ").strip() for ln in head.splitlines() if ln.strip("-* ").strip()]
    return steps, answer.strip()


def _gate(state: CoachState):
    hit = decision.gate(state["question"])
    if hit:
        return {"policy": hit, "plan": decision.policy_plan(hit),
                "trace": [{"level": "1 policy", "decision": f"boundary: {hit['rule']}", "by": "code"}]}
    return {"policy": None, "trace": [{"level": "1 policy", "decision": "allowed", "by": "code"}]}


def _route_gate(state: CoachState):
    return "execute" if state.get("policy") else "plan"


def _plan(state: CoachState):
    q = state["question"]
    prompt = PLANNER.format(
        intents=decision.catalog_text(), tools=_tool_catalog(), metric_keys=", ".join(metrics.registry()),
        questions="\n".join(f"{x['id']}: {x['question']}" for x in data.questions()),
        history=_history_text(state.get("history", [])), question=q)
    proposal, by = None, "llm"
    try:
        proposal = parse_json(get_llm(temperature=0).invoke([HumanMessage(prompt)]).content)
    except Exception as e:  # rate limit or bad response: the keyword planner still answers the question
        by = f"fallback ({type(e).__name__})"
    if not proposal:
        proposal, by = decision.heuristic_plan(q), (by if by != "llm" else "fallback (no JSON)")
    plan, notes = decision.validate_plan(proposal, q)
    trace = [{"level": "2 intent", "decision": f"{plan['intent']}: {plan['why'] or proposal.get('why', '')}".strip(": "),
              "by": by}]
    trace += [{**n, "level": "2 intent" if n["level"] == "intent" else "3 plan"} for n in notes]
    return {"plan": plan, "trace": [*state["trace"], *trace]}


def _execute(state: CoachState):
    tools = {t.name: t for t in ALL_TOOLS}
    evidence, trace = [], []
    for call in state["plan"]["tools"]:
        try:
            output = tools[call["name"]].invoke(call["args"])
            ok = True
        except Exception as e:
            output, ok = f"Tool error: {type(e).__name__}: {e}", False
        evidence.append({"name": call["name"], "args": call["args"], "output": output, "ok": ok})
        trace.append({"level": "3 execute", "decision": f"{call['name']}({json.dumps(call['args'])[1:-1]})"
                                                        f"{'' if ok else ' failed'}", "by": "code"})
    return {"evidence": evidence, "trace": [*state["trace"], *trace]}


def _evidence_text(evidence: list) -> str:
    if not evidence:
        return "(no tool results; use the fact sheet)"
    return "\n\n".join(f"[{e['name']}({json.dumps(e['args'])[1:-1]})]\n{e['output'][:MAX_EVIDENCE_CHARS]}" for e in evidence)


def _answer(state: CoachState):
    plan = state["plan"]
    policy = state.get("policy")
    prompt = ANSWER.format(
        question=state["question"], intent=plan["intent"], playbook=decision.INTENTS[plan["intent"]]["playbook"],
        policy=f"POLICY: {policy['guidance']}\n" if policy else "", evidence=_evidence_text(state["evidence"]))
    msgs = [SystemMessage(vicky_system()), *state.get("history", []), HumanMessage(prompt)]
    raw = get_llm().invoke(msgs).content
    steps, answer = split_reasoning(raw)
    return {"raw": raw, "reasoning": steps, "answer": answer}


def _audit(state: CoachState):
    text = "\n".join([*state["reasoning"], state["answer"]])
    report = auditor.audit(text, extra_known=[scenario_facts(), *[e["output"] for e in state["evidence"]]])
    result = {"passed": report.passed, "issues": report.issues, "summary": report.summary()}
    return {"audit": result, "audit_history": [*state.get("audit_history", []), result]}


def _route_audit(state: CoachState):
    if not state["audit"]["passed"] and state.get("revisions", 0) < MAX_REVISIONS:
        return "revise"
    return END


def _revise(state: CoachState):
    issues = auditor.revision_brief(state["audit"]["issues"])
    draft = "REASONING:\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(state["reasoning"], 1)) + \
            f"\nANSWER:\n{state['answer']}"
    prompt = CHAT_REVISE.format(issues=issues, evidence=_evidence_text(state["evidence"]), draft=draft)
    raw = get_llm(temperature=0.1).invoke([SystemMessage(vicky_system()), HumanMessage(prompt)]).content
    steps, answer = split_reasoning(raw)
    return {"raw": raw, "reasoning": steps or state["reasoning"], "answer": answer,
            "revisions": state.get("revisions", 0) + 1}


def _timed(step: str, fn):
    """Wrap a node so each run records its wall-clock time."""
    @wraps(fn)
    def run(state: CoachState):
        start = time.perf_counter()
        out = fn(state)
        return {**out, "timings": [{"step": step, "seconds": round(time.perf_counter() - start, 2)}]}
    return run


def build():
    g = StateGraph(CoachState)
    for name, fn in [("gate", _gate), ("plan", _plan), ("execute", _execute), ("answer", _answer),
                     ("audit", _audit), ("revise", _revise)]:
        g.add_node(name, _timed(name, fn))
    g.add_edge(START, "gate")
    g.add_conditional_edges("gate", _route_gate, {"plan": "plan", "execute": "execute"})
    g.add_edge("plan", "execute")
    g.add_edge("execute", "answer")
    g.add_edge("answer", "audit")
    g.add_conditional_edges("audit", _route_audit, {"revise": "revise", END: END})
    g.add_edge("revise", "audit")
    return g.compile()


GRAPH = None


def ask(history: list, question: str) -> dict:
    """Run one founder question. history is a list of LangChain messages from earlier turns."""
    global GRAPH
    GRAPH = GRAPH or build()
    start = time.perf_counter()
    out = GRAPH.invoke({"question": question, "history": list(history), "trace": [], "audit_history": [],
                        "revisions": 0, "timings": []})
    return {
        "answer": out["answer"],
        "reasoning": out["reasoning"],
        "intent": out["plan"]["intent"],
        "plan": out["plan"],
        "policy": out.get("policy"),
        "decision_trace": out["trace"],
        "evidence": [{k: e[k] for k in ("name", "args", "ok")} | {"preview": e["output"][:600]} for e in out["evidence"]],
        "tool_calls": [{"name": e["name"], "args": e["args"]} for e in out["evidence"]],
        "audit": out["audit"],
        "audit_history": out["audit_history"],
        "revised": out.get("revisions", 0) > 0,
        "timings": out["timings"],
        "seconds": round(time.perf_counter() - start, 2),
    }
