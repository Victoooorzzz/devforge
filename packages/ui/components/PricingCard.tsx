// packages/ui/components/PricingCard.tsx
"use client";

import React, { useState } from "react";

interface PricingFeature {
  text: string;
  included: boolean;
}

interface PricingCardProps {
  planName: string;
  price: number;
  currency?: string;
  interval?: string;
  description: string;
  features: PricingFeature[];
  ctaText?: string;
  onCheckout: () => void;
  popular?: boolean;
}

export function PricingCard({
  planName,
  price,
  currency = "$",
  interval = "month",
  description,
  features,
  ctaText = "Start Free Trial",
  onCheckout,
  popular = true,
}: PricingCardProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await onCheckout();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="py-20 md:py-28">
      <div className="section-container flex justify-center">
        <div
          className="w-full max-w-md relative p-8 rounded-lg"
          style={{
            backgroundColor: "var(--color-surface)",
            border: popular ? "1px solid var(--color-accent)" : "1px solid rgba(38,38,38,0.15)",
          }}
        >
          {popular && (
            <div
              className="absolute -top-3 left-1/2 -translate-x-1/2 badge"
            >
              Most Popular
            </div>
          )}

          <div className="text-center mb-8">
            <h3
              className="text-lg font-semibold mb-2"
              style={{ color: "var(--color-text)" }}
            >
              {planName}
            </h3>
            <p
              className="text-sm mb-6"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {description}
            </p>
            <div className="flex items-baseline justify-center gap-1">
              <span
                className="text-5xl font-bold tracking-tight font-mono"
                style={{ color: "var(--color-text)" }}
              >
                {currency}{price}
              </span>
              <span
                className="text-sm"
                style={{ color: "var(--color-text-secondary)" }}
              >
                /{interval}
              </span>
            </div>
          </div>

          <ul className="space-y-4 mb-8">
            {features.map((feature, index) => (
              <li key={index} className="flex items-start gap-3">
                <span
                  className="mt-0.5 flex-shrink-0"
                  style={{
                    color: feature.included
                      ? "var(--color-accent)"
                      : "var(--color-text-secondary)",
                  }}
                >
                  {feature.included ? (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M13.3 4.3L6.5 11.1L2.7 7.3"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M4 8H12"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  )}
                </span>
                <span
                  className="text-sm"
                  style={{
                    color: feature.included
                      ? "var(--color-text)"
                      : "var(--color-text-secondary)",
                  }}
                >
                  {feature.text}
                </span>
              </li>
            ))}
          </ul>

          <button
            onClick={handleClick}
            disabled={isLoading}
            className="btn-primary w-full py-3 text-base disabled:opacity-50"
          >
            {isLoading ? "Redirecting..." : ctaText}
          </button>
        </div>
      </div>
    </section>
  );
}
