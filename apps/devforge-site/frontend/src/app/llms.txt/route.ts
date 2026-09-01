import { buildSuiteLlmsTxt } from "@devforge/core";

export const dynamic = "force-static";

export function GET() {
  const content = buildSuiteLlmsTxt().replace(
    "- Canonical URL: https://devforgeapp.pro",
    "- Canonical URL: https://tools.devforgeapp.pro",
  );

  return new Response(content, {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=3600, s-maxage=86400",
    },
  });
}
