"""LangGraph node implementations for the OpsPilot agent."""
import time
import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from ..tools.shopify import get_order, check_inventory
from ..tools.slack_tool import notify_slack
from ..tools.sheets import append_audit_log
from ..tools.linear_tool import create_ticket
from ..core.config import settings
from .state import AgentState

_llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=settings.anthropic_api_key,
    max_tokens=4096,
).bind_tools([get_order, check_inventory, notify_slack, append_audit_log, create_ticket])

INVESTIGATE_SYSTEM = """You are OpsPilot, an e-commerce operations AI.
Your job: investigate Shopify order exceptions and surface inventory discrepancies.

Given an order ID:
1. Call get_order to retrieve full order details.
2. For each line item, call check_inventory on the variant to verify stock.
3. Identify any discrepancies: unfulfilled items with 0 stock, fulfillment holds, 3PL issues.
4. Return a structured JSON summary with fields: order_name, fulfillment_status, issues (list).

Be concise and factual. Do not speculate."""

DECIDE_SYSTEM = """You are OpsPilot decision engine.
Given an investigation summary, decide one of:
  - "release": no real issues, safe to proceed
  - "hold": inventory/fulfillment problem that can be auto-resolved or needs monitoring
  - "escalate": complex exception requiring human judgment

Respond ONLY with valid JSON: {"decision": "...", "reason": "one sentence"}"""


async def investigate(state: AgentState) -> dict:
    """Query Shopify, check inventory, return structured findings."""
    start = time.time()
    order_gid = f"gid://shopify/Order/{state['order_id']}"

    messages = [
        SystemMessage(content=INVESTIGATE_SYSTEM),
        HumanMessage(content=f"Investigate order {order_gid} from event: {state['event_type']}"),
    ]

    # Agentic loop — keep calling tools until model stops
    current_messages = messages
    total_tokens = 0
    for _ in range(6):  # max 6 tool rounds
        response = await _llm.ainvoke(current_messages)
        total_tokens += response.usage_metadata.get("total_tokens", 0) if response.usage_metadata else 0
        current_messages = current_messages + [response]

        if not response.tool_calls:
            break

        # Execute tool calls
        from langchain_core.messages import ToolMessage
        tool_results = []
        for tc in response.tool_calls:
            tool_map = {
                "get_order": get_order,
                "check_inventory": check_inventory,
            }
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = await tool_fn.ainvoke(tc["args"])
                tool_results.append(
                    ToolMessage(content=json.dumps(result), tool_call_id=tc["id"])
                )
        current_messages = current_messages + tool_results

    # Parse the final text response as investigation summary
    try:
        summary = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        summary = {"raw": response.content}

    latency = int((time.time() - start) * 1000)
    return {
        "messages": current_messages[len(messages):],
        "order_data": summary,
        "inventory_issues": summary.get("issues", []),
        "tokens_used": total_tokens,
        "latency_ms": latency,
    }


async def decide(state: AgentState) -> dict:
    """Decide: hold / release / escalate based on investigation findings."""
    messages = [
        SystemMessage(content=DECIDE_SYSTEM),
        HumanMessage(
            content=f"Investigation summary:\n{json.dumps(state['order_data'], indent=2)}"
        ),
    ]
    response = await _llm.ainvoke(messages)
    tokens = response.usage_metadata.get("total_tokens", 0) if response.usage_metadata else 0

    try:
        parsed = json.loads(response.content)
        decision = parsed.get("decision", "escalate")
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, TypeError):
        decision = "escalate"
        reason = str(response.content)

    return {
        "messages": [response],
        "decision": decision,
        "decision_reason": reason,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


async def act(state: AgentState) -> dict:
    """Take action: notify Slack, log to Sheets, optionally create ticket."""
    actions = []
    order_name = state["order_data"].get("order_name", state["order_id"])
    decision = state["decision"]
    reason = state["decision_reason"]

    slack_message = (
        f"*OpsPilot* | Order `{order_name}` | Decision: *{decision.upper()}*\n"
        f"_{reason}_\n"
        f"Issues: {', '.join(i.get('description', str(i)) for i in state.get('inventory_issues', [])) or 'None'}"
    )

    slack_result = await notify_slack.ainvoke({"message": slack_message})
    actions.append(f"slack:{slack_result.get('ts', 'sent')}")

    sheet_result = append_audit_log.invoke({
        "order_id": order_name,
        "event_type": state["event_type"],
        "decision": decision,
        "action_taken": ", ".join(actions),
        "notes": reason,
        "tokens_used": state.get("tokens_used", 0),
        "latency_ms": state.get("latency_ms", 0),
    })
    actions.append(f"sheet:{sheet_result.get('updated_range', 'logged')}")

    ticket_url = ""
    if decision == "escalate":
        ticket = await create_ticket.ainvoke({
            "title": f"OpsPilot escalation: {order_name}",
            "description": (
                f"**Event**: {state['event_type']}\n"
                f"**Reason**: {reason}\n"
                f"**Issues**: {json.dumps(state.get('inventory_issues', []), indent=2)}"
            ),
        })
        ticket_url = ticket.get("issue", {}).get("url", ticket.get("url", ""))
        actions.append(f"ticket:{ticket_url}")

    return {
        "actions_taken": actions,
        "slack_ts": slack_result.get("ts", ""),
        "sheet_row": sheet_result.get("updated_range", ""),
        "ticket_url": ticket_url,
    }
