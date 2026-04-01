"use client";

import { useMemo, useState } from "react";

interface Props {
  defaultCapital?: number;
  symbol?: string;
}

function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

function formatCapital(value: string): string {
  if (!value) return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return new Intl.NumberFormat("vi-VN").format(n);
}

export function CapitalInputForm({ defaultCapital, symbol }: Props) {
  const initialDigits = useMemo(() => (defaultCapital && defaultCapital > 0 ? String(Math.trunc(defaultCapital)) : ""), [defaultCapital]);
  const [capitalDigits, setCapitalDigits] = useState(initialDigits);

  return (
    <form method="GET" className="flex flex-wrap items-end gap-3 mb-4">
      {symbol && <input type="hidden" name="symbol" value={symbol} />}
      <input type="hidden" name="capital" value={capitalDigits} />
      <label className="min-w-[220px] flex-1">
        <span className="text-xs text-tv-muted">Vốn muốn vào lệnh (đ)</span>
        <input
          type="text"
          inputMode="numeric"
          value={formatCapital(capitalDigits)}
          placeholder="VD: 10.000.000"
          onChange={(e) => setCapitalDigits(digitsOnly(e.target.value))}
          className="mt-1 w-full rounded-md border border-tv-border bg-tv-panel px-3 py-2 text-sm text-tv-text outline-none focus:border-tv-accent"
        />
      </label>
      <button
        type="submit"
        className="rounded-md bg-tv-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
      >
        Tính gợi ý mua
      </button>
    </form>
  );
}
