import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ViiStock",
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
            📊 ViiStock
          </a>
          <a href="/signals" className="text-slate-600 hover:text-slate-900 text-sm">
            Tín hiệu
          </a>
          <a href="/stats" className="text-slate-600 hover:text-slate-900 text-sm">
            Thống kê
          </a>
        </nav>
        {/* Trust Bar */}
        <div className="bg-white border-b border-slate-100 px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="text-blue-500">✓</span>
              Mô hình proprietary (độc quyền) đã được kiểm tra trên dữ liệu lịch sử VN-Index
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-blue-500">✓</span>
              Cập nhật tín hiệu hàng ngày từ 15h30–16h30
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-blue-500">✓</span>
              PnL tính từ giá thực tế (giá mở cửa T+1)
            </span>
          </div>
        </div>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
