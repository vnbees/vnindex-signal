import type { Metadata } from "next";
import { publishReviewedSignalsAction, type ReviewActionResult } from "./actions";
import { fetchWithTimeout } from "@/lib/serverFetch";
import { getServerBackendUrl } from "@/lib/serverBackendUrl";
import type { SignalEntryListResponse } from "@/lib/api";

export const metadata: Metadata = {
  title: "Review tín hiệu chờ publish",
  description: "Review mã AI chọn trước khi publish lên newsfeed.",
};

export const dynamic = "force-dynamic";

const FETCH_MS = 12_000;

type ReviewSignal = {
  symbol: string;
  rank: number | null;
  sector: string | null;
  recommendation: string | null;
  price: number | null;
  why_selected: string[];
};

function parseReviewSignals(payload: Record<string, unknown> | null): ReviewSignal[] {
  const rows = payload?.buy_signals;
  if (!Array.isArray(rows)) return [];
  return rows
    .filter((r): r is Record<string, unknown> => !!r && typeof r === "object")
    .map((r) => ({
      symbol: String(r.symbol ?? "").trim().toUpperCase(),
      rank: typeof r.rank === "number" ? r.rank : null,
      sector: typeof r.sector === "string" ? r.sector : null,
      recommendation: typeof r.recommendation === "string" ? r.recommendation : null,
      price: typeof r.price === "number" ? r.price : null,
      why_selected: Array.isArray(r.why_selected)
        ? r.why_selected.map((x) => String(x || "").trim()).filter(Boolean)
        : [],
    }))
    .filter((x) => x.symbol);
}

async function loadPendingReviews(): Promise<{
  status: "ok";
  data: SignalEntryListResponse;
} | {
  status: "error";
  message: string;
}> {
  const base = getServerBackendUrl();
  try {
    const res = await fetchWithTimeout(`${base}/api/v1/review/signal-entries?limit=100&offset=0`, {
      cache: "no-store",
      timeoutMs: FETCH_MS,
    });
    if (!res.ok) {
      return { status: "error", message: `Không tải được danh sách review (HTTP ${res.status}).` };
    }
    return { status: "ok", data: (await res.json()) as SignalEntryListResponse };
  } catch (e) {
    return {
      status: "error",
      message: e instanceof Error ? e.message : "Không thể kết nối backend.",
    };
  }
}

export default async function ReviewSignalEntriesPage() {
  const loaded = await loadPendingReviews();
  if (loaded.status === "error") {
    return <p className="rounded border border-tv-border bg-tv-panel p-4 text-sm text-tv-down">{loaded.message}</p>;
  }

  async function publishAction(entryId: number, formData: FormData): Promise<ReviewActionResult> {
    "use server";
    return publishReviewedSignalsAction(entryId, formData);
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-tv-text">Review tín hiệu trước khi publish</h1>
        <p className="mt-1 text-sm text-tv-muted">
          Trang này không cần đăng nhập. Hệ thống chỉ đưa lên newsfeed sau khi bạn chọn mã và bấm publish.
        </p>
      </header>

      {loaded.data.items.length === 0 ? (
        <p className="rounded border border-tv-border bg-tv-panel p-4 text-sm text-tv-muted">
          Hiện không có tín hiệu nào chờ review.
        </p>
      ) : (
        <div className="space-y-3">
          {loaded.data.items.map((entry) => {
            const signals = parseReviewSignals(entry.payload);
            return (
              <article key={entry.id} className="rounded-lg border border-tv-border bg-tv-panel p-4">
                <div className="mb-3">
                  <p className="text-sm text-tv-muted">
                    Entry #{entry.id} {entry.reference_date ? `- ${entry.reference_date}` : ""}
                  </p>
                  {entry.title ? <p className="text-sm text-tv-text">{entry.title}</p> : null}
                </div>

                {signals.length === 0 ? (
                  <p className="text-sm text-tv-down">Entry này không có danh sách mã hợp lệ để publish.</p>
                ) : (
                  <form action={publishAction.bind(null, entry.id)} className="space-y-3">
                    <div className="space-y-2">
                      {signals.map((sig) => (
                        <label
                          key={`${entry.id}-${sig.symbol}`}
                          className="block rounded border border-tv-border/80 bg-tv-bg p-3"
                        >
                          <div className="flex items-center gap-2">
                            <input type="checkbox" name="symbols" value={sig.symbol} defaultChecked />
                            <span className="font-semibold text-tv-text">
                              {sig.symbol}
                              {typeof sig.rank === "number" ? ` (#${sig.rank})` : ""}
                            </span>
                            {sig.sector ? <span className="text-xs text-tv-muted">- {sig.sector}</span> : null}
                          </div>
                          <p className="mt-1 text-xs text-tv-muted">
                            {sig.recommendation ?? "THEO DÕI MUA"}
                            {sig.price != null ? ` - Giá: ${sig.price.toLocaleString("vi-VN")} đ` : ""}
                          </p>
                          {sig.why_selected.length > 0 ? (
                            <ul className="mt-2 space-y-1 text-xs text-tv-text">
                              {sig.why_selected.map((reason, idx) => (
                                <li key={`${sig.symbol}-${idx}`}>- {reason}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-2 text-xs text-tv-muted">Chưa có lý do chi tiết từ AI.</p>
                          )}
                        </label>
                      ))}
                    </div>
                    <button
                      type="submit"
                      className="rounded bg-tv-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
                    >
                      Publish mã đã chọn
                    </button>
                  </form>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
