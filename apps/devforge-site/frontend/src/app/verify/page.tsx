"use client";

import { Suspense, useMemo } from "react";
import { DEVFORGE_PRODUCTS, type ProductSlug } from "@devforge/core";
import { VerifyEmail } from "@devforge/ui";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

function normalizeProduct(value: string | null): ProductSlug {
  return DEVFORGE_PRODUCTS.some((product) => product.slug === value) ? (value as ProductSlug) : "filecleaner";
}

function VerifyContent() {
  const searchParams = useSearchParams();
  const productSlug = normalizeProduct(searchParams.get("product"));
  const selectedProduct = useMemo(
    () => DEVFORGE_PRODUCTS.find((product) => product.slug === productSlug) || DEVFORGE_PRODUCTS[0],
    [productSlug],
  );

  return (
    <main className="min-h-screen bg-black px-4 py-12 text-white">
      <div className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-md flex-col justify-center">
        <div className="mb-8 text-center">
          <Link href="/" className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--color-text-secondary)" }}>
            DevForge
          </Link>
          <h1 className="heading-section mt-4 text-3xl">Verify email</h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
            After verification, we will open {selectedProduct.name}.
          </p>
        </div>
        <VerifyEmail onVerified={() => { window.location.href = `${selectedProduct.url}/dashboard`; }} />
      </div>
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black" />}>
      <VerifyContent />
    </Suspense>
  );
}
