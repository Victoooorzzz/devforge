"use client";
import { redirectToPortal } from "@devforge/core";

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-2" style={{ color: "var(--color-text)" }}>Settings</h1>
      <p className="text-sm mb-8" style={{ color: "var(--color-text-secondary)" }}>Manage your account and subscription.</p>
      <div className="p-6 rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>Subscription</h2>
        <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>Manage your billing, update payment methods, or cancel your plan.</p>
        <button onClick={() => redirectToPortal()} className="btn-secondary">Manage Subscription</button>
      </div>
    </div>
  );
}
