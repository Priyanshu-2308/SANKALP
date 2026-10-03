/** @type {import('next').NextConfig} */
const isExport = process.env.EXPORT === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || (isExport ? "/SANKALP" : "");

const nextConfig = {
  reactStrictMode: true,
  output: isExport ? "export" : undefined,
  basePath: basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
