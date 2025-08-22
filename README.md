# PayNow + Agent Assist

A minimal FastAPI service that decides whether to allow, review, or block a payment. It uses:
- A token-bucket rate limiter per customer to protect the API
- Idempotency keys to safely retry the same request
- An agent (deterministic) that gathers balance and risk signals, makes a decision, and logs an agentTrace
- Atomic DB updates (balance, payment, idempotency key) in one commit
- Event publishing after commit (payment.decided or payment.failed)
- Metrics endpoint for quick visibility

In short: the API receives a payment request, rate limits it, checks if we’ve already seen the same request (idempotency), calls the “agent” to compute a decision, atomically persists the result (and deducts balance on allow), publishes an event, and returns a structured response with reasons and an agent trace.


## How to Run Locally

## Run (Docker)

You can start the API using Docker or Docker Compose:

- Using Docker Compose (recommended):

```bash
docker compose -f docker/docker-compose.yml up --build
```

- Or Using uvicorn
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open `http://localhost:8000/docs` for api details.

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

## Post - Payments Decide
```sh
curl -X POST http://localhost:8000/payments/decide \
  -H 'X-API-Key: test-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"customerId": "c_123", "amount": 125.50, "currency": "USD", "payeeId": "p_789", "idempotencyKey": "uuid-1"}'
```

### Get - Metrics
```sh
curl http://localhost:8000/metrics
```
### Running Evaluation Locally
Evaluation script is executed in the CI pipleine :
Checkout in Github Actions: https://github.com/dhanyaaleena/paynow-with-agent/actions
sample run: https://github.com/dhanyaaleena/paynow-with-agent/actions/runs/17149409999

```sh
# Alternatively run basic evaluation in local
python -m tests.integration.run_eval.py

```

## Sample Evaluation Test Cases
These examples show the kinds of scenarios the agent handles. More cases are available in `tests/integration/eval_test_cases.json`.

- Small, clean payment (should allow):
```json
{
  "customerId": "c_100",
  "amount": 100.0,
  "currency": "USD",
  "payeeId": "p_789",
  "idempotencyKey": "sample-allow-1"
}
```

- Customer with recent disputes (should review):
```json
{
  "customerId": "c_123",
  "amount": 75.0,
  "currency": "USD",
  "payeeId": "p_789",
  "idempotencyKey": "sample-review-1"
}
```

- Large amount with insufficient balance (should block):
```json
{
  "customerId": "c_123",
  "amount": 15000.0,
  "currency": "USD",
  "payeeId": "p_789",
  "idempotencyKey": "sample-block-1"
}
```

More examples and the expected outcomes can be found in `tests/integration/eval_test_cases.json`.
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

## Defense-in-Depth
- Redacted PII in logs: customerId masked in request logs; requestId added to correlate
- Separated system reasons vs user display text: API returns both `reasons` and `user_display`
- Simple input validation: negative/zero amounts are blocked (invalid_amount); API key required via `X-API-Key`

## What Was Optimized
- Latency: minimized DB round-trips; concurrent tool calls (asyncio.gather) for balance + risk
- Simplicity: deterministic agent, SQLite, in-memory metrics, straightforward models
- Security: API key check, PII redaction, clear validation, idempotency

## Trade-offs
- In-memory rate limiter for simplicity; suitable for single-instance dev. Trade-off: not distributed-safe (suggest Redis option for prod)
- SQLite for local development; easy to run, limited concurrency at scale
- Deterministic agent (no external LLM) for reliable tests; less flexible than ML-driven policies
- In-process metrics (basic p95);

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
- Tools: get_balance, get_risk_signals, create_case
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
The project includes a CI pipeline in `.github/workflows/ci.yml` that runs on every push to `main` and pull request:

1. **Unit Tests** (`test_api.py`): Tests API functionality, idempotency, rate limiting, and edge cases
2. **Agent Evaluation** (`ci_eval.py`): Validates agent decision-making accuracy

### Evaluation Thresholds
The CI pipeline enforces minimum accuracy thresholds:
- **Decision Accuracy**: ≥95% (agent makes correct allow/review/block decisions)
- **Reasons Accuracy**: ≥85% (agent identifies correct risk factors)
- **Overall Accuracy**: ≥85% (combined decision and reasons accuracy)

### Test Coverage
- **Unit Tests**: 7 test cases covering API functionality
- **Agent Evaluation**: 7 test cases covering business logic scenarios
- **CI Pipeline**: Automated testing on every code change

### Screenshots:
- CI pipeline run:
Link : https://github.com/dhanyaaleena/paynow-with-agent/actions/runs/17149289805
<img width="2830" height="848" alt="image" src="https://github.com/user-attachments/assets/6344aa5d-918c-410f-88bb-3772d377a646" />

- Unit Test Cases executed:
<img width="2856" height="1516" alt="image" src="https://github.com/user-attachments/assets/ce516eee-5a97-40e1-a44d-50743c901975" />

- Eval Test Cases executed:
<img width="2802" height="1464" alt="image" src="https://github.com/user-attachments/assets/34334a64-b2a0-4416-82ca-bf724d71e5b0" />

- Docker container in execution:
<img width="1202" height="568" alt="image" src="https://github.com/user-attachments/assets/34b31f23-7db3-41d8-875d-4a4d55e8a5c0" />

- Swagger docs in local:
<img width="2778" height="1564" alt="image" src="https://github.com/user-attachments/assets/73771012-029c-487e-8a7a-6b90d3721445" />

- Postman API testing:

<img width="1430" height="1520" alt="image" src="https://github.com/user-attachments/assets/8e530d71-27bf-4036-bba6-1c7cd2bfc4e7" />

<img width="1464" height="1492" alt="image" src="https://github.com/user-attachments/assets/db8dad33-4f6d-4449-8751-d58314f4c2a3" />



## TODOs
- [ ] Frontend demo 
- [ ] Use cases for event publisher(use kafka)
- [ ] Use LLM integration insted of simulation
- [ ] Redis-backed rate limiter option
- [ ] event retries, idempotency cleanup
