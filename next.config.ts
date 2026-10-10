import type { NextConfig } from "next"

// The engine API (api/index.py) answers on /api/py/*. On Vercel it runs as a
// Python function in the same deployment; in development uvicorn serves it on
// port 8000 (`npm run dev` starts both).
const API_DEV = "http://127.0.0.1:8000"

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      {
        source: "/api/py/:path*",
        destination: process.env.NODE_ENV === "development" ? `${API_DEV}/api/py/:path*` : "/api/",
      },
    ]
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ]
  },
}

export default nextConfig
