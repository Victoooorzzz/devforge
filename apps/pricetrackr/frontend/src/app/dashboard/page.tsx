import { getServerUser } from "../../lib/auth";
import { sql } from "../../lib/db";
import { redirect } from "next/navigation";
import DashboardClient from "./components/DashboardClient";

export default async function DashboardPage() {
  const user = getServerUser();
  if (!user) {
    redirect("/login");
  }

  // 1. Fetch trackers directly from Neon (pooled)
  const trackers = await sql`
    SELECT * FROM tracked_urls
    WHERE user_id = ${user.userId}
    ORDER BY created_at DESC
  `;

  // 2. Calculate summary statistics
  const active = trackers.filter((t: any) => t.status === 'active');
  let priceDropCount = 0;
  let outOfStockCount = 0;
  let potentialSavings = 0;

  for (const t of active) {
    const current = t.current_price !== null ? parseFloat(t.current_price) : null;
    const previous = t.previous_price !== null ? parseFloat(t.previous_price) : null;
    const minimum = t.min_price !== null ? parseFloat(t.min_price) : null;

    if (current !== null && previous !== null && current < previous) {
      priceDropCount++;
    }
    if (t.in_stock === false) {
      outOfStockCount++;
    }
    if (current !== null && minimum !== null && current > minimum) {
      potentialSavings += (current - minimum);
    }
  }

  const summary = {
    total_trackers: trackers.length,
    active_trackers: active.length,
    price_drop_count: priceDropCount,
    out_of_stock_count: outOfStockCount,
    potential_savings: parseFloat(potentialSavings.toFixed(2)),
  };

  // 3. Compute Health
  const now = new Date();
  const healthList = trackers.map((t: any) => {
    const trackerId = t.id;
    const label = t.label || t.url || `Tracker ${trackerId}`;
    const lastChecked = t.last_checked ? new Date(t.last_checked) : null;
    const frequencyHours = parseInt(t.check_frequency_hours) || 24;
    const staleAfterHours = Math.max(frequencyHours * 2, 24);
    const currentPrice = t.current_price;
    const inStock = t.in_stock;

    let health = 'healthy';
    let severity = 'ok';
    let detail = 'Tracker is checking successfully.';

    if (!lastChecked) {
      health = 'never_checked';
      severity = 'critical';
      detail = 'Tracker has not completed an initial scrape.';
    } else if (lastChecked && (now.getTime() - lastChecked.getTime()) > (staleAfterHours * 60 * 60 * 1000)) {
      health = 'stale';
      severity = 'warning';
      detail = `No successful check in more than ${staleAfterHours} hours.`;
    } else if (currentPrice === null) {
      health = 'price_missing';
      severity = 'critical';
      detail = 'Last scrape did not return a usable price.';
    } else if (inStock === false) {
      health = 'out_of_stock';
      severity = 'warning';
      detail = 'Product is currently reported out of stock.';
    }

    return {
      id: trackerId,
      label,
      health,
      severity,
      detail,
      last_checked: lastChecked ? lastChecked.toISOString() : null,
      check_frequency_hours: frequencyHours,
    };
  });

  const severityOrder: Record<string, number> = { critical: 0, warning: 1, ok: 2 };
  const health = healthList.sort((a: any, b: any) => {
    const orderA = severityOrder[a.severity] ?? 3;
    const orderB = severityOrder[b.severity] ?? 3;
    if (orderA !== orderB) return orderA - orderB;
    return a.label.toLowerCase().localeCompare(b.label.toLowerCase());
  });

  // Cast sql result objects to TrackedUrl shape for TS compilation
  const trackersTyped = trackers.map((t: any) => ({
    id: t.id,
    url: t.url,
    label: t.label,
    current_price: t.current_price !== null ? parseFloat(t.current_price) : null,
    previous_price: t.previous_price !== null ? parseFloat(t.previous_price) : null,
    min_price: t.min_price !== null ? parseFloat(t.min_price) : null,
    in_stock: t.in_stock,
    last_checked: t.last_checked ? new Date(t.last_checked).toISOString() : null,
    check_frequency_hours: parseInt(t.check_frequency_hours) || 24,
    status: t.status,
    alert_threshold: t.alert_threshold !== null ? parseFloat(t.alert_threshold) : null,
    pending_price: t.pending_price !== null ? parseFloat(t.pending_price) : null,
    pending_stock: t.pending_stock,
    pending_text: t.pending_text,
    last_text: t.last_text,
  }));

  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <DashboardClient
          initialTrackers={trackersTyped}
          initialSummary={summary}
          initialHealth={health as any}
          userEmail={user.email}
        />
      </div>
    </div>
  );
}
