import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

// Turbopack must resolve deps from this app dir, not parent apps/
const appRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: appRoot,
  },
};

export default nextConfig;
