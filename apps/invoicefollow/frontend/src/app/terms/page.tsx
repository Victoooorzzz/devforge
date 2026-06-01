import React from "react";
import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Terms of Service</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2026</p>
        <p>By using InvoiceFollow, you agree to these terms. We provide this tool "as is", without any warranties. You are responsible for your use of the platform.</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">1. Use of Service</h2>
          <p>You must not use our service for any illegal or unauthorized purpose. Abuse of the platform will result in account termination.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">2. Payments & Subscriptions</h2>
          <p>We offer a 7-day free trial. A $9.99/mo charge will be processed afterwards. You can cancel at any time before the charge is processed.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">3. Changes to Terms</h2>
          <p>We reserve the right to modify these terms at any time. We will notify you of significant changes.</p>
        </div>
      </div>
    </div>
  );
}
