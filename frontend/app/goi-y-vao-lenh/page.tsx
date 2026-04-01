import { RecommendationBadge } from "@/components/RecommendationBadge";
import {
  getAllocationSuggestion,
  type AllocationSuggestionResponse,
} from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";
import { CapitalInputForm } from "@/components/CapitalInputForm";
import { PriceFilter } from "@/components/PriceFilter";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: {
    capital?: string;
    price_min?: string;
    price_max?: string;
  };
}

function formatMoney(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${formatPrice(v)} đ`;
}

export default async function GoiYVaoLenhPage({ searchParams }: Props) {
  const capital = searchParams.capital ? Number(searchParams.capital) : undefined;
  const priceMin = searchParams.price_min ? Number(searchParams.price_min) : undefined;
  const priceMax = searchParams.price_max ? Number(searchParams.price_max) : undefined;

  let allocation: AllocationSuggestionResponse | null = null;
  let allocationError: string | null = null;

  if (capital !== undefined && capital > 0) {
    try {
      allocation = await getAllocationSuggestion(capital, "top_cap", undefined, priceMin, priceMax);
    } catch {
      allocationError = "Không lấy được gợi ý phân bổ vốn.";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-tv-text tracking-tight">Gợi ý vào lệnh theo vốn</h1>
          <p className="text-sm text-tv-muted mt-1">Ưu tiên PnL, phân bổ theo lô chẵn 100 và không vượt vốn.</p>
        </div>
      </div>

      <div className="tv-panel p-4">
        <div className="mb-3">
          <PriceFilter />
          <p className="text-xs text-tv-muted mt-2">
            Khoảng giá sẽ được dùng để ưu tiên loại tín hiệu có thống kê PnL và winrate tốt nhất.
          </p>
        </div>
        <h2 className="tv-section-title mb-3">Nhập vốn muốn vào lệnh</h2>
        <CapitalInputForm defaultCapital={capital} priceMin={priceMin} priceMax={priceMax} />

        <h3 className="text-sm font-medium text-tv-text mb-3">Kết quả gợi ý mua theo vốn (lô chẵn)</h3>
        {capital === undefined ? (
          <p className="text-sm text-tv-muted">Nhập vốn để hệ thống gợi ý cổ phiếu nên mua ở phiên tiếp theo.</p>
        ) : allocationError ? (
          <p className="text-sm text-tv-down">{allocationError}</p>
        ) : !allocation ? (
          <p className="text-sm text-tv-muted">Không có dữ liệu gợi ý.</p>
        ) : allocation.suggestions.length === 0 ? (
          <div className="rounded-md border border-tv-border bg-tv-panel p-3 text-sm">
            <p className="text-tv-down font-medium">
              {allocation.no_result_message || "Không tìm thấy kết quả."}
            </p>
            {allocation.min_required_capital !== null && allocation.min_required_capital !== undefined && (
              <p className="text-tv-muted mt-1">
                Gợi ý vốn tối thiểu:{" "}
                <span className="text-tv-text font-medium">{formatMoney(allocation.min_required_capital)}</span>
              </p>
            )}
            {allocation.min_required_symbol && allocation.min_required_reference_price !== null && allocation.min_required_reference_price !== undefined && (
              <p className="text-tv-muted mt-1">
                Theo mã <span className="text-tv-text font-medium">{allocation.min_required_symbol}</span> (giá tham
                chiếu {formatPrice(allocation.min_required_reference_price)} đ/cp, lô {allocation.lot_size} cổ phiếu).
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-sm text-tv-muted">
              Run date: <span className="text-tv-text font-medium">{formatDate(allocation.run_date)}</span> | Tổng vốn:{" "}
              <span className="text-tv-text font-medium">{formatMoney(allocation.capital)}</span> | Dự chi:{" "}
              <span className="text-tv-text font-medium">{formatMoney(allocation.total_planned)}</span> | Tiền dư:{" "}
              <span className="text-tv-text font-medium">{formatMoney(allocation.cash_left)}</span>
            </div>
            <div className="overflow-x-auto rounded-lg border border-tv-border">
              <table className="min-w-full text-sm">
                <thead className="border-b border-tv-border tv-table-head">
                  <tr>
                    <th className="px-3 py-2 text-left">Mã</th>
                    <th className="px-3 py-2 text-left">Ngày tín hiệu</th>
                    <th className="px-3 py-2 text-left">KN</th>
                    <th className="px-3 py-2 text-right">Giá tham chiếu</th>
                    <th className="px-3 py-2 text-right">SL (lô 100)</th>
                    <th className="px-3 py-2 text-right">Số tiền mua</th>
                    <th className="px-3 py-2 text-left">Vì sao chọn</th>
                  </tr>
                </thead>
                <tbody>
                  {allocation.suggestions.map((item) => (
                    <tr key={item.symbol} className="border-b border-tv-border/60">
                      <td className="px-3 py-2 font-semibold text-tv-text">{item.symbol}</td>
                      <td className="px-3 py-2 text-tv-muted">{formatDate(item.signal_date)}</td>
                      <td className="px-3 py-2">
                        <RecommendationBadge recommendation={item.recommendation} />
                      </td>
                      <td className="px-3 py-2 text-right">{formatPrice(item.reference_price)}</td>
                      <td className="px-3 py-2 text-right text-tv-text">{item.quantity}</td>
                      <td className="px-3 py-2 text-right text-tv-text">{formatMoney(item.amount_to_buy)}</td>
                      <td className="px-3 py-2 text-tv-muted">
                        <div className="space-y-1">
                          {item.reasons.map((reason, idx) => (
                            <p key={`${item.symbol}-reason-${idx}`}>- {reason}</p>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
