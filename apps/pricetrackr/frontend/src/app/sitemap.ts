import type { MetadataRoute } from 'next';
import { sql } from '../lib/db';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://pricetrackr.devforgeapp.pro';

  // Base routes
  const routes = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily' as const,
      priority: 1.0,
    },
    {
      url: `${baseUrl}/p`,
      lastModified: new Date(),
      changeFrequency: 'daily' as const,
      priority: 0.8,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: 'yearly' as const,
      priority: 0.3,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: 'yearly' as const,
      priority: 0.3,
    },
    {
      url: `${baseUrl}/refunds`,
      lastModified: new Date(),
      changeFrequency: 'yearly' as const,
      priority: 0.3,
    },
  ];

  try {
    // Fetch all public product slugs
    const publicProducts = await sql`
      SELECT slug, last_checked, created_at FROM tracked_urls
      WHERE is_public = TRUE AND status != 'deleted'
    `;

    const productRoutes = publicProducts.map((p: any) => ({
      url: `${baseUrl}/p/${p.slug}`,
      lastModified: p.last_checked ? new Date(p.last_checked) : new Date(p.created_at || Date.now()),
      changeFrequency: 'hourly' as const,
      priority: 0.6,
    }));

    return [...routes, ...productRoutes];
  } catch (error) {
    console.error("Error generating sitemap dynamically:", error);
    return routes;
  }
}
