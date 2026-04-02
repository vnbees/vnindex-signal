import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { getPnlStats, getAccuracyStats, type PnlStat, type AccuracyStat } from "@/lib/api";
import { PnlStatsChart } from "@/components/PnlStatsChart";
import { PriceFilter } from "@/components/PriceFilter";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Thống kê tín hiệu cổ phiếu hôm nay",
  description:
    "Thống kê PnL và tỷ lệ thắng theo nhãn khuyến nghị (dữ liệu lịch sử HOSE). Tham khảo; không phải lời khuyên đầu tư.",
};

function pnlCellClass(v: number | null | undefined) {
  if (v === null || v === undefined) return "text-tv-muted";
  return v >= 0 ? "text-tv-up" : "text-tv-down";
}

interface Props {
  searchParams: { price_min?: string; price_max?: string };
}

export default async function ThongKeTinHieuPage({ searchParams }: Props) {
  const priceMin = searchParams.price_min ? Number(searchParams.price_min) : undefined;
  const priceMax = searchParams.price_max ? Number(searchParams.price_max) : undefined;

  let pnlStats: PnlStat[] = [];
  let accuracyStats: AccuracyStat[] = [];

  try {
    [pnlStats, accuracyStats] = await Promise.all([
      getPnlStats(60, priceMin, priceMax),
      getAccuracyStats(priceMin, priceMax),
    ]);
  } catch {
    // Continue with empty data
  }

  const filterLabel =
    priceMin !== undefined && priceMax !== undefined
      ? `${priceMin}k–${priceMax}k`
      : priceMin !== undefined
        ? `Trên ${priceMin}k`
        : priceMax !== undefined
          ? `Dưới ${priceMax}k`
          : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-tv-text tracking-tight">Thống kê hiệu suất</h1>
      </div>

      <div className="tv-panel p-4 mb-4">
        <Suspense fallback={null}>
          <PriceFilter />
        </Suspense>
      </div>

      <div className="tv-panel p-6 mb-6">
        <h2 className="tv-section-title mb-1">PnL trung bình theo nhãn khuyến nghị (60 ngày gần đây)</h2>
        <p className="text-xs text-tv-muted mb-4 leading-relaxed">
          Số liệu là <strong className="text-tv-text font-medium">thống kê lịch sử</strong> theo quy tắc tính của website; không
          đảm bảo kết quả tương lai.{" "}
          <Link href="/mien-tru-trach-nhiem" className="text-tv-accent hover:underline underline-offset-2">
            Miễn trừ trách nhiệm
          </Link>
        </p>
        {filterLabel && (
          <p className="text-xs text-tv-muted mb-4">
            Lọc giá: <span className="text-tv-accent font-medium">{filterLabel}</span>
          </p>
        )}
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

      <div className="tv-panel p-6 mb-6">
        <h2 className="tv-section-title mb-1">Tỷ lệ PnL dương theo nhãn (thống kê lịch sử)</h2>
        {filterLabel && (
          <p className="text-xs text-tv-muted mb-4">
            Lọc giá: <span className="text-tv-accent font-medium">{filterLabel}</span>
          </p>
        )}
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

      <p className="text-xs text-tv-muted leading-relaxed max-w-3xl">
        &quot;Khuyến nghị&quot; trên bảng chỉ là <strong className="text-tv-text font-medium">nhãn phân loại tín hiệu</strong> do
        mô hình gán; không phải lời mua/bán cá nhân hóa. Dùng song song với nghiên cứu riêng và quản trị rủi ro.
      </p>
    </div>
  );
}
