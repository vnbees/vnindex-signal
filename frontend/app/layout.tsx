import type { Metadata } from "next";
import Script from "next/script";
import { IBM_Plex_Sans } from "next/font/google";
import { AppNav } from "@/components/AppNav";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

const ibmSans = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ViiStock",
  description: "Tín hiệu mua/bán cổ phiếu HOSE",
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
  const gaId = process.env.NEXT_PUBLIC_GA_ID;

  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('vii-theme');document.documentElement.setAttribute('data-theme',t==='light'||t==='dark'?t:'dark');}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`,
          }}
        />
        {gaId && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${gaId}');
              `}
            </Script>
          </>
        )}
      </head>
      <body className={`${ibmSans.className} min-h-screen bg-tv-bg antialiased tabular-nums`}>
        <header className="border-b border-tv-border bg-tv-bg px-4 py-3">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
            <AppNav />
            <ThemeToggle />
          </div>
        </header>
        <div className="border-b border-tv-border bg-tv-panel/50 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-tv-muted">
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">✓</span>
              Mô hình proprietary (độc quyền) đã được kiểm tra trên dữ liệu lịch sử VN-Index
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">✓</span>
              Cập nhật tín hiệu hàng ngày từ 15h30–16h30
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-tv-accent">✓</span>
              PnL tính từ giá thực tế (giá mở cửa T+1)
            </span>
          </div>
        </div>
        <main className="max-w-7xl mx-auto px-4 py-6 text-tv-text">{children}</main>
        <FeedbackWidget />
      </body>
    </html>
  );
}
