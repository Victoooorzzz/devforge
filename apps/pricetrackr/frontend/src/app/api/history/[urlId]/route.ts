import { NextRequest, NextResponse } from 'next/server';
import { getServerUser } from '../../../../lib/auth';
import { sql } from '../../../../lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: { urlId: string } }
) {
  const user = getServerUser();
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const trackerId = parseInt(params.urlId);
  if (isNaN(trackerId)) {
    return NextResponse.json({ error: 'Invalid tracker ID' }, { status: 400 });
  }

  try {
    // Verify tracker ownership
    const tracker = await sql`
      SELECT id FROM tracked_urls
      WHERE id = ${trackerId} AND user_id = ${user.userId}
      LIMIT 1
    `;

    if (tracker.length === 0) {
      return NextResponse.json({ error: 'Tracker not found' }, { status: 404 });
    }

    const history = await sql`
      SELECT price, in_stock, recorded_at
      FROM price_history
      WHERE tracker_id = ${trackerId}
      ORDER BY recorded_at ASC
      LIMIT 30
    `;

    return NextResponse.json(history);
  } catch (error) {
    console.error("Error reading price history:", error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
