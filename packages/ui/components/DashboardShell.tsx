// packages/ui/components/DashboardShell.tsx
"use client";

import React, { useState } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  active?: boolean;
}

interface DashboardShellProps {
  productName: string;
  logoSrc?: string;
  navItems: NavItem[];
  userName: string;
  userEmail: string;
  onLogout: () => void;
  children: React.ReactNode;
}

export function DashboardShell({
  productName,
  logoSrc,
  navItems,
  userName,
  userEmail,
  onLogout,
  children,
}: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: "var(--color-bg)" }}>
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 md:relative md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ backgroundColor: "var(--color-surface)" }}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center h-16 px-6 gap-3">
            {logoSrc && <img src={logoSrc} alt="DevForge" className="h-5 w-auto" />}
            <a
              href="/dashboard"
              className={`text-lg font-bold tracking-tight ${logoSrc ? 'border-l border-white/10 pl-3' : ''}`}
              style={{ color: "var(--color-text)" }}
            >
              {productName}
            </a>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4">
            <ul className="space-y-1">
              {navItems.map((item) => (
                <li key={item.href}>
                  <a
                    href={item.href}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors duration-200"
                    style={{
                      backgroundColor: item.active
                        ? "var(--color-accent-dim)"
                        : "transparent",
                      color: item.active
                        ? "var(--color-accent)"
                        : "var(--color-text-secondary)",
                    }}
                  >
                    <span className="w-5 h-5 flex-shrink-0">{item.icon}</span>
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {/* User section */}
          <div
            className="p-4 mx-3 mb-4 rounded-lg"
            style={{ backgroundColor: "var(--color-surface-raised)" }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-accent-dim)",
                  color: "var(--color-accent)",
                }}
              >
                {userName.charAt(0).toUpperCase()}
              </div>
              <div className="overflow-hidden">
                <p
                  className="text-sm font-medium truncate"
                  style={{ color: "var(--color-text)" }}
                >
                  {userName}
                </p>
                <p
                  className="text-xs truncate"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {userEmail}
                </p>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="w-full text-left text-xs px-2 py-1.5 rounded transition-colors duration-200"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header
          className="flex items-center h-16 px-6 border-b md:hidden"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "var(--color-border)",
          }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-md"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 5H17M3 10H17M3 15H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
          <span
            className="ml-4 text-sm font-semibold"
            style={{ color: "var(--color-text)" }}
          >
            {productName}
          </span>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 md:p-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
