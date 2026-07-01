import React from "react";

interface ProductDemoShellProps {
  eyebrow?: string;
  title: string;
  description: string;
  children: React.ReactNode;
}

export function ProductDemoShell({ eyebrow = "Interactive demo", title, description, children }: ProductDemoShellProps) {
  return (
    <section id="demo" className="py-16 md:py-24">
      <div className="section-container">
        <div className="mb-8 max-w-3xl">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-accent)" }}>
            {eyebrow}
          </p>
          <h2 className="heading-section mt-3 text-3xl md:text-4xl">{title}</h2>
          <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            {description}
          </p>
        </div>
        <div className="demo-panel demo-scanline surface-card border border-white/10 p-4 md:p-6">
          {children}
        </div>
      </div>
    </section>
  );
}
