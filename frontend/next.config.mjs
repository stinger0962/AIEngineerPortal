/** @type {import('next').NextConfig} */
const nextConfig = {
  typedRoutes: false,
  // Keep local/product build artifacts separate from the personal portal.
  distDir: process.env.NEXT_PUBLIC_PRODUCT_MODE === "paid" ? ".next-paid" : ".next"
};

export default nextConfig;
