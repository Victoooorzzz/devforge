"use client";

import { Suspense, useMemo, useState } from "react";
import { auth, DEVFORGE_PRODUCTS, type PlanSlug, type ProductSlug, trackEvent } from "@devforge/core";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

type RegisterPlan = Extract<PlanSlug, "free" | "pro" | "team">;

const planOptions: Array<{ slug: RegisterPlan; label: string; detail: string }> = [
  { slug: "free", label: "Free", detail: "$0" },
  { slug: "pro", label: "Pro", detail: "Pro checkout" },
  { slug: "team", label: "Team", detail: "Max limits" },
];

function normalizePlan(value: string | null): RegisterPlan {
  return value === "free" || value === "team" ? value : "pro";
}

function normalizeProduct(value: string | null): ProductSlug {
  return DEVFORGE_PRODUCTS.some((product) => product.slug === value) ? (value as ProductSlug) : "webhookmonitor";
}

function RegisterForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [plan, setPlan] = useState<RegisterPlan>(() => normalizePlan(searchParams.get("plan")));
  const [productSlug, setProductSlug] = useState<ProductSlug>(() => normalizeProduct(searchParams.get("product")));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedProduct = useMemo(
    () => DEVFORGE_PRODUCTS.find((product) => product.slug === productSlug) || DEVFORGE_PRODUCTS[0],
    [productSlug],
  );

  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { success, error: authError, checkoutUrl, isEmailVerified } = await auth.register({
        name,
        email,
        password,
        app_name: selectedProduct.slug,
        plan,
      });

      if (!success) {
        setError(authError || "Registration failed");
        return;
      }

      trackEvent("suite_signup", { plan, product: selectedProduct.slug });

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
        return;
      }

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
      <div className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-5xl items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="surface-card-raised border border-white/10 p-6 md:p-8">
            <Link href="/" className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--color-text-secondary)" }}>
              DevForge
            </Link>
            <h1 className="heading-section mt-5 text-3xl md:text-4xl">Start with one workflow</h1>
            <p className="mt-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
              Pick the product and plan you want to enter from the suite. Your account uses the shared DevForge backend.
            </p>
            <div className="mt-6 grid gap-3">
              {DEVFORGE_PRODUCTS.map((product) => (
                <button
                  key={product.slug}
                  type="button"
                  onClick={() => setProductSlug(product.slug)}
                  className="rounded-md border p-4 text-left transition hover:border-white/25"
                  style={{
                    borderColor: product.slug === productSlug ? product.accentColor : "rgba(255,255,255,0.1)",
                    backgroundColor: product.slug === productSlug ? `${product.accentColor}18` : "rgba(255,255,255,0.035)",
                  }}
                >
                  <span className="block text-sm font-semibold">{product.name}</span>
                  <span className="mt-1 block text-xs" style={{ color: "var(--color-text-secondary)" }}>
                    {product.category}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="surface-card-raised border border-white/10 p-6 md:p-8">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase" style={{ color: selectedProduct.accentColor }}>
                {selectedProduct.name}
              </p>
              <h2 className="heading-section mt-2 text-2xl">Create account</h2>
              <p className="mt-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
                {plan === "free" ? "Create a free workspace." : `Continue with ${plan.toUpperCase()} for ${selectedProduct.name}.`}
              </p>
            </div>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label htmlFor="suite-register-name" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Name</label>
                <input id="suite-register-name" value={name} onChange={(event) => setName(event.target.value)} className="input-field" placeholder="Your name" autoComplete="name" />
              </div>
              <div>
                <label htmlFor="suite-register-email" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Email</label>
                <input id="suite-register-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input-field" placeholder="name@example.com" required autoComplete="email" />
              </div>
              <div>
                <label htmlFor="suite-register-password" className="mb-1.5 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Password</label>
                <input id="suite-register-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="input-field" placeholder="Password" required autoComplete="new-password" />
              </div>

              <div>
                <label className="mb-2 block text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Plan</label>
                <div className="grid grid-cols-3 gap-2">
                  {planOptions.map((option) => (
                    <button
                      key={option.slug}
                      type="button"
                      onClick={() => setPlan(option.slug)}
                      className="rounded-md border px-3 py-2 text-left text-xs transition"
                      style={{
                        borderColor: plan === option.slug ? selectedProduct.accentColor : "rgba(255,255,255,0.1)",
                        backgroundColor: plan === option.slug ? `${selectedProduct.accentColor}18` : "rgba(255,255,255,0.04)",
                        color: plan === option.slug ? "var(--color-text)" : "var(--color-text-secondary)",
                      }}
                    >
                      <span className="block font-semibold">{option.label}</span>
                      <span>{option.detail}</span>
                    </button>
                  ))}
                </div>
              </div>

              {error ? <p className="text-center text-xs text-red-400">{error}</p> : null}

              <button type="submit" disabled={loading} className="btn-primary w-full py-4 text-sm">
                {loading ? "Creating account..." : plan === "free" ? "Create Free Account" : `Continue with ${plan}`}
              </button>
            </form>

            <p className="mt-6 text-center text-sm" style={{ color: "var(--color-text-secondary)" }}>
              Already have an account? <Link href={`/login?product=${selectedProduct.slug}`} className="font-semibold" style={{ color: selectedProduct.accentColor }}>Log in</Link>
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black" />}>
      <RegisterForm />
    </Suspense>
  );
}
