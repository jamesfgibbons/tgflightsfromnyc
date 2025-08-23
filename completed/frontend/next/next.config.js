/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: [],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_CF_DOMAIN: process.env.NEXT_PUBLIC_CF_DOMAIN,
  },
}

module.exports = nextConfig 