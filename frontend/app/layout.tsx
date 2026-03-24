import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VNINDEX Signal",
  description: "Tín hiệu mua/bán cổ phiếu HOSE",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-slate-50">
        <nav className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-6">
          <a href="/" className="font-bold text-lg text-slate-800">
            📊 VNINDEX Signal
          </a>
          <a href="/signals" className="text-slate-600 hover:text-slate-900 text-sm">
            Tín hiệu
          </a>
          <a href="/stats" className="text-slate-600 hover:text-slate-900 text-sm">
            Thống kê
          </a>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
