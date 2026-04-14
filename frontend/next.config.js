/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  serverRuntimeConfig: {
    apiUrlInternal: process.env.API_URL_INTERNAL || "",
  },
  async redirects() {
    return [
      {
        source: "/stats",
        destination: "/thong-ke-tin-hieu-co-phieu-hom-nay",
        permanent: true,
      },
    ];
  },
};
module.exports = nextConfig;
