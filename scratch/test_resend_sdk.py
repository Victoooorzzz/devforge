import resend
import os
from dotenv import load_dotenv
from pathlib import Path

# Load configuration
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")

# Configure API Key (Resend official way)
resend.api_key = os.getenv("SMTP_PASSWORD") # We use the same API key stored in SMTP_PASSWORD

def test_email():
    target_email = "victormanuelangelvillalobos@gmail.com"
    params = {
        "from": "DevForge <notificaciones@devforgeapp.pro>",
        "to": [target_email],
        "subject": "🚀 Prueba Oficial SDK - DevForge",
        "html": """
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #6366f1; border-radius: 12px; background-color: #f8fafc;">
            <h2 style="color: #4338ca; margin-top: 0;">¡Confirmación del SDK!</h2>
            <p>Esta prueba utiliza el <strong>SDK Oficial de Resend</strong> vía HTTPS.</p>
            <p>Si recibes esto, significa que:</p>
            <ul style="color: #334155;">
                <li>Tu dominio <strong>devforgeapp.pro</strong> está correctamente autenticado.</li>
                <li>Tu API Key es válida.</li>
                <li>El sistema está listo para producción.</li>
            </ul>
            <p style="font-size: 12px; color: #64748b; margin-top: 20px;">
                Enviado desde el entorno de desarrollo de DevForge.
            </p>
        </div>
        """,
    }

    print(f"Iniciando envio via SDK a: {target_email}...")
    try:
        email = resend.Emails.send(params)
        print(f"\nSUCCESS! ID del envio: {email.get('id')}")
        print("El correo ha sido enviado exitosamente siguiendo la documentacion oficial.")
    except Exception as e:
        print(f"\nERROR del SDK: {str(e)}")

if __name__ == "__main__":
    test_email()
