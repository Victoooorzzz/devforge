import { NextRequest, NextResponse } from 'next/server';
import { getServerUser } from '../../../lib/auth';
import { sql } from '../../../lib/db';

export async function GET(request: NextRequest) {
  const user = getServerUser();
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const getSummary = searchParams.get('summary') === 'true';
  const getHealth = searchParams.get('health') === 'true';

  try {
    // 1. Fetch trackers
    const trackers = await sql`
      SELECT * FROM tracked_urls
      WHERE user_id = ${user.userId}
        AND deleted_at IS NULL
      ORDER BY created_at DESC
    `;

    const result: any = { trackers };

    // 2. Compute Summary if requested
    if (getSummary) {
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

      result.summary = {
        total_trackers: trackers.length,
        active_trackers: active.length,
        price_drop_count: priceDropCount,
        out_of_stock_count: outOfStockCount,
        potential_savings: parseFloat(potentialSavings.toFixed(2)),
      };
    }

    // 3. Compute Health if requested
    if (getHealth) {
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
        } else if ((now.getTime() - lastChecked.getTime()) > (staleAfterHours * 60 * 60 * 1000)) {
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
      result.health = healthList.sort((a: any, b: any) => {
        const orderA = severityOrder[a.severity] ?? 3;
        const orderB = severityOrder[b.severity] ?? 3;
        if (orderA !== orderB) return orderA - orderB;
        return a.label.toLowerCase().localeCompare(b.label.toLowerCase());
      });
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error reading tracked urls:", error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
