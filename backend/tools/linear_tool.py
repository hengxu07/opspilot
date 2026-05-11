"""Linear tool — creates escalation tickets for human review."""
import httpx
from langchain_core.tools import tool
from ..core.config import settings

LINEAR_API = "https://api.linear.app/graphql"


@tool
async def create_ticket(title: str, description: str, priority: int = 2) -> dict:
    """Create a Linear ticket to escalate an order exception to a human.

    Args:
        title: Short ticket title.
        description: Full context including order ID, exception type, and what the agent tried.
        priority: 1=urgent, 2=high, 3=medium, 4=low. Defaults to high.
    """
    if not settings.linear_api_key:
        return {"mock": True, "title": title, "description": description}

    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier url }
      }
    }
    """
    variables = {
        "input": {
            "title": title,
            "description": description,
            "teamId": settings.linear_team_id,
            "priority": priority,
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            LINEAR_API,
            headers={"Authorization": settings.linear_api_key},
            json={"query": mutation, "variables": variables},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("issueCreate", {})
