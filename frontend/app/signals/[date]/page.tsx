import { notFound } from "next/navigation";
import { getSignals, type Signal } from "@/lib/api";
import { SignalTable } from "@/components/SignalTable";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface Props {
  params: { date: string };
}

export default async function SignalsDatePage({ params }: Props) {
  const { date } = params;

  // Validate date format
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    notFound();
  }

  let signals: Signal[] = [];
  try {
    signals = await getSignals(date);
  } catch {
    notFound();
  }

  const buyCount = signals.filter((s) => ["BUY_STRONG", "BUY"].includes(s.recommendation)).length;
  const avoidCount = signals.filter((s) => ["AVOID", "SELL"].includes(s.recommendation)).length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            📅 {formatDate(date)}
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {signals.length} mã phân tích · {buyCount} Mua · {avoidCount} Tránh/Bán
          </p>
        </div>
        <Link
          href="/signals"
          className="text-sm text-slate-500 hover:text-slate-700"
        >
          ← Danh sách ngày
        </Link>
      </div>

      {/* Disclaimer Card */}
      <div className="mb-4 bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 flex gap-2.5">
        <span className="text-blue-400 flex-shrink-0 mt-0.5">ℹ️</span>
        <p className="text-xs text-blue-800 leading-relaxed">
          <span className="font-medium">Mô hình phân tích kỹ thuật độc quyền</span> đã kiểm tra trên dữ liệu lịch sử VN-Index.{" "}
          Hiệu suất quá khứ không đảm bảo kết quả tương lai. Không phải lời khuyên đầu tư — luôn tự nghiên cứu và quản lý rủi ro.
        </p>
      </div>

      <SignalTable signals={signals} runDate={date} />

      <p className="text-xs text-slate-400 mt-4">
        * PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi ngày từ 15h30-16h30.
      </p>
    </div>
  );
}
