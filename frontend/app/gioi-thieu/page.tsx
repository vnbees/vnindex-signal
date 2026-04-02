import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Giới thiệu & liên hệ",
  description:
    "ViiStock: công cụ thống kê tín hiệu cổ phiếu HOSE. Thông tin liên hệ và mục đích dự án.",
};

export default function GioiThieuPage() {
  return (
    <article className="max-w-3xl space-y-6 text-sm text-tv-text leading-relaxed">
      <div className="text-xs text-tv-muted">
        <Link href="/thong-ke-tin-hieu-co-phieu-hom-nay" className="hover:text-tv-accent">
          Trang chủ thống kê
        </Link>
        <span className="mx-1.5 text-tv-border">/</span>
        <span className="text-tv-text">Giới thiệu</span>
      </div>
      <h1 className="text-2xl font-semibold text-tv-text tracking-tight">Giới thiệu &amp; liên hệ</h1>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">ViiStock là gì?</h2>
        <p className="text-tv-muted">
          ViiStock là website công khai cung cấp <strong className="text-tv-text">công cụ thông tin</strong> xoay quanh tín hiệu
          và thống kê lịch sử trên cổ phiếu niêm yết HOSE: bảng tín hiệu theo ngày, thống kê PnL/win rate, tìm kiếm theo mã, và
          gợi ý phân bổ vốn mang tính minh họa. Mục tiêu là giúp người dùng tự tra cứu và học từ dữ liệu —{" "}
          <strong className="text-tv-text">không</strong> thay thế nghiên cứu riêng hay tư vấn chuyên nghiệp.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Ai vận hành?</h2>
        <p className="text-tv-muted">
          Dự án do <strong className="text-tv-text">cá nhân</strong> xây dựng và vận hành, không đại diện cho công ty chứng khoán
          hay tổ chức tài chính. Không cung cấp dịch vụ môi giới, quản lý danh mục hay tư vấn đầu tư có thu phí theo quy định pháp
          lý về chứng khoán.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Liên hệ</h2>
        <p className="text-tv-muted">
          Bạn có thể gửi góp ý, báo lỗi hoặc câu hỏi qua <strong className="text-tv-text">widget &quot;Góp ý&quot;</strong> trên
          website (biểu tượng ở góc màn hình). Nội dung gửi đi được mô tả trong{" "}
          <Link href="/chinh-sach-bao-mat" className="text-tv-accent hover:underline underline-offset-2">
            Chính sách bảo mật
          </Link>
          .
        </p>
      </section>

      <p className="text-xs text-tv-muted">
        <Link href="/mien-tru-trach-nhiem" className="text-tv-accent hover:underline underline-offset-2">
          Miễn trừ trách nhiệm
        </Link>
      </p>
    </article>
  );
}
