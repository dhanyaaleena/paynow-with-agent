from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Customer, PaymentDecisionEnum, AgentTraceStep
from typing import List, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)  # make request id available in all logs


async def retry_tool(tool_func, *args, max_retries=2, fallback=None, **kwargs):
    for attempt in range(max_retries):
        try:
            return await tool_func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                return fallback


async def get_balance(db: AsyncSession, customer_id: str) -> float:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    return customer.balance if customer else 0.0


async def get_risk_signals(
        db: AsyncSession, customer_id: str) -> Dict[str, Any]:
    # Simulate risk signals (in real life, fetch from risk service)
    # For demo: recent_disputes = 2 if customer_id ends with '3',
    # device_change = True if ends with '9'
    recent_disputes = 2 if customer_id.endswith('3') else 0
    device_change = customer_id.endswith('9')
    return {"recent_disputes": recent_disputes, "device_change": device_change}


async def create_case(
        db: AsyncSession,
        customer_id: str,
        payee_id: str,
        amount: float,
        decision: str,
        reasons: List[str]) -> str:
    # Simulate creating a case for manual review or blocked payments
    # In a real system, this would create a case in a case management system
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    # For demo purposes, we'll just log it
    logger.info(
        f"Created case {case_id} for customer {customer_id}, decision: {decision}, reasons: {reasons}")
    return case_id


async def agent_decide(
        db: AsyncSession,
        customer_id: str,
        amount: float,
        currency: str,
        payee_id: str) -> dict:
    agent_trace: List[AgentTraceStep] = []
    agent_trace.append(
        AgentTraceStep(
            step="plan",
            detail="Check balance, risk, and limits"))
    # use async gather to get balance and risk signals
    balance = await retry_tool(get_balance, db, customer_id, max_retries=2, fallback=0.0)
    agent_trace.append(
        AgentTraceStep(
            step="tool:getBalance",
            detail=f"balance={
                balance:.2f}"
        ))
    risk = await retry_tool(get_risk_signals, db, customer_id, max_retries=2, fallback={"recent_disputes": 0, "device_change": False})
    agent_trace.append(
        AgentTraceStep(
            step="tool:getRiskSignals",
            detail=f"recent_disputes={
                risk['recent_disputes']}, device_change={
                risk['device_change']}"
        ))
    reasons = []
    user_display = []
    if balance < amount:
        decision = PaymentDecisionEnum.block
        reasons.append("insufficient_balance")
        user_display.append("Insufficient balance to complete payment.")
        agent_trace.append(
            AgentTraceStep(
                step="tool:recommend",
                detail="block due to insufficient balance"))
    elif risk["recent_disputes"] > 0 or amount > 10000:
        decision = PaymentDecisionEnum.review
        if risk["recent_disputes"] > 0:
            reasons.append("recent_disputes")
            user_display.append(
                "Your account has recent disputes. Manual review required.")
        if amount > 10000:
            reasons.append("amount_above_daily_threshold")
            user_display.append(
                "Amount exceeds daily threshold. Manual review required.")
        agent_trace.append(
            AgentTraceStep(
                step="tool:recommend",
                detail="route to manual review"))
    else:
        decision = PaymentDecisionEnum.allow
        agent_trace.append(
            AgentTraceStep(
                step="tool:recommend",
                detail="allow payment"))

    # Create case for review/block decisions
    if decision in [PaymentDecisionEnum.review, PaymentDecisionEnum.block]:
        case_id = await retry_tool(create_case, db, customer_id, payee_id, amount, decision.value, reasons, max_retries=2, fallback="case_failed")
        agent_trace.append(
            AgentTraceStep(
                step="tool:createCase",
                detail=f"case_id={case_id}"))

    return {
        "decision": decision.value,
        "reasons": reasons,
        "user_display": user_display,
        "agent_trace": [s.model_dump() for s in agent_trace]
    }
