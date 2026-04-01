"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback } from "react";

interface PriceRange {
  label: string;
  min?: number;
  max?: number;
}

const PRICE_RANGES: PriceRange[] = [
  { label: "Tất cả" },
  { label: "Dưới 10k", max: 10 },
  { label: "10–20k", min: 10, max: 20 },
  { label: "20–30k", min: 20, max: 30 },
  { label: "30–50k", min: 30, max: 50 },
  { label: "50–100k", min: 50, max: 100 },
  { label: "Trên 100k", min: 100 },
];

function isActive(range: PriceRange, currentMin?: string, currentMax?: string): boolean {
  const min = currentMin ? Number(currentMin) : undefined;
  const max = currentMax ? Number(currentMax) : undefined;
  if (!range.min && !range.max) return !min && !max;
  return range.min === min && range.max === max;
}

export function PriceFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const currentMin = searchParams.get("price_min") ?? undefined;
  const currentMax = searchParams.get("price_max") ?? undefined;

  const applyRange = useCallback(
    (range: PriceRange) => {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("price_min");
      params.delete("price_max");
      if (range.min !== undefined) params.set("price_min", String(range.min));
      if (range.max !== undefined) params.set("price_max", String(range.max));
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams]
  );

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-tv-muted font-medium shrink-0">Khoảng giá:</span>
      <div className="inline-flex flex-wrap gap-0 p-1 rounded-lg bg-tv-panel border border-tv-border">
        {PRICE_RANGES.map((range) => {
          const active = isActive(range, currentMin, currentMax);
          return (
            <button
              key={range.label}
              type="button"
              onClick={() => applyRange(range)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                active
                  ? "bg-tv-accent text-white shadow-sm"
                  : "text-tv-muted hover:text-tv-text hover:bg-tv-panel-hover/80"
              }`}
            >
              {range.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
