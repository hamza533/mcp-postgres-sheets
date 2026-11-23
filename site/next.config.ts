import type { NextConfig } from "next";

// Static export: the site is plain HTML/CSS/JS in out/, hostable anywhere (Vercel Hobby, GitHub Pages…).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  poweredByHeader: false,
};

export default nextConfig;
