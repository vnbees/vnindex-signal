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
      <div className="text-xs text-tv-muted mb-4 tracking-wide">
        <Link href="/signals" className="hover:text-tv-accent">
          Tín hiệu
        </Link>
        <span className="mx-1.5 text-tv-border">/</span>
        <Link href={`/signals/${date}`} className="hover:text-tv-accent">
          {formatDate(date)}
        </Link>
        <span className="mx-1.5 text-tv-border">/</span>
        <span className="text-tv-text font-medium">{signal.symbol}</span>
      </div>

      <div className="flex items-start justify-between mb-6 gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold text-tv-text tracking-tight">{signal.symbol}</h1>
            <CorporateActionWarning show={signal.has_corporate_action} symbol={signal.symbol} />
          </div>
          {signal.has_corporate_action && (
            <p className="text-amber-400/90 text-sm mt-1">
              Có thể có split/dividend — cần review thủ công trước khi dùng PnL để phân tích
            </p>
          )}
        </div>
        <RecommendationBadge recommendation={signal.recommendation} size="md" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="tv-panel p-5">
          <h2 className="tv-section-title mb-4">Điểm tổng</h2>
          <div className="space-y-3">
            <div className="flex justify-between font-semibold">
              <span className="text-tv-text">Tổng</span>
              <span
                className={
                  signal.score_total > 0
                    ? "text-tv-up"
                    : signal.score_total < 0
                      ? "text-tv-down"
                      : "text-tv-muted"
                }
              >
                {signal.score_total > 0 ? `+${signal.score_total}` : signal.score_total}
              </span>
            </div>
          </div>
        </div>

        <div className="tv-panel p-5">
          <h2 className="tv-section-title mb-4">Giá &amp; PnL</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-tv-muted">Giá đóng cửa ngày phân tích</span>
              <span className="text-sm font-medium text-tv-text">{formatPrice(signal.price_close_signal_date)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-tv-muted">Giá mở cửa T+1 (PnL ref)</span>
              <span className="text-sm font-medium text-tv-text">
                {signal.price_open_t1 ? formatPrice(signal.price_open_t1) : <span className="text-tv-muted">Chưa có</span>}
              </span>
            </div>
            <div className="pt-2 border-t border-tv-border space-y-2">
              {[
                { label: "T+3", pnl: signal.pnl_d3 },
              ].map(({ label, pnl }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-sm text-tv-muted">{label}</span>
                  <PnlBadge pnl={pnl} />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="tv-panel p-5 md:col-span-2">
          <h2 className="tv-section-title mb-4">Biểu đồ PnL</h2>
          <PnlChart
            symbol={signal.symbol}
            pnlD3={signal.pnl_d3}
          />
          <p className="text-xs text-tv-muted mt-2">
            * PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi ngày từ 15h30-16h30.
          </p>
        </div>

        {signal.detail_technical && (
          <div className="tv-panel p-5">
            <h2 className="tv-section-title mb-4">Kỹ thuật</h2>
            <div className="space-y-2 text-sm">
              {Object.entries(signal.detail_technical).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <span className="text-tv-muted shrink-0">{k}</span>
                  <span className="font-medium text-tv-text text-right">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {signal.detail_financial && (
          <div className="tv-panel p-5">
            <h2 className="tv-section-title mb-4">Tài chính</h2>
            <div className="space-y-2 text-sm">
              {Object.entries(signal.detail_financial).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <span className="text-tv-muted shrink-0">{k}</span>
                  <span className="font-medium text-tv-text text-right">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
