"use client";

import { Suspense, useMemo, useState } from "react";
import { auth, DEVFORGE_PRODUCTS, type ProductSlug, trackEvent } from "@devforge/core";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

function normalizeProduct(value: string | null): ProductSlug {
  return DEVFORGE_PRODUCTS.some((product) => product.slug === value) ? (value as ProductSlug) : "webhookmonitor";
}

function LoginForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [productSlug, setProductSlug] = useState<ProductSlug>(() => normalizeProduct(searchParams.get("product")));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedProduct = useMemo(
    () => DEVFORGE_PRODUCTS.find((product) => product.slug === productSlug) || DEVFORGE_PRODUCTS[0],
    [productSlug],
  );

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { success, error: authError, isEmailVerified } = await auth.login(email, password);
      if (!success) {
        setError(authError || "Invalid credentials");
        return;
      }

      trackEvent("suite_login", { product: selectedProduct.slug });

      if (isEmailVerified === false) {
        router.push(`/verify?product=${selectedProduct.slug}`);
        return;
      }

      window.location.href = `${selectedProduct.url}/dashboard`;
    } catch {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-black px-4 py-12 text-white">
      <div className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-md items-center justify-center">
        <section className="surface-card-raised w-full border border-white/10 p-6 md:p-8">
          <Link href="/" className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--color-text-secondary)" }}>
            DevForge
          </Link>
          <h1 className="heading-section mt-5 text-3xl">Log in</h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
            Choose which product dashboard to open after signing in.
          </p>

          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <div>
              <label htmlFor="suite-login-product" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Product</label>
              <select id="suite-login-product" value={productSlug} onChange={(event) => setProductSlug(event.target.value as ProductSlug)} className="input-field">
                {DEVFORGE_PRODUCTS.map((product) => (
                  <option key={product.slug} value={product.slug}>{product.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="suite-login-email" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Email</label>
              <input id="suite-login-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input-field" placeholder="name@example.com" required autoComplete="email" />
            </div>
            <div>
              <label htmlFor="suite-login-password" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Password</label>
              <input id="suite-login-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="input-field" placeholder="Password" required autoComplete="current-password" />
            </div>

            {error ? <p className="text-center text-xs text-red-400">{error}</p> : null}

            <button type="submit" disabled={loading} className="btn-primary w-full py-4 text-sm">
              {loading ? "Signing in..." : `Open ${selectedProduct.shortName}`}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: "var(--color-text-secondary)" }}>
            Need an account? <Link href={`/register?product=${selectedProduct.slug}&plan=free`} className="font-semibold" style={{ color: selectedProduct.accentColor }}>Start free</Link>
          </p>
        </section>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black" />}>
      <LoginForm />
    </Suspense>
  );
}
