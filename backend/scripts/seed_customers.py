import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from app.core.db import AsyncSessionLocal
from app.core.models import Customer
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if customers already exist to avoid duplicate seeding
        result = await session.execute(select(Customer).limit(1))
        if result.scalar_one_or_none():
            print("Customers already seeded, skipping...")
            return
            
        customers = [
            # Test customers for evaluation test cases
            Customer(id="c_123123", name="Test Customer", balance=1000.0),  
            Customer(id="c_789789", name="Device Change Customer", balance=2000.0), 
            Customer(id="c_100100", name="Clean Customer", balance=15000.0),  
        ]
        session.add_all(customers)
        await session.commit()
    print("Seeded customers for evaluation tests!")
    print("Test customers:")
    print("  - c_123123: 1000.0 balance (has recent_disputes=2)")
    print("  - c_789789: 2000.0 balance (has device_change=true)")
    print("  - c_100100: 15000.0 balance (clean, no risk signals)")
    print("")
    print("These customers are used in eval_test_cases.json")

if __name__ == "__main__":
    from app.core.db import init_db
    async def main():
        await init_db()
        await seed()
    asyncio.run(main())
