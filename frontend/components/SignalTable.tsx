"use client";

import { useState } from "react";
import Link from "next/link";
import type { Signal } from "@/lib/api";
import { RecommendationBadge } from "./RecommendationBadge";
import { PnlBadge } from "./PnlBadge";
import { CorporateActionWarning } from "./CorporateActionWarning";
import { ScoreCell } from "./ScoreCell";
import { formatPrice, formatDate } from "@/lib/utils";

interface Props {
  signals: Signal[];
  runDate: string;
}

const FILTERS = [
  { label: "Tất cả", value: "" },
  { label: "🟢🟢 Mua mạnh", value: "BUY_STRONG" },
  { label: "🟢 Mua", value: "BUY" },
  { label: "🟡 Theo dõi", value: "HOLD" },
  { label: "🟠 Tránh", value: "AVOID" },
  { label: "🔴 Bán", value: "SELL" },
];

export function SignalTable({ signals, runDate }: Props) {
  const [filter, setFilter] = useState("");

  const filtered = filter ? signals.filter((s) => s.recommendation === filter) : signals;

  return (
    <div>
      {/* Filter tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filter === f.value
                ? "bg-slate-800 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Vốn hoá</th>
              <th className="px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Mã</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">TC</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">SS</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">KT</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">DT</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Tổng</th>
              <th className="px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">KN</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Giá đóng</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide" title="Tính từ giá mở cửa T+1">T+1</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide" title="Tính từ giá mở cửa T+1">T+5</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide" title="Tính từ giá mở cửa T+1">T+20</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((signal) => (
              <tr key={signal.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-3 py-2.5 text-slate-500 text-xs">
                  {signal.market_cap_bil ? `${Math.round(signal.market_cap_bil / 1000)}B` : "—"}
                </td>
                <td className="px-3 py-2.5 font-semibold">
                  <div className="flex items-center gap-1">
                    <CorporateActionWarning show={signal.has_corporate_action} symbol={signal.symbol} />
                    <Link
                      href={`/signals/${runDate}/${signal.symbol}`}
                      className="text-blue-600 hover:underline"
                    >
                      {signal.symbol}
                    </Link>
                  </div>
                </td>
                <td className="px-3 py-2.5 text-center">
                  <ScoreCell score={signal.score_financial} />
                </td>
                <td className="px-3 py-2.5 text-center">
                  <ScoreCell score={signal.score_seasonal} />
                </td>
                <td className="px-3 py-2.5 text-center">
                  <ScoreCell score={signal.score_technical} />
                </td>
                <td className="px-3 py-2.5 text-center">
                  <ScoreCell score={signal.score_cashflow} />
                </td>
                <td className="px-3 py-2.5 text-center font-bold">
                  <ScoreCell score={signal.score_total} />
                </td>
                <td className="px-3 py-2.5">
                  <RecommendationBadge recommendation={signal.recommendation} />
                </td>
                <td className="px-3 py-2.5 text-right text-slate-700">
                  {formatPrice(signal.price_close_signal_date)}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d1} label="T+1" />
                </td>
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d5} label="T+5" />
                </td>
                <td className="px-3 py-2.5 text-right">
                  <PnlBadge pnl={signal.pnl_d20} label="T+20" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-slate-400">Không có tín hiệu nào.</div>
        )}
      </div>
    </div>
  );
}
