import Link from "next/link";
import { getRuns, type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function SignalsListPage() {
  let runs: Run[] = [];
  try {
    runs = await getRuns(30);
  } catch {
    runs = [];
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text tracking-tight mb-6">Danh sách phân tích</h1>
      {runs.length === 0 ? (
        <div className="text-tv-muted text-center py-12 tv-panel">Chưa có dữ liệu phân tích nào.</div>
      ) : (
        <div className="grid gap-2">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/signals/${run.run_date}`}
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
