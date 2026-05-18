import React from "react";
import { Layout } from "@devforge/ui";

export default function PrivacyPage() {
  return (
    <Layout productName="DevForge" productDomain="devforgeapp.pro">
      <div className="section-container py-20 max-w-3xl mx-auto" style={{ color: "var(--color-text)" }}>
        <h1 className="text-4xl font-bold mb-6">Privacy Policy</h1>
        <div className="space-y-4" style={{ color: "var(--color-text-secondary)" }}>
          <p>Last updated: May 2024</p>
          <p>At DevForge, we respect your privacy. This policy explains how we collect and protect your data across our ecosystem.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2" style={{ color: "var(--color-text)" }}>1. Collected Data</h2>
          <p>We collect your email address for the management of your unified account.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2" style={{ color: "var(--color-text)" }}>2. Payments</h2>
          <p>Processed by Lemon Squeezy, we do not store your credit card information.</p>
        </div>
      </div>
    </Layout>
  );
}
