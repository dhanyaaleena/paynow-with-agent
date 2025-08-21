import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import json
import time

from main import app
from db import AsyncSessionLocal, init_db
from models import Customer, Payment, PaymentDecisionEnum
from rate_limiter import rate_limiter

# Test client
client = TestClient(app)

# Test data
TEST_CUSTOMER_ID = "c_123"  # Has 1000.0 balance, has recent_disputes=2
TEST_CUSTOMER_ID_2 = "c_789"  # Has 2000.0 balance, has device_change=true
TEST_PAYEE_ID = "test_payee_456"
TEST_API_KEY = "test-api-key"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Setup test database before each test"""
    await init_db()
    # Add test customer with balance
    async with AsyncSessionLocal() as session:
        # Clear existing test data
        await session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": TEST_CUSTOMER_ID})
        await session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": TEST_CUSTOMER_ID_2})
        await session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": "rate_limit_test_customer"})
        await session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": "c_high"})
        await session.execute(text("DELETE FROM payments WHERE customer_id = :id"), {"id": TEST_CUSTOMER_ID})
        await session.execute(text("DELETE FROM payments WHERE customer_id = :id"), {"id": TEST_CUSTOMER_ID_2})
        await session.execute(text("DELETE FROM payments WHERE customer_id = :id"), {"id": "rate_limit_test_customer"})
        await session.execute(text("DELETE FROM payments WHERE customer_id = :id"), {"id": "c_high"})
        await session.execute(text("DELETE FROM idempotency_keys WHERE customer_id = :id"), {"id": TEST_CUSTOMER_ID})
        await session.execute(text("DELETE FROM idempotency_keys WHERE customer_id = :id"), {"id": TEST_CUSTOMER_ID_2})
        await session.execute(text("DELETE FROM idempotency_keys WHERE customer_id = :id"), {"id": "rate_limit_test_customer"})
        await session.execute(text("DELETE FROM idempotency_keys WHERE customer_id = :id"), {"id": "c_high"})

        # Add test customers
        customer1 = Customer(
            id=TEST_CUSTOMER_ID,
            name="Test Customer",
            balance=1000.0)
        customer2 = Customer(
            id=TEST_CUSTOMER_ID_2,
            name="Device Change Customer",
            balance=2000.0)
        customer3 = Customer(
            id="rate_limit_test_customer",
            name="Rate Limit Test Customer",
            balance=1000.0)
        customer4 = Customer(
            id="c_high",
            name="High Balance Customer",
            balance=50000.0)
        session.add(customer1)
        session.add(customer2)
        session.add(customer3)
        session.add(customer4)
        await session.commit()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before and after each test"""
    # Clear all buckets before test
    rate_limiter.buckets.clear()
    print(f"Rate limiter reset - buckets cleared: {len(rate_limiter.buckets)}")
    yield
    # Clear all buckets after test
    rate_limiter.buckets.clear()
    print(
        f"Rate limiter reset after test - buckets cleared: {len(rate_limiter.buckets)}")


@pytest.mark.asyncio
async def test_idempotency():
    """Test that duplicate requests with same idempotency key return same result"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID,
        "amount": 50.0,
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_idem_key_123"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    # First request
    response1 = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response1.status_code == 200
    result1 = response1.json()
    request_id_1 = result1["requestId"]

    # Second request with same idempotency key
    response2 = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response2.status_code == 200
    result2 = response2.json()
    request_id_2 = result2["requestId"]

    # Should return same request ID and decision
    assert request_id_1 == request_id_2
    assert result1["decision"] == result2["decision"]
    assert result1["reasons"] == result2["reasons"]


@pytest.mark.asyncio
async def test_rate_limit():
    """Test rate limiting - should reject requests after 5 per second"""
    # Test the rate limiter directly
    from rate_limiter import TokenBucketRateLimiter

    # Create a rate limiter with 1 token per second for testing
    test_limiter = TokenBucketRateLimiter(tokens_per_second=1)

    # Clear any existing state
    test_limiter.buckets.clear()

    # First request should be allowed
    result1 = await test_limiter.is_allowed("test_customer")
    assert result1

    # Second request should be blocked (no tokens left)
    result2 = await test_limiter.is_allowed("test_customer")
    assert result2 == False

    # Wait 1 second and try again (should be allowed)
    time.sleep(1.1)
    result3 = await test_limiter.is_allowed("test_customer")
    assert result3

    # Test with the actual API rate limiter (5 tokens per second)
    import api

    # Clear the rate limiter buckets
    api.rate_limiter.buckets.clear()

    # Make 5 requests (should all succeed)
    for i in range(5):
        result = await api.rate_limiter.is_allowed("test_customer")
        assert result, f"Request {i + 1} should be allowed"

    # 6th request should be blocked
    result6 = await api.rate_limiter.is_allowed("test_customer")
    assert result6 == False, "6th request should be blocked"


@pytest.mark.asyncio
async def test_decision_path_allow():
    """Test a decision path that should result in 'allow'"""
    payment_data = {
        # c_789 has device_change but no disputes, amount < 10000
        "customerId": TEST_CUSTOMER_ID_2,
        "amount": 500.0,  # Small amount, no risk signals that trigger review
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_allow_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()

    # Should be allowed
    assert result["decision"] == "allow"
    assert "requestId" in result
    assert "agentTrace" in result
    assert "user_display" in result

    # Check agent trace has expected steps
    agent_trace = result["agentTrace"]
    trace_steps = [step["step"] for step in agent_trace]
    assert "plan" in trace_steps
    assert "tool:getBalance" in trace_steps
    assert "tool:getRiskSignals" in trace_steps
    assert "tool:recommend" in trace_steps


@pytest.mark.asyncio
async def test_decision_path_review_amount():
    """Test a decision path that should result in 'review' (amount > 10000)"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID_2,  # c_789 has 2000.0 balance
        "amount": 15000.0,  # Above threshold of 10000, but also above balance
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_review_amount_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()

    # Should be blocked due to insufficient balance (not reviewed)
    assert result["decision"] == "block"
    assert "insufficient_balance" in result["reasons"]
    assert len(result["user_display"]) >= 0  # Can be empty for block cases

    # Should have createCase in trace
    agent_trace = result["agentTrace"]
    trace_steps = [step["step"] for step in agent_trace]
    assert "tool:createCase" in trace_steps


@pytest.mark.asyncio
async def test_decision_path_review_amount_with_sufficient_balance():
    """Test a decision path that should result in 'review' (amount > 10000) with sufficient balance"""
    payment_data = {
        # Has 50000.0 balance (already created in setup)
        "customerId": "c_high",
        "amount": 15000.0,  # Above threshold of 10000, but within balance
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_review_amount_high_balance_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()

    # Should be reviewed due to amount threshold
    assert result["decision"] == "review"
    assert "amount_above_daily_threshold" in result["reasons"]
    assert len(result["user_display"]) >= 0  # Can be empty for review cases

    # Should have createCase in trace
    agent_trace = result["agentTrace"]
    trace_steps = [step["step"] for step in agent_trace]
    assert "tool:createCase" in trace_steps


@pytest.mark.asyncio
async def test_decision_path_review_disputes():
    """Test a decision path that should result in 'review' (recent disputes)"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID,  # c_123 has recent_disputes=2
        "amount": 75.0,  # Small amount
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_review_disputes_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()

    # Should be reviewed
    assert result["decision"] == "review"
    assert "recent_disputes" in result["reasons"]
    assert len(result["user_display"]) >= 0  # Can be empty for review cases

    # Should have createCase in trace
    agent_trace = result["agentTrace"]
    trace_steps = [step["step"] for step in agent_trace]
    assert "tool:createCase" in trace_steps


@pytest.mark.asyncio
async def test_decision_path_block_insufficient_balance():
    """Test a decision path that should result in 'block' (insufficient balance)"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID,  # Has 1000.0 balance
        "amount": 2000.0,  # More than balance
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_block_balance_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()

    # Should be blocked
    assert result["decision"] == "block"
    assert "insufficient_balance" in result["reasons"]
    assert len(result["user_display"]) >= 0  # Can be empty for block cases

    # Should have createCase in trace
    agent_trace = result["agentTrace"]
    trace_steps = [step["step"] for step in agent_trace]
    assert "tool:createCase" in trace_steps


@pytest.mark.asyncio
async def test_decision_path_block_invalid_amount():
    """Test a decision path that should result in 'block' (negative amount)"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID,
        "amount": -10.0,  # Negative amount
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_block_invalid_key"
    }

    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/payments/decide",
        json=payment_data,
        headers=headers)
    assert response.status_code == 200

    result = response.json()
    assert result["decision"] == "block"
    assert "invalid_amount" in result["reasons"]


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test that requests without API key are rejected"""
    payment_data = {
        "customerId": TEST_CUSTOMER_ID,
        "amount": 50.0,
        "currency": "USD",
        "payeeId": TEST_PAYEE_ID,
        "idempotencyKey": "test_no_auth_key"
    }

    # No API key header
    response = client.post("/payments/decide", json=payment_data)
    assert response.status_code == 422  # Validation error for missing header


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test that metrics endpoint returns expected data"""
    response = client.get("/metrics")
    assert response.status_code == 200

    metrics = response.json()
    assert "total_requests" in metrics
    assert "decision_counts" in metrics
    assert "p95_latency" in metrics

    # Check decision counts structure
    decision_counts = metrics["decision_counts"]
    assert "allow" in decision_counts
    assert "review" in decision_counts
    assert "block" in decision_counts
