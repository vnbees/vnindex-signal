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

interface Props {
  data: PnlStat[];
}

export function PnlStatsChart({ data }: Props) {
  const chartData = data.map((d) => ({
    name: d.recommendation,
    "T+1": d.avg_pnl_d1,
    "T+5": d.avg_pnl_d5,
    "T+20": d.avg_pnl_d20,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => [`${v?.toFixed(2)}%`]} />
        <Legend />
        <ReferenceLine y={0} stroke="#94a3b8" />
        <Bar dataKey="T+1" fill="#60a5fa" />
        <Bar dataKey="T+5" fill="#34d399" />
        <Bar dataKey="T+20" fill="#a78bfa" />
      </BarChart>
    </ResponsiveContainer>
  );
}
