"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { PnlStat } from "@/lib/api";

const GRID = "#2a2e39";
const AXIS = "#787b86";
const ZERO = "#4b5563";

const BAR_T3 = "#2962ff";

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

interface Props {
  data: PnlStat[];
}

export function PnlStatsChart({ data }: Props) {
  const chartData = data.map((d) => ({
    name: d.recommendation,
    "T+3": d.avg_pnl_d3,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: AXIS }} stroke={GRID} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12, fill: AXIS }} stroke={GRID} />
        <Tooltip
          formatter={(v: number) => [`${v?.toFixed(2)}%`]}
          contentStyle={tooltipStyles.contentStyle}
          labelStyle={tooltipStyles.labelStyle}
          itemStyle={tooltipStyles.itemStyle}
        />
        <Legend wrapperStyle={{ paddingTop: 8, color: AXIS }} iconType="square" />
        <ReferenceLine y={0} stroke={ZERO} />
        <Bar dataKey="T+3" fill={BAR_T3} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
