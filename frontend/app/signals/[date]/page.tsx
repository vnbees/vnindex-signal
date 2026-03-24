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

      <SignalTable signals={signals} runDate={date} />

      <p className="text-xs text-slate-400 mt-4">
        * PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi giờ.
      </p>
    </div>
  );
}
