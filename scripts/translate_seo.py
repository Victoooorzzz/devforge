import os
import glob

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

replacements = {
    # FileCleaner
    "El problema:": "The Problem:",
    "La solución:": "The Solution:",
    "Para quién es:": "Who is it for:",
    "¿Cansado de perder horas limpiando archivos CSV llenos de nulos y duplicados?": "Tired of wasting hours cleaning CSV files full of nulls and duplicates?",
    "Esta herramienta procesa y corrige anomalías de forma ultrarrápida usando FastAPI.": "This tool processes and fixes anomalies blazingly fast using FastAPI.",
    "Ideal para data analysts y equipos de operaciones.": "Ideal for data analysts and operations teams.",

    # InvoiceFollow
    "¿Cansado de perseguir clientes que no pagan sus facturas a tiempo?": "Tired of chasing clients who don't pay their invoices on time?",
    "Esta herramienta automatiza el envío de recordatorios de cobro inteligentes.": "This tool automates the sending of smart payment reminders.",
    "Ideal para freelancers, agencias y consultores que cobran por proyecto.": "Ideal for freelancers, agencies, and project-based consultants.",

    # PriceTrackr
    "¿Cansado de revisar manualmente los precios de tus competidores todos los días?": "Tired of manually checking your competitors' prices every day?",
    "Esta herramienta monitorea URLs en segundo plano y te alerta cuando hay cambios de precio.": "This tool monitors URLs in the background and alerts you to price changes.",
    "Ideal para dueños de e-commerce, dropshippers y estrategas de mercado.": "Ideal for e-commerce owners, dropshippers, and market strategists.",

    # WebhookMonitor
    "¿Cansado de que fallen tus integraciones con Stripe o Shopify y no saber por qué?": "Tired of failing Stripe or Shopify integrations without knowing why?",
    "Esta herramienta intercepta, inspecciona y permite hacer replay de webhooks.": "This tool intercepts, inspects, and allows you to replay webhooks.",
    "Ideal para backend developers, integradores y equipos de DevOps.": "Ideal for backend developers, integrators, and DevOps teams.",

    # FeedbackLens
    "¿Cansado de leer miles de reseñas de usuarios sin poder encontrar el problema principal?": "Tired of reading thousands of user reviews without finding the core issue?",
    "Esta herramienta extrae quejas comunes y sentimiento utilizando inteligencia artificial.": "This tool extracts common complaints and sentiment using artificial intelligence.",
    "Ideal para Product Managers, equipos de soporte y SaaS founders.": "Ideal for Product Managers, support teams, and SaaS founders.",

    # Legal General
    "Términos de Servicio": "Terms of Service",
    "Política de Privacidad": "Privacy Policy",
    "Política de Reembolsos": "Refund Policy",
    "Última actualización: Mayo 2024": "Last updated: May 2024",

    # Terms
    'DevForge es una plataforma que agrupa diversas herramientas. Al utilizar DevForge, usted acepta estos términos. Proveemos esta herramienta "tal cual", sin garantías de ningún tipo.': 'DevForge is a platform that groups various tools. By using DevForge, you agree to these terms. We provide this tool "as is", without any warranties.',
    "1. Uso del Servicio": "1. Use of Service",
    "No debe usar nuestro servicio para fines ilegales o no autorizados.": "You must not use our service for any illegal or unauthorized purpose.",

    # Privacy
    "En DevForge respetamos su privacidad. Esta política explica cómo recopilamos y protegemos sus datos en todo nuestro ecosistema.": "At DevForge, we respect your privacy. This policy explains how we collect and protect your data across our ecosystem.",
    "1. Datos Recopilados": "1. Collected Data",
    "Recopilamos su correo electrónico para la gestión de su cuenta unificada.": "We collect your email address for the management of your unified account.",
    "2. Pagos": "2. Payments",
    "Procesados por Lemon Squeezy, no almacenamos su tarjeta.": "Processed by Lemon Squeezy, we do not store your credit card information.",

    # Refunds
    "Para asegurar la satisfacción, todas nuestras aplicaciones en DevForge ofrecen un período de prueba gratuito de 7 días.": "To ensure satisfaction, all our applications at DevForge offer a 7-day free trial.",
    "Una vez transcurridos los 7 días de prueba, se procesará automáticamente el cargo de suscripción. Debido a esta política generosa, <strong>una vez procesado el pago, todas las ventas son definitivas y no se emiten reembolsos.</strong>": "Once the 7-day trial has elapsed, the subscription charge will be processed automatically. Due to this generous policy, <strong>once the payment is processed, all sales are final and no refunds are issued.</strong>"
}

# Find all tsx files in the apps directory recursively
tsx_files = glob.glob(os.path.join(base_dir, "**", "*.tsx"), recursive=True)

for file_path in tsx_files:
    # Skip node_modules or dist if they exist
    if "node_modules" in file_path or ".next" in file_path:
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    for es, en in replacements.items():
        content = content.replace(es, en)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated translations in {file_path}")

print("Translation complete.")
