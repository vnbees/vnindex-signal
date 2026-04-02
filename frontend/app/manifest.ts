import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ViiStock",
    short_name: "ViiStock",
    description: "Thống kê tín hiệu cổ phiếu HOSE (tham khảo, không phải tư vấn đầu tư).",
    start_url: "/",
    display: "standalone",
    background_color: "#131722",
    theme_color: "#131722",
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
