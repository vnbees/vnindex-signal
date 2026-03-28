import { getPnlStats, getAccuracyStats, type PnlStat, type AccuracyStat } from "@/lib/api";
import { PnlStatsChart } from "@/components/PnlStatsChart";

export const dynamic = "force-dynamic";

export default async function StatsPage() {
  let pnlStats: PnlStat[] = [];
  let accuracyStats: AccuracyStat[] = [];

  try {
    [pnlStats, accuracyStats] = await Promise.all([
      getPnlStats(60),
      getAccuracyStats(),
    ]);
  } catch {
    // Continue with empty data
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Thống kê hiệu suất</h1>
      </div>

      {/* PnL by Recommendation */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <h2 className="font-semibold text-slate-700 mb-4">PnL trung bình theo khuyến nghị (60 ngày)</h2>
        {pnlStats.length > 0 ? (
          <>
            <PnlStatsChart data={pnlStats} />
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">Khuyến nghị</th>
                    <th className="text-right py-2 px-3 text-slate-500 font-medium">Số lượng</th>
                    <th className="text-right py-2 px-3 text-slate-500 font-medium">T+3</th>
                    <th className="text-right py-2 px-3 text-slate-500 font-medium">T+10</th>
                    <th className="text-right py-2 px-3 text-slate-500 font-medium">T+20</th>
                  </tr>
                </thead>
                <tbody>
                  {pnlStats.map((stat) => (
                    <tr key={stat.recommendation} className="border-b border-slate-50">
                      <td className="py-2 px-3 font-medium">{stat.recommendation}</td>
                      <td className="py-2 px-3 text-right text-slate-500">{stat.total}</td>
                      <td className={`py-2 px-3 text-right ${(stat.avg_pnl_d3 ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {stat.avg_pnl_d3 !== null ? `${stat.avg_pnl_d3 >= 0 ? "+" : ""}${stat.avg_pnl_d3}%` : "—"}
                      </td>
                      <td className={`py-2 px-3 text-right ${(stat.avg_pnl_d10 ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {stat.avg_pnl_d10 !== null ? `${stat.avg_pnl_d10 >= 0 ? "+" : ""}${stat.avg_pnl_d10}%` : "—"}
                      </td>
                      <td className={`py-2 px-3 text-right ${(stat.avg_pnl_d20 ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {stat.avg_pnl_d20 !== null ? `${stat.avg_pnl_d20 >= 0 ? "+" : ""}${stat.avg_pnl_d20}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-slate-400 text-center py-8">Chưa có dữ liệu thống kê.</p>
        )}
      </div>

      {/* Win Rate */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-700 mb-4">Win Rate (PnL &gt; 0)</h2>
        {accuracyStats.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">Khuyến nghị</th>
                  <th className="text-right py-2 px-3 text-slate-500 font-medium">Tổng</th>
                  <th className="text-right py-2 px-3 text-slate-500 font-medium">Win T+3</th>
                  <th className="text-right py-2 px-3 text-slate-500 font-medium">Win T+10</th>
                  <th className="text-right py-2 px-3 text-slate-500 font-medium">Win T+20</th>
                </tr>
              </thead>
              <tbody>
                {accuracyStats.map((stat) => (
                  <tr key={stat.recommendation} className="border-b border-slate-50">
                    <td className="py-2 px-3 font-medium">{stat.recommendation}</td>
                    <td className="py-2 px-3 text-right text-slate-500">{stat.total}</td>
                    <td className="py-2 px-3 text-right">
                      {stat.winrate_d3 !== null ? `${stat.winrate_d3}%` : "—"}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {stat.winrate_d10 !== null ? `${stat.winrate_d10}%` : "—"}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {stat.winrate_d20 !== null ? `${stat.winrate_d20}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">Chưa có dữ liệu thống kê.</p>
        )}
      </div>
    </div>
  );
}
