import type { NextConfig } from "next";
import withBundleAnalyzer from "@next/bundle-analyzer";

const nextConfig: NextConfig = {
  // Output: standard static export + server-side rendering
  trailingSlash: false,
  // Environment variables passed to client
  env: {
    MALT_RADAR_API_BASE_URL: process.env.MALT_RADAR_API_BASE_URL || 'http://localhost:8080',
  },
  // Images: use remotePatterns for whisky images from backend
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'maltradar.com',
        pathname: '/**',
      },
    ],
  },
  // React strict mode for development
  reactStrictMode: true,
  // Turbopack for dev
  experimental: {
    // turbo: {}, // enable if needed
  },
};

// Bundle analyzer — only active when ANALYZE=true (ESM-compatible wrapper)
const analyze = process.env.ANALYZE === 'true';
export default withBundleAnalyzer({ enabled: analyze })(nextConfig);
