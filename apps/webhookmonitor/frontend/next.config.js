/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@devforge/core", "@devforge/ui"],
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "https://devforge-universal-backend.onrender.com";

    return [
      {
        source: "/in/:slug",
        destination: `${backendUrl}/in/:slug`,
      },
    ];
  },
};
module.exports = nextConfig;
