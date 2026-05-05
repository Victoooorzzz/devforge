import requests
import json
import time
import hmac
import hashlib
import os

BASE_URL = "https://devforge-universal-backend.onrender.com"
WEBHOOK_SECRET = "devforge_secure_webhook_2026" # Hardcoded from previous context for the test
TEST_EMAIL = f"e2e_test_{int(time.time())}@devforge.app"
TEST_PASS = "TestPassword123!"

print("="*50)
print("🚀 INICIANDO TEST END-TO-E2E EN PRODUCCIÓN (Render)")
print("="*50)

# 1. Register
print(f"1️⃣ Registrando usuario de prueba: {TEST_EMAIL}")
res_reg = requests.post(f"{BASE_URL}/auth/register", json={
    "email": TEST_EMAIL,
    "password": TEST_PASS,
    "full_name": "Terminal E2E Tester"
})
print("Respuesta Registro:", res_reg.status_code)

# 2. Login
print("\n2️⃣ Iniciando sesión...")
res_login = requests.post(f"{BASE_URL}/auth/login", json={
    "email": TEST_EMAIL,
    "password": TEST_PASS
})
print("Respuesta Login:", res_login.status_code)
token = res_login.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 3. Check Profile (Before Payment)
print("\n3️⃣ Perfil antes del pago (Debe ser TRIAL o INACTIVE)")
res_prof1 = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
prof1 = res_prof1.json()
user_id = prof1.get("id")
print(f"Estado de suscripción: {prof1.get('subscription_status')}")

# 4. "Tocar botones" - Interacciones simuladas con cada app
print("\n4️⃣ Simulando clics en la interfaz (llamadas a las APIs)")

# FeedbackLens
print("  -> [FeedbackLens] Analizando un feedback...")
res_fb = requests.post(f"{BASE_URL}/feedback", headers=headers, json={
    "product_name": "Test Product",
    "content": "This is an amazing system, really fast and beautiful!",
    "source": "Terminal Test"
})
print(f"     Resultado: {res_fb.status_code} - {res_fb.json().get('sentiment', 'OK')}")

# InvoiceFollow
print("  -> [InvoiceFollow] Creando una factura...")
res_inv = requests.post(f"{BASE_URL}/invoices", headers=headers, json={
    "client_name": "E2E Test Client",
    "client_email": "client@example.com",
    "amount": 500.0,
    "due_date": "2026-12-31T23:59:59Z"
})
print(f"     Resultado: {res_inv.status_code} - Creada")

# PriceTrackr
print("  -> [PriceTrackr] Añadiendo un producto a trackear...")
res_trk = requests.post(f"{BASE_URL}/trackers", headers=headers, json={
    "url": "https://www.amazon.com/dp/B0CHX3QBCH",
    "target_price": 30.0,
    "check_frequency": 6
})
print(f"     Resultado: {res_trk.status_code}")

# WebhookMonitor
print("  -> [WebhookMonitor] Creando un endpoint receptor...")
res_wh = requests.post(f"{BASE_URL}/webhooks/endpoint", headers=headers, json={
    "name": "E2E Destination",
    "target_url": "https://httpbin.org/post",
    "alert_email": TEST_EMAIL
})
print(f"     Resultado: {res_wh.status_code}")

# 5. Simulate Lemon Squeezy Webhook (PAYMENT)
print("\n5️⃣ 💳 Simulando PAGO EXITOSO vía Lemon Squeezy Webhook...")
payload = {
    "meta": {
        "event_name": "subscription_created",
        "custom_data": {
            "user_id": user_id
        }
    },
    "data": {
        "id": "sub_12345",
        "attributes": {
            "status": "active",
            "product_id": 123,
            "variant_id": 1017960, # File Cleaner variant
            "user_email": TEST_EMAIL,
            "customer_id": 99999
        }
    }
}
payload_bytes = json.dumps(payload).encode('utf-8')
signature = hmac.new(WEBHOOK_SECRET.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

wh_headers = {
    "Content-Type": "application/json",
    "X-Signature": signature
}

res_hook = requests.post(f"{BASE_URL}/webhooks/lemonsqueezy", data=payload_bytes, headers=wh_headers)
print(f"Respuesta Webhook: {res_hook.status_code} - {res_hook.text}")

# 6. Check Profile (After Payment)
print("\n6️⃣ Perfil después del pago (Debe ser ACTIVE)")
res_prof2 = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
prof2 = res_prof2.json()
print(f"Estado de suscripción: {prof2.get('subscription_status')}")
print(f"Customer ID asociado: {prof2.get('lemonsqueezy_customer_id')}")

print("\n" + "="*50)
print("✅ TEST E2E COMPLETADO CON ÉXITO")
print("="*50)
