import type { Metadata } from "next";
import Link from "next/link";
import { getRuns, type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Danh sách ngày phân tích",
  description:
    "Lịch các phiên có dữ liệu tín hiệu ViiStock (HOSE). Thông tin tham khảo; không phải dịch vụ môi giới.",
};

const PAGE_SIZE = 20;

export default async function SignalsListPage({
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
    const res = await getRuns(PAGE_SIZE, "top_cap", offset);
    runs = res.items;
    total = res.total;
  } catch {
    runs = [];
    total = 0;
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text tracking-tight mb-6">
        Danh sách phân tích
      </h1>

      {runs.length === 0 ? (
        <div className="text-tv-muted text-center py-12 tv-panel">
          Chưa có dữ liệu phân tích nào.
        </div>
      ) : (
        <>
          <div className="grid gap-2">
            {runs.map((run) => (
              <Link
                key={run.id}
                href={`/signals/${run.run_date}`}
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
                <div className="flex items-center gap-4 text-sm text-tv-muted">
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
                  href={`/signals?page=${page - 1}`}
                  className="px-3 py-1.5 text-sm rounded border border-tv-border text-tv-muted hover:text-tv-text hover:border-tv-accent/40 transition-colors"
                >
                  ← Trước
                </Link>
              )}

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Link
                  key={p}
                  href={`/signals?page=${p}`}
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
                  href={`/signals?page=${page + 1}`}
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
