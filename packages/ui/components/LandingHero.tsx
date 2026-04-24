// packages/ui/components/LandingHero.tsx
import React from "react";

interface LandingHeroProps {
  badge?: string;
  headline: string;
  subtitle: string;
  ctaText: string;
  ctaHref: string;
  secondaryCtaText?: string;
  secondaryCtaHref?: string;
}

export function LandingHero({
  badge,
  headline,
  subtitle,
  ctaText,
  ctaHref,
  secondaryCtaText,
  secondaryCtaHref,
}: LandingHeroProps) {
  return (
    <section className="relative overflow-hidden">
      {/* Ambient glow behind hero */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] rounded-full opacity-20 blur-3xl pointer-events-none"
        style={{
          background: `radial-gradient(ellipse, var(--color-accent) 0%, transparent 70%)`,
        }}
      />

      <div className="section-container relative z-10 pt-24 pb-20 md:pt-32 md:pb-28 flex flex-col items-center text-center">
        {badge && (
          <div className="badge mb-6 animate-fade-in">
            {badge}
          </div>
        )}

        <h1
          className="heading-display text-4xl md:text-5xl lg:text-6xl max-w-4xl mb-6 animate-slide-up text-balance"
        >
          {headline}
        </h1>

        <p
          className="text-lg md:text-xl max-w-2xl mb-10 leading-relaxed animate-slide-up"
          style={{
            color: "var(--color-text-secondary)",
            animationDelay: "100ms",
          }}
        >
          {subtitle}
        </p>

        <div
          className="flex flex-col sm:flex-row items-center gap-4 animate-slide-up"
          style={{ animationDelay: "200ms" }}
        >
          <a href={ctaHref} className="btn-primary text-base px-8 py-3">
            {ctaText}
          </a>
          {secondaryCtaText && secondaryCtaHref && (
            <a href={secondaryCtaHref} className="btn-secondary text-base px-8 py-3">
              {secondaryCtaText}
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
