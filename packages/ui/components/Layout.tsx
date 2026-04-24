// packages/ui/components/Layout.tsx
import React from "react";

interface NavLink {
  label: string;
  href: string;
}

interface LayoutProps {
  productName: string;
  productDomain: string;
  navLinks?: NavLink[];
  ctaText?: string;
  ctaHref?: string;
  children: React.ReactNode;
}

export function Layout({
  productName,
  productDomain,
  navLinks = [],
  ctaText = "Get Started",
  ctaHref = "/register",
  children,
}: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "var(--color-bg)" }}>
      <header className="glass sticky top-0 z-50 border-b" style={{ borderColor: "rgba(38,38,38,0.15)" }}>
        <nav className="section-container flex items-center justify-between h-16">
          <a
            href="/"
            className="text-lg font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            {productName}
          </a>

          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm transition-colors duration-200 hover:opacity-80"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <a
              href="/login"
              className="text-sm transition-colors duration-200 hover:opacity-80"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Log in
            </a>
            <a href={ctaHref} className="btn-primary">
              {ctaText}
            </a>
          </div>
        </nav>
      </header>

      <main className="flex-1">{children}</main>

      <footer style={{ backgroundColor: "var(--color-surface)" }}>
        <div className="section-container py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <span className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                {productName}
              </span>
              <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                {productDomain}
              </span>
            </div>

            <div className="flex items-center gap-6">
              <a
                href="https://devforge.io"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm transition-colors duration-200 hover:opacity-80"
                style={{ color: "var(--color-text-secondary)" }}
              >
                Built by DevForge
              </a>
            </div>
          </div>

          <div className="divider my-8" />

          <p className="text-center text-xs" style={{ color: "var(--color-text-secondary)" }}>
            &copy; {new Date().getFullYear()} {productName}. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
