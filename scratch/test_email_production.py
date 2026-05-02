import asyncio
import os
import sys
from pathlib import Path

# Add the packages directory to sys.path to allow importing backend_core
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Mock environment variables for local test (loading from .env)
from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from packages.backend_core.email_service import send_email

async def main():
    target_email = "victormanuelangelvillalobos@gmail.com"
    subject = "🚀 Prueba de Producción - DevForge"
    html_content = """
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px; max-width: 600px;">
        <h1 style="color: #6366f1;">¡Funciona!</h1>
        <p>Este es un correo de prueba enviado desde tu nueva infraestructura de <strong>DevForge</strong>.</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;" />
        <p style="font-size: 14px; color: #666;">
            <strong>Remitente:</strong> notificaciones@devforgeapp.pro<br>
            <strong>Estado:</strong> Dominio Verificado en Resend
        </p>
    </div>
    """
    
    print(f"Enviando correo de prueba a: {target_email}...")
    print(f"Usando SMTP_HOST: {os.getenv('SMTP_HOST')}")
    print(f"Usando SMTP_PORT: {os.getenv('SMTP_PORT')}")
    print(f"Usando SMTP_FROM: {os.getenv('SMTP_FROM')}")
    
    try:
        success = await send_email(to=target_email, subject=subject, html_body=html_content)
        if success:
            print("\nSUCCESS! El correo ha sido enviado y aceptado por Resend.")
            print("Revisa tu bandeja de entrada.")
        else:
            print("\nFAILED! send_email retorno False. Revisa los logs arriba.")
    except Exception as e:
        import traceback
        print(f"\nEXCEPTION al enviar el correo: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
