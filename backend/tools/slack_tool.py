"""Slack tool — posts operational alerts."""
from slack_sdk.web.async_client import AsyncWebClient
from langchain_core.tools import tool
from ..core.config import settings

_client = AsyncWebClient(token=settings.slack_bot_token)


@tool
async def notify_slack(message: str, channel: str | None = None) -> dict:
    """Post a message to the ops Slack channel.

    Args:
        message: The alert text to send (supports Slack markdown).
        channel: Override the default ops channel if needed.
    """
    target = channel or settings.slack_ops_channel
    response = await _client.chat_postMessage(channel=target, text=message)
    return {"ok": response["ok"], "ts": response.get("ts")}
