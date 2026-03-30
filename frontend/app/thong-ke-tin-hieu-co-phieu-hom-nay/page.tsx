import type { Metadata } from "next";
import { getPnlStats, getAccuracyStats, type PnlStat, type AccuracyStat } from "@/lib/api";
import { PnlStatsChart } from "@/components/PnlStatsChart";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Thống kê tín hiệu cổ phiếu hôm nay",
  description:
    "Thống kê hiệu suất PnL và win rate theo khuyến nghị ViiStock — dữ liệu HOSE, cập nhật hàng ngày.",
};

function pnlCellClass(v: number | null | undefined) {
  if (v === null || v === undefined) return "text-tv-muted";
  return v >= 0 ? "text-tv-up" : "text-tv-down";
}

export default async function ThongKeTinHieuPage() {
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
        <h1 className="text-xl font-semibold text-tv-text tracking-tight">Thống kê hiệu suất</h1>
      </div>

      <div className="tv-panel p-6 mb-6">
        <h2 className="tv-section-title mb-4">PnL trung bình theo khuyến nghị (60 ngày)</h2>
        {pnlStats.length > 0 ? (
          <>
            <PnlStatsChart data={pnlStats} />
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-tv-border tv-table-head">
                    <th className="text-left py-2.5 px-3 font-medium rounded-tl-md">Khuyến nghị</th>
                    <th className="text-right py-2.5 px-3 font-medium">Số lượng</th>
                    <th className="text-right py-2.5 px-3 font-medium">T+3</th>
                    <th className="text-right py-2.5 px-3 font-medium">T+10</th>
                    <th className="text-right py-2.5 px-3 font-medium rounded-tr-md">T+20</th>
                  </tr>
                </thead>
                <tbody>
                  {pnlStats.map((stat) => (
                    <tr key={stat.recommendation} className="border-b border-tv-border/80 hover:bg-tv-panel-hover/50">
                      <td className="py-2.5 px-3 font-medium text-tv-text">{stat.recommendation}</td>
                      <td className="py-2.5 px-3 text-right text-tv-muted">{stat.total}</td>
                      <td className={`py-2.5 px-3 text-right ${pnlCellClass(stat.avg_pnl_d3)}`}>
                        {stat.avg_pnl_d3 !== null ? `${stat.avg_pnl_d3 >= 0 ? "+" : ""}${stat.avg_pnl_d3}%` : "—"}
                      </td>
                      <td className={`py-2.5 px-3 text-right ${pnlCellClass(stat.avg_pnl_d10)}`}>
                        {stat.avg_pnl_d10 !== null ? `${stat.avg_pnl_d10 >= 0 ? "+" : ""}${stat.avg_pnl_d10}%` : "—"}
                      </td>
                      <td className={`py-2.5 px-3 text-right ${pnlCellClass(stat.avg_pnl_d20)}`}>
                        {stat.avg_pnl_d20 !== null ? `${stat.avg_pnl_d20 >= 0 ? "+" : ""}${stat.avg_pnl_d20}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-tv-muted text-center py-8">Chưa có dữ liệu thống kê.</p>
        )}
      </div>

      <div className="tv-panel p-6">
        <h2 className="tv-section-title mb-4">Win Rate (PnL &gt; 0)</h2>
        {accuracyStats.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-tv-border tv-table-head">
                  <th className="text-left py-2.5 px-3 font-medium rounded-tl-md">Khuyến nghị</th>
                  <th className="text-right py-2.5 px-3 font-medium">Tổng</th>
                  <th className="text-right py-2.5 px-3 font-medium">Win T+3</th>
                  <th className="text-right py-2.5 px-3 font-medium">Win T+10</th>
                  <th className="text-right py-2.5 px-3 font-medium rounded-tr-md">Win T+20</th>
                </tr>
              </thead>
              <tbody>
                {accuracyStats.map((stat) => (
                  <tr key={stat.recommendation} className="border-b border-tv-border/80 hover:bg-tv-panel-hover/50">
                    <td className="py-2.5 px-3 font-medium text-tv-text">{stat.recommendation}</td>
                    <td className="py-2.5 px-3 text-right text-tv-muted">{stat.total}</td>
                    <td className="py-2.5 px-3 text-right text-tv-text">
                      {stat.winrate_d3 !== null ? `${stat.winrate_d3}%` : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-right text-tv-text">
                      {stat.winrate_d10 !== null ? `${stat.winrate_d10}%` : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-right text-tv-text">
                      {stat.winrate_d20 !== null ? `${stat.winrate_d20}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-tv-muted text-center py-8">Chưa có dữ liệu thống kê.</p>
        )}
      </div>
    </div>
  );
}
