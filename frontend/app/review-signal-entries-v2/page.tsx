import type { Metadata } from "next";
import { publishReviewV2SignalsAction } from "./actions";
import { fetchWithTimeout } from "@/lib/serverFetch";
import { getServerBackendUrl } from "@/lib/serverBackendUrl";

export const metadata: Metadata = {
  title: "Review tín hiệu v2 (FireAnt live)",
  description: "Review mã từ api.fireant.vn trước khi publish lên newsfeed.",
};

export const dynamic = "force-dynamic";

const FETCH_MS = 120_000;

type ReviewV2BuySignal = {
  rank: number;
  symbol: string;
  sector: string | null;
  recommendation: string;
  price: number | null;
  why_selected: string[];
};

type ReviewV2CandidatesResponse = {
  ok: boolean;
  reference_date: string;
  as_of_date: string;
  title: string;
  source: string;
  screened_count: number;
  display_count: number;
  buy_signals: ReviewV2BuySignal[];
  cached: boolean;
  computed_at: string;
};

async function loadReviewV2Candidates(refresh: boolean): Promise<{
  status: "ok";
  data: ReviewV2CandidatesResponse;
} | {
  status: "error";
  message: string;
}> {
  const base = getServerBackendUrl();
  const qs = refresh ? "?refresh=true" : "";
  try {
    const res = await fetchWithTimeout(`${base}/api/v1/review-v2/candidates${qs}`, {
      cache: "no-store",
      timeoutMs: FETCH_MS,
    });
    if (!res.ok) {
      return { status: "error", message: `Không tải được dữ liệu review v2 (HTTP ${res.status}).` };
    }
    return { status: "ok", data: (await res.json()) as ReviewV2CandidatesResponse };
  } catch (e) {
    return {
      status: "error",
      message: e instanceof Error ? e.message : "Không thể kết nối backend.",
    };
  }
}

export default async function ReviewSignalEntriesV2Page({
  searchParams,
}: {
  searchParams?: { refresh?: string };
}) {
  const refresh = searchParams?.refresh === "1" || searchParams?.refresh === "true";
  const loaded = await loadReviewV2Candidates(refresh);

  async function publishAction(formData: FormData): Promise<void> {
    "use server";
    await publishReviewV2SignalsAction(formData);
  }

  if (loaded.status === "error") {
    return (
      <div className="space-y-3">
        <p className="rounded border border-tv-border bg-tv-panel p-4 text-sm text-tv-down">{loaded.message}</p>
        <p className="text-sm text-tv-muted">
          Lần tải đầu có thể mất 1–2 phút (226 mã). Thử lại hoặc{" "}
          <a href="/review-signal-entries-v2?refresh=1" className="text-tv-accent underline">
            refresh live
          </a>
          .
        </p>
      </div>
    );
  }

  const { data } = loaded;
  const signals = data.buy_signals;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-tv-text">Review tín hiệu v2 (FireAnt live)</h1>
        <p className="mt-1 text-sm text-tv-muted">
          Dữ liệu live từ api.fireant.vn. Chỉ hiển thị mã có dòng tiền ngành dương và khối lượng phiên mới nhất cao
          hơn trung bình 5 phiên.
        </p>
        <p className="mt-1 text-xs text-tv-muted">
          Ngày {data.reference_date} · {data.display_count}/{data.screened_count} mã hiển thị
          {data.cached ? " · cache" : " · vừa tính"} ·{" "}
          <a href="/review-signal-entries-v2?refresh=1" className="text-tv-accent underline">
            Tải lại live
          </a>
        </p>
      </header>

      {signals.length === 0 ? (
        <p className="rounded border border-tv-border bg-tv-panel p-4 text-sm text-tv-muted">
          Không có mã nào thỏa bộ lọc hiển thị ({data.display_count}/{data.screened_count} sau screened).
        </p>
      ) : (
        <article className="rounded-lg border border-tv-border bg-tv-panel p-4">
          <div className="mb-3">
            <p className="text-sm text-tv-muted">Entry live — {data.reference_date}</p>
            <p className="text-sm text-tv-text">{data.title}</p>
          </div>

          <form action={publishAction} className="space-y-3">
            <div className="space-y-2">
              {signals.map((sig) => (
                <label
                  key={sig.symbol}
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
                    <p className="mt-2 text-xs text-tv-muted">Chưa có lý do chi tiết.</p>
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
        </article>
      )}
    </div>
  );
}
