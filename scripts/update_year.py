import os
import glob

base_dir = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

tsx_files = glob.glob(os.path.join(base_dir, "**", "*.tsx"), recursive=True)

for file_path in tsx_files:
    if "node_modules" in file_path or ".next" in file_path:
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content.replace("Last updated: May 2024", "Last updated: May 2026")
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated year in {file_path}")

print("Year update complete.")
