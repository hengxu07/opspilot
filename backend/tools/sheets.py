"""Google Sheets tool — appends rows to the ops audit log."""
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from langchain_core.tools import tool
from ..core.config import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LOG_RANGE = "AuditLog!A:H"


def _get_service():
    info = json.loads(settings.google_service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


@tool
def append_audit_log(
    order_id: str,
    event_type: str,
    decision: str,
    action_taken: str,
    notes: str,
    tokens_used: int,
    latency_ms: int,
) -> dict:
    """Append a row to the Google Sheets audit log.

    Args:
        order_id: Shopify order ID or name (e.g. #1234).
        event_type: Webhook event type (order.created, order.updated, etc.).
        decision: Agent decision — hold | release | escalate.
        action_taken: Human-readable summary of actions taken.
        notes: Any additional context or exception details.
        tokens_used: Total tokens consumed by this agent run.
        latency_ms: Total wall-clock time in milliseconds.
    """
    from datetime import datetime, timezone

    row = [
        datetime.now(timezone.utc).isoformat(),
        order_id,
        event_type,
        decision,
        action_taken,
        notes,
        tokens_used,
        latency_ms,
    ]
    svc = _get_service()
    result = (
        svc.spreadsheets()
        .values()
        .append(
            spreadsheetId=settings.google_sheets_id,
            range=LOG_RANGE,
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        )
        .execute()
    )
    return {"updated_range": result.get("updates", {}).get("updatedRange")}
