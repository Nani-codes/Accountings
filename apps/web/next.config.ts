import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produce a minimal standalone server bundle for Docker/Coolify.
  output: "standalone",
};

export default nextConfig;
