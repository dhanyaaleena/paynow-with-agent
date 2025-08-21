from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from models import Payment, IdempotencyKey, PaymentDecisionEnum, Customer
from agent import agent_decide
import json
import logging
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request as StarletteRequest
from db import AsyncSessionLocal
from rate_limiter import rate_limiter
from event_publisher import event_publisher

# Configure logging
logger = logging.getLogger("paynow")

# Create router
router = APIRouter()

# --- Models ---


class PaymentRequest(BaseModel):
    customerId: str
    amount: float
    currency: str
    payeeId: str
    idempotencyKey: str


class AgentTraceStep(BaseModel):
    step: str
    detail: str


class PaymentDecisionResponse(BaseModel):
    decision: str  # allow | review | block
    reasons: List[str]
    user_display: List[str]
    agentTrace: List[AgentTraceStep]
    requestId: str


# --- In-memory metrics (to be replaced with persistent/accurate version) ---
metrics = {
    "total_requests": 0,
    "decision_counts": {"allow": 0, "review": 0, "block": 0},
    "latencies": [],  # store last 100 latencies for p95
}

# --- API Key Security ---
API_KEY = "test-api-key"  # In production, use env var or secret manager


def get_api_key(x_api_key: str = Header(...)):
    """
    Dependency to check the X-API-Key header for authentication.
    Raises 401 if the key is invalid.
    """
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key")
    return x_api_key

# Database dependency


async def get_db():
    """
    Dependency that provides an async SQLAlchemy session for DB operations.
    """
    async with AsyncSessionLocal() as db:
        yield db

# --- Endpoints ---


@router.post("/payments/decide", response_model=PaymentDecisionResponse)
async def decide_payment(
    payment: PaymentRequest,
    request: Request,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Decide on a payment request by running agent logic, enforcing idempotency, concurrency safety, rate limiting, and logging.
    Returns a decision (allow, review, block) with reasons, user display messages, agent trace, and requestId.
    Publishes events and updates metrics.
    """
    start = time.time()
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    # Rate limiting check
    if not await rate_limiter.is_allowed(payment.customerId):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 requests per second per customer.")

    try:
        # Input validation
        if payment.amount <= 0:
            return PaymentDecisionResponse(
                decision="block",
                reasons=["invalid_amount"],
                user_display=["Amount must be positive."],
                agentTrace=[
                    AgentTraceStep(
                        step="plan",
                        detail="Invalid amount")],
                requestId=request_id)
        # Redact customerId for logs
        redacted_customer_id = payment.customerId[:2] + \
            "***" if len(payment.customerId) > 2 else "***"
        logger.info(
            f"[requestId={request_id}] Incoming payment request: customerId={redacted_customer_id}, amount={
                payment.amount}, payeeId={
                payment.payeeId}, idempotencyKey={
                payment.idempotencyKey}")
        # Idempotency check
        idem_stmt = select(Payment).where(
            Payment.customer_id == payment.customerId,
            Payment.idempotency_key == payment.idempotencyKey
        )
        result = await db.execute(idem_stmt)
        existing_payment = result.scalar_one_or_none()
        if existing_payment:
            reasons = existing_payment.reasons.split(
                ",") if existing_payment.reasons else []
            agent_trace = json.loads(
                existing_payment.agent_trace) if existing_payment.agent_trace else []
            decision = existing_payment.decision.value if hasattr(
                existing_payment.decision, 'value') else existing_payment.decision
            logger.info(
                f"[requestId={
                    existing_payment.request_id}] Idempotent request, returning previous decision: {decision}")
            metrics["total_requests"] += 1
            metrics["decision_counts"][decision] += 1
            latency = time.time() - start
            metrics["latencies"].append(latency)
            if len(metrics["latencies"]) > 100:
                metrics["latencies"] = metrics["latencies"][-100:]
            return PaymentDecisionResponse(
                decision=decision,
                reasons=reasons,
                user_display=[],
                agentTrace=[AgentTraceStep(**step) for step in agent_trace],
                requestId=existing_payment.request_id
            )
        # Run agent logic
        agent_result = await agent_decide(
            db,
            customer_id=payment.customerId,
            amount=payment.amount,
            currency=payment.currency,
            payee_id=payment.payeeId
        )
        decision = agent_result["decision"]
        reasons = agent_result["reasons"]
        user_display = agent_result.get("user_display", [])
        agent_trace = agent_result["agent_trace"]
        # Concurrency safety: reserve balance if allowed
        if decision == PaymentDecisionEnum.allow.value:
            cust_stmt = select(Customer).where(
                Customer.id == payment.customerId).with_for_update()
            cust_result = await db.execute(cust_stmt)
            customer = cust_result.scalar_one_or_none()
            if not customer or customer.balance < payment.amount:
                decision = PaymentDecisionEnum.block.value
                reasons = ["insufficient_balance"]
                user_display = ["Insufficient balance to complete payment."]
                agent_trace.append(
                    {"step": "tool:recommend", "detail": "block due to insufficient balance (concurrent)"})
            else:
                customer.balance -= payment.amount
        # Store payment and idempotency record
        payment_obj = Payment(
            customer_id=payment.customerId,
            payee_id=payment.payeeId,
            amount=payment.amount,
            currency=payment.currency,
            decision=decision,
            reasons=",".join(reasons),
            agent_trace=json.dumps(agent_trace),
            request_id=request_id,
            idempotency_key=payment.idempotencyKey
        )
        db.add(payment_obj)
        await db.flush()
        idem_obj = IdempotencyKey(
            customer_id=payment.customerId,
            idempotency_key=payment.idempotencyKey,
            payment_id=payment_obj.id
        )
        db.add(idem_obj)
        await db.commit()

        # Publish payment.decided event
        await event_publisher.publish_payment_decided(
            payment_id=payment_obj.id,
            customer_id=payment.customerId,
            payee_id=payment.payeeId,
            amount=payment.amount,
            currency=payment.currency,
            decision=decision,
            reasons=reasons,
            request_id=request_id,
            agent_trace=agent_trace,
            user_display=user_display
        )

        logger.info(
            f"[requestId={request_id}] Decision: {decision}, reasons={reasons}")
        metrics["total_requests"] += 1
        metrics["decision_counts"][decision] += 1
        latency = time.time() - start
        metrics["latencies"].append(latency)
        if len(metrics["latencies"]) > 100:
            metrics["latencies"] = metrics["latencies"][-100:]
        return PaymentDecisionResponse(
            decision=decision,
            reasons=reasons,
            user_display=user_display,
            agentTrace=[AgentTraceStep(**step) for step in agent_trace],
            requestId=request_id
        )
    except Exception as e:
        # Publish payment.failed event
        await event_publisher.publish_payment_failed(
            customer_id=payment.customerId,
            payee_id=payment.payeeId,
            amount=payment.amount,
            currency=payment.currency,
            error=str(e),
            request_id=request_id
        )
        logger.exception(
            f"[requestId={request_id}] Exception during payment decision")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics")
def get_metrics():
    """
    Returns in-memory metrics: total requests, decision counts, and p95 latency.
    """
    # Calculate p95 latency
    lats = sorted(metrics["latencies"])
    p95 = lats[int(0.95 * len(lats))] if lats else 0
    return {
        "total_requests": metrics["total_requests"],
        "decision_counts": metrics["decision_counts"],
        "p95_latency": p95
    }
