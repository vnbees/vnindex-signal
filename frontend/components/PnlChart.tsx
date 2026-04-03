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

const GRID = "#2a2e39";
const AXIS = "#787b86";
const ZERO = "#4b5563";

interface PnlPoint {
  day: string;
  pnl: number | null;
}

interface Props {
  symbol: string;
  pnlD3: number | null;
}

const tooltipStyles = {
  contentStyle: {
    backgroundColor: "#1e222d",
    border: `1px solid ${GRID}`,
    borderRadius: "6px",
    fontSize: "12px",
  },
  labelStyle: { color: AXIS },
  itemStyle: { color: "#d1d4dc" },
};

export function PnlChart({ symbol, pnlD3 }: Props) {
  const toNum = (v: number | null) => (v === null || v === undefined ? null : Number(v));
  const data: PnlPoint[] = [
    { day: "T+0", pnl: 0 },
    { day: "T+3", pnl: toNum(pnlD3) },
  ].filter((d) => d.pnl !== null || d.day === "T+0");

  if (data.length <= 1) {
    return (
      <div className="flex items-center justify-center h-32 text-tv-muted text-sm">
        Chưa có dữ liệu PnL
      </div>
    );
  }

  const lineColor = Number(pnlD3 ?? 0) >= 0 ? "#089981" : "#f23645";

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
        <XAxis dataKey="day" tick={{ fontSize: 12, fill: AXIS }} stroke={GRID} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12, fill: AXIS }} stroke={GRID} />
        <Tooltip
          formatter={(v: number) => [`${v?.toFixed(2)}%`, "PnL"]}
          contentStyle={tooltipStyles.contentStyle}
          labelStyle={tooltipStyles.labelStyle}
          itemStyle={tooltipStyles.itemStyle}
        />
        <ReferenceLine y={0} stroke={ZERO} strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="pnl"
          name={symbol}
          stroke={lineColor}
          strokeWidth={2}
          dot={{ r: 4, fill: lineColor }}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
