# packages/backend-core/email_service.py

import logging
import resend
from .config import get_settings

logger = logging.getLogger(__name__)

async def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Sends an email using the Resend SDK.
    Bypasses SMTP port blocking issues by using HTTPS.
    """
    settings = get_settings()

    # Use SMTP_PASSWORD as the API key if it's the Resend key
    # In .env it is: re_PztWswJC_3wtU7cUbk4noRoznokcxZmMw
    api_key = settings.smtp_password
    
    if not api_key:
        logger.warning("Resend API Key (SMTP_PASSWORD) not configured, skipping email to %s", to)
        return False

    resend.api_key = api_key
    
    from_email = settings.smtp_from or "onboarding@resend.dev"

    try:
        # Resend SDK call is synchronous, but since we call it from BackgroundTasks, 
        # it runs in a threadpool and doesn't block the event loop.
        params = {
            "from": from_email,
            "to": to,
            "subject": subject,
            "html": html_body,
        }
        
        response = resend.Emails.send(params)
        logger.info("Email sent via Resend SDK to %s. ID: %s", to, getattr(response, "id", "unknown"))
        return True
    except Exception as exc:
        logger.error("Failed to send email via Resend SDK to %s: %s", to, exc)
        return False
