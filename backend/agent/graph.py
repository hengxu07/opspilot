"""LangGraph state machine definition for OpsPilot."""
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import investigate, decide, act


def _route_decision(state: AgentState) -> str:
    """Conditional edge: after decide, go to act or directly to done."""
    # All paths go through act; act handles escalation internally.
    return "act"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("investigate", investigate)
    g.add_node("decide", decide)
    g.add_node("act", act)

    g.set_entry_point("investigate")
    g.add_edge("investigate", "decide")
    g.add_conditional_edges("decide", _route_decision, {"act": "act"})
    g.add_edge("act", END)

    return g.compile()


# Singleton compiled graph
opspilot_graph = build_graph()
