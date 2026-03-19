import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // output: "standalone" removed — Vercel handles builds natively
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
