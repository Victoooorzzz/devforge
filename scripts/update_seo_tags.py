import os
import re

apps = {
    "filecleaner": {
        "title": "FileCleaner - Industrial-grade data cleaning",
        "description": "Clean CSV and Excel files instantly. Fix nulls and duplicates with AI. Ideal for data analysts and teams.",
        "domain": "filecleaner.devforgeapp.pro",
        "problem": "¿Cansado de perder horas limpiando archivos CSV llenos de nulos y duplicados?",
        "solution": "Esta herramienta procesa y corrige anomalías de forma ultrarrápida usando FastAPI.",
        "target": "Ideal para data analysts y equipos de operaciones."
    },
    "invoicefollow": {
        "title": "InvoiceFollow - Automated payment recovery",
        "description": "Automate invoice follow-ups and get paid faster. Perfect for freelancers and agencies. Send smart reminders.",
        "domain": "invoicefollow.devforgeapp.pro",
        "problem": "¿Cansado de perseguir clientes que no pagan sus facturas a tiempo?",
        "solution": "Esta herramienta automatiza el envío de recordatorios de cobro inteligentes.",
        "target": "Ideal para freelancers, agencias y consultores que cobran por proyecto."
    },
    "pricetrackr": {
        "title": "PriceTrackr - Real-time market intelligence",
        "description": "Monitor competitor prices in background. Get alerted instantly on price changes. Built for e-commerce owners.",
        "domain": "pricetrackr.devforgeapp.pro",
        "problem": "¿Cansado de revisar manualmente los precios de tus competidores todos los días?",
        "solution": "Esta herramienta monitorea URLs en segundo plano y te alerta cuando hay cambios de precio.",
        "target": "Ideal para dueños de e-commerce, dropshippers y estrategas de mercado."
    },
    "webhookmonitor": {
        "title": "WebhookMonitor - Terminal-grade webhook inspection",
        "description": "Intercept, inspect, and replay webhooks. Universal logging for Stripe, GitHub. Made for backend developers.",
        "domain": "webhookmonitor.devforgeapp.pro",
        "problem": "¿Cansado de que fallen tus integraciones con Stripe o Shopify y no saber por qué?",
        "solution": "Esta herramienta intercepta, inspecciona y permite hacer replay de webhooks.",
        "target": "Ideal para backend developers, integradores y equipos de DevOps."
    },
    "feedbacklens": {
        "title": "FeedbackLens - Local sentiment analysis",
        "description": "Analyze customer feedback instantly. Extract complaints, sentiment, and duplicates locally. Perfect for Product Managers.",
        "domain": "feedbacklens.devforgeapp.pro",
        "problem": "¿Cansado de leer miles de reseñas de usuarios sin poder encontrar el problema principal?",
        "solution": "Esta herramienta extrae quejas comunes, sentimiento y duplicados con analisis local.",
        "target": "Ideal para Product Managers, equipos de soporte y SaaS founders."
    }
}

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

# 1. Generate Sitemap for all 6 apps (including devforge-site)
all_apps = list(apps.keys()) + ["devforge-site"]
for app in all_apps:
    domain = apps[app]["domain"] if app in apps else "devforgeapp.pro"
    sitemap_content = f"""import type {{ MetadataRoute }} from 'next'

export default function sitemap(): MetadataRoute.Sitemap {{
  return [
    {{
      url: 'https://{domain}',
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 1,
    }},
    {{
      url: 'https://{domain}/terms',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    }},
    {{
      url: 'https://{domain}/privacy',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    }},
    {{
      url: 'https://{domain}/refunds',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    }},
  ]
}}
"""
    sitemap_path = os.path.join(base_dir, app, "frontend", "src", "app", "sitemap.ts")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_content)

# 2. Update layout.tsx and page.tsx for the 5 micro-saas apps
for app, data in apps.items():
    # Update layout.tsx
    layout_path = os.path.join(base_dir, app, "frontend", "src", "app", "layout.tsx")
    with open(layout_path, "r", encoding="utf-8") as f:
        layout_content = f.read()

    # Add import
    if "seoMetadata" not in layout_content:
        layout_content = layout_content.replace('import type { Metadata } from "next";', 
                                                'import type { Metadata } from "next";\nimport { generateMetadata as seoMetadata } from "@devforge/core";')
    
    # Replace metadata object
    new_metadata = f"""export const metadata: Metadata = seoMetadata({{
  title: "{data['title']}",
  description: "{data['description']}",
  url: "https://{data['domain']}",
  productName: "{data['title'].split(' - ')[0]}",
}});"""
    
    layout_content = re.sub(r'export const metadata: Metadata = \{[\s\S]*?\};', new_metadata, layout_content)
    with open(layout_path, "w", encoding="utf-8") as f:
        f.write(layout_content)

    # Update page.tsx
    page_path = os.path.join(base_dir, app, "frontend", "src", "app", "page.tsx")
    with open(page_path, "r", encoding="utf-8") as f:
        page_content = f.read()
    
    # Look for the hero subtitle block (usually a <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12" ...</p>)
    seo_blocks = f"""
          <div className="text-sm text-neutral-400 space-y-3 mt-6 mb-12 max-w-2xl mx-auto border border-white/5 bg-white/[0.02] p-6 rounded-xl text-left">
            <p><strong className="text-white">El problema:</strong> {data['problem']}</p>
            <p><strong className="text-white">La solución:</strong> {data['solution']}</p>
            <p><strong className="text-white">Para quién es:</strong> {data['target']}</p>
          </div>
"""
    # Replace the mb-12 class on the paragraph to mb-6 to make space for the new block
    page_content = page_content.replace("mx-auto mb-12", "mx-auto mb-6")
    
    # We find the closing </p> tag for the subtitle and insert our block right after it
    # Because there might be multiple </p>, we match the one right after the hero headline
    match = re.search(r'(<h1.*?</h1>\s*<p.*?</p>)', page_content, re.DOTALL)
    if match:
        original = match.group(1)
        if "El problema:" not in original: # prevent duplicate insertions
            new_block = original + seo_blocks
            page_content = page_content.replace(original, new_block)
            
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(page_content)

print("SEO updates applied to all products.")
