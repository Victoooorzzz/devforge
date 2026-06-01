import React from "react";
import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Privacy Policy</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2026</p>
        <p>At PriceTrackr, we value your privacy. This policy explains how we collect, use, and protect your data.</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">1. Collected Data</h2>
          <p>We collect your email address for account management and communication, and app usage data to improve our services.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">2. Payment Processing</h2>
          <p>Your payments are securely processed by Polar. We do not store your credit card information.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">3. Contact</h2>
          <p>For data deletion requests or privacy concerns, contact us at support@devforgeapp.pro.</p>
        </div>
      </div>
    </div>
  );
}
