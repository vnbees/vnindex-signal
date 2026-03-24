"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

interface PnlPoint {
  day: string;
  pnl: number | null;
}

interface Props {
  symbol: string;
  pnlD1: number | null;
  pnlD5: number | null;
  pnlD10: number | null;
  pnlD20: number | null;
}

export function PnlChart({ symbol, pnlD1, pnlD5, pnlD10, pnlD20 }: Props) {
  const data: PnlPoint[] = [
    { day: "T+0", pnl: 0 },
    { day: "T+1", pnl: pnlD1 },
    { day: "T+5", pnl: pnlD5 },
    { day: "T+10", pnl: pnlD10 },
    { day: "T+20", pnl: pnlD20 },
  ].filter((d) => d.pnl !== null || d.day === "T+0");

  if (data.length <= 1) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-sm">
        Chưa có dữ liệu PnL
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="day" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => [`${v?.toFixed(2)}%`, "PnL"]} />
        <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="pnl"
          stroke={
            (pnlD20 ?? pnlD10 ?? pnlD5 ?? pnlD1 ?? 0) >= 0 ? "#16a34a" : "#dc2626"
          }
          strokeWidth={2}
          dot={{ r: 4 }}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
