import Link from "next/link";
import { getRuns, type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

const PORTFOLIO_LOW = "low_cap";
const PAGE_SIZE = 20;

export default async function VonItListPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, parseInt(params.page || "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  let runs: Run[] = [];
  let total = 0;
  try {
    const res = await getRuns(PAGE_SIZE, PORTFOLIO_LOW, offset);
    runs = res.items;
    total = res.total;
  } catch {
    runs = [];
    total = 0;
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text tracking-tight mb-2">
        Danh mục vốn ít
      </h1>
      <p className="text-sm text-tv-muted mb-6">
        Vốn hoá cao, thanh khoản tốt, giá cổ phiếu ≤ 30k (theo pipeline
        backtest). Khác với TOP 30 vốn hoá lớn nhất.
      </p>
      {runs.length === 0 ? (
        <div className="text-tv-muted text-center py-12 tv-panel">
          Chưa có dữ liệu danh mục vốn ít. Chạy script{" "}
          <code className="text-tv-text">run_analysis_von_it.py</code> để đẩy
          dữ liệu.
        </div>
      ) : (
        <>
          <div className="grid gap-2">
            {runs.map((run) => (
              <Link
                key={run.id}
                href={`/danh-muc-von-it/${run.run_date}`}
                className="flex items-center justify-between p-4 tv-panel border-tv-border hover:border-tv-accent/40 hover:bg-tv-panel-hover/60 transition-colors"
              >
                <div>
                  <span className="font-semibold text-tv-text">
                    {formatDate(run.run_date)}
                  </span>
                  <span className="text-tv-muted text-sm ml-3">
                    {run.run_date}
                  </span>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-sm text-tv-muted">
                  <span className="whitespace-nowrap">
                    <span className="text-tv-accent font-medium">
                      {run.buy_strong_count ?? 0}
                    </span>{" "}
                    mua mạnh
                    <span className="mx-1.5 text-tv-border">·</span>
                    <span className="text-emerald-500/90 font-medium">
                      {run.buy_count ?? 0}
                    </span>{" "}
                    mua
                  </span>
                  <span>{run.signal_count} mã</span>
                  <span>Giữ {run.hold_days} ngày</span>
                  <span className="text-tv-accent">→</span>
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-6">
              {page > 1 && (
                <Link
                  href={`/danh-muc-von-it?page=${page - 1}`}
                  className="px-3 py-1.5 text-sm rounded border border-tv-border text-tv-muted hover:text-tv-text hover:border-tv-accent/40 transition-colors"
                >
                  ← Trước
                </Link>
              )}

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Link
                  key={p}
                  href={`/danh-muc-von-it?page=${p}`}
                  className={`px-3 py-1.5 text-sm rounded border transition-colors ${
                    p === page
                      ? "border-tv-accent bg-tv-accent/10 text-tv-accent font-semibold"
                      : "border-tv-border text-tv-muted hover:text-tv-text hover:border-tv-accent/40"
                  }`}
                >
                  {p}
                </Link>
              ))}

              {page < totalPages && (
                <Link
                  href={`/danh-muc-von-it?page=${page + 1}`}
                  className="px-3 py-1.5 text-sm rounded border border-tv-border text-tv-muted hover:text-tv-text hover:border-tv-accent/40 transition-colors"
                >
                  Sau →
                </Link>
              )}

              <span className="text-xs text-tv-muted ml-2">
                {total} ngày
              </span>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
