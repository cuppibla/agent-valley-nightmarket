import type { NextConfig } from "next";

// The page is exported to static files once (bash valley.sh) and served by
// the same Python process that owns the line — one origin, one port. In dev,
// `npm run dev` on 3451 talks to that process through NEXT_PUBLIC_STAGE_ORIGIN.
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
