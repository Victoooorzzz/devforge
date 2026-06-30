import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';

export async function POST(request: NextRequest) {
  try {
    const { secret, slug } = await request.json();
    const expectedSecret = process.env.REVALIDATE_SECRET || process.env.JWT_SECRET || 'change-me-in-production';

    if (secret !== expectedSecret) {
      return NextResponse.json({ error: 'Unauthorized revalidation' }, { status: 401 });
    }

    if (slug) {
      revalidatePath(`/p/${slug}`);
      revalidatePath('/p');
      return NextResponse.json({ revalidated: true, slug });
    }

    return NextResponse.json({ error: 'Missing slug' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
