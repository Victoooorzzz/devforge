import os
import resend
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("SMTP_PASSWORD")

try:
    response = resend.Emails.send({
        "from": "DevForge <notificaciones@devforgeapp.pro>",
        "to": ["victormanuelangelvillalobos@gmail.com"],
        "subject": "Test Resend - DevForge",
        "html": "<p>This is a test.</p>"
    })
    print("SUCCESS:", response)
except Exception as e:
    print("ERROR:", e)
