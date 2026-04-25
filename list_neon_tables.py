import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def check_tables():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        
        if not tables:
            print("No se encontraron tablas en el esquema 'public'.")
        else:
            print("Tablas encontradas en Neon:")
            for table in tables:
                print(f"- {table[0]}")

if __name__ == "__main__":
    asyncio.run(check_tables())
