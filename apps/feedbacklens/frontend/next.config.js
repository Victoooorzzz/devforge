const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@devforge/core", "@devforge/ui"],
  output: "export"
};

module.exports = nextConfig;
