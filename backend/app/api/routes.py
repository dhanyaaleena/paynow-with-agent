from fastapi import APIRouter, HTTPException, Header, status, Depends
from typing import Optional, List
import uuid
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.models import Payment, IdempotencyKey, PaymentDecisionEnum, Customer, PaymentRequest, AgentTraceStep, PaymentDecisionResponse, RecentDecisionsResponse
from app.core.agent import agent_decide
import json
import logging
from app.core.db import AsyncSessionLocal
from app.services.rate_limiter import rate_limiter
from app.services.event_publisher import event_publisher
from datetime import timezone

# Configure logging
logger = logging.getLogger("paynow")

router = APIRouter()

# In-memory metrics (to be replaced with persistent)
metrics = {
    "total_requests": 0,
    "decision_counts": {"allow": 0, "review": 0, "block": 0},
    "latencies": [],  # store last 100 latencies for p95
}

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

async def get_db():
    """
    Dependency that provides an async SQLAlchemy session for DB operations.
    """
    async with AsyncSessionLocal() as db:
        yield db

#Helpers

def _redact_customer_id(customer_id: str) -> str:
    if not customer_id:
        return "***"
    if len(customer_id) > 5:
        return customer_id[:2] + "***" + customer_id[-3:]
    elif len(customer_id) > 1:
        return customer_id[0] + "***" + customer_id[-1]
    else:
        return "***"


def _update_metrics(decision: str, start_time: float) -> None:
    metrics["total_requests"] += 1
    metrics["decision_counts"].setdefault(decision, 0)
    metrics["decision_counts"][decision] += 1
    latency = time.time() - start_time
    metrics["latencies"].append(latency)
    if len(metrics["latencies"]) > 100:
        metrics["latencies"] = metrics["latencies"][-100:]


def _invalid_amount_response(request_id: str) -> PaymentDecisionResponse:
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return PaymentDecisionResponse(
        id=-1,
        decision="block",
        reasons=["invalid_amount"],
        user_display=["Amount must be positive."],
        agentTrace=[AgentTraceStep(step="plan", detail="Invalid amount")],
        requestId=request_id,
        customerId="invalid",
        maskedCustomerId="***",
        payeeId="invalid",
        amount=0.0,
        latency=0.0,
        createdAt=now_utc,
    )


async def _find_idempotent_payment(db: AsyncSession, customer_id: str, idempotency_key: str) -> Optional[Payment]:
    stmt = select(Payment).where(
        Payment.customer_id == customer_id,
        Payment.idempotency_key == idempotency_key,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _user_display_from_reasons(reasons: List[str]) -> List[str]:
    mapping = {
        "insufficient_balance": "Insufficient balance to complete payment.",
        "recent_disputes": "Your account has recent disputes. Manual review required.",
        "amount_above_daily_threshold": "Amount exceeds daily threshold. Manual review required.",
        "invalid_amount": "Amount must be positive."
    }
    return [mapping[r] for r in reasons if r in mapping]


def _response_from_existing(existing_payment: Payment, start_time: float) -> PaymentDecisionResponse:
    reasons = existing_payment.reasons.split(",") if existing_payment.reasons else []
    agent_trace = json.loads(existing_payment.agent_trace) if existing_payment.agent_trace else []
    decision = existing_payment.decision.value if hasattr(existing_payment.decision, 'value') else existing_payment.decision
    logger.info(f"Idempotent request, returning previous decision: {decision}")
    latency = time.time() - start_time
    _update_metrics(decision, start_time)
    return PaymentDecisionResponse(
        id=existing_payment.id,
        decision=decision,
        reasons=reasons,
        user_display=_user_display_from_reasons(reasons),
        agentTrace=[AgentTraceStep(**step) for step in agent_trace],
        requestId=existing_payment.request_id,
        customerId=existing_payment.customer_id,
        maskedCustomerId=_redact_customer_id(existing_payment.customer_id),
        payeeId=existing_payment.payee_id,
        amount=existing_payment.amount,
        latency=latency,
        createdAt=existing_payment.created_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') if existing_payment.created_at else "",
    )


async def _run_agent(db: AsyncSession, payment: PaymentRequest) -> dict:
    return await agent_decide(
        db,
        customer_id=payment.customerId,
        amount=payment.amount,
        currency=payment.currency,
        payee_id=payment.payeeId,
    )


async def _persist_atomic_and_publish(
    db: AsyncSession,
    payment: PaymentRequest,
    decision: str,
    reasons: List[str],
    agent_trace: List[dict],
    user_display: List[str],
    request_id: str,
):
    # Work on copies so we can safely mutate
    final_decision = decision
    final_reasons = list(reasons)
    final_user_display = list(user_display)
    final_agent_trace = list(agent_trace)

    # Use existing transaction for balance update + payment + idempotency
    if final_decision == PaymentDecisionEnum.allow.value:
        cust_stmt = select(Customer).where(Customer.id == payment.customerId).with_for_update()
        cust_result = await db.execute(cust_stmt)
        customer = cust_result.scalar_one_or_none()
        if not customer or customer.balance < payment.amount:
            final_decision = PaymentDecisionEnum.block.value
            if "insufficient_balance" not in final_reasons:
                final_reasons.append("insufficient_balance")
            if "Insufficient balance to complete payment." not in final_user_display:
                final_user_display.append("Insufficient balance to complete payment.")
            final_agent_trace.append({
                "step": "tool:recommend",
                "detail": "block due to insufficient balance (concurrent)"
            })
        else:
            customer.balance -= payment.amount

    payment_obj = Payment(
        customer_id=payment.customerId,
        payee_id=payment.payeeId,
        amount=payment.amount,
        currency=payment.currency,
        decision=final_decision,
        reasons=",".join(final_reasons),
        agent_trace=json.dumps(final_agent_trace),
        request_id=request_id,
        idempotency_key=payment.idempotencyKey,
    )
    db.add(payment_obj)
    await db.flush()

    idem_obj = IdempotencyKey(
        customer_id=payment.customerId,
        idempotency_key=payment.idempotencyKey,
        payment_id=payment_obj.id,
    )
    db.add(idem_obj)
    await db.commit()

    # After commit, publish event
    await event_publisher.publish_payment_decided(
        payment_id=payment_obj.id,
        customer_id=payment.customerId,
        payee_id=payment.payeeId,
        amount=payment.amount,
        currency=payment.currency,
        decision=final_decision,
        reasons=final_reasons,
        request_id=request_id,
        agent_trace=final_agent_trace,
        user_display=final_user_display,
    )

    return final_decision, final_reasons, final_user_display, final_agent_trace, payment_obj


def _build_response(decision: str, reasons: List[str], agent_trace: List[dict], user_display: List[str], request_id: str, start_time: float, payment: PaymentRequest, payment_obj: Payment) -> PaymentDecisionResponse:
    logger.info(f"Decision: {decision}, reasons={reasons}")
    latency = time.time() - start_time
    _update_metrics(decision, start_time)
    return PaymentDecisionResponse(
        id=payment_obj.id,
        decision=decision,
        reasons=reasons,
        user_display=user_display,
        agentTrace=[AgentTraceStep(**step) for step in agent_trace],
        requestId=request_id,
        customerId=payment.customerId,
        maskedCustomerId=_redact_customer_id(payment.customerId),
        payeeId=payment.payeeId,
        amount=payment.amount,
        latency=latency,
        createdAt=payment_obj.created_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') if payment_obj.created_at else "",
    )

@router.post("/api/decide", response_model=PaymentDecisionResponse)
async def decide_payment(
    payment: PaymentRequest,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
):
    """
    Decide on a payment request by running agent logic, enforcing idempotency, concurrency safety, rate limiting, and logging.
    Returns a decision (allow, review, block) with reasons, user display messages, agent trace, and requestId.
    Publishes events and updates metrics.
    """
    start = time.time()
    request_id = x_request_id or f"req_{uuid.uuid4().hex[:8]}"

    # Rate limiting check
    if not await rate_limiter.is_allowed(payment.customerId):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 requests per second per customer.")

    try:
        # input validation
        if payment.amount <= 0:
            # For invalid amount, return latency as well
            latency = time.time() - start
            resp = _invalid_amount_response(request_id)
            resp.latency = latency
            return resp

        #Redact customerId for logs
        redacted_customer_id = _redact_customer_id(payment.customerId)
        logger.info(
            f"Incoming payment request: customerId={redacted_customer_id}, amount={payment.amount}, payeeId={payment.payeeId}, idempotencyKey={payment.idempotencyKey}")

        #Idempotency check
        existing_payment = await _find_idempotent_payment(db, payment.customerId, payment.idempotencyKey)
        if existing_payment:
            return _response_from_existing(existing_payment, start)

        #Run agent
        agent_result = await _run_agent(db, payment)
        decision = agent_result["decision"]
        reasons = agent_result["reasons"]
        user_display = agent_result.get("user_display", [])
        agent_trace = agent_result["agent_trace"]

        #Atomic persist (balance + payment + idempotency) and publish event
        decision, reasons, user_display, agent_trace, payment_obj = await _persist_atomic_and_publish(
            db, payment, decision, reasons, agent_trace, user_display, request_id
        )

        #build response and update metrics
        return _build_response(decision, reasons, agent_trace, user_display, request_id, start, payment, payment_obj)
    except Exception as e:
        #Publish payment.failed event
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


@router.get("/api/decide", response_model=RecentDecisionsResponse)
async def get_recent_decisions(
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the last 20 payment decisions for display in the frontend table.
    Requires X-API-Key.
    """
    try:
        # Query last 20 payments ordered by creation time descending
        stmt = select(Payment).order_by(Payment.created_at.desc()).limit(20)
        result = await db.execute(stmt)
        payments = result.scalars().all()
        decisions = []
        for payment in payments:
            # Mask customer ID for security
            masked_customer_id = _redact_customer_id(payment.customer_id)
            
            logger.info(f"Payment object createdAt: {payment.amount}, {payment.created_at}")
            decisions.append({
                "id": payment.id,
                "decision": payment.decision.value if hasattr(payment.decision, 'value') else payment.decision,
                "amount": payment.amount,
                "currency": payment.currency,
                "customerId": masked_customer_id,
                "payeeId": payment.payee_id,
                "createdAt": payment.created_at.isoformat()+"Z" if payment.created_at else "",
                "requestId": payment.request_id,
                "reasons": payment.reasons.split(",") if payment.reasons else [],
                "agentTrace": json.loads(payment.agent_trace) if payment.agent_trace else []
            })
        
        return {"decisions": decisions}
    except Exception as e:
        logger.exception("Error fetching recent decisions")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/metrics")
def get_metrics(api_key: str = Depends(get_api_key)):
    """
    Returns in-memory metrics: total requests, decision counts, and p95 latency.
    Requires X-API-Key.
    """
    # Calculate p95 latency
    lats = sorted(metrics["latencies"])
    p95 = lats[int(0.95 * len(lats))] if lats else 0
    return {
        "total_requests": metrics["total_requests"],
        "decision_counts": metrics["decision_counts"],
        "p95_latency": p95
    }
