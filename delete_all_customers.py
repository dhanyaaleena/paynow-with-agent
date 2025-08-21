import asyncio
from db import AsyncSessionLocal, init_db
from sqlalchemy import text

async def delete_all():
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(text('DELETE FROM customers'))
        await session.commit()
    print("All customers deleted!")

if __name__ == "__main__":
    asyncio.run(delete_all())
