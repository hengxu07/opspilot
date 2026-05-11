"""REST endpoints that expose telemetry data to the React dashboard."""
import json
from fastapi import APIRouter
from ..core.redis_client import get_redis

router = APIRouter()


@router.get("/telemetry/dlq")
async def get_dlq(limit: int = 50):
    """Return items in the dead-letter queue."""
    redis = get_redis()
    items = await redis.lrange("opspilot:dlq", 0, limit - 1)
    return {"items": [json.loads(i) for i in items]}


@router.delete("/telemetry/dlq/{index}")
async def remove_dlq_item(index: int):
    """Remove a specific DLQ item by index (replace with sentinel then clean)."""
    redis = get_redis()
    sentinel = "__deleted__"
    await redis.lset("opspilot:dlq", index, sentinel)
    await redis.lrem("opspilot:dlq", 0, sentinel)
    return {"status": "removed"}


@router.get("/telemetry/stats")
async def get_stats():
    """Aggregate stats from Redis (counters incremented by agent nodes)."""
    redis = get_redis()
    keys = ["total_events", "total_hold", "total_release", "total_escalate", "total_tokens"]
    values = await redis.mget(*[f"opspilot:stat:{k}" for k in keys])
    return {k: int(v or 0) for k, v in zip(keys, values)}
