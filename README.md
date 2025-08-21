# PayNow + Agent Assist

## How to Run Locally
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Architecture Diagram
```
+--------+      +-------------------+      +-----------------+
| Client | ---> | FastAPI Backend   | ---> | SQLite DB       |
+--------+      |  /payments/decide |      | (SQLAlchemy ORM)|
                |  /metrics         |      +-----------------+
                +-------------------+
                        |
                        v
                +-------------------+
                | Agent Orchestrator|
                |  (tools, retries) |
                +-------------------+
                        |
                        v
                +-------------------+
                | Rate Limiter      |
                | (in-memory, per   |
                |  customerId)      |
                +-------------------+
                        |
                        v
                +-------------------+
                | Event Publisher   |
                | (stdout events)   |
                +-------------------+
```

## Database Schema

### customers
| Column    | Type   | Description                |
|-----------|--------|---------------------------|
| id        | str    | Primary key (e.g., c_123) |
| name      | str    | Customer name             |
| balance   | float  | Current balance           |

### payees #TODO: mention that this is not used
| Column    | Type   | Description                |
|-----------|--------|---------------------------|
| id        | str    | Primary key (e.g., p_789) |
| name      | str    | Payee name                |

### payments
| Column          | Type   | Description                                  |
|-----------------|--------|----------------------------------------------|
| id              | int    | Primary key (auto-increment)                 |
| customer_id     | str    | Foreign key to customers                     |
| payee_id        | str    | Foreign key to payees                        |
| amount          | float  | Payment amount                               |
| currency        | str    | Currency code (e.g., USD)                    |
| decision        | enum   | allow, review, block                         |
| reasons         | str    | Comma-separated system reasons               |
| agent_trace     | str    | JSON string of agent steps                   |
| request_id      | str    | Unique request identifier                    |
| created_at      | datetime | Timestamp                                  |
| idempotency_key | str    | For idempotency (see previous answer)        |

### idempotency_keys
| Column          | Type   | Description                                  |
|-----------------|--------|----------------------------------------------|
| id              | int    | Primary key (auto-increment)                 |
| customer_id     | str    | Customer for this idempotency key            |
| idempotency_key | str    | The idempotency key                          |
| payment_id      | int    | Foreign key to payments                      |
| created_at      | datetime | Timestamp                                  |

## In-Memory Rate Limiter
- **Type:** Token Bucket (5 requests/sec per customerId)
- **Purpose:** Prevents abuse and enforces fair usage per customer.
- **Implementation:** See `rate_limiter.py`. Used as a FastAPI dependency in the `/payments/decide` endpoint.
- **Trade-offs:** Simple and fast, but not horizontally scalable (would need Redis or similar for distributed systems).
- **Behavior:** If a customer exceeds 5 requests/sec, they receive a 429 error.

## Event Publisher (Simulated Kafka)
- **Purpose:** Publishes `payment.decided` and `payment.failed` events to stdout to simulate event-driven architecture (e.g., Kafka).
- **Implementation:** See `event_publisher.py`. Events are published after each payment decision or failure.
- **Event Types:**
  - `payment.decided`: Emitted on successful payment decision
  - `payment.failed`: Emitted on error/exception
- **Event Format Example:**
```json
{
  "event_type": "payment.decided",
  "event_id": "evt_00000001",
  "timestamp": "2024-06-20T12:34:56.789Z",
  "data": {
    "payment_id": 123,
    "customer_id": "c_123",
    "payee_id": "p_789",
    "amount": 125.5,
    "currency": "USD",
    "decision": "allow",
    "reasons": [],
    "request_id": "req_abc123",
    "agent_trace": [ ... ],
    "user_display": [ ... ]
  },
  "metadata": {
    "source": "paynow-api",
    "version": "1.0"
  }
}
```

## What Was Optimized
- **Latency:** Async endpoints, agent tool retries, minimal DB roundtrips(TODO)
- **Simplicity:** In-memory rate limiter, event publisher for observability, clear agent trace, single-file run(TODO)
- **Security:** API key, PII redaction in logs, input validation

## Trade-offs
- **In-memory rate limiter**: Simpler, but not horizontally scalable
- **Event publisher to stdout**: Good for demo and local dev, but not a real message bus
- **SQLite**: Easy local setup, not for high concurrency
- **No external LLM**: Deterministic agent for demo, easy to test

## Sample cURL
```sh
curl -X POST http://localhost:8000/payments/decide \
  -H 'X-API-Key: test-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"customerId": "c_123", "amount": 125.50, "currency": "USD", "payeeId": "p_789", "idempotencyKey": "uuid-1"}'
```

### Get Metrics
```sh
curl http://localhost:8000/metrics
```

## Performance
- p95 latency tracked in /metrics
- Async DB and agent tools
- Pre-validation of input

## Security
- API key required (X-API-Key)
- PII redacted in logs (customerId)
- Input validation on payment fields

## Observability
- Logs include requestId for traceability
- /metrics endpoint for requests, decisions, p95 latency
- Agent trace returned in API response

## Agent
- Tools: getBalance, getRiskSignals, recommend
- Retries/guardrails: max 2 retries per tool, fallback values
- Plan and tool calls shown in agentTrace
- No external LLM required

1. REQUEST RECEIVED
   ↓
2. IDEMPOTENCY CHECK
   ├── READ payments (check if exists)
   └── READ idempotency_keys (check if exists)
   ↓
3. IF NEW REQUEST:
   ├── AGENT LOGIC
   │   └── READ customers (get balance)
   │
   ├── DECISION MADE
   │   └── UPDATE customers (if allow: deduct balance)
   │
   ├── STORE PAYMENT
   │   └── INSERT payments
   │
   └── STORE IDEMPOTENCY
       └── INSERT idempotency_keys
   ↓
4. RESPONSE SENT

## TODOs
- [ ] Redis-backed rate limiter for distributed scale
- [ ] WebSocket/event publish for payment.decided
- [ ] More robust input validation and error handling
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Frontend demo (optional)



autopep8 --in-place --aggressive --aggressive agent.py