"""Ask Vicky: the founder asks finance questions.

agent <-> tools (up to MAX_TOOL_ROUNDS) -> audit -> (revise -> audit) -> end
The audit is deterministic (vicky.audit); a failed audit triggers one revision with the issues.
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .. import audit as auditor
from ..llm import get_llm
from ..prompts import vicky_system
from ..tools import ALL_TOOLS, scenario_facts

MAX_TOOL_ROUNDS = 3
MAX_REVISIONS = 1


class CoachState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_rounds: int
    revisions: int
    audit: dict
    audit_history: list


def _agent(state: CoachState):
    llm = get_llm()
    if state.get("tool_rounds", 0) < MAX_TOOL_ROUNDS:
        llm = llm.bind_tools(ALL_TOOLS)
    msgs = [SystemMessage(vicky_system()), *state["messages"]]
    reply = llm.invoke(msgs)
    return {"messages": [reply]}


def _route_agent(state: CoachState):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "audit"


def _count_round(state: CoachState):
    return {"tool_rounds": state.get("tool_rounds", 0) + 1}


def _tool_outputs(state: CoachState) -> list[str]:
    return [m.content for m in state["messages"] if isinstance(m, ToolMessage)]


def _audit(state: CoachState):
    answer = state["messages"][-1].content
    report = auditor.audit(answer, extra_known=[scenario_facts(), *_tool_outputs(state)])
    result = {"passed": report.passed, "issues": report.issues, "summary": report.summary()}
    return {"audit": result, "audit_history": [*state.get("audit_history", []), result]}


def _route_audit(state: CoachState):
    if not state["audit"]["passed"] and state.get("revisions", 0) < MAX_REVISIONS:
        return "revise"
    return END


def _revise(state: CoachState):
    issues = "\n".join(f"- {i['type']}: '{i['text']}' in \"{i['sentence']}\" ({i['detail']})" for i in state["audit"]["issues"])
    draft = state["messages"][-1].content
    msgs = [SystemMessage(vicky_system()), *state["messages"][:-1],
            HumanMessage(f"[Internal audit, not from the founder] Your draft answer failed an independent check:\n{issues}\n\n"
                         f"Rewrite the answer fixing every issue. Use only fact-sheet numbers; attribute founder claims; "
                         f"no valuations; source any benchmark or drop it. Output only the revised answer.\n\nDRAFT:\n{draft}")]
    reply = get_llm(temperature=0.1).invoke(msgs)
    # replace the failed draft in the visible conversation
    return {"messages": [AIMessage(content=reply.content, id=state["messages"][-1].id)],
            "revisions": state.get("revisions", 0) + 1}


def build():
    g = StateGraph(CoachState)
    g.add_node("agent", _agent)
    g.add_node("tools", ToolNode(ALL_TOOLS))
    g.add_node("count_round", _count_round)
    g.add_node("audit", _audit)
    g.add_node("revise", _revise)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _route_agent, {"tools": "tools", "audit": "audit"})
    g.add_edge("tools", "count_round")
    g.add_edge("count_round", "agent")
    g.add_conditional_edges("audit", _route_audit, {"revise": "revise", END: END})
    g.add_edge("revise", "audit")
    return g.compile()


GRAPH = None


def ask(history: list, question: str) -> dict:
    """Run one founder question. history is a list of LangChain messages from earlier turns."""
    global GRAPH
    GRAPH = GRAPH or build()
    out = GRAPH.invoke({"messages": [*history, HumanMessage(question)], "tool_rounds": 0, "revisions": 0,
                        "audit_history": []})
    new = out["messages"][len(history) + 1:]
    tool_calls = [{"name": tc["name"], "args": tc["args"]} for m in new if isinstance(m, AIMessage) for tc in m.tool_calls]
    return {
        "answer": out["messages"][-1].content,
        "tool_calls": tool_calls,
        "audit": out["audit"],
        "audit_history": out["audit_history"],
        "revised": out.get("revisions", 0) > 0,
    }
