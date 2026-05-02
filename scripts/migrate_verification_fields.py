import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def update_schema():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL no encontrada en .env")
        return

    # Render uses postgres://, SQLAlchemy requires postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"Conectando a la base de datos para actualizar el esquema...")
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        try:
            # Añadir columnas a la tabla 'users'
            # Usamos subconsultas o capturamos el error si ya existen
            print("Verificando/Añadiendo columna 'is_email_verified'...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE;"))
            
            print("Verificando/Añadiendo columna 'verification_code'...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code VARCHAR;"))
            
            await conn.commit()
            print("¡ÉXITO! El esquema de la base de datos se ha actualizado correctamente.")
        except Exception as e:
            print(f"Error al actualizar el esquema: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_schema())
