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

const FILTERS = [
  { label: "Tất cả", value: "" },
  { label: "Mua mạnh", value: "BUY_STRONG" },
  { label: "Mua", value: "BUY" },
  { label: "Theo dõi", value: "HOLD" },
  { label: "Tránh", value: "AVOID" },
  { label: "Bán", value: "SELL" },
];

export function SignalTable({ signals, runDate, detailBasePath = "/signals" }: Props) {
  const [filter, setFilter] = useState("");

  const filtered = filter ? signals.filter((s) => s.recommendation === filter) : signals;

  return (
    <div>
      <div className="inline-flex flex-wrap gap-0 p-1 mb-4 rounded-lg bg-tv-panel border border-tv-border">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === f.value
                ? "bg-tv-accent text-white shadow-sm"
                : "text-tv-muted hover:text-tv-text hover:bg-tv-panel-hover/80"
            }`}
          >
            {f.label}
          </button>
        ))}
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
              <th
                className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide"
                title="Tính từ giá mở cửa T+1"
              >
                T+10
              </th>
              <th
                className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide"
                title="Tính từ giá mở cửa T+1"
              >
                T+20
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
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d10} label="T+10" />
                </td>
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d20} label="T+20" />
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
