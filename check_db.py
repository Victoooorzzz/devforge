import asyncio
from sqlmodel import select
from packages.backend_core.database import SessionLocal
from packages.backend_core.auth import User

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(u.email, u.hashed_password)

asyncio.run(main())
