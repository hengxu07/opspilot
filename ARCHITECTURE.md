# OpsPilot — Architecture

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind | Ops dashboard — polls every 5s |
| Backend | FastAPI (Python) | Webhook receiver + telemetry API |
| AI | Claude Sonnet 4.6 (via LangChain Anthropic) | Investigation, decision, and action |
| Orchestration | LangGraph (StateGraph) | 3-node pipeline: investigate → decide → act |
| Tools | Shopify GraphQL, Slack, Google Sheets, Linear | External integrations |
| Queue | Redis | Webhook deduplication, DLQ, stats counters |
| Observability | LangSmith | Full agent trace per webhook event |

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Shopify (webhook source)                     │
│  POST X-Shopify-Topic: orders/updated                          │
│  X-Shopify-Hmac-Sha256: <signature>                            │
└───────────────────────────┬────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                               │
│                                                                │
│  POST /api/webhooks/shopify                                    │
│    1. Verify HMAC signature                                    │
│    2. Deduplicate via Redis (1hr TTL)                          │
│    3. Return 200 immediately                                   │
│    4. Dispatch background task → LangGraph agent              │
│                                                                │
│  GET  /api/telemetry/stats   — aggregate counters from Redis   │
│  GET  /api/telemetry/dlq     — failed events queue            │
│  DELETE /api/telemetry/dlq/{index} — dismiss a DLQ item       │
└──────────┬─────────────────────────────────────────────────────┘
           │ background task
┌──────────▼─────────────────────────────────────────────────────┐
│               LangGraph Agent  (StateGraph)                     │
│                                                                 │
│  AgentState flows through 3 nodes:                             │
│                                                                 │
│  [investigate] ──────────────────────────────────────────────  │
│    Claude + tools (up to 6 rounds):                            │
│      get_order(order_gid)         → Shopify GraphQL            │
│      check_inventory(variant_gid) → Shopify GraphQL            │
│    Returns: order_data, inventory_issues                        │
│                                                                 │
│  [decide] ────────────────────────────────────────────────────  │
│    Claude (single call, no tools):                             │
│    Input: investigation summary                                 │
│    Output: decision ∈ {hold | release | escalate} + reason     │
│                                                                 │
│  [act] ────────────────────────────────────────────────────────  │
│    notify_slack(message)          → Slack API                  │
│    append_audit_log(...)          → Google Sheets              │
│    create_ticket(...) [escalate only] → Linear API             │
└──────────┬──────────────────┬──────────────────────────────────┘
           │ on error         │ on success
┌──────────▼──────┐  ┌────────▼────────────────────────────────┐
│  Redis DLQ      │  │  External Services                       │
│  opspilot:dlq   │  │                                          │
│  (Redis list)   │  │  Slack   — ops alert message            │
└─────────────────┘  │  Sheets  — append audit log row         │
                     │  Linear  — escalation ticket (if needed) │
                     └─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                React Dashboard  (Vite + Tailwind)               │
│                                                                  │
│  useTelemetry() — polls /api/telemetry/* every 5s               │
│  StatCards  — total events, hold, release, escalate, tokens     │
│  DecisionChart — hold/release/escalate breakdown                │
│  DLQTable   — inspect and dismiss failed events                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Webhook received
```
1. Shopify POSTs to /api/webhooks/shopify
2. HMAC-SHA256 signature verified against SHOPIFY_WEBHOOK_SECRET
3. Redis checked for dedup key opspilot:seen:{topic}:{order_id} (1hr TTL)
4. If duplicate → return {"status": "duplicate"} and stop
5. Dedup key written; 200 returned immediately to Shopify
6. Background task fires: _run_agent(event_type, order_id, payload)
```

### Agent run
```
investigate:
  Claude calls get_order → get full order + line items
  Claude calls check_inventory for each variant → verify stock levels
  Up to 6 tool-call rounds; final response parsed as JSON summary

decide:
  Claude receives investigation JSON
  Returns {decision, reason} — no tools, single call
  Defaults to "escalate" if JSON parse fails

act:
  Always: notify_slack + append_audit_log
  If escalate: create_ticket in Linear
  On any exception: push to Redis DLQ (opspilot:dlq)
```

---

## LangGraph State

`AgentState` (TypedDict) is the single shared context flowing through all nodes:

| Field | Set by | Description |
|---|---|---|
| `event_type`, `order_id`, `raw_payload` | webhook | Input from Shopify |
| `order_data`, `inventory_issues` | investigate | Structured findings |
| `decision`, `decision_reason` | decide | hold / release / escalate |
| `actions_taken`, `slack_ts`, `sheet_row`, `ticket_url` | act | Outputs |
| `tokens_used`, `latency_ms`, `error` | all nodes | Telemetry |

---

## Redis Keys

| Key | Type | Purpose |
|---|---|---|
| `opspilot:seen:{topic}:{order_id}` | string (TTL 1hr) | Webhook deduplication |
| `opspilot:dlq` | list | Failed agent runs (LPUSH on error) |
| `opspilot:stat:total_events` | string (counter) | Aggregate telemetry |
| `opspilot:stat:total_hold` | string (counter) | Aggregate telemetry |
| `opspilot:stat:total_release` | string (counter) | Aggregate telemetry |
| `opspilot:stat:total_escalate` | string (counter) | Aggregate telemetry |
| `opspilot:stat:total_tokens` | string (counter) | Aggregate telemetry |

---

## Directory Structure

```
opspilot/
├── backend/
│   ├── main.py                 — FastAPI app, CORS, router registration
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── webhook.py          — Shopify webhook receiver, HMAC verify, dedup
│   │   └── telemetry.py        — DLQ and stats endpoints for dashboard
│   ├── agent/
│   │   ├── graph.py            — LangGraph StateGraph definition
│   │   ├── nodes.py            — investigate, decide, act node implementations
│   │   └── state.py            — AgentState TypedDict
│   ├── tools/
│   │   ├── shopify.py          — get_order, check_inventory (GraphQL)
│   │   ├── slack_tool.py       — notify_slack
│   │   ├── sheets.py           — append_audit_log (Google Sheets)
│   │   └── linear_tool.py      — create_ticket
│   └── core/
│       ├── config.py           — pydantic-settings Settings
│       └── redis_client.py     — async Redis connection pool
└── frontend/
    ├── src/
    │   ├── App.tsx             — dashboard layout, stat cards, DLQ table
    │   ├── components/
    │   │   ├── StatCard.tsx
    │   │   ├── DecisionChart.tsx
    │   │   └── DLQTable.tsx
    │   └── hooks/
    │       └── useTelemetry.ts — polling hook for stats + DLQ
    ├── vite.config.ts
    └── tailwind.config.js
```
