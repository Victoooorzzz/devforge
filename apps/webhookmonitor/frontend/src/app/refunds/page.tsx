import React from "react";
import Link from "next/link";

export default function RefundsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-24 max-w-3xl mx-auto selection:bg-accent selection:text-black">
      <Link href="/" className="text-neutral-400 hover:text-white transition-colors mb-8 inline-block text-sm">
        ← Back to home
      </Link>
      <h1 className="text-4xl font-bold mb-6">Refund Policy</h1>
      <div className="space-y-6 text-neutral-400">
        <p>Last updated: May 2024</p>
        
        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Trial Period & Charges</h2>
          <p>To ensure user satisfaction, WebhookMonitor offers a 7-day free trial. During this time, you have full access to our platform's enterprise-grade infrastructure features, allowing you to evaluate if it meets your needs.</p>
          <p className="mt-2">Once the 7-day trial has elapsed, the recurring monthly charge of $9.99 will be processed automatically.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Final Sales Policy</h2>
          <p>Because we offer this extended trial period for you to freely evaluate the product, once the subscription charge is processed, all sales are final and no refunds are issued under any circumstances.</p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mt-6 mb-2 text-white">Cancellations</h2>
          <p>You are free to cancel your subscription at any time before the trial period ends to avoid charges, or at any time thereafter to avoid future monthly charges. You can cancel directly from your dashboard or via Lemon Squeezy emails.</p>
        </div>
      </div>
    </div>
  );
}
