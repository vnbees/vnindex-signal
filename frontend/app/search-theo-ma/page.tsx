import Link from "next/link";
import { RecommendationBadge } from "@/components/RecommendationBadge";
import { searchSignalsBySymbol, type SymbolSearchResult } from "@/lib/api";
import { formatDate, formatPnl, formatPrice, getPnlClass } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: {
    symbol?: string;
  };
}

export default async function SearchTheoMaPage({ searchParams }: Props) {
  const symbol = (searchParams.symbol || "").trim().toUpperCase();
  let searchData: SymbolSearchResult | null = null;
  let searchError: string | null = null;

  if (symbol) {
    try {
      searchData = await searchSignalsBySymbol(symbol, 30);
    } catch {
      searchError = "Không lấy được dữ liệu search theo mã.";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-tv-text tracking-tight">Search theo mã cổ phiếu</h1>
          <p className="text-sm text-tv-muted mt-1">Tra cứu tín hiệu và thống kê theo từng mã cổ phiếu.</p>
        </div>
      </div>

      <div className="tv-panel p-4">
        <h2 className="tv-section-title mb-3">Search theo mã cổ phiếu</h2>
        <form method="GET" className="flex flex-wrap items-end gap-3">
          <label className="min-w-[220px] flex-1">
            <span className="text-xs text-tv-muted">Mã cổ phiếu</span>
            <input
              type="text"
              name="symbol"
              defaultValue={symbol}
              placeholder="VD: FPT, HPG..."
              className="mt-1 w-full rounded-md border border-tv-border bg-tv-panel px-3 py-2 text-sm text-tv-text outline-none focus:border-tv-accent"
            />
          </label>
          <button
            type="submit"
            className="rounded-md bg-tv-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Xem kết quả
          </button>
        </form>
      </div>

      <div className="tv-panel p-4">
        <h2 className="tv-section-title mb-3">Thống kê liên quan tới mã</h2>
        {!symbol ? (
          <p className="text-sm text-tv-muted">Nhập mã để xem tín hiệu và thống kê.</p>
        ) : searchError ? (
          <p className="text-sm text-tv-down">{searchError}</p>
        ) : !searchData || !searchData.stats ? (
          <p className="text-sm text-tv-muted">Không có dữ liệu cho mã này.</p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 text-sm">
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">Tổng tín hiệu</p>
                <p className="font-semibold text-tv-text">{searchData.stats.total_signals}</p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">BUY_STRONG</p>
                <p className="font-semibold text-tv-text">{searchData.stats.buy_strong_count}</p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">BUY</p>
                <p className="font-semibold text-tv-text">{searchData.stats.buy_count}</p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">HOLD</p>
                <p className="font-semibold text-tv-text">{searchData.stats.hold_count}</p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">Winrate T+20</p>
                <p className="font-semibold text-tv-text">
                  {searchData.stats.winrate_d20 !== null ? `${searchData.stats.winrate_d20}%` : "—"}
                </p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">Winrate T+3</p>
                <p className="font-semibold text-tv-text">
                  {searchData.stats.winrate_d3 !== null ? `${searchData.stats.winrate_d3}%` : "—"}
                </p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">PnL TB T+3</p>
                <p className={`font-semibold ${getPnlClass(searchData.stats.avg_pnl_d3)}`}>
                  {formatPnl(searchData.stats.avg_pnl_d3)}
                </p>
              </div>
              <div className="rounded border border-tv-border p-2">
                <p className="text-tv-muted text-xs">PnL TB T+10</p>
                <p className={`font-semibold ${getPnlClass(searchData.stats.avg_pnl_d10)}`}>
                  {formatPnl(searchData.stats.avg_pnl_d10)}
                </p>
              </div>
            </div>
            <div className="overflow-x-auto rounded-lg border border-tv-border">
              <table className="min-w-full text-sm">
                <thead className="border-b border-tv-border tv-table-head">
                  <tr>
                    <th className="px-3 py-2 text-left">Ngày</th>
                    <th className="px-3 py-2 text-left">Mã</th>
                    <th className="px-3 py-2 text-left">KN</th>
                    <th className="px-3 py-2 text-right">Giá đóng</th>
                    <th className="px-3 py-2 text-right">T+3</th>
                    <th className="px-3 py-2 text-right">T+10</th>
                    <th className="px-3 py-2 text-right">T+20</th>
                  </tr>
                </thead>
                <tbody>
                  {searchData.signals.map((s) => (
                    <tr key={s.id} className="border-b border-tv-border/60">
                      <td className="px-3 py-2 text-tv-muted">{formatDate(s.run_date)}</td>
                      <td className="px-3 py-2">
                        <Link className="text-tv-accent hover:underline" href={`/signals/${s.run_date}/${s.symbol}`}>
                          {s.symbol}
                        </Link>
                      </td>
                      <td className="px-3 py-2">
                        <RecommendationBadge recommendation={s.recommendation} />
                      </td>
                      <td className="px-3 py-2 text-right">{formatPrice(s.price_close_signal_date)}</td>
                      <td className={`px-3 py-2 text-right ${getPnlClass(s.pnl_d3)}`}>{formatPnl(s.pnl_d3)}</td>
                      <td className={`px-3 py-2 text-right ${getPnlClass(s.pnl_d10)}`}>{formatPnl(s.pnl_d10)}</td>
                      <td className={`px-3 py-2 text-right ${getPnlClass(s.pnl_d20)}`}>{formatPnl(s.pnl_d20)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
