"""Shopify webhook endpoint with HMAC verification and Redis deduplication."""
import hashlib
import hmac
import base64
import json
import time
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from ..core.config import settings
from ..core.redis_client import get_redis
from ..agent.graph import opspilot_graph
from ..agent.state import AgentState

router = APIRouter()

DEDUP_TTL = 3600  # 1 hour — ignore duplicate webhook deliveries
DLQ_KEY = "opspilot:dlq"


def _verify_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    if not settings.shopify_webhook_secret:
        return True  # dev mode: skip verification
    digest = hmac.new(
        settings.shopify_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, hmac_header)


async def _run_agent(event_type: str, order_id: str, payload: dict) -> None:
    """Background task: run the LangGraph agent for a webhook event."""
    redis = get_redis()
    try:
        initial_state: AgentState = {
            "messages": [],
            "event_type": event_type,
            "order_id": str(order_id),
            "raw_payload": payload,
            "order_data": {},
            "inventory_issues": [],
            "decision": "",
            "decision_reason": "",
            "actions_taken": [],
            "slack_ts": "",
            "sheet_row": "",
            "ticket_url": "",
            "tokens_used": 0,
            "latency_ms": 0,
            "error": "",
        }
        await opspilot_graph.ainvoke(initial_state)
    except Exception as exc:
        # Push to dead-letter queue for inspection
        await redis.lpush(
            DLQ_KEY,
            json.dumps({
                "event_type": event_type,
                "order_id": order_id,
                "error": str(exc),
                "ts": time.time(),
            }),
        )
        raise


@router.post("/webhooks/shopify")
async def shopify_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not _verify_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    event_type = request.headers.get("X-Shopify-Topic", "unknown")
    payload = json.loads(body)
    order_id = str(payload.get("id", ""))

    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order id in payload")

    # Deduplication: ignore events already processed within TTL
    redis = get_redis()
    dedup_key = f"opspilot:seen:{event_type}:{order_id}"
    if await redis.exists(dedup_key):
        return {"status": "duplicate", "order_id": order_id}
    await redis.setex(dedup_key, DEDUP_TTL, "1")

    background_tasks.add_task(_run_agent, event_type, order_id, payload)
    return {"status": "accepted", "order_id": order_id}
