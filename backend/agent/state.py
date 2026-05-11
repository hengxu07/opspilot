"""AgentState — the shared context flowing through every LangGraph node."""
from typing import Annotated, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Conversation/tool call history
    messages: Annotated[list[BaseMessage], add_messages]

    # Raw webhook payload
    event_type: str
    order_id: str
    raw_payload: dict[str, Any]

    # Populated by [investigate] node
    order_data: dict[str, Any]
    inventory_issues: list[dict[str, Any]]

    # Populated by [decide] node
    decision: str          # "hold" | "release" | "escalate"
    decision_reason: str

    # Populated by [act] node
    actions_taken: list[str]
    slack_ts: str
    sheet_row: str
    ticket_url: str

    # Telemetry
    tokens_used: int
    latency_ms: int
    error: str
