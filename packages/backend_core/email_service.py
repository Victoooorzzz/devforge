# packages/backend-core/email_service.py

import logging
import resend
from .config import get_settings

logger = logging.getLogger(__name__)

def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Sends an email using the Resend SDK.
    Bypasses SMTP port blocking issues by using HTTPS.
    NOTE: Using synchronous def so FastAPI BackgroundTasks runs this in a threadpool.
    """
    settings = get_settings()
    api_key = settings.smtp_password
    
    print(f"[EMAIL] Iniciando proceso para {to}")
    
    if not api_key:
        print(f"[EMAIL] ERROR: Resend API Key (SMTP_PASSWORD) no configurada.")
        return False

    resend.api_key = api_key
    from_email = settings.smtp_from or "onboarding@resend.dev"

    try:
        print(f"[EMAIL] Llamando al SDK de Resend (From: {from_email})...")
        params = {
            "from": from_email,
            "to": to,
            "subject": subject,
            "html": html_body,
        }
        
        response = resend.Emails.send(params)
        email_id = getattr(response, "id", "unknown")
        print(f"[EMAIL] SUCCESS: Correo enviado a {to}. ID: {email_id}")
        return True
    except Exception as exc:
        print(f"[EMAIL] EXCEPTION al enviar a {to}: {str(exc)}")
        return False
