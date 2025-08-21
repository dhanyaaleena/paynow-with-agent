import asyncio
from db import AsyncSessionLocal, init_db
from models import Customer

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        customers = [
            # Test customers for evaluation test cases
            Customer(id="c_123", name="Test Customer", balance=1000.0),  # For eval tests (has disputes, balance for testing)
            Customer(id="c_789", name="Device Change Customer", balance=2000.0),  # For eval tests (has device_change)
        ]
        session.add_all(customers)
        await session.commit()
    print("Seeded customers for evaluation tests!")
    print("Test customers:")
    print("  - c_123: 1000.0 balance (has recent_disputes=2)")
    print("  - c_789: 2000.0 balance (has device_change=true)")
    print("")
    print("These customers are used in eval_test_cases.json")

if __name__ == "__main__":
    asyncio.run(seed())
