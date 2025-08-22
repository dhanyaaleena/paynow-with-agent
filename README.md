# PayNow + Agent Assist

## How to Run Locally
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Docker
```sh
# Build and run with Docker
docker build -t paynow-api .
docker run -p 8000:8000 paynow-api

# Or use docker-compose
docker-compose up --build
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

### payees 
| Column    | Type   | Description                |
|-----------|--------|---------------------------|
| id        | str    | Primary key (e.g., p_789) |
| name      | str    | Payee name                |

> Note: Payees table exists for completeness but is not used in the current demo flow.

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
- **Latency:** Async endpoints, agent tool retries, minimal DB roundtrips
- **Simplicity:** In-memory rate limiter, event publisher for observability, clear agent trace, single-file run
- **Security:** API key, PII redaction in logs, input validation

## Trade-offs
- **In-memory rate limiter**: Simpler, but not horizontally scalable
- **Event publisher to stdout**: Good for demo and local dev, but not a real message bus
- **SQLite**: Easy local setup, not for high concurrency
- **No external LLM**: Deterministic agent for demo, easy to test

## Post Payments Decide
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

```text
1. REQUEST RECEIVED
  ↓
1a. RATE LIMITER (Token Bucket per customerId)
  └── CHECK allowance (5 req/sec)
  ↓
2. IDEMPOTENCY CHECK
  ├── READ payments (check if exists)
  └── READ idempotency_keys (check if exists)
  ↓
3. IF NEW REQUEST:
  ├── AGENT LOGIC
  │   ├── READ customers (get balance)
  │   ├── FETCH risk signals
  │   ├── MAKE decision (allow / review / block)
  │   └── IF decision in {review, block}: CREATE CASE
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
4. COMMIT TRANSACTION
  ↓
5. EVENT PUBLISHER
  ├── payment.decided (on success)
  └── payment.failed (on error)
  ↓
6. RESPONSE SENT
```

## Project Structure


```
paynow-with-agent/
├── app/                    # Main application code
│   ├── api/               # API-related modules
│   │   ├── routes.py      # FastAPI routes and endpoints
│   │   └── __init__.py
│   ├── core/              # Core business logic
│   │   ├── agent.py       # Agent decision logic
│   │   ├── models.py      # Database models
│   │   ├── db.py          # Database configuration
│   │   └── __init__.py
│   ├── services/          # Business services
│   │   ├── rate_limiter.py
│   │   ├── event_publisher.py
│   │   └── __init__.py
│   ├── utils/             # Utilities
│   │   ├── logging_config.py
│   │   └── __init__.py
│   └── __init__.py
├── tests/                 # Test files
│   ├── test_api.py        # Unit tests
│   ├── integration/       # Integration tests
│   │   ├── run_eval.py    # Agent evaluation script
│   │   ├── ci_eval.py     # CI evaluation wrapper
│   │   ├── eval_test_cases.json
│   │   └── __init__.py
│   └── __init__.py
├── scripts/               # Utility scripts
│   ├── seed_customers.py
│   ├── clear_db.py
│   └── __init__.py
├── docker/                # Docker-related files
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/               # GitHub Actions CI/CD
├── main.py                # Application entry point
├── requirements.txt
└── README.md
```
## CI/CD Pipeline

### GitHub Actions Workflow
The project includes a comprehensive CI/CD pipeline in `.github/workflows/ci.yml` that runs on every push to `main` and pull request:

1. **Unit Tests** (`test_api.py`): Tests API functionality, idempotency, rate limiting, and edge cases
2. **Agent Evaluation** (`ci_eval.py`): Validates agent decision-making accuracy

### Evaluation Thresholds
The CI pipeline enforces minimum accuracy thresholds:
- **Decision Accuracy**: ≥95% (agent makes correct allow/review/block decisions)
- **Reasons Accuracy**: ≥85% (agent identifies correct risk factors)
- **Overall Accuracy**: ≥85% (combined decision and reasons accuracy)

### Running Evaluation Locally
```sh
# Run basic evaluation
python run_eval.py

# Run CI evaluation with threshold checking
python ci_eval.py
```

### Test Coverage
- **Unit Tests**: 7 test cases covering API functionality
- **Agent Evaluation**: 7 test cases covering business logic scenarios
- **CI Pipeline**: Automated testing on every code change


## TODOs
- [ ] Frontend demo 
- [ ] Implement Redis for better caching
- [ ] Use cases for event publisher(use kafka)
- [ ] Use LLM integration insted of simulation