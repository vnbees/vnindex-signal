# Investigation Report: price-tracking-backfill

mode: implement

## Request
Khi chạy prompt trong khung giờ 15h30–16h30, ngoài việc update dữ liệu tín hiệu mới ra, thống kê và giá T+ ở các ngày trước cũng phải được cập nhật đúng và chính xác. Hiện tại các signals cũ (run_date trước hôm nay) không được backfill T+1/T+5/T+10/T+20 khi chạy prompt.

---

## Draft v1 — AI A
agent_count: 7
agents_succeeded: 7/7

### Understanding
Endpoint `GET /price-updates/pending` có `limit=50` mặc định khiến chỉ 50 signals đầu được check. Với nhiều run_dates (mỗi ngày 30 signals), các signals từ những ngày cũ hơn bị bỏ qua hoàn toàn — không bao giờ được backfill T+1/T+5/T+10/T+20. Ngoài ra, Bước 6B của prompt chưa có logic lấy thêm data Fireant cho mã không có trong TOP N hôm nay một cách rõ ràng.

### Evidence

**price_updates.py:32,37** — limit=50 cứng:
```python
async def get_pending_updates(
    limit: int = 50,          # ← default quá nhỏ
    ...
):
    result = await db.execute(
        select(Signal).where(Signal.status == "active")
        .order_by(Signal.run_date.desc())
        .limit(limit)          # ← chỉ lấy 50 signals đầu
    )
```

**Tính toán thực tế:** 7 run_dates × 30 signals = 210 signals active → limit=50 bỏ sót 160 signals cuối (các run_dates cũ hơn).

**main-prompt.txt:239-245** — Bước 6B.2 mới thêm có logic đúng nhưng còn thiếu explicit loop để đảm bảo fetch tất cả mã:
```
Lấy thêm historical-quotes cho các mã trong pending chưa có data từ Bước 2A.
```
Tuy nhiên nếu limit=50 không được fix, Bước 6B.2 không bao giờ nhận được signals cũ để fetch.

### Root Cause / What Needs to Change
| File | Line | Current | Should Be | Reason |
|------|------|---------|-----------|--------|
| backend/routers/price_updates.py | 32 | `limit: int = 50` | `limit: int = 500` | 50 quá nhỏ khi có nhiều run_dates, 500 đủ cho ~16 ngày × 30 signals |
| backend/routers/price_updates.py | 37 | `.limit(limit)` trên Signal query | giữ nguyên (tăng default là đủ) | limit áp dụng trên số signals, không phải số pending items |
| main-prompt.txt | 229 | `GET /price-updates/pending` không có param | thêm `?limit=500` explicit | đảm bảo lấy đủ signals dù default thay đổi |

### Final Proposed Changes v1

1. **[backend/routers/price_updates.py:32]** — Tăng default limit từ `50` → `500`
2. **[main-prompt.txt:229]** — Thêm `?limit=500` vào URL GET /price-updates/pending để explicit

---

## Review v1 — AI B
### Feedback
- [FB-1-001] price_updates.py:32 — limit=500 vẫn là magic number, nên bỏ limit hoàn toàn hoặc dùng số rất lớn để đảm bảo không bao giờ truncate
- [FB-1-002] main-prompt.txt:239 — Bước 6B.2 cần fetch **tất cả** unique symbols từ pending (không chỉ thiếu), vì Bước 2A chỉ lấy top N hôm nay, không đảm bảo có đủ signals cũ
- [FB-1-003] main-prompt.txt:229 — Cần explicit `?limit=10000` trong URL

## Review v2 — AI B
### Feedback
- [FB-2-001] main-prompt.txt:243 — limit=1000 không đủ → KHÔNG HỢP LỆ: 1000 phiên = ~4 năm, T+20 của signal 30 ngày trước chỉ cần ~50 ngày, hoàn toàn trong phạm vi
- [FB-2-002] main-prompt.txt:239 — làm rõ tiêu chí fetch → ĐÃ GIẢI QUYẾT bằng Draft v2 change #3: fetch tất cả unique symbols từ pending thay vì chỉ thiếu

> NO NEW FEEDBACK — Analysis complete, proceed to implementation

---

## Implementation Summary — AI C
### Files Changed
- [backend/routers/price_updates.py:32](backend/routers/price_updates.py#L32) — `limit: int = 50` → `limit: int = 10000`
- [main-prompt.txt:229](main-prompt.txt#L229) — thêm `?limit=10000` vào URL
- [main-prompt.txt:239-245](main-prompt.txt#L239) — Sửa Bước 6B.2: fetch cho tất cả unique symbols trong pending, không chỉ mã thiếu
### Notes / Deviations
- none
### Status: DONE

---

## Verification — AI A v1
- limit=10000 confirmed tại price_updates.py:32
- `?limit=10000` confirmed tại main-prompt.txt:229
- Bước 6B.2 fetch cho tất cả unique symbols confirmed
- Flow với 210 signals hoạt động đúng

**Verdict: APPROVED**

## Verification — AI B v1
- 3 changes confirmed implemented đúng
- Scenario 7 run_dates × 30 signals: limit=10000 >> 210, không truncate
- Không có blocking issue

**Verdict: APPROVED**

## Final Verification — APPROVED

---

## Draft v2 — AI A
agent_count: 7
agents_succeeded: 7/7

### Resolved
- [FB-1-001] — Tăng default limit từ 50 → 10000 (không bao giờ truncate)
- [FB-1-002] — Sửa Bước 6B.2: fetch cho tất cả unique symbols trong pending
- [FB-1-003] — Thêm `?limit=10000` trong prompt URL

### Final Proposed Changes v2

1. **[backend/routers/price_updates.py:32]** — `limit: int = 50` → `limit: int = 10000`
2. **[main-prompt.txt:229]** — Thêm `?limit=10000` vào URL GET /price-updates/pending
3. **[main-prompt.txt:239-245]** — Sửa Bước 6B.2: fetch historical-quotes cho **tất cả** unique symbols từ pending (không chỉ mã chưa có trong Bước 2A), chạy song song

---
