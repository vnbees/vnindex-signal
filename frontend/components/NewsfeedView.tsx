import { getNewfeeds, type NewfeedItem } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";

function formatCreatedAt(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(new Date(iso));
}

type HorizonStats = {
  validCount: number;
  winCount: number;
  winratePct: number | null;
  avgProfitPct: number | null;
};

function calcHorizonStats(
  items: NewfeedItem[],
  key: "pnl_3d_pct" | "pnl_5d_pct" | "pnl_10d_pct"
): HorizonStats {
  const values = items
    .flatMap((item) => item.buy_signals)
    .map((sig) => sig[key])
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const validCount = values.length;
  if (validCount === 0) {
    return { validCount: 0, winCount: 0, winratePct: null, avgProfitPct: null };
  }
  const winCount = values.filter((v) => v > 0).length;
  const winratePct = (winCount / validCount) * 100;
  const avgProfitPct = values.reduce((sum, v) => sum + v, 0) / validCount;
  return { validCount, winCount, winratePct, avgProfitPct };
}

function StatChip({ label, stats }: { label: string; stats: HorizonStats }) {
  const fmtPct = (v: number | null) => (v == null ? "--" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`);
  return (
    <div className="rounded-md border border-tv-border bg-tv-panel px-3 py-2 text-sm">
      <p className="font-medium text-tv-text">{label}</p>
      <p className="mt-1 text-xs text-tv-muted">
        Winrate: {stats.winCount}/{stats.validCount} ({fmtPct(stats.winratePct)})
      </p>
      <p className={`text-xs ${stats.avgProfitPct == null ? "text-tv-muted" : stats.avgProfitPct >= 0 ? "text-tv-up" : "text-tv-down"}`}>
        Avg Profit: {fmtPct(stats.avgProfitPct)}
      </p>
    </div>
  );
}

function BuySignalsBlock({ item }: { item: NewfeedItem }) {
  if (!item.buy_signals.length) {
    return <p className="text-sm text-tv-muted">Không có mã mua hợp lệ.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {item.buy_signals.map((sig, idx) => {
        const pnlClass = (value?: number | null) =>
          value == null ? "text-tv-muted" : value >= 0 ? "text-tv-up" : "text-tv-down";
        const fmtPct = (value?: number | null) =>
          value == null ? "--" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;

        return (
          <div
            key={`${item.id}-${sig.symbol}-${idx}`}
            className="rounded-md border border-tv-border bg-tv-panel px-2.5 py-1.5 text-sm"
            title={sig.sector ?? undefined}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-tv-text">{sig.symbol}</span>
              {typeof sig.rank === "number" ? (
                <span className="text-xs text-tv-muted">#{sig.rank}</span>
              ) : null}
              {sig.price != null ? (
                <span className="text-xs text-tv-muted">Giá vào: {formatPrice(sig.price)} đ</span>
              ) : null}
              {sig.current_price != null ? (
                <span className="text-xs text-tv-text">Hiện tại: {formatPrice(sig.current_price)} đ</span>
              ) : null}
            </div>
            <div className="mt-1 flex flex-wrap gap-3 text-xs">
              <span className={pnlClass(sig.pnl_3d_pct)}>PnL 3 phiên: {fmtPct(sig.pnl_3d_pct)}</span>
              <span className={pnlClass(sig.pnl_5d_pct)}>PnL 5 phiên: {fmtPct(sig.pnl_5d_pct)}</span>
              <span className={pnlClass(sig.pnl_10d_pct)}>PnL 10 phiên: {fmtPct(sig.pnl_10d_pct)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export async function NewsfeedView() {
  let items: NewfeedItem[] = [];
  let error = "";
  try {
    const res = await getNewfeeds(50, 0);
    items = res.items;
  } catch {
    error = "Không tải được newsfeed. Vui lòng kiểm tra backend.";
  }

  const stats3d = calcHorizonStats(items, "pnl_3d_pct");
  const stats5d = calcHorizonStats(items, "pnl_5d_pct");
  const stats10d = calcHorizonStats(items, "pnl_10d_pct");

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-tv-text tracking-tight">Newsfeed tín hiệu mua</h1>
        <p className="mt-1 text-sm text-tv-muted">
          Hiển thị mã mua theo ngày phân tích, đồng thời lưu và xem lại toàn bộ nội dung gốc.
        </p>
      </header>

      {!error ? (
        <section className="rounded-lg border border-tv-border bg-tv-panel p-4">
          <p className="text-sm font-medium text-tv-text">Thống kê hiệu suất global (danh sách hiện tại)</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            <StatChip label="Sau 3 phiên" stats={stats3d} />
            <StatChip label="Sau 5 phiên" stats={stats5d} />
            <StatChip label="Sau 10 phiên" stats={stats10d} />
          </div>
        </section>
      ) : null}

      {error ? (
        <p className="rounded border border-tv-border bg-tv-panel p-3 text-sm text-tv-down">{error}</p>
      ) : items.length === 0 ? (
        <p className="rounded border border-tv-border bg-tv-panel p-3 text-sm text-tv-muted">
          Chưa có dữ liệu newsfeed.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-lg border border-tv-border bg-tv-panel p-4">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <h2 className="text-base font-semibold text-tv-text">
                  {item.reference_date ? formatDate(item.reference_date) : "Không có ngày tham chiếu"}
                </h2>
                <span className="text-xs text-tv-muted">{formatCreatedAt(item.created_at)}</span>
                {item.title ? <span className="text-xs text-tv-muted">- {item.title}</span> : null}
              </div>

              <div className="mt-3">
                <p className="mb-2 text-sm font-medium text-tv-text">Mã mua</p>
                <BuySignalsBlock item={item} />
              </div>

              <details className="mt-3 rounded border border-tv-border/80 bg-tv-bg px-3 py-2">
                <summary className="cursor-pointer text-sm text-tv-accent">
                  Xem toàn bộ nội dung phân tích
                </summary>
                <pre className="mt-2 whitespace-pre-wrap text-xs text-tv-muted">{item.raw_text}</pre>
              </details>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
