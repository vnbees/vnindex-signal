import { notFound } from "next/navigation";
import { getSignals, type Signal } from "@/lib/api";
import { SignalTable } from "@/components/SignalTable";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

export const dynamic = "force-dynamic";

const PORTFOLIO_LOW = "low_cap";

interface Props {
  params: { date: string };
}

export default async function VonItDatePage({ params }: Props) {
  const { date } = params;

  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    notFound();
  }

  let signals: Signal[] = [];
  try {
    signals = await getSignals(date, undefined, "score_total", "desc", PORTFOLIO_LOW);
  } catch {
    notFound();
  }

  const buyCount = signals.filter((s) => ["BUY_STRONG", "BUY"].includes(s.recommendation)).length;
  const avoidCount = signals.filter((s) => ["AVOID", "SELL"].includes(s.recommendation)).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-tv-text tracking-tight">{formatDate(date)}</h1>
          <p className="text-tv-muted text-sm mt-1">
            Danh mục vốn ít · {signals.length} mã · <span className="text-tv-up">{buyCount} Mua</span>
            {" · "}
            <span className="text-tv-down">{avoidCount} Tránh/Bán</span>
          </p>
        </div>
        <Link
          href="/danh-muc-von-it"
          className="text-sm text-tv-muted hover:text-tv-accent transition-colors"
        >
          ← Danh sách ngày
        </Link>
      </div>

      <div className="mb-4 rounded-lg border border-tv-info-border bg-tv-info-bg px-4 py-3 flex items-center gap-2.5">
        <span className="text-tv-accent flex-shrink-0">ℹ</span>
        <p className="text-xs text-tv-text/90 leading-relaxed">
          Universe: vốn hoá tối thiểu, thanh khoản trung bình theo cửa sổ phiên, giá đóng ≤ 30k (nghìn VND). Cùng mô hình
          điểm với backtest; không phải khuyến nghị đầu tư.
        </p>
      </div>

      <SignalTable signals={signals} runDate={date} detailBasePath="/danh-muc-von-it" />

      <p className="text-xs text-tv-muted mt-4">
        * PnL tính từ giá mở cửa T+1. Cập nhật mỗi ngày từ 15h30-16h30.
      </p>
    </div>
  );
}
