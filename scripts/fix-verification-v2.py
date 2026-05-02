import os

apps = [
    "filecleaner",
    "invoicefollow",
    "pricetrackr",
    "webhookmonitor",
    "feedbacklens",
    "template"
]

base_path = r"c:\Users\victor\Downloads\microsaas\devforge\apps"

verify_content = """'use client';
import { VerifyEmail } from "@devforge/ui";
import { product } from "@/config/product";
import Link from "next/link";

export default function VerifyPage() {
  return (
    <div className="min-h-screen bg-black flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-8">
        <Link href="/" className="text-3xl font-bold tracking-tighter text-white">
          {product.name.split(' ')[0]}<span className="text-indigo-500">{product.name.split(' ')[1] || ''}</span>
        </Link>
      </div>
      <VerifyEmail />
    </div>
  );
}
"""

def update_file(path, is_register):
    if not os.path.exists(path):
        return
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    modified = False
    
    # Method 1: auth.register/login
    method_name = "register" if is_register else "login"
    search_str = f"const {{ success, error: authError }} = await auth.{method_name}"
    if search_str in content and "isEmailVerified" not in content:
        content = content.replace(search_str, f"const {{ success, error: authError, isEmailVerified }} = await auth.{method_name}")
        modified = True
    
    # Method 2: apiClient.post
    endpoint = f"/auth/{method_name}"
    if f'apiClient.post("{endpoint}"' in content or f"apiClient.post('{endpoint}'" in content:
        # Update interface if exists
        interface_name = "RegisterResponse" if is_register else "LoginResponse"
        if f"interface {interface_name} {{" in content and "is_email_verified" not in content:
            content = content.replace(f"interface {interface_name} {{", f"interface {interface_name} {{\n  is_email_verified: boolean;")
            modified = True
            
        # Add redirect logic for apiClient
        if 'if (data.access_token)' in content and 'router.push("/verify")' not in content:
             content = content.replace('if (data.access_token) {', 'if (data.access_token) {\n      if (data.is_email_verified === false) {\n        setToken(data.access_token);\n        router.push("/verify");\n        return;\n      }')
             modified = True
        elif 'setToken(data.access_token);' in content and 'router.push("/verify")' not in content:
             content = content.replace('setToken(data.access_token);', 'setToken(data.access_token);\n      if (data.is_email_verified === false) {\n        router.push("/verify");\n        return;\n      }')
             modified = True

    # Common redirect logic for auth object
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
    
    # Verify page
    verify_path = os.path.join(app_dir, "verify", "page.tsx")
    if os.path.exists(app_dir):
        os.makedirs(os.path.dirname(verify_path), exist_ok=True)
        with open(verify_path, "w", encoding="utf-8") as f:
            f.write(verify_content)
            
    update_file(os.path.join(app_dir, "register", "page.tsx"), True)
    update_file(os.path.join(app_dir, "login", "page.tsx"), False)
