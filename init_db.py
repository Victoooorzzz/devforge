import asyncio
import os
from dotenv import load_dotenv
import sys

# Add the root and packages directory to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "packages"))

load_dotenv()

async def main():
    print("Iniciando creación de tablas en Neon...")
    # Importar el creador de tablas
    from backend_core.database import create_db_and_tables
    
    # IMPORTANTE: Importar los modelos de cada app para que SQLModel los registre
    from apps.feedbacklens.backend.main import FeedbackEntry
    from apps.filecleaner.backend.main import ProcessedFile
    from apps.invoicefollow.backend.main import Invoice
    from apps.pricetrackr.backend.main import TrackedUrl
    from apps.webhookmonitor.backend.main import WebhookEndpoint, WebhookRequest
    try:
        await create_db_and_tables()
        print("EXITO: Las tablas se crearon correctamente en Neon.")
    except Exception as e:
        print(f"ERROR al crear las tablas: {e}")

if __name__ == "__main__":
    asyncio.run(main())
