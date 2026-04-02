import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Chính sách bảo mật",
  description:
    "Cách ViiStock thu thập và sử dụng dữ liệu: phản hồi người dùng, Google Analytics 4, cookie trình duyệt.",
};

export default function ChinhSachBaoMatPage() {
  return (
    <article className="max-w-3xl space-y-6 text-sm text-tv-text leading-relaxed">
      <div className="text-xs text-tv-muted">
        <Link href="/thong-ke-tin-hieu-co-phieu-hom-nay" className="hover:text-tv-accent">
          Trang chủ thống kê
        </Link>
        <span className="mx-1.5 text-tv-border">/</span>
        <span className="text-tv-text">Chính sách bảo mật</span>
      </div>
      <h1 className="text-2xl font-semibold text-tv-text tracking-tight">Chính sách bảo mật</h1>
      <p className="text-tv-muted">
        Chính sách này mô tả thông tin có thể được thu thập khi bạn sử dụng website ViiStock và mục đích sử dụng.
      </p>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Người thu thập</h2>
        <p className="text-tv-muted">
          Website được vận hành bởi cá nhân chủ sở hữu dự án ViiStock (không phải tổ chức tài chính). Để liên hệ, xem trang{" "}
          <Link href="/gioi-thieu" className="text-tv-accent hover:underline underline-offset-2">
            Giới thiệu &amp; liên hệ
          </Link>
          .
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Dữ liệu bạn gửi chủ động</h2>
        <ul className="list-disc pl-5 space-y-2 text-tv-muted">
          <li>
            <strong className="text-tv-text">Góp ý / phản hồi:</strong> Khi gửi form phản hồi, chúng tôi có thể lưu nội dung tin
            nhắn, tên hoặc thông tin liên hệ bạn nhập (nếu có), và địa chỉ trang bạn đang xem. Mục đích: xử lý phản hồi và cải thiện
            dịch vụ.
          </li>
        </ul>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Google Analytics 4 (GA4)</h2>
        <p className="text-tv-muted">
          Chúng tôi có thể dùng Google Analytics 4 để hiểu cách người dùng tương tác với website (ví dụ số lượt xem, luồng trang).
          Google có thể đặt cookie và xử lý dữ liệu theo{" "}
          <a
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="text-tv-accent hover:underline underline-offset-2"
          >
            chính sách của Google
          </a>
          . Bạn có thể cài đặt trình duyệt hoặc tiện ích chặn cookie theo lựa chọn cá nhân.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Cookie và lưu cục bộ</h2>
        <p className="text-tv-muted">
          Website có thể lưu tùy chọn giao diện (sáng/tối) trong trình duyệt của bạn (localStorage) để trải nghiệm nhất quán. Các
          cookie hoặc công nghệ tương tự từ bên thứ ba (như Google) có thể được dùng khi bạn đồng ý hoặc theo cài đặt trình duyệt.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Lưu trữ và bảo mật</h2>
        <p className="text-tv-muted">
          Phản hồi có thể được lưu trên máy chủ do nhà cung cấp hosting quản lý. Chúng tôi áp dụng các biện pháp hợp lý để hạn chế
          truy cập trái phép; không có hệ thống nào an toàn tuyệt đối.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Thay đổi chính sách</h2>
        <p className="text-tv-muted">
          Chính sách có thể được cập nhật. Phiên bản hiện tại luôn có tại địa chỉ này. Tiếp tục sử dụng website sau khi thay đổi
          nghĩa là bạn chấp nhận các điều khoản mới trong phạm vi áp dụng.
        </p>
      </section>

      <p className="text-xs text-tv-muted">
        Xem{" "}
        <Link href="/mien-tru-trach-nhiem" className="text-tv-accent hover:underline underline-offset-2">
          Miễn trừ trách nhiệm
        </Link>{" "}
        về nội dung đầu tư.
      </p>
    </article>
  );
}
