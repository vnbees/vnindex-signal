/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  serverRuntimeConfig: {
    apiUrlInternal: process.env.API_URL_INTERNAL || "",
  },
};
module.exports = nextConfig;
