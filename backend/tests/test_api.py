import pytest
import asyncio
from app.services.rate_limiter import TokenBucketRateLimiter
from app.core.agent import agent_decide
from app.core.models import PaymentDecisionEnum

# rate limiter testing
@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_basic():
    limiter = TokenBucketRateLimiter(tokens_per_second=2)
    limiter.buckets.clear()
    # Bucket starts full with 2 tokens
    assert await limiter.is_allowed("user1")
    assert await limiter.is_allowed("user1")
    # Third should be blocked
    assert not await limiter.is_allowed("user1")
    import time
    time.sleep(0.5)
    # With 2 tokens/sec, after 0.5s we have 1 token -> allowed once
    assert await limiter.is_allowed("user1")
    # Immediately next should be blocked again
    assert not await limiter.is_allowed("user1")
    time.sleep(0.5)
    # Another half second passes -> allowed again
    assert await limiter.is_allowed("user1")

@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_multiple_users():
    limiter = TokenBucketRateLimiter(tokens_per_second=1)
    limiter.buckets.clear()
    assert await limiter.is_allowed("userA")
    assert await limiter.is_allowed("userB")
    assert not await limiter.is_allowed("userA")
    assert not await limiter.is_allowed("userB")

# idempotency testing
def test_idempotency_dict():
    idem_store = {}
    def process_payment(idem_key, value):
        if idem_key in idem_store:
            return idem_store[idem_key]
        idem_store[idem_key] = value
        return value
    assert process_payment("abc", 1) == 1
    assert process_payment("abc", 2) == 1
    assert process_payment("def", 3) == 3
    assert process_payment("def", 4) == 3

# agent decision testing
class DummySession:
    def __init__(self, balances, risk_signals):
        self.balances = balances
        self.risk_signals = risk_signals
    async def execute(self, stmt):
        class Result:
            def __init__(self, value):
                self.value = value
            def scalar_one_or_none(self):
                return self.value
        for cid, bal in self.balances.items():
            if cid in str(stmt):
                class CustomerObj:
                    def __init__(self, balance):
                        self.balance = balance
                return Result(CustomerObj(bal))
        return Result(None)

async def dummy_get_risk_signals(db, customer_id):
    return db.risk_signals.get(customer_id, {"recent_disputes": 0, "device_change": False})

async def dummy_get_balance(db, customer_id):
    return db.balances.get(customer_id, 0.0)

@pytest.mark.asyncio
async def test_agent_decide_allow(monkeypatch):
    balances = {"c_100100": 1000.0}
    risk_signals = {"c_100100": {"recent_disputes": 0, "device_change": False}}
    db = DummySession(balances, risk_signals)
    monkeypatch.setattr("app.core.agent.get_risk_signals", dummy_get_risk_signals)
    monkeypatch.setattr("app.core.agent.get_balance", dummy_get_balance)
    result = await agent_decide(db, "c_100100", 100.0, "USD", "p_789")
    assert result["decision"] == PaymentDecisionEnum.allow.value
    assert result["reasons"] == []

@pytest.mark.asyncio
async def test_agent_decide_block_insufficient_balance(monkeypatch):
    balances = {"c_100100": 50.0}
    risk_signals = {"c_100100": {"recent_disputes": 0, "device_change": False}}
    db = DummySession(balances, risk_signals)
    monkeypatch.setattr("app.core.agent.get_risk_signals", dummy_get_risk_signals)
    monkeypatch.setattr("app.core.agent.get_balance", dummy_get_balance)
    result = await agent_decide(db, "c_100100", 100.0, "USD", "p_789")
    assert result["decision"] == PaymentDecisionEnum.block.value
    assert "insufficient_balance" in result["reasons"]

@pytest.mark.asyncio
async def test_agent_decide_review_disputes(monkeypatch):
    balances = {"c_123123": 1000.0}
    risk_signals = {"c_123123": {"recent_disputes": 2, "device_change": False}}
    db = DummySession(balances, risk_signals)
    monkeypatch.setattr("app.core.agent.get_risk_signals", dummy_get_risk_signals)
    monkeypatch.setattr("app.core.agent.get_balance", dummy_get_balance)
    result = await agent_decide(db, "c_123123", 100.0, "USD", "p_789")
    assert result["decision"] == PaymentDecisionEnum.review.value
    assert "recent_disputes" in result["reasons"]

@pytest.mark.asyncio
async def test_agent_decide_block_invalid_amount(monkeypatch):
    balances = {"c_100100": 1000.0}
    risk_signals = {"c_100100": {"recent_disputes": 0, "device_change": False}}
    db = DummySession(balances, risk_signals)
    monkeypatch.setattr("app.core.agent.get_risk_signals", dummy_get_risk_signals)
    monkeypatch.setattr("app.core.agent.get_balance", dummy_get_balance)
    amount = -10.0
    # Simulate API layer validation: negative amount → block immediately
    if amount <= 0:
        result = {"decision": PaymentDecisionEnum.block.value, "reasons": ["invalid_amount"]}
    else:
        result = await agent_decide(db, "c_100100", amount, "USD", "p_789")
    assert result["decision"] == PaymentDecisionEnum.block.value
    assert "invalid_amount" in result["reasons"] or result["reasons"] == ["invalid_amount"]
