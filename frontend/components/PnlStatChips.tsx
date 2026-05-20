export type HorizonStats = {
  validCount: number;
  winCount: number;
  winratePct: number | null;
  avgProfitPct: number | null;
};

export function calcHorizonStatsFromValues(
  values: (number | null | undefined)[]
): HorizonStats {
  const nums = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const validCount = nums.length;
  if (validCount === 0) {
    return { validCount: 0, winCount: 0, winratePct: null, avgProfitPct: null };
  }
  const winCount = nums.filter((v) => v > 0).length;
  const winratePct = (winCount / validCount) * 100;
  const avgProfitPct = nums.reduce((sum, v) => sum + v, 0) / validCount;
  return { validCount, winCount, winratePct, avgProfitPct };
}

export function StatChip({ label, stats }: { label: string; stats: HorizonStats }) {
  const fmtPct = (v: number | null) => (v == null ? "--" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`);
  return (
    <div className="rounded-md border border-tv-border bg-tv-panel px-3 py-2 text-sm">
      <p className="font-medium text-tv-text">{label}</p>
      <p className="mt-1 text-xs text-tv-muted">
        Winrate: {stats.winCount}/{stats.validCount} ({fmtPct(stats.winratePct)})
      </p>
      <p
        className={`text-xs ${stats.avgProfitPct == null ? "text-tv-muted" : stats.avgProfitPct >= 0 ? "text-tv-up" : "text-tv-down"}`}
      >
        Avg Profit: {fmtPct(stats.avgProfitPct)}
      </p>
    </div>
  );
}
