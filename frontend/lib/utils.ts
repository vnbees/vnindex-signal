import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "—";
  return new Intl.NumberFormat("vi-VN").format(price);
}

export function formatPnl(pnl: number | null): string {
  if (pnl === null || pnl === undefined) return "—";
  const sign = pnl >= 0 ? "+" : "";
  return `${sign}${pnl.toFixed(2)}%`;
}

export function getPnlClass(pnl: number | null): string {
  if (pnl === null || pnl === undefined) return "text-slate-400";
  if (pnl > 0) return "text-green-600 font-medium";
  if (pnl < 0) return "text-red-600 font-medium";
  return "text-slate-500";
}

export function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

export function getRecommendationConfig(rec: string) {
  switch (rec) {
    case "BUY_STRONG":
      return { label: "Mua mạnh", color: "bg-green-700 text-white", emoji: "🟢🟢" };
    case "BUY":
      return { label: "Mua", color: "bg-green-500 text-white", emoji: "🟢" };
    case "HOLD":
      return { label: "Theo dõi", color: "bg-yellow-400 text-slate-900", emoji: "🟡" };
    case "AVOID":
      return { label: "Tránh", color: "bg-orange-500 text-white", emoji: "🟠" };
    case "SELL":
      return { label: "Bán", color: "bg-red-600 text-white", emoji: "🔴" };
    default:
      return { label: rec, color: "bg-slate-400 text-white", emoji: "⚪" };
  }
}
