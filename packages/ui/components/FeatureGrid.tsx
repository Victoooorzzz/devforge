// packages/ui/components/FeatureGrid.tsx
import React from "react";

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface FeatureGridProps {
  title?: string;
  subtitle?: string;
  features: Feature[];
}

export function FeatureGrid({ title, subtitle, features }: FeatureGridProps) {
  return (
    <section className="py-20 md:py-28" style={{ backgroundColor: "var(--color-surface)" }}>
      <div className="section-container">
        {(title || subtitle) && (
          <div className="text-center mb-16">
            {title && (
              <h2 className="heading-section text-3xl md:text-4xl mb-4">
                {title}
              </h2>
            )}
            {subtitle && (
              <p
                className="text-lg max-w-2xl mx-auto"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {subtitle}
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-8 rounded-lg transition-all duration-300 hover:translate-y-[-2px]"
              style={{
                backgroundColor: "var(--color-surface-raised)",
              }}
            >
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center mb-6 transition-colors duration-300"
                style={{
                  backgroundColor: "var(--color-accent-dim)",
                  color: "var(--color-accent)",
                }}
              >
                {feature.icon}
              </div>
              <h3
                className="text-lg font-semibold mb-3"
                style={{ color: "var(--color-text)" }}
              >
                {feature.title}
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
