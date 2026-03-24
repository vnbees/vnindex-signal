import Link from "next/link";
import { getRuns, type Run } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const revalidate = 3600;

export default async function SignalsListPage() {
  let runs: Run[] = [];
  try {
    runs = await getRuns(30);
  } catch {
    runs = [];
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Danh sách phân tích</h1>
      {runs.length === 0 ? (
        <div className="text-slate-500 text-center py-12">Chưa có dữ liệu phân tích nào.</div>
      ) : (
        <div className="grid gap-2">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/signals/${run.run_date}`}
              className="flex items-center justify-between p-4 bg-white rounded-lg border border-slate-200 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div>
                <span className="font-semibold text-slate-800">{formatDate(run.run_date)}</span>
                <span className="text-slate-400 text-sm ml-3">{run.run_date}</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-500">
                <span>{run.signal_count} mã</span>
                <span>Giữ {run.hold_days} ngày</span>
                <span className="text-blue-500">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
