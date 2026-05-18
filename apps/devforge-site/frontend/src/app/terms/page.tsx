import React from "react";
import { Layout } from "@devforge/ui";

export default function TermsPage() {
  return (
    <Layout productName="DevForge" productDomain="devforgeapp.pro">
      <div className="section-container py-20 max-w-3xl mx-auto" style={{ color: "var(--color-text)" }}>
        <h1 className="text-4xl font-bold mb-6">Terms of Service</h1>
        <div className="space-y-4" style={{ color: "var(--color-text-secondary)" }}>
          <p>Last updated: May 2024</p>
          <p>DevForge is a platform that groups various tools. By using DevForge, you agree to these terms. We provide this tool "as is", without any warranties.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2" style={{ color: "var(--color-text)" }}>1. Use of Service</h2>
          <p>You must not use our service for any illegal or unauthorized purpose.</p>
        </div>
      </div>
    </Layout>
  );
}
