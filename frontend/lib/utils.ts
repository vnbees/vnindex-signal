import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | string | null): string {
  if (price === null || price === undefined) return "—";
  const n = Number(price);
  if (isNaN(n)) return "—";
  return new Intl.NumberFormat("vi-VN").format(n);
}

export function formatPnl(pnl: number | string | null): string {
  if (pnl === null || pnl === undefined) return "—";
  const n = Number(pnl);
  if (isNaN(n)) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export function getPnlClass(pnl: number | string | null): string {
  if (pnl === null || pnl === undefined) return "text-tv-muted";
  const n = Number(pnl);
  if (isNaN(n)) return "text-tv-muted";
  if (n > 0) return "text-tv-up font-medium";
  if (n < 0) return "text-tv-down font-medium";
  return "text-tv-muted";
}

export function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

export function getRecommendationConfig(rec: string) {
  switch (rec) {
    case "BUY_STRONG":
      return {
        label: "Mua mạnh",
        color: "bg-emerald-950/80 text-emerald-300 border border-emerald-500/35",
        emoji: "●●",
      };
    case "BUY":
      return {
        label: "Mua",
        color: "bg-emerald-900/70 text-emerald-200 border border-emerald-600/30",
        emoji: "●",
      };
    case "HOLD":
      return {
        label: "Theo dõi",
        color: "bg-amber-950/70 text-amber-200 border border-amber-500/35",
        emoji: "●",
      };
    case "AVOID":
      return {
        label: "Tránh",
        color: "bg-orange-950/70 text-orange-200 border border-orange-500/35",
        emoji: "●",
      };
    case "SELL":
      return {
        label: "Bán",
        color: "bg-red-950/80 text-red-200 border border-red-500/40",
        emoji: "●",
      };
    default:
      return {
        label: rec,
        color: "bg-tv-panel-hover text-tv-muted border border-tv-border",
        emoji: "○",
      };
  }
}
