import os

apps = ["filecleaner", "feedbacklens", "invoicefollow", "pricetrackr", "webhookmonitor"]
pages = ["terms", "privacy", "refunds"]

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

templates = {
    "terms": """import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Términos de Servicio</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Última actualización: Mayo 2024</p>
          <p>Al utilizar {APP_NAME}, usted acepta estos términos. Proveemos esta herramienta "tal cual", sin garantías de ningún tipo. Usted es responsable del uso que le dé a la plataforma.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">1. Uso del Servicio</h2>
          <p>No debe usar nuestro servicio para fines ilegales o no autorizados. El abuso de la plataforma resultará en la terminación de su cuenta.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">2. Pagos y Suscripciones</h2>
          <p>Ofrecemos un trial gratuito de 7 días. Luego se realizará un cobro de $9.99/mes. Puede cancelar en cualquier momento antes de que se procese el cargo.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">3. Cambios en los Términos</h2>
          <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Le notificaremos de cambios significativos.</p>
        </div>
      </div>
    </div>
  );
}
""",
    "privacy": """import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Política de Privacidad</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Última actualización: Mayo 2024</p>
          <p>En {APP_NAME}, valoramos su privacidad. Esta política explica cómo recopilamos, usamos y protegemos sus datos.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">1. Datos Recopilados</h2>
          <p>Recopilamos su dirección de correo electrónico para la gestión de cuentas y comunicación, y datos de uso de la aplicación para mejorar nuestros servicios.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">2. Procesamiento de Pagos</h2>
          <p>Sus pagos son procesados de forma segura por Lemon Squeezy. Nosotros no almacenamos información de su tarjeta de crédito.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">3. Contacto</h2>
          <p>Para solicitudes de eliminación de datos o dudas sobre privacidad, contáctenos en support@devforgeapp.pro.</p>
        </div>
      </div>
    </div>
  );
}
""",
    "refunds": """import Link from "next/link";

export default function RefundsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Política de Reembolsos</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Última actualización: Mayo 2024</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Período de Prueba y Cargos</h2>
          <p>Para asegurar la satisfacción de nuestros usuarios, {APP_NAME} ofrece un <strong>período de prueba gratuito de 7 días</strong>. Durante este tiempo, usted tiene acceso completo a las funciones de infraestructura de grado empresarial de nuestra plataforma, permitiéndole evaluar si cumple con sus necesidades.</p>
          <p>Una vez transcurridos los 7 días de prueba, se procesará automáticamente el cargo mensual recurrente de <strong>$9.99 dólares</strong>.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Política de Reembolsos Definitivos</h2>
          <p>Debido a que ofrecemos este período de prueba extendido para que usted evalúe libremente el producto, <strong>una vez procesado el cargo de la suscripción, todas las ventas son definitivas y no se emiten reembolsos bajo ninguna circunstancia.</strong></p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Cancelaciones</h2>
          <p>Usted es libre de cancelar su suscripción en cualquier momento antes de que se cumpla el período de prueba para evitar cobros, o en cualquier momento posterior para evitar futuros cobros mensuales. Puede realizar la cancelación directamente desde su panel de control o a través de los correos de Lemon Squeezy.</p>
        </div>
      </div>
    </div>
  );
}
"""
}

for app in apps:
    app_name = app.capitalize()
    if app == "pricetrackr": app_name = "PriceTrackr"
    elif app == "invoicefollow": app_name = "InvoiceFollow"
    elif app == "webhookmonitor": app_name = "WebhookMonitor"
    elif app == "feedbacklens": app_name = "FeedbackLens"
    elif app == "filecleaner": app_name = "FileCleaner"

    for page in pages:
        folder_path = os.path.join(base_dir, app, "frontend", "src", "app", page)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, "page.tsx")
        
        content = templates[page].replace("{APP_NAME}", app_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created {file_path}")

print("All legal pages created successfully.")
