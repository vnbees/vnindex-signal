# Investigation Report: stats-t3-t10-t20

mode: implement

## Request
Hiện tại đang thống kê theo t1 t5 và t20, tôi muốn đổi lại thành t3 t10 và t20

---

## Draft v1 — AI A
agent_count: 7
agents_succeeded: 7/7

### Understanding
Thay đổi các cột thống kê hiển thị từ T+1/T+5/T+20 sang T+3/T+10/T+20 trên trang stats và bảng signals. T+10 đã có trong DB (`pnl_d10`), nhưng T+3 (`pnl_d3`) chưa tồn tại — cần thêm vào materialized view và toàn bộ data pipeline.

### Evidence

**Materialized view hiện tại** (`001_initial_schema.py`):
```sql
LEFT JOIN price_tracking pt_1  ON pt_1.signal_id = s.id AND pt_1.days_after = 1
LEFT JOIN price_tracking pt_5  ON pt_5.signal_id = s.id AND pt_5.days_after = 5
LEFT JOIN price_tracking pt_10 ON pt_10.signal_id = s.id AND pt_10.days_after = 10
LEFT JOIN price_tracking pt_20 ON pt_20.signal_id = s.id AND pt_20.days_after = 20
-- Output columns: pnl_d1, pnl_d5, pnl_d10, pnl_d20
```

**Bảng thống kê PnL** (`stats/page.tsx:43-46`):
```tsx
<th>T+1</th>
<th>T+5</th>
<th>T+10</th>
<th>T+20</th>
```

**Bảng Win Rate** (`stats/page.tsx:72-74`):
```tsx
<th>Win T+1</th>
<th>Win T+5</th>
<th>Win T+20</th>
```

**Biểu đồ** (`PnlStatsChart.tsx:14-16`):
```tsx
"T+1": d.avg_pnl_d1,
"T+5": d.avg_pnl_d5,
"T+20": d.avg_pnl_d20,
```

**SignalTable** (`SignalTable.tsx:59-61`):
```tsx
<th>T+1</th>
<th>T+5</th>
<th>T+20</th>
-- Dữ liệu: pnl_d1, pnl_d5, pnl_d20
```

**PnlChart** (`PnlChart.tsx:21-26`):
```tsx
{ day: "T+1", pnl: toNum(pnlD1) },
{ day: "T+5", pnl: toNum(pnlD5) },
{ day: "T+10", pnl: toNum(pnlD10) },
{ day: "T+20", pnl: toNum(pnlD20) },
```

**API & Types** (`lib/api.ts`):
- `PnlStat`: có `avg_pnl_d1, avg_pnl_d5, avg_pnl_d10, avg_pnl_d20`
- `AccuracyStat`: có `win_d1, win_d5, win_d20, winrate_d1, winrate_d5, winrate_d20`
- `Signal`: có `pnl_d1, pnl_d5, pnl_d10, pnl_d20`

**Backend schema** (`schemas/signal_output.py`):
- `SignalListItem`: có `pnl_d1, pnl_d5, pnl_d10, pnl_d20`
- `PendingPriceUpdate`: không liên quan trực tiếp

### Root Cause / What Needs to Change

| File | Line | Current | Should Be | Reason |
|------|------|---------|-----------|--------|
| `backend/alembic/versions/002_add_pnl_d3.py` | NEW | — | Migration thêm `pnl_d3` vào materialized view | T+3 chưa có trong DB |
| `backend/routers/stats.py` | 13-18 | `AVG(pnl_d1)`, `AVG(pnl_d5)` | `AVG(pnl_d3)`, `AVG(pnl_d10)` | Đổi cột thống kê |
| `backend/routers/stats.py` | 30-42 | `pnl_d1`, `pnl_d5`, `winrate_d1`, `winrate_d5` | `pnl_d3`, `pnl_d10`, `winrate_d3`, `winrate_d10` | Đổi win rate columns |
| `backend/schemas/signal_output.py` | 20-22 | `pnl_d1, pnl_d5` | `pnl_d3, pnl_d10` (thêm `pnl_d3`) | Schema cần thêm field mới |
| `frontend/lib/api.ts` | 38-41 | `avg_pnl_d1, avg_pnl_d5` | `avg_pnl_d3, avg_pnl_d10` | Type interface |
| `frontend/lib/api.ts` | 49-53 | `win_d1, win_d5, winrate_d1, winrate_d5` | `win_d3, win_d10, winrate_d3, winrate_d10` | AccuracyStat interface |
| `frontend/lib/api.ts` | 22-23 | `pnl_d1, pnl_d5` | thêm `pnl_d3` | Signal interface |
| `frontend/app/stats/page.tsx` | 43-46 | T+1, T+5 headers | T+3, T+10 | Bảng PnL |
| `frontend/app/stats/page.tsx` | 51-58 | `avg_pnl_d1, avg_pnl_d5` | `avg_pnl_d3, avg_pnl_d10` | Data binding |
| `frontend/app/stats/page.tsx` | 72-74 | Win T+1, Win T+5 | Win T+3, Win T+10 | Bảng win rate |
| `frontend/app/stats/page.tsx` | 80-85 | `winrate_d1, winrate_d5` | `winrate_d3, winrate_d10` | Data binding |
| `frontend/components/PnlStatsChart.tsx` | 14-16 | T+1, T+5 | T+3, T+10 | Biểu đồ bar |
| `frontend/components/SignalTable.tsx` | 59-61 | T+1, T+5 | T+3, T+10 | Cột bảng |
| `frontend/components/SignalTable.tsx` | 85-89 | `pnl_d1, pnl_d5` | `pnl_d3, pnl_d10` | Data binding |
| `frontend/components/PnlChart.tsx` | 21-24 | T+1, T+5 data points | T+3, T+10 | Line chart points |

### Final Proposed Changes v1

1. **`backend/alembic/versions/002_add_pnl_d3.py`** (NEW) — Tạo migration thêm `pnl_d3` vào materialized view `signal_pnl_summary` bằng cách DROP và RECREATE với thêm LEFT JOIN `days_after = 3`

2. **`backend/routers/stats.py`** — Đổi SQL: thay `pnl_d1→pnl_d3`, `pnl_d5→pnl_d10` trong cả 2 endpoints (`/stats/pnl` và `/stats/accuracy`). Xóa `avg_pnl_d1`, `avg_pnl_d5`; thêm `avg_pnl_d3`, `avg_pnl_d10`. Winrate: xóa `winrate_d1`, `winrate_d5`; thêm `winrate_d3`, `winrate_d10`.

3. **`backend/schemas/signal_output.py`** — Thêm `pnl_d3: Optional[Decimal] = None` vào `SignalListItem`. Cập nhật `PendingPriceUpdate` nếu cần (không cần vì nó không dùng pnl fields trực tiếp).

4. **`frontend/lib/api.ts`** — Cập nhật interfaces:
   - `Signal`: thêm `pnl_d3: number | null`
   - `PnlStat`: thay `avg_pnl_d1→avg_pnl_d3`, `avg_pnl_d5→avg_pnl_d10`
   - `AccuracyStat`: thay `win_d1→win_d3`, `win_d5→win_d10`, `winrate_d1→winrate_d3`, `winrate_d5→winrate_d10`

5. **`frontend/app/stats/page.tsx`** — Đổi headers T+1→T+3, T+5→T+10; đổi data bindings `avg_pnl_d1→avg_pnl_d3`, `avg_pnl_d5→avg_pnl_d10`, `winrate_d1→winrate_d3`, `winrate_d5→winrate_d10`

6. **`frontend/components/PnlStatsChart.tsx`** — Đổi keys: `"T+1"→"T+3"`, `"T+5"→"T+10"`, cập nhật data mapping sang `avg_pnl_d3`, `avg_pnl_d10`

7. **`frontend/components/SignalTable.tsx`** — Đổi headers và PnlBadge: T+1→T+3, T+5→T+10, `pnl_d1→pnl_d3`, `pnl_d5→pnl_d10`

8. **`frontend/components/PnlChart.tsx`** — Đổi data points: T+1→T+3 (dùng `pnlD3`), T+5→T+10 (dùng `pnlD10`); cập nhật Props interface thêm `pnlD3`, xóa `pnlD1`, xóa `pnlD5`

---

## Review v1 — AI B
agent_count: 7
agents_succeeded: 7/7

### Feedback

- [FB-1-001] `frontend/components/PnlChart.tsx:Props` — Component này nhận `pnlD1, pnlD5` từ caller. Cần kiểm tra file `signals/[date]/[symbol]/page.tsx` để biết caller truyền props như thế nào, tránh break caller.

- [FB-1-002] `backend/schemas/signal_output.py` — `pnl_d1` và `pnl_d5` vẫn cần giữ lại trong schema nếu materialized view vẫn còn các columns đó (view sẽ rebuild với pnl_d3 thay pnl_d1/pnl_d5, nhưng pnl_d5 và pnl_d1 sẽ bị xóa khỏi view). Cần xác nhận: ta sẽ XÓA `pnl_d1` và `pnl_d5` khỏi view, hay chỉ THÊM `pnl_d3`? Điều này ảnh hưởng đến backward compatibility của API.

- [FB-1-003] `backend/routers/signals.py` — Chưa kiểm tra file này. Nó có SELECT `pnl_d1, pnl_d5` từ materialized view không? Nếu có thì sẽ break sau khi view thay đổi.

> Cần kiểm tra thêm: `signals/[date]/[symbol]/page.tsx` và `backend/routers/signals.py` trước khi implement.

---

## Draft v2 — AI A
agent_count: 7
agents_succeeded: 7/7

### Resolved

- [FB-1-001] Đã kiểm tra `signals/[date]/[symbol]/page.tsx` — xem thêm dưới
- [FB-1-002] Quyết định: **XÓA pnl_d1 và pnl_d5, THÊM pnl_d3** khỏi materialized view. Đây là thay đổi breaking của internal API nhưng không có external consumers. Frontend sẽ được cập nhật đồng bộ.
- [FB-1-003] Đã kiểm tra `backend/routers/signals.py`

### Additional Evidence (from FB investigation)

**`backend/routers/signals.py`** — SELECT từ `signal_pnl_summary`:
```python
# Dùng Pydantic schema SignalListItem, map từ materialized view
# Có pnl_d1, pnl_d5, pnl_d10, pnl_d20 trong SELECT
```

**`frontend/app/signals/[date]/[symbol]/page.tsx`** — Truyền props vào PnlChart:
```tsx
<PnlChart
  symbol={signal.symbol}
  pnlD1={signal.pnl_d1}
  pnlD5={signal.pnl_d5}
  pnlD10={signal.pnl_d10}
  pnlD20={signal.pnl_d20}
/>
```
→ Caller truyền `pnlD1` và `pnlD5`. Sau khi đổi, caller sẽ truyền `pnlD3` và không còn `pnlD5`.

### Final Proposed Changes v2

1. **`backend/alembic/versions/002_add_pnl_d3.py`** (NEW) — Migration DROP và RECREATE `signal_pnl_summary` với:
   - Xóa `pt_1` (days_after=1) và `pt_5` (days_after=5)
   - Thêm `pt_3` (days_after=3)
   - Giữ `pt_10` (days_after=10) và `pt_20` (days_after=20)
   - Output columns: `pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct`

2. **`backend/routers/stats.py`** — Đổi cả 2 endpoints:
   - `/stats/pnl`: `AVG(pnl_d1)→AVG(pnl_d3)`, `AVG(pnl_d5)→AVG(pnl_d10)`, xóa `avg_pnl_d1`/`avg_pnl_d5`, thêm `avg_pnl_d3`/`avg_pnl_d10`
   - `/stats/accuracy`: thay `pnl_d1→pnl_d3`, `pnl_d5→pnl_d10` trong CASE WHEN, cập nhật column aliases

3. **`backend/schemas/signal_output.py`** — Cập nhật `SignalListItem`: thay `pnl_d1→pnl_d3`, `pnl_d5` xóa (hoặc giữ optional để backward compat)

4. **`frontend/lib/api.ts`** — Cập nhật 3 interfaces:
   - `Signal`: thêm `pnl_d3`, xóa `pnl_d1`, xóa `pnl_d5`
   - `PnlStat`: `avg_pnl_d1→avg_pnl_d3`, `avg_pnl_d5→avg_pnl_d10`
   - `AccuracyStat`: `win_d1→win_d3`, `win_d5→win_d10`, tương tự winrate

5. **`frontend/app/stats/page.tsx`** — Headers + data bindings: T+1→T+3, T+5→T+10

6. **`frontend/components/PnlStatsChart.tsx`** — Đổi keys và data: T+1→T+3, T+5→T+10

7. **`frontend/components/SignalTable.tsx`** — Headers + PnlBadge: T+1→T+3, T+5→T+10

8. **`frontend/components/PnlChart.tsx`** — Props: thêm `pnlD3`, xóa `pnlD1`/`pnlD5`; data points dùng `pnlD3` thay `pnlD1`/`pnlD5`

9. **`frontend/app/signals/[date]/[symbol]/page.tsx`** — Truyền props mới vào PnlChart: `pnlD3={signal.pnl_d3}`, xóa `pnlD1`/`pnlD5`

---

## Review v2 — AI B
agent_count: 7
agents_succeeded: 7/7

> NO NEW FEEDBACK — Analysis complete, proceed to implementation

---

## Implementation Summary — AI C
### Files Changed
- `backend/alembic/versions/002_add_pnl_d3.py` (NEW) — Migration DROP + RECREATE materialized view với pnl_d3 thay pnl_d1/pnl_d5
- `backend/routers/stats.py` — Đổi pnl_d1→pnl_d3, pnl_d5→pnl_d10 trong cả 2 SQL queries
- `backend/routers/signals.py` — Đổi SELECT và mapping: pnl_d1/pnl_d5→pnl_d3 trong cả 2 endpoints
- `backend/schemas/signal_output.py` — Xóa pnl_d1, pnl_d5; thêm pnl_d3
- `frontend/lib/api.ts` — Cập nhật Signal, PnlStat, AccuracyStat interfaces
- `frontend/app/stats/page.tsx` — Đổi headers T+1→T+3, T+5→T+10; data bindings avg_pnl_d3, avg_pnl_d10, winrate_d3, winrate_d10
- `frontend/components/PnlStatsChart.tsx` — Đổi chart keys T+1→T+3, T+5→T+10
- `frontend/components/SignalTable.tsx` — Đổi headers và PnlBadge: T+1→T+3, T+5→T+10, pnl_d3, pnl_d10
- `frontend/components/PnlChart.tsx` — Đổi Props: pnlD3 thay pnlD1/pnlD5; data points T+3, T+10, T+20
- `frontend/app/signals/[date]/[symbol]/page.tsx` — Cập nhật PnlChart props và PnL list: T+3, T+10, T+20

### Notes / Deviations
- Migration cần chạy `alembic upgrade head` trên PROD để áp dụng thay đổi materialized view
- Dữ liệu `days_after = 3` đã tồn tại trong `price_tracking` table (được track cùng với tất cả các ngày khác), materialized view sẽ có data ngay sau khi rebuild

### Status: DONE

---

## Verification — AI A v1
Đã kiểm tra tất cả 10 files:
- Migration đúng: DROP + RECREATE với pt_3 (days_after=3), xóa pt_1 và pt_5
- stats.py: SQL dùng pnl_d3, pnl_d10 — khớp với view mới
- signals.py: SELECT và mapping dùng pnl_d3 — consistent
- schemas: pnl_d3, pnl_d10, pnl_d20 — không còn pnl_d1/pnl_d5
- Frontend types: Signal, PnlStat, AccuracyStat đều updated
- stats/page.tsx: headers T+3, T+10, T+20; bindings avg_pnl_d3, avg_pnl_d10, winrate_d3, winrate_d10
- PnlStatsChart: T+3, T+10, T+20 bars với avg_pnl_d3, avg_pnl_d10
- SignalTable: headers và PnlBadge dùng pnl_d3, pnl_d10
- PnlChart: Props pnlD3, pnlD10, pnlD20; data points T+3, T+10, T+20; stroke color dùng pnlD3
- signal detail page: PnlChart nhận pnlD3={signal.pnl_d3}; PnL list: T+3, T+10, T+20

**Verdict: APPROVED**

## Verification — AI B v1
Cross-check toàn bộ data flow: DB view → API → Schema → Frontend types → UI components
- Materialized view output: pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct ✅
- Backend SELECT khớp với view columns ✅
- Pydantic schema khớp với SELECT ✅
- TypeScript interfaces khớp với API response ✅
- UI components dùng đúng field names ✅
- Không còn reference nào đến pnl_d1, pnl_d5, avg_pnl_d1, avg_pnl_d5, winrate_d1, winrate_d5, pnlD1, pnlD5 trong production code ✅

**Verdict: APPROVED**

## Final Verification — APPROVED

