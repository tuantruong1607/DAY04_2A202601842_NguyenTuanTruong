import type { NextConfig } from "next";

const pythonApi = process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${pythonApi}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
