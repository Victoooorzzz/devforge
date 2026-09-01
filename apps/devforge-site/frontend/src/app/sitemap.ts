import type { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://tools.devforgeapp.pro',
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 1,
    },
    {
      url: 'https://tools.devforgeapp.pro/hire',
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: 'https://tools.devforgeapp.pro/terms',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    },
    {
      url: 'https://tools.devforgeapp.pro/privacy',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    },
    {
      url: 'https://tools.devforgeapp.pro/refunds',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    },
  ]
}
