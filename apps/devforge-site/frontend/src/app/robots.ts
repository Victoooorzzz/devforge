import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/llms.txt", "/terms", "/privacy", "/refunds", "/hire"],
        disallow: ["/api", "/api/*"],
      },
      {
        userAgent: [
          "GPTBot",
          "ChatGPT-User",
          "Claude-Web",
          "ClaudeBot",
          "PerplexityBot",
          "GeminiBot",
          "Google-Extended",
          "facebookexternalhit",
          "Applebot-Extended",
        ],
        allow: ["/", "/llms.txt", "/terms", "/privacy", "/refunds", "/hire"],
        disallow: ["/api", "/api/*"],
      },
    ],
    sitemap: "https://devforgeapp.pro/sitemap.xml",
  };
}
