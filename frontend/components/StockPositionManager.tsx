"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createStockPosition,
  deleteStockPosition,
  getStockPositions,
  sellStockPosition,
  type StockPosition,
} from "@/lib/api";
import { calcHorizonStatsFromValues, StatChip } from "@/components/PnlStatChips";
import { formatDate, formatPnl, formatPrice, getPnlClass } from "@/lib/utils";

function todayVN(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" });
}

function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

function parsePriceInput(value: string): number | null {
  const d = digitsOnly(value);
  if (!d) return null;
  const n = Number(d);
  return Number.isFinite(n) && n > 0 ? n : null;
}

const inputClass =
  "mt-1 w-full rounded-md border border-tv-border bg-tv-panel px-3 py-2 text-sm text-tv-text outline-none focus:border-tv-accent";

export function StockPositionManager() {
  const [items, setItems] = useState<StockPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [buySymbol, setBuySymbol] = useState("");
  const [buySignalDate, setBuySignalDate] = useState(todayVN);
  const [buyValuation, setBuyValuation] = useState("");
  const [buyPrice, setBuyPrice] = useState("");

  const [sellId, setSellId] = useState("");
  const [sellPrice, setSellPrice] = useState("");
  const [sellDate, setSellDate] = useState(todayVN);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getStockPositions("all");
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được danh sách.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openItems = useMemo(() => items.filter((i) => i.status === "open"), [items]);
  const closedItems = useMemo(() => items.filter((i) => i.status === "closed"), [items]);

  const openUnrealizedStats = calcHorizonStatsFromValues(openItems.map((i) => i.unrealized_pnl_pct));
  const closedRealizedStats = calcHorizonStatsFromValues(closedItems.map((i) => i.realized_pnl_pct));
  const stats3d = calcHorizonStatsFromValues(openItems.map((i) => i.pnl_3d_pct));
  const stats5d = calcHorizonStatsFromValues(openItems.map((i) => i.pnl_5d_pct));
  const stats10d = calcHorizonStatsFromValues(openItems.map((i) => i.pnl_10d_pct));

  async function handleBuy(e: React.FormEvent) {
    e.preventDefault();
    const symbol = buySymbol.trim().toUpperCase();
    const price = parsePriceInput(buyPrice);
    const valuation = buyValuation.trim() ? parsePriceInput(buyValuation) : null;
    if (!symbol) {
      setError("Vui lòng nhập mã cổ phiếu.");
      return;
    }
    if (price == null) {
      setError("Giá mua phải lớn hơn 0.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createStockPosition({
        symbol,
        signal_date: buySignalDate,
        buy_price: price,
        valuation_price: valuation ?? undefined,
      });
      setBuySymbol("");
      setBuyValuation("");
      setBuyPrice("");
      setBuySignalDate(todayVN());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thêm được lệnh mua.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSell(e: React.FormEvent) {
    e.preventDefault();
    const id = Number(sellId);
    const price = parsePriceInput(sellPrice);
    if (!id || !openItems.some((p) => p.id === id)) {
      setError("Chọn vị thế đang mở để bán.");
      return;
    }
    if (price == null) {
      setError("Giá bán phải lớn hơn 0.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await sellStockPosition(id, { sell_price: price, sell_date: sellDate });
      setSellId("");
      setSellPrice("");
      setSellDate(todayVN());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ghi được lệnh bán.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Xóa vị thế này?")) return;
    setBusy(true);
    setError("");
    try {
      await deleteStockPosition(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold text-tv-text tracking-tight">Quản lý mua bán</h1>
        <p className="mt-1 text-sm text-tv-muted">
          Nhập tín hiệu mua/bán thủ công. Giá được cập nhật tự động sau 16h30 các ngày giao dịch.
        </p>
      </header>

      {error ? (
        <p className="rounded border border-tv-border bg-tv-panel p-3 text-sm text-tv-down">{error}</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="tv-panel p-4">
          <h2 className="tv-section-title mb-3">Nhập mua</h2>
          <form onSubmit={handleBuy} className="space-y-3">
            <label className="block">
              <span className="text-xs text-tv-muted">Mã cổ phiếu</span>
              <input
                type="text"
                value={buySymbol}
                onChange={(e) => setBuySymbol(e.target.value.toUpperCase())}
                placeholder="VD: FPT"
                className={inputClass}
                required
              />
            </label>
            <label className="block">
              <span className="text-xs text-tv-muted">Ngày có tín hiệu</span>
              <input
                type="date"
                value={buySignalDate}
                onChange={(e) => setBuySignalDate(e.target.value)}
                className={inputClass}
                required
              />
            </label>
            <label className="block">
              <span className="text-xs text-tv-muted">Định giá (tùy chọn)</span>
              <input
                type="text"
                inputMode="numeric"
                value={buyValuation}
                onChange={(e) => setBuyValuation(e.target.value)}
                placeholder="VD: 100000"
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className="text-xs text-tv-muted">Giá mua</span>
              <input
                type="text"
                inputMode="numeric"
                value={buyPrice}
                onChange={(e) => setBuyPrice(e.target.value)}
                placeholder="VD: 95000"
                className={inputClass}
                required
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-tv-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              Thêm mua
            </button>
          </form>
        </section>

        <section className="tv-panel p-4">
          <h2 className="tv-section-title mb-3">Ghi bán</h2>
          {openItems.length === 0 ? (
            <p className="text-sm text-tv-muted">Chưa có vị thế đang mở.</p>
          ) : (
            <form onSubmit={handleSell} className="space-y-3">
              <label className="block">
                <span className="text-xs text-tv-muted">Chọn cổ phiếu đã mua</span>
                <select
                  value={sellId}
                  onChange={(e) => setSellId(e.target.value)}
                  className={inputClass}
                  required
                >
                  <option value="">-- Chọn mã --</option>
                  {openItems.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.symbol} — mua {formatDate(p.signal_date)} @ {formatPrice(p.buy_price)} đ
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-xs text-tv-muted">Giá bán</span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={sellPrice}
                  onChange={(e) => setSellPrice(e.target.value)}
                  placeholder="VD: 98000"
                  className={inputClass}
                  required
                />
              </label>
              <label className="block">
                <span className="text-xs text-tv-muted">Ngày bán</span>
                <input
                  type="date"
                  value={sellDate}
                  onChange={(e) => setSellDate(e.target.value)}
                  className={inputClass}
                  required
                />
              </label>
              <button
                type="submit"
                disabled={busy}
                className="rounded-md border border-tv-border px-4 py-2 text-sm font-medium text-tv-text hover:bg-tv-panel disabled:opacity-50"
              >
                Ghi bán
              </button>
            </form>
          )}
        </section>
      </div>

      <section className="rounded-lg border border-tv-border bg-tv-panel p-4 space-y-4">
        <p className="text-sm font-medium text-tv-text">Thống kê (danh sách hiện tại)</p>
        <div>
          <p className="text-xs text-tv-muted mb-2">Vị thế đang mở — PnL chưa chốt</p>
          <div className="grid gap-2 sm:grid-cols-4">
            <StatChip label="PnL hiện tại" stats={openUnrealizedStats} />
            <StatChip label="Sau 3 phiên" stats={stats3d} />
            <StatChip label="Sau 5 phiên" stats={stats5d} />
            <StatChip label="Sau 10 phiên" stats={stats10d} />
          </div>
        </div>
        <div>
          <p className="text-xs text-tv-muted mb-2">Vị thế đã bán — PnL đã chốt</p>
          <StatChip label="Lãi/lỗ đã chốt" stats={closedRealizedStats} />
        </div>
      </section>

      <section className="tv-panel p-4 overflow-x-auto">
        <h2 className="tv-section-title mb-3">Danh sách</h2>
        {loading ? (
          <p className="text-sm text-tv-muted">Đang tải...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-tv-muted">Chưa có lệnh nào.</p>
        ) : (
          <table className="w-full text-sm text-left min-w-[900px]">
            <thead>
              <tr className="text-xs text-tv-muted border-b border-tv-border">
                <th className="py-2 pr-3">Mã</th>
                <th className="py-2 pr-3">Ngày TH</th>
                <th className="py-2 pr-3">Định giá</th>
                <th className="py-2 pr-3">Giá mua</th>
                <th className="py-2 pr-3">Giá hiện tại</th>
                <th className="py-2 pr-3">PnL %</th>
                <th className="py-2 pr-3">3/5/10 phiên</th>
                <th className="py-2 pr-3">Bán</th>
                <th className="py-2"> </th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                const pnl = p.status === "open" ? p.unrealized_pnl_pct : p.realized_pnl_pct;
                return (
                  <tr key={p.id} className="border-b border-tv-border/60">
                    <td className="py-2 pr-3 font-semibold text-tv-text">{p.symbol}</td>
                    <td className="py-2 pr-3 text-tv-muted">{formatDate(p.signal_date)}</td>
                    <td className="py-2 pr-3 text-tv-muted">
                      {p.valuation_price != null ? `${formatPrice(p.valuation_price)} đ` : "—"}
                    </td>
                    <td className="py-2 pr-3">{formatPrice(p.buy_price)} đ</td>
                    <td className="py-2 pr-3">
                      {p.current_price != null ? (
                        <>
                          {formatPrice(p.current_price)} đ
                          {p.price_as_of ? (
                            <span className="block text-xs text-tv-muted">{formatDate(p.price_as_of)}</span>
                          ) : null}
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className={`py-2 pr-3 ${getPnlClass(pnl)}`}>{formatPnl(pnl)}</td>
                    <td className="py-2 pr-3 text-xs">
                      <span className={getPnlClass(p.pnl_3d_pct)}>3d: {formatPnl(p.pnl_3d_pct)}</span>
                      {" · "}
                      <span className={getPnlClass(p.pnl_5d_pct)}>5d: {formatPnl(p.pnl_5d_pct)}</span>
                      {" · "}
                      <span className={getPnlClass(p.pnl_10d_pct)}>10d: {formatPnl(p.pnl_10d_pct)}</span>
                    </td>
                    <td className="py-2 pr-3 text-tv-muted">
                      {p.sell_price != null && p.sell_date ? (
                        <>
                          {formatDate(p.sell_date)} @ {formatPrice(p.sell_price)} đ
                        </>
                      ) : (
                        <span className="text-tv-accent">Đang mở</span>
                      )}
                    </td>
                    <td className="py-2">
                      <button
                        type="button"
                        onClick={() => void handleDelete(p.id)}
                        disabled={busy}
                        className="text-xs text-tv-down hover:underline disabled:opacity-50"
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
