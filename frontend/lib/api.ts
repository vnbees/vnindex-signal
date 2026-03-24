function getApiUrl(): string {
  if (typeof window === "undefined") {
    // Server-side: đọc runtime env mỗi lần (không cache ở module level)
    return process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export interface Signal {
  id: number;
  run_date: string;
  symbol: string;
  status: string;
  score_financial: number;
  score_seasonal: number;
  score_technical: number;
  score_cashflow: number;
  score_total: number;
  recommendation: string;
  signal_type: string;
  price_close_signal_date: number;
  price_open_t1: number | null;
  market_cap_bil: number | null;
  has_corporate_action: boolean;
  pnl_d1: number | null;
  pnl_d5: number | null;
  pnl_d10: number | null;
  pnl_d20: number | null;
  latest_pnl_pct: number | null;
  detail_financial?: Record<string, unknown>;
  detail_technical?: Record<string, unknown>;
  detail_cashflow?: Record<string, unknown>;
  detail_seasonal?: Record<string, unknown>;
}

export interface Run {
  id: number;
  run_date: string;
  top_n: number;
  hold_days: number;
  signal_count: number;
}

export interface PnlStat {
  recommendation: string;
  total: number;
  avg_pnl_d1: number | null;
  avg_pnl_d5: number | null;
  avg_pnl_d10: number | null;
  avg_pnl_d20: number | null;
  avg_latest_pnl: number | null;
}

export interface AccuracyStat {
  recommendation: string;
  total: number;
  win_d1: number;
  win_d5: number;
  win_d20: number;
  winrate_d1: number | null;
  winrate_d5: number | null;
  winrate_d20: number | null;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, {
    ...options,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json();
}

export async function getLatestRunDate(): Promise<string | null> {
  try {
    const runs = await fetchAPI<Run[]>("/api/v1/runs?limit=1");
    return runs[0]?.run_date ?? null;
  } catch {
    return null;
  }
}

export async function getRuns(limit = 30): Promise<Run[]> {
  return fetchAPI<Run[]>(`/api/v1/runs?limit=${limit}`);
}

export async function getSignals(
  runDate: string,
  recommendation?: string,
  sortBy = "score_total",
  order = "desc"
): Promise<Signal[]> {
  let path = `/api/v1/signals/${runDate}?sort_by=${sortBy}&order=${order}`;
  if (recommendation) path += `&recommendation=${recommendation}`;
  return fetchAPI<Signal[]>(path);
}

export async function getSignalDetail(runDate: string, symbol: string): Promise<Signal> {
  return fetchAPI<Signal>(`/api/v1/signals/${runDate}/${symbol}`);
}

export async function getPnlStats(days = 60): Promise<PnlStat[]> {
  return fetchAPI<PnlStat[]>(`/api/v1/stats/pnl?days=${days}`);
}

export async function getAccuracyStats(): Promise<AccuracyStat[]> {
  return fetchAPI<AccuracyStat[]>("/api/v1/stats/accuracy");
}
