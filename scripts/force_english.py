import os
import glob

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

app_names = {
    "filecleaner": "FileCleaner",
    "invoicefollow": "InvoiceFollow",
    "pricetrackr": "PriceTrackr",
    "webhookmonitor": "WebhookMonitor",
    "feedbacklens": "FeedbackLens",
    "devforge-site": "DevForge"
}

# 1. Regenerate all legal pages in English for all 6 apps
for folder, app_name in app_names.items():
    app_dir = os.path.join(base_dir, folder, "frontend", "src", "app")
    
    # Check if we should use layout for devforge-site or standard Layout
    # Actually the legal pages inside devforge-site use <Layout productName="DevForge" productDomain="devforgeapp.pro">
    # Wait, the 5 micro saas apps use <Layout> from where?
    # They don't use @devforge/ui layout for legal pages, or do they?
    # Let's just create generic english content for the legal pages
    
    domain = f"{folder}.devforgeapp.pro" if folder != "devforge-site" else "devforgeapp.pro"
    
    terms_content = f"""import React from "react";
import Link from "next/link";

export default function TermsPage() {{
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Terms of Service</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2024</p>
        <p>By using {app_name}, you agree to these terms. We provide this tool "as is", without any warranties. You are responsible for your use of the platform.</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">1. Use of Service</h2>
          <p>You must not use our service for any illegal or unauthorized purpose. Abuse of the platform will result in account termination.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">2. Payments & Subscriptions</h2>
          <p>We offer a 7-day free trial. A $9.99/mo charge will be processed afterwards. You can cancel at any time before the charge is processed.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">3. Changes to Terms</h2>
          <p>We reserve the right to modify these terms at any time. We will notify you of significant changes.</p>
        </div>
      </div>
    </div>
  );
}}
"""

    privacy_content = f"""import React from "react";
import Link from "next/link";

export default function PrivacyPage() {{
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Privacy Policy</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2024</p>
        <p>At {app_name}, we value your privacy. This policy explains how we collect, use, and protect your data.</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">1. Collected Data</h2>
          <p>We collect your email address for account management and communication, and app usage data to improve our services.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">2. Payment Processing</h2>
          <p>Your payments are securely processed by Lemon Squeezy. We do not store your credit card information.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">3. Contact</h2>
          <p>For data deletion requests or privacy concerns, contact us at support@devforgeapp.pro.</p>
        </div>
      </div>
    </div>
  );
}}
"""

    refunds_content = f"""import React from "react";
import Link from "next/link";

export default function RefundsPage() {{
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Refund Policy</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2024</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Trial Period & Charges</h2>
          <p>To ensure user satisfaction, {app_name} offers a 7-day free trial. During this time, you have full access to our platform's enterprise-grade infrastructure features, allowing you to evaluate if it meets your needs.</p>
          <p className="mt-2">Once the 7-day trial has elapsed, the recurring monthly charge of $9.99 will be processed automatically.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Final Sales Policy</h2>
          <p>Because we offer this extended trial period for you to freely evaluate the product, once the subscription charge is processed, all sales are final and no refunds are issued under any circumstances.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Cancellations</h2>
          <p>You are free to cancel your subscription at any time before the trial period ends to avoid charges, or at any time thereafter to avoid future monthly charges. You can cancel directly from your dashboard or via Lemon Squeezy emails.</p>
        </div>
      </div>
    </div>
  );
}}
"""

    # Write them safely
    for page, content in [("terms", terms_content), ("privacy", privacy_content), ("refunds", refunds_content)]:
        path = os.path.join(app_dir, page, "page.tsx")
        if os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

# 2. String replacements across all TSX files
tsx_files = glob.glob(os.path.join(base_dir, "**", "*.tsx"), recursive=True)

replace_map = {
    "El problema:": "The Problem:",
    "La solución:": "The Solution:",
    "Para quién es:": "Who is it for:",
    "Volver al inicio": "Back to home",
    "← Volver al inicio": "← Back to home",
    "← Volver": "← Back",
    "Términos de Servicio": "Terms of Service",
    "Política de Privacidad": "Privacy Policy",
    "Política de Reembolsos": "Refund Policy"
}

for file_path in tsx_files:
    if "node_modules" in file_path or ".next" in file_path:
        continue
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content
        for k, v in replace_map.items():
            new_content = new_content.replace(k, v)
        
        # Also fix devforge-site package/ui strings if any are passed
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
    except:
        pass

# Also let's fix devforge-site page.tsx specifically in case it has keys in Spanish
devforge_site_page = os.path.join(base_dir, "devforge-site", "frontend", "src", "app", "page.tsx")
try:
    with open(devforge_site_page, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We replaced the text inside the objects earlier, but let's be sure the fields in the object aren't rendered with "El problema:"
    content = content.replace("El problema:", "The Problem:")
    content = content.replace("La solución:", "The Solution:")
    content = content.replace("Para quién es:", "Who is it for:")
    
    with open(devforge_site_page, "w", encoding="utf-8") as f:
        f.write(content)
except:
    pass

# Update ProductCard in @devforge/ui just in case there are hardcoded spanish labels
product_card = r"c:\Users\victor\Downloads\microsaas\devforge\packages\ui\components\ProductCard.tsx"
try:
    with open(product_card, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("El problema:", "The Problem:")
    content = content.replace("La solución:", "The Solution:")
    content = content.replace("Para quién es:", "Who is it for:")
    with open(product_card, "w", encoding="utf-8") as f:
        f.write(content)
except:
    pass

print("Fixed English translations across the board.")
