import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Miễn trừ trách nhiệm",
  description:
    "ViiStock không phải tư vấn đầu tư hay môi giới chứng khoán. Thông tin mang tính tham khảo; người dùng tự chịu rủi ro.",
};

export default function MienTruPage() {
  return (
    <article className="max-w-3xl space-y-6 text-sm text-tv-text leading-relaxed">
      <div className="text-xs text-tv-muted">
        <Link href="/thong-ke-tin-hieu-co-phieu-hom-nay" className="hover:text-tv-accent">
          Trang chủ thống kê
        </Link>
        <span className="mx-1.5 text-tv-border">/</span>
        <span className="text-tv-text">Miễn trừ trách nhiệm</span>
      </div>
      <h1 className="text-2xl font-semibold text-tv-text tracking-tight">Miễn trừ trách nhiệm</h1>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Không phải tư vấn đầu tư</h2>
        <p className="text-tv-muted">
          Nội dung trên ViiStock (tín hiệu, thống kê PnL, biểu đồ, gợi ý phân bổ vốn, v.v.) chỉ nhằm mục đích{" "}
          <strong className="text-tv-text">thông tin và giáo dục</strong>, mang tính <strong className="text-tv-text">tham khảo</strong>.
          Đây <strong className="text-tv-text">không phải</strong> là lời khuyên đầu tư cá nhân, khuyến nghị mua hoặc bán chứng
          khoán, hay dịch vụ tư vấn tài chính theo quy định pháp luật. Chúng tôi không phải công ty chứng khoán, không hành nghề
          môi giới và không nhận ủy thác đầu tư.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Rủi ro và kết quả lịch sử</h2>
        <p className="text-tv-muted">
          Đầu tư chứng khoán có rủi ro, có thể mất vốn. Mọi số liệu hiệu suất, PnL hoặc thống kê được trình bày dựa trên dữ liệu
          lịch sử và giả định mô hình — <strong className="text-tv-text">không đảm bảo</strong> hoặc dự báo lợi nhuận trong tương lai.
          Thị trường thay đổi; kết quả trong quá khứ không báo hiệu kết quả tương lai.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Độ chính xác của dữ liệu</h2>
        <p className="text-tv-muted">
          Chúng tôi cố gắng xử lý dữ liệu nhất quán (ví dụ điều chỉnh giá, sự kiện doanh nghiệp) nhưng không cam kết dữ liệu
          không có sai sót hoặc trễ. Người dùng nên tự kiểm chứng trước khi ra quyết định tài chính.
        </p>
      </section>

      <section className="tv-panel p-5 space-y-3">
        <h2 className="text-base font-semibold text-tv-text">Giới hạn trách nhiệm</h2>
        <p className="text-tv-muted">
          Trong phạm vi pháp luật cho phép, ViiStock và người vận hành không chịu trách nhiệm đối với bất kỳ tổn thất trực tiếp
          hay gián tiếp nào phát sinh từ việc sử dụng hoặc tin cậy vào nội dung trên website.
        </p>
      </section>

      <p className="text-xs text-tv-muted">
        Cập nhật gần nhất theo phiên bản công khai của website. Xem thêm{" "}
        <Link href="/chinh-sach-bao-mat" className="text-tv-accent hover:underline underline-offset-2">
          Chính sách bảo mật
        </Link>{" "}
        và{" "}
        <Link href="/gioi-thieu" className="text-tv-accent hover:underline underline-offset-2">
          Giới thiệu
        </Link>
        .
      </p>
    </article>
  );
}
