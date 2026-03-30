# Investigation Report: main-prompt-compatibility

mode: query-only

## Request
Khi chạy main-prompt.txt thì mọi thứ sẽ hoạt động bình thường, không cần update gì thêm đúng không?

Context: Hệ thống vừa đổi thống kê từ T+1/T+5/T+20 sang T+3/T+10/T+20. Migration 002 đã chạy thành công trên PROD (`alembic current = 002 head`).

---

## Draft v1 — AI A
agent_count: 3
agents_succeeded: 3/3

### Understanding
Câu hỏi là liệu `main-prompt.txt` (file hướng dẫn Playwright agent chạy toàn bộ luồng signal + price tracking) có cần update sau khi đổi T+1/T+5 → T+3/T+10 không.

### Evidence

#### main-prompt.txt — KHÔNG đề cập T+1/T+5 cứng nhắc
File không hardcode T+1, T+5, pnl_d1, pnl_d5, days_after=1/5 ở bất kỳ chỗ nào liên quan đến logic tracking. Các section liên quan:

- **Line 5**: `HOLD_DAYS = 20` — tổng số phiên tracking, không thay đổi
- **Line 229**: `GET {WEBSITE_URL}/api/v1/price-updates/pending?limit=10000` — endpoint đúng, không đổi
- **Line 231**: Response format `{signal_id, symbol, run_date, track_dates_needed, needs_price_open_t1}` — vẫn đúng
- **Line 253-262**: `POST {WEBSITE_URL}/api/v1/price-updates` với body `{track_date, prices, skip_refresh}` — vẫn đúng

#### Backend price_updates.py — Không cần thay đổi
`price_updates.py:96-99`: Vẫn populate `price_open_t1` khi `days_after == 1` — đây là reference price để tính PnL, **vẫn cần** dù bỏ T+1 khỏi stats

#### Backend signal_pnl_summary view — ĐÃ cập nhật qua migration 002
- JOIN `pt_3  ON days_after = 3` → `pnl_d3`
- JOIN `pt_10 ON days_after = 10` → `pnl_d10`
- JOIN `pt_20 ON days_after = 20` → `pnl_d20`

#### Backend signals.py, stats.py, schemas — ĐÃ cập nhật
Tất cả đã dùng `pnl_d3`, `pnl_d10`, không còn `pnl_d1`, `pnl_d5`

#### Frontend — ĐÃ cập nhật
- `api.ts`: interfaces dùng `pnl_d3`, `avg_pnl_d3`, `winrate_d3`
- `SignalTable.tsx`: headers T+3, T+10, T+20
- `PnlChart.tsx`: data points T+3, T+10, T+20
- `PnlStatsChart.tsx`: bars T+3, T+10, T+20
- `stats/page.tsx`: headers và data bindings đúng

#### export.py — CHƯA cập nhật (nhưng không liên quan main-prompt)
`export.py:27` vẫn SELECT `pnl_d1, pnl_d5` — sẽ lỗi nếu gọi endpoint export CSV. Nhưng main-prompt.txt không gọi endpoint này.

### Root Cause / What Needs to Change
| Phần | Status | Ghi chú |
|------|--------|---------|
| main-prompt.txt | ✅ Không cần sửa | Không hardcode T+1/T+5 |
| Migration 002 | ✅ Đã chạy trên PROD | Confirmed: `alembic current = 002 head` |
| Backend signals/stats | ✅ Đã cập nhật | Dùng pnl_d3/pnl_d10 |
| Frontend | ✅ Đã cập nhật | Hiển thị T+3/T+10/T+20 |
| export.py | ⚠️ Chưa cập nhật | Nhưng main-prompt không gọi export |

### Final Proposed Changes v1
Không có gì cần thay đổi để main-prompt.txt chạy bình thường. Query-only — không implement.

---

## Review v1 — AI B
### Feedback
- [FB-1-001] `backend/services/calendar_service.py:43` — `targets = [1, 5, 10, 20]` vẫn hardcode T+1/T+5. View signal_pnl_summary kỳ vọng `days_after = 3` nhưng price_tracking chỉ có `days_after = 1, 5` → `pnl_d3` sẽ luôn NULL cho signal mới
- [FB-1-002] `backend/routers/export.py:27,38` — query `pnl_d1, pnl_d5` không còn tồn tại trong view → export endpoint sẽ crash

---

## Draft v2 — AI A
agent_count: 3
agents_succeeded: 3/3

### Resolved
- [FB-1-001] — Confirmed: `calendar_service.py:43` là `targets = [1, 5, 10, 20]`. Cần đổi thành `[3, 10, 20]`. **Critical** — price tracking lưu `days_after=1,5` nhưng view JOIN `days_after=3,10` → pnl_d3/pnl_d10 NULL mãi mãi
- [FB-1-002] — Confirmed: export.py query cột không tồn tại. Cần fix nhưng không liên quan main-prompt trực tiếp

### Final Proposed Changes v2
Query-only mode — không implement. Nhưng cần fix 2 file trên.

---

## Review v2 — AI B
> NO NEW FEEDBACK — Analysis complete, proceed to implementation
