import { notFound } from "next/navigation";
import Link from "next/link";
import { getSignalDetail } from "@/lib/api";
import { RecommendationBadge } from "@/components/RecommendationBadge";
import { PnlBadge } from "@/components/PnlBadge";
import { PnlChart } from "@/components/PnlChart";
import { CorporateActionWarning } from "@/components/CorporateActionWarning";
import { formatPrice, formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface Props {
  params: { date: string; symbol: string };
}

export default async function SignalDetailPage({ params }: Props) {
  const { date, symbol } = params;

  let signal;
  try {
    signal = await getSignalDetail(date, symbol.toUpperCase());
  } catch {
    notFound();
  }

  return (
    <div className="max-w-4xl">
      {/* Breadcrumb */}
      <div className="text-sm text-slate-400 mb-4">
        <Link href="/signals" className="hover:text-slate-600">Tín hiệu</Link>
        {" / "}
        <Link href={`/signals/${date}`} className="hover:text-slate-600">{formatDate(date)}</Link>
        {" / "}
        <span className="text-slate-700 font-medium">{signal.symbol}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-800">{signal.symbol}</h1>
            <CorporateActionWarning show={signal.has_corporate_action} symbol={signal.symbol} />
          </div>
          {signal.has_corporate_action && (
            <p className="text-amber-600 text-sm mt-1">
              ⚠️ Có thể có split/dividend — cần review thủ công trước khi dùng PnL để phân tích
            </p>
          )}
        </div>
        <RecommendationBadge recommendation={signal.recommendation} size="md" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Scores */}
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Điểm tổng</h2>
          <div className="space-y-3">
            <div className="flex justify-between font-semibold">
              <span className="text-slate-700">Tổng</span>
              <span className={signal.score_total > 0 ? "text-green-700" : signal.score_total < 0 ? "text-red-700" : "text-slate-500"}>
                {signal.score_total > 0 ? `+${signal.score_total}` : signal.score_total}
              </span>
            </div>
          </div>
        </div>

        {/* Price & PnL */}
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Giá & PnL</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Giá đóng cửa ngày phân tích</span>
              <span className="text-sm font-medium">{formatPrice(signal.price_close_signal_date)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Giá mở cửa T+1 (PnL ref)</span>
              <span className="text-sm font-medium">
                {signal.price_open_t1 ? formatPrice(signal.price_open_t1) : <span className="text-slate-400">Chưa có</span>}
              </span>
            </div>
            <div className="pt-2 border-t border-slate-100 space-y-2">
              {[
                { label: "T+1", pnl: signal.pnl_d1 },
                { label: "T+5", pnl: signal.pnl_d5 },
                { label: "T+10", pnl: signal.pnl_d10 },
                { label: "T+20", pnl: signal.pnl_d20 },
              ].map(({ label, pnl }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-sm text-slate-600">{label}</span>
                  <PnlBadge pnl={pnl} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* PnL Chart */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 md:col-span-2">
          <h2 className="font-semibold text-slate-700 mb-4">Biểu đồ PnL</h2>
          <PnlChart
            symbol={signal.symbol}
            pnlD1={signal.pnl_d1}
            pnlD5={signal.pnl_d5}
            pnlD10={signal.pnl_d10}
            pnlD20={signal.pnl_d20}
          />
          <p className="text-xs text-slate-400 mt-2">
            * PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi ngày từ 15h30-16h30.
          </p>
        </div>

        {/* Technical Details */}
        {signal.detail_technical && (
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-700 mb-4">Kỹ thuật</h2>
            <div className="space-y-2 text-sm">
              {Object.entries(signal.detail_technical).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-slate-500">{k}</span>
                  <span className="font-medium">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Financial Details */}
        {signal.detail_financial && (
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-700 mb-4">Tài chính</h2>
            <div className="space-y-2 text-sm">
              {Object.entries(signal.detail_financial).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-slate-500">{k}</span>
                  <span className="font-medium">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
