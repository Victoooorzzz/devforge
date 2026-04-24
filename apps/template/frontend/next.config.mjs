/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@devforge/ui", "@devforge/core"],
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
