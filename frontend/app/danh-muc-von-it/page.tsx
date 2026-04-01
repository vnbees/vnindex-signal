import Link from "next/link";
import { getRuns, type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

const PORTFOLIO_LOW = "low_cap";

export default async function VonItListPage() {
  let runs: Run[] = [];
  try {
    runs = await getRuns(30, PORTFOLIO_LOW);
  } catch {
    runs = [];
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text tracking-tight mb-2">
        Danh mục vốn ít
      </h1>
      <p className="text-sm text-tv-muted mb-6">
        Vốn hoá cao, thanh khoản tốt, giá cổ phiếu ≤ 30k (theo pipeline backtest). Khác với TOP 30 vốn hoá lớn nhất.
      </p>
      {runs.length === 0 ? (
        <div className="text-tv-muted text-center py-12 tv-panel">
          Chưa có dữ liệu danh mục vốn ít. Chạy script <code className="text-tv-text">run_analysis_von_it.py</code> để
          đẩy dữ liệu.
        </div>
      ) : (
        <div className="grid gap-2">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/danh-muc-von-it/${run.run_date}`}
              className="flex items-center justify-between p-4 tv-panel border-tv-border hover:border-tv-accent/40 hover:bg-tv-panel-hover/60 transition-colors"
            >
              <div>
                <span className="font-semibold text-tv-text">{formatDate(run.run_date)}</span>
                <span className="text-tv-muted text-sm ml-3">{run.run_date}</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-tv-muted">
                <span>{run.signal_count} mã</span>
                <span>Giữ {run.hold_days} ngày</span>
                <span className="text-tv-accent">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
