import type { Metadata } from "next";
import { getNewfeeds, type NewfeedItem } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Newsfeed tín hiệu mua",
  description: "Danh sách mã cổ phiếu được khuyến nghị mua theo từng ngày phân tích.",
};

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

function BuySignalsBlock({ item }: { item: NewfeedItem }) {
  if (!item.buy_signals.length) {
    return <p className="text-sm text-tv-muted">Không có mã mua hợp lệ.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {item.buy_signals.map((sig, idx) => (
        <div
          key={`${item.id}-${sig.symbol}-${idx}`}
          className="rounded-md border border-tv-border bg-tv-panel px-2.5 py-1.5 text-sm"
          title={sig.sector ?? undefined}
        >
          <span className="font-semibold text-tv-text">{sig.symbol}</span>
          {typeof sig.rank === "number" ? (
            <span className="ml-1 text-xs text-tv-muted">#{sig.rank}</span>
          ) : null}
          {sig.price !== null ? (
            <span className="ml-2 text-xs text-tv-muted">{formatPrice(sig.price)} đ</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default async function NewsfeedPage() {
  let items: NewfeedItem[] = [];
  let error = "";
  try {
    const res = await getNewfeeds(50, 0);
    items = res.items;
  } catch {
    error = "Không tải được newsfeed. Vui lòng kiểm tra backend.";
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-tv-text tracking-tight">Newsfeed tín hiệu mua</h1>
        <p className="mt-1 text-sm text-tv-muted">
          Hiển thị mã mua theo ngày phân tích, đồng thời lưu và xem lại toàn bộ nội dung gốc.
        </p>
      </header>

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
