const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@devforge/core", "@devforge/ui"],
  experimental: {
    turbo: {
      root: path.join(__dirname, '../../../')
    }
  }
};

module.exports = nextConfig;
