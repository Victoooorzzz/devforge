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

for app in apps:
    app_dir = os.path.join(base_path, app, "frontend", "src", "app")
    
    # 1. Fix verify page
    verify_path = os.path.join(app_dir, "verify", "page.tsx")
    if os.path.exists(app_dir):
        os.makedirs(os.path.dirname(verify_path), exist_ok=True)
        with open(verify_path, "w", encoding="utf-8") as f:
            f.write(verify_content)
        print(f"Fixed verify page for {app}")

    # 2. Update register page
    register_path = os.path.join(app_dir, "register", "page.tsx")
    if os.path.exists(register_path):
        with open(register_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Ensure isEmailVerified is destructured
        if "isEmailVerified" not in content:
            content = content.replace("const { success, error: authError } = await auth.register", "const { success, error: authError, isEmailVerified } = await auth.register")
        
        # Add redirect logic (safely)
        if 'if (success) {' in content and 'router.push("/verify")' not in content:
            # We insert it right after the success check
            insertion = """if (success) {
        if (isEmailVerified === false) {
          router.push("/verify");
          return;
        }"""
            content = content.replace("if (success) {", insertion)
            print(f"Updated register page for {app}")
        
        with open(register_path, "w", encoding="utf-8") as f:
            f.write(content)

    # 3. Update login page
    login_path = os.path.join(app_dir, "login", "page.tsx")
    if os.path.exists(login_path):
        with open(login_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Ensure isEmailVerified is destructured
        if "isEmailVerified" not in content:
            content = content.replace("const { success, error: authError } = await auth.login", "const { success, error: authError, isEmailVerified } = await auth.login")
        
        # Add redirect logic
        if 'if (success) {' in content and 'router.push("/verify")' not in content:
            insertion = """if (success) {
        if (isEmailVerified === false) {
          router.push("/verify");
          return;
        }"""
            content = content.replace("if (success) {", insertion)
            print(f"Updated login page for {app}")
            
        with open(login_path, "w", encoding="utf-8") as f:
            f.write(content)
