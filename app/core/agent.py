from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.models import Customer, PaymentDecisionEnum, AgentTraceStep
from typing import List, Dict, Any
import uuid
import logging
import asyncio

logger = logging.getLogger(__name__) 


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
    
    # Extract the base customer ID if it's a test case generated ID
    base_customer_id = customer_id.split("_test_case_")[0]

    recent_disputes = 2 if base_customer_id.endswith('3') or customer_id.endswith('3') else 0
    device_change = base_customer_id.endswith('9') or customer_id.endswith('9')
    return {"recent_disputes": recent_disputes, "device_change": device_change}


async def create_case(
        db: AsyncSession,
        customer_id: str,
        payee_id: str,
        amount: float,
        decision: str,
        reasons: List[str]) -> str:
    # simulate creating a case for manual review or blocked payments
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
    # using asyncio.gather to get balance and risk signals concurrently
    balance_task = retry_tool(get_balance, db, customer_id, max_retries=2, fallback=0.0)
    risk_task = retry_tool(get_risk_signals, db, customer_id, max_retries=2, fallback={"recent_disputes": 0, "device_change": False})
    balance, risk = await asyncio.gather(balance_task, risk_task)
    agent_trace.append(
        AgentTraceStep(
            step="tool:getBalance",
            detail=f"balance={balance:.2f}"
        ))
    agent_trace.append(
        AgentTraceStep(
            step="tool:getRiskSignals",
            detail=f"recent_disputes={risk['recent_disputes']}, device_change={risk['device_change']}"
        ))
    reasons = []
    user_display = []
    
    #check balance first
    if balance < amount:
        reasons.append("insufficient_balance")
        user_display.append("Insufficient balance to complete payment.")
    
    #check risk signals (regardless of balance)
    if risk["recent_disputes"] > 0:
        reasons.append("recent_disputes")
        user_display.append("Your account has recent disputes. Manual review required.")
    
    if amount > 10000:
        reasons.append("amount_above_daily_threshold")
        user_display.append("Amount exceeds daily threshold. Manual review required.")
    
    if "insufficient_balance" in reasons:
        decision = PaymentDecisionEnum.block
        agent_trace.append(
            AgentTraceStep(
                step="tool:recommend",
                detail="block due to insufficient balance"))
    elif "recent_disputes" in reasons or "amount_above_daily_threshold" in reasons:
        decision = PaymentDecisionEnum.review
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

    #create case for review/block decisions
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
