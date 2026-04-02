import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-tv-border bg-tv-panel/30 px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-4">
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Link href="/mien-tru-trach-nhiem" className="text-tv-muted hover:text-tv-accent">
            Miễn trừ trách nhiệm
          </Link>
          <Link href="/chinh-sach-bao-mat" className="text-tv-muted hover:text-tv-accent">
            Chính sách bảo mật
          </Link>
          <Link href="/gioi-thieu" className="text-tv-muted hover:text-tv-accent">
            Giới thiệu &amp; liên hệ
          </Link>
        </nav>
        <p className="text-xs text-tv-muted leading-relaxed max-w-3xl">
          ViiStock cung cấp công cụ thông tin và thống kê lịch sử;{" "}
          <strong className="text-tv-text font-medium">không phải</strong> lời khuyên đầu tư cá nhân, dịch vụ môi giới
          hay đề nghị mua/bán chứng khoán. Bạn tự chịu rủi ro khi sử dụng dữ liệu. Kết quả trong quá khứ không báo hiệu
          kết quả tương lai.{" "}
          <Link href="/mien-tru-trach-nhiem" className="text-tv-accent hover:underline underline-offset-2">
            Đọc miễn trừ đầy đủ
          </Link>
          .
        </p>
      </div>
    </footer>
  );
}
