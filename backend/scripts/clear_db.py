import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from app.core.db import AsyncSessionLocal, init_db
from sqlalchemy import text

async def delete_all():
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(text('DELETE FROM payments'))
        await session.execute(text('DELETE FROM idempotency_keys'))
        await session.execute(text('DELETE FROM payees'))
        await session.execute(text('DELETE FROM customers'))
        await session.commit()
    print("All data deleted from payments, idempotency_keys, payees, and customers")

if __name__ == "__main__":
    asyncio.run(delete_all())
