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
  pnl_d3: number | null;
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
  portfolio_kind?: string;
  top_n: number;
  hold_days: number;
  signal_count: number;
}

export interface PnlStat {
  recommendation: string;
  total: number;
  avg_pnl_d3: number | null;
  avg_pnl_d10: number | null;
  avg_pnl_d20: number | null;
  avg_latest_pnl: number | null;
}

export interface AccuracyStat {
  recommendation: string;
  total: number;
  win_d3: number;
  win_d10: number;
  win_d20: number;
  winrate_d3: number | null;
  winrate_d10: number | null;
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

export async function getRuns(limit = 30, portfolioKind = "top_cap"): Promise<Run[]> {
  const pk = encodeURIComponent(portfolioKind);
  return fetchAPI<Run[]>(`/api/v1/runs?limit=${limit}&portfolio_kind=${pk}`);
}

export async function getSignals(
  runDate: string,
  recommendation?: string,
  sortBy = "score_total",
  order = "desc",
  portfolioKind = "top_cap"
): Promise<Signal[]> {
  const pk = encodeURIComponent(portfolioKind);
  let path = `/api/v1/signals/${runDate}?sort_by=${sortBy}&order=${order}&portfolio_kind=${pk}`;
  if (recommendation) path += `&recommendation=${recommendation}`;
  return fetchAPI<Signal[]>(path);
}

export async function getSignalDetail(
  runDate: string,
  symbol: string,
  portfolioKind = "top_cap"
): Promise<Signal> {
  const pk = encodeURIComponent(portfolioKind);
  return fetchAPI<Signal>(`/api/v1/signals/${runDate}/${symbol}?portfolio_kind=${pk}`);
}

export async function getPnlStats(
  days = 60,
  priceMin?: number,
  priceMax?: number
): Promise<PnlStat[]> {
  let path = `/api/v1/stats/pnl?days=${days}`;
  if (priceMin !== undefined) path += `&price_min=${priceMin}`;
  if (priceMax !== undefined) path += `&price_max=${priceMax}`;
  return fetchAPI<PnlStat[]>(path);
}

export async function getAccuracyStats(
  priceMin?: number,
  priceMax?: number
): Promise<AccuracyStat[]> {
  let path = "/api/v1/stats/accuracy";
  const params: string[] = [];
  if (priceMin !== undefined) params.push(`price_min=${priceMin}`);
  if (priceMax !== undefined) params.push(`price_max=${priceMax}`);
  if (params.length > 0) path += `?${params.join("&")}`;
  return fetchAPI<AccuracyStat[]>(path);
}

export interface FeedbackSubmit {
  message: string;
  name?: string;
  contact?: string;
  page_url: string;
}

export interface FeedbackItem {
  id: number;
  message: string;
  name: string | null;
  contact: string | null;
  page_url: string;
  created_at: string;
}

export async function submitFeedback(payload: FeedbackSubmit): Promise<FeedbackItem> {
  const res = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `API error ${res.status}`;
    try {
      const err = (await res.json()) as {
        detail?: string | Array<{ msg?: string; loc?: unknown }>;
      };
      if (typeof err.detail === "string") {
        detail = err.detail;
      } else if (Array.isArray(err.detail)) {
        detail = err.detail
          .map((d) => (typeof d.msg === "string" ? d.msg : JSON.stringify(d)))
          .join("; ");
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<FeedbackItem>;
}
