import type { Metadata } from "next";
import Script from "next/script";
import { IBM_Plex_Sans } from "next/font/google";
import { AppNav } from "@/components/AppNav";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { SiteFooter } from "@/components/SiteFooter";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

const ibmSans = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ViiStock",
  description:
    "Công cụ thống kê tín hiệu cổ phiếu HOSE: dữ liệu lịch sử, PnL tham khảo. Không phải lời khuyên đầu tư hay môi giới.",
  verification: {
    google: "wl1UgbSWQ9JFEANdXeE_wX5XbqSk4b2ugKWGV24LucQ",
  },
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      {
        url: "/icons/icon-32.png",
        sizes: "32x32",
        type: "image/png",
        media: "(prefers-color-scheme: light)",
      },
      {
        url: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        media: "(prefers-color-scheme: light)",
      },
      {
        url: "/icons/icon-192-inverted.png",
        sizes: "192x192",
        type: "image/png",
        media: "(prefers-color-scheme: dark)",
      },
    ],
    apple: [{ url: "/icons/icon-180.png", sizes: "180x180", type: "image/png" }],
    shortcut: ["/favicon.ico"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const gaId = process.env.NEXT_PUBLIC_GA_ID?.trim();
  const googleAdsId = (
    process.env.NEXT_PUBLIC_GOOGLE_ADS_ID ?? "AW-880926849"
  ).trim();
  const gtagLoaderId = gaId || googleAdsId;
  const gtagInitScript =
    gtagLoaderId &&
    `
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                ${gaId ? `gtag('config', ${JSON.stringify(gaId)});` : ""}
                ${googleAdsId ? `gtag('config', ${JSON.stringify(googleAdsId)});` : ""}
              `.trim();

  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('vii-theme');document.documentElement.setAttribute('data-theme',t==='light'||t==='dark'?t:'dark');}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`,
          }}
        />
        {gtagLoaderId && gtagInitScript && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gtagLoaderId}`}
              strategy="afterInteractive"
            />
            <Script id="google-tags" strategy="afterInteractive">
              {gtagInitScript}
            </Script>
          </>
        )}
      </head>
      <body className={`${ibmSans.className} min-h-screen flex flex-col bg-tv-bg antialiased tabular-nums`}>
        <header className="border-b border-tv-border bg-tv-bg px-4 py-3">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
            <AppNav />
            <ThemeToggle />
          </div>
        </header>
        <div className="border-b border-tv-border bg-tv-panel/50 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-tv-muted">
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">•</span>
              Mô hình thống kê riêng; kết quả hiển thị dựa trên dữ liệu lịch sử — không dự báo hiệu suất tương lai
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">•</span>
              Cập nhật tín hiệu hàng ngày (khung giờ hậu phiên, tham khảo)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">•</span>
              PnL minh họa theo giá thực tế (ví dụ giá mở cửa T+1), mang tính tham khảo
            </span>
          </div>
        </div>
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6 text-tv-text">{children}</main>
        <SiteFooter />
        <FeedbackWidget />
      </body>
    </html>
  );
}
