/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server bundle (.next/standalone) for a slim Docker image.
  output: "standalone",
};

module.exports = nextConfig;
