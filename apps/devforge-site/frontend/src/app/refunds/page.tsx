import React from "react";
import { Layout } from "@devforge/ui";

export default function RefundsPage() {
  return (
    <Layout productName="DevForge" productDomain="devforgeapp.pro">
      <div className="section-container py-20 max-w-3xl mx-auto" style={{ color: "var(--color-text)" }}>
        <h1 className="text-4xl font-bold mb-6">Refund Policy</h1>
        <div className="space-y-4" style={{ color: "var(--color-text-secondary)" }}>
          <p>Last updated: May 2024</p>
          <p>To ensure satisfaction, all our applications at DevForge offer a 7-day free trial.</p>
          <p>Once the 7-day trial has elapsed, the subscription charge will be processed automatically. Due to this generous policy, <strong>once the payment is processed, all sales are final and no refunds are issued.</strong></p>
        </div>
      </div>
    </Layout>
  );
}
