import os
import glob

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

replacements = {
    "Reembolsos: Tienes un trial gratuito de 7 días. Una vez procesado el cargo mensual de $9.99, todas las ventas son definitivas y no se emiten reembolsos.": "Refunds: You have a 7-day free trial. Once the $9.99 monthly charge is processed, all sales are final and no refunds are issued.",
    "Reembolsos:": "Refunds:",
    "Tienes un trial gratuito de 7 días.": "You have a 7-day free trial.",
    "Una vez procesado el cargo mensual de $9.99, todas las ventas son definitivas y no se emiten reembolsos.": "Once the $9.99 monthly charge is processed, all sales are final and no refunds are issued.",
    "Crear cuenta gratis": "Create free account",
    "Importar en masa": "Bulk import",
    "Pausar recordatorios (promesa de pago)": "Pause reminders (promise to pay)",
    "Error desconocido": "Unknown error",
    "Error en análisis de IA": "Analysis error",
    "No se detectaron problemas — los datos parecen limpios.": "No issues detected — the data appears clean."
}

tsx_files = glob.glob(os.path.join(base_dir, "**", "*.tsx"), recursive=True)

for file_path in tsx_files:
    if "node_modules" in file_path or ".next" in file_path:
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content
    for k, v in replacements.items():
        new_content = new_content.replace(k, v)
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed remaining Spanish in {file_path}")

print("Done")
