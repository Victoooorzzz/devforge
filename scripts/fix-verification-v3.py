import os
import re

apps = [
    "filecleaner",
    "invoicefollow",
    "pricetrackr",
    "webhookmonitor",
    "feedbacklens",
    "template"
]

base_path = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

def update_file(path, is_register):
    if not os.path.exists(path):
        return
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    modified = False
    method_name = "register" if is_register else "login"
    
    # Method 1: auth.register/login
    search_str = f"const {{ success, error: authError }} = await auth.{method_name}"
    if search_str in content and "isEmailVerified" not in content:
        content = content.replace(search_str, f"const {{ success, error: authError, isEmailVerified }} = await auth.{method_name}")
        modified = True
    
    # Method 2: apiClient.post with possible Generics
    # Match apiClient.post<...>(...) or apiClient.post(...)
    api_pattern = rf'apiClient\.post(<[^>]+>)?\(\s*["\']/auth/{method_name}["\']'
    if re.search(api_pattern, content):
        # Update interface
        interface_name = "RegisterResponse" if is_register else "LoginResponse"
        interface_pattern = rf'interface\s+{interface_name}\s+{{'
        if re.search(interface_pattern, content) and "is_email_verified" not in content:
            content = re.sub(interface_pattern, f'interface {interface_name} {{\n  is_email_verified: boolean;', content)
            modified = True
            
        # Add redirect logic
        if 'setToken(data.access_token);' in content and 'router.push("/verify")' not in content:
             content = content.replace('setToken(data.access_token);', 'setToken(data.access_token);\n      if (data.is_email_verified === false) {\n        router.push("/verify");\n        return;\n      }')
             modified = True

    # Common redirect logic for success
    if 'if (success) {' in content and 'router.push("/verify")' not in content:
        insertion = """if (success) {
        if (isEmailVerified === false) {
          router.push("/verify");
          return;
        }"""
        content = content.replace("if (success) {", insertion)
        modified = True
        
    if modified:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {path}")

for app in apps:
    app_dir = os.path.join(base_path, app, "frontend", "src", "app")
    update_file(os.path.join(app_dir, "register", "page.tsx"), True)
    update_file(os.path.join(app_dir, "login", "page.tsx"), False)
