# PayNow + Agent Assist — Fullstack

A production-minded slice of a banking/payments flow where a user initiates a payment and an agentic AI assists with checks and recommendations.  
**Backend:** FastAPI, SQLite, agentic decision logic, observability, security, and eventing.  
**Frontend:** Next.js, Zustand, Tailwind CSS — a modern dashboard for submitting and viewing payment decisions.

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Docker (optional, for easy backend setup)

### 1. Start the Backend

**With Docker Compose (recommended):**
```sh
cd backend
docker compose -f docker/docker-compose.yml up --build
```

**Or manually:**
```sh
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
- API docs: http://localhost:8000/docs

### 2. Start the Frontend

```sh
cd frontend
npm install
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_API_KEY=test-api-key
npm run dev
```
- App: http://localhost:3000

---

## Architecture

```
+--------+      +-------------------+      +-----------------+
| Client | ---> | FastAPI Backend   | ---> | SQLite DB       |
+--------+      |  /api/decide      |      | (SQLAlchemy ORM)|
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

---

## API Endpoints

- **POST `/api/decide`**: Submit payment decision
- **GET `/api/decide`**: Get last 20 decisions
- **GET `/metrics`**: Observability metrics

**Sample cURL:**
```sh
curl -X POST http://localhost:8000/api/decide \
  -H 'X-API-Key: test-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"customerId": "c_123", "amount": 125.50, "currency": "INR", "payeeId": "p_789", "idempotencyKey": "uuid-1"}'
```

---

## Frontend Features

- **Submit Form:** Amount, payee, customerId → calls `/api/decide`
- **Results Table:** Last 20 decisions, masked customerId, latency, timestamp
- **Details Drawer:** Collapsible reasons + Agent Trace
- **Accessibility:** Labeled inputs, keyboard navigation, ARIA, focus management
- **Security:** Customer IDs masked as `c_***123`, no PII exposure
- **Testing:** Jest + RTL test for drawer expansion and accessibility
- **Performance:** Memoized row rendering, efficient state management

---

## Backend Features

- **Agentic Decision Logic:** Deterministic agent plans, calls tools, retries, and traces steps
- **Idempotency:** Ensures safe retries with idempotencyKey
- **Concurrency Safety:** Atomic DB transactions for balance and payments
- **Rate Limiting:** 5 requests/sec per customerId (token bucket)
- **Security:** API key required, PII redaction in logs
- **Observability:** Logs with requestId, `/metrics` endpoint, event publishing
- **Event Publisher:** Simulates Kafka by publishing events to stdout

---

## Database Schema

- **customers:** id, name, balance
- **payees:** id, name
- **payments:** id, customer_id, payee_id, amount, currency, decision, reasons, agent_trace, request_id, created_at, idempotency_key
- **idempotency_keys:** id, customer_id, idempotency_key, payment_id, created_at

---

## Testing

**Backend:**
- `pytest` for unit and integration tests
- Evaluation script: `python -m tests.integration.run_eval.py`

**Frontend:**
- `npm test` for Jest + React Testing Library
- Coverage for drawer, accessibility, and integration

---

## Security & Observability

- **PII Redaction:** Masked customerId in logs and UI
- **API Key:** Required for all endpoints
- **Metrics:** `/metrics` endpoint for requests, decisions, p95 latency
- **Agent Trace:** Returned in API response and visible in UI

---

## Project Structure

```
paynow-with-agent/
├── backend/
│   ├── app/...
│   ├── tests/...
│   ├── scripts/...
│   ├── docker/...
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/components/...
│   ├── src/store/...
│   ├── src/services/...
│   ├── src/types/...
│   ├── README.md
│   └── package.json
└── README.md  # (this file)
```

---

## Trade-offs & Future Enhancements

- **In-memory rate limiter:** Simple, not distributed (suggest Redis for prod)
- **SQLite:** Easy for dev, limited concurrency
- **Deterministic agent:** Reliable for tests, less flexible than ML
- **Frontend:** Zustand for state, Tailwind for rapid UI, Headless UI for accessibility

**Potential Improvements:**
- Real-time updates (WebSocket)
- Advanced filtering, export, dark mode
- Redis-backed rate limiter
- LLM integration for agent
- Production-grade eventing (Kafka)

---
