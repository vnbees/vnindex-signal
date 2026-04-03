"use client";

import { useState } from "react";
import Link from "next/link";
import type { Signal } from "@/lib/api";
import { RecommendationBadge } from "./RecommendationBadge";
import { PnlBadge } from "./PnlBadge";
import { CorporateActionWarning } from "./CorporateActionWarning";
import { formatPrice } from "@/lib/utils";

interface Props {
  signals: Signal[];
  runDate: string;
  /** Base path for detail links, e.g. /signals or /danh-muc-von-it */
  detailBasePath?: string;
}

const REC_FILTERS = [
  { label: "Tất cả", value: "" },
  { label: "Mua mạnh", value: "BUY_STRONG" },
  { label: "Mua", value: "BUY" },
  { label: "Theo dõi", value: "HOLD" },
  { label: "Tránh", value: "AVOID" },
  { label: "Bán", value: "SELL" },
];

interface PriceRange {
  label: string;
  min?: number;
  max?: number;
}

const PRICE_RANGES: PriceRange[] = [
  { label: "Tất cả" },
  { label: "< 10k", max: 10 },
  { label: "10–20k", min: 10, max: 20 },
  { label: "20–30k", min: 20, max: 30 },
  { label: "30–50k", min: 30, max: 50 },
  { label: "50–100k", min: 50, max: 100 },
  { label: "> 100k", min: 100 },
];

function matchesPriceRange(price: number | null | undefined, range: PriceRange): boolean {
  if (!range.min && !range.max) return true;
  const p = Number(price ?? 0);
  if (range.min !== undefined && p < range.min) return false;
  if (range.max !== undefined && p > range.max) return false;
  return true;
}

export function SignalTable({ signals, runDate, detailBasePath = "/signals" }: Props) {
  const [recFilter, setRecFilter] = useState("");
  const [priceRange, setPriceRange] = useState<PriceRange>(PRICE_RANGES[0]);

  const filtered = signals.filter((s) => {
    if (recFilter && s.recommendation !== recFilter) return false;
    if (!matchesPriceRange(s.price_close_signal_date, priceRange)) return false;
    return true;
  });

  return (
    <div>
      <div className="flex flex-col gap-2 mb-4">
        <div className="inline-flex flex-wrap gap-0 p-1 rounded-lg bg-tv-panel border border-tv-border">
          {REC_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setRecFilter(f.value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                recFilter === f.value
                  ? "bg-tv-accent text-white shadow-sm"
                  : "text-tv-muted hover:text-tv-text hover:bg-tv-panel-hover/80"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-tv-muted font-medium shrink-0">Khoảng giá:</span>
          <div className="inline-flex flex-wrap gap-0 p-1 rounded-lg bg-tv-panel border border-tv-border">
            {PRICE_RANGES.map((r) => {
              const active = r.label === priceRange.label;
              return (
                <button
                  key={r.label}
                  type="button"
                  onClick={() => setPriceRange(r)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    active
                      ? "bg-tv-accent text-white shadow-sm"
                      : "text-tv-muted hover:text-tv-text hover:bg-tv-panel-hover/80"
                  }`}
                >
                  {r.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-tv-border bg-tv-panel">
        <table className="min-w-full text-sm">
          <thead className="border-b border-tv-border tv-table-head">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide">
                Vốn hoá
              </th>
              <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide">Mã</th>
              <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide">KN</th>
              <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide">Giá đóng</th>
              <th
                className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide"
                title="Tính từ giá mở cửa T+1"
              >
                T+3
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-tv-border/80">
            {filtered.map((signal) => (
              <tr key={signal.id} className="hover:bg-tv-panel-hover/50 transition-colors">
                <td className="px-3 py-2.5 text-tv-muted text-xs">
                  {signal.market_cap_bil ? `${Math.round(Number(signal.market_cap_bil) / 1000)}B` : "—"}
                </td>
                <td className="px-3 py-2.5 font-semibold">
                  <div className="flex items-center gap-1">
                    <CorporateActionWarning show={signal.has_corporate_action} symbol={signal.symbol} />
                    <Link
                      href={`${detailBasePath}/${runDate}/${signal.symbol}`}
                      className="text-tv-accent hover:text-tv-text hover:underline underline-offset-2"
                    >
                      {signal.symbol}
                    </Link>
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <RecommendationBadge recommendation={signal.recommendation} />
                </td>
                <td className="px-3 py-2.5 text-right text-tv-text">
                  {formatPrice(signal.price_close_signal_date)}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d3} label="T+3" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-tv-muted">Không có tín hiệu nào.</div>
        )}
      </div>
    </div>
  );
}
