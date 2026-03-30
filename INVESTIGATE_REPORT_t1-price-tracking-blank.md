# Investigation Report: t1-price-tracking-blank

mode: implement

## Request
Hôm nay là 2026-03-27. Sau khi chạy prompt, phần t+1 của ngày hôm qua (2026-03-26) không thấy cập nhật dữ liệu, vẫn bị bỏ trống. Sau prompt thì thấy thông báo:
- "Website đã cập nhật: run_id=4, inserted=30 signals, views refreshed"
- "Không có price tracking cần update — tất cả track dates đều là tương lai (2026-03-30 trở đi)"

---

## Draft v1 — AI A
agent_count: 7
agents_succeeded: 7/7

### Understanding
Khi AI chạy prompt ngày 2026-03-27 với run_date=2026-03-26, T+1 = 2026-03-27 (hôm nay). Nhưng historical-quotes từ Fireant không có data cho ngày hôm nay (phiên chưa chốt), nên prompt bỏ qua T+1 theo đúng logic dòng 240 của main-prompt.txt. Kết quả: T+1 mãi bỏ trống vì không bao giờ được retry khi phiên đã chốt.

### Evidence

**main-prompt.txt:239-241** — Logic bỏ qua track_date:
```
Tìm price_open + price_close từ historical-quotes đã lấy ở Bước 2A
Bỏ qua nếu track_date chưa có trong historical-quotes (ngày tương lai hoặc chưa chốt phiên)
KHÔNG gửi null hoặc 0 cho price_open/price_close nếu không có data
```

**main-prompt.txt:67-68** — Historical quotes lấy từ Fireant, chỉ có dữ liệu đã chốt phiên:
```
GET https://restv2.fireant.vn/symbols/{sym}/historical-quotes
    ?startDate=2021-01-01&endDate=2030-12-31&limit=1000
```

**backend/routers/price_updates.py:30-61** — Endpoint `/price-updates/pending` không filter theo today:
```python
needed = [d for d in track_dates if d not in existing_dates]
# Không có: needed = [d for d in needed if d <= date.today()]
```

**Flow bị break:**
1. AI chạy ngày 2026-03-27, lấy historical-quotes → chỉ có data đến 2026-03-26
2. GET `/price-updates/pending` → trả về `track_dates_needed = [2026-03-27, 2026-03-30, ...]`
3. Với track_date=2026-03-27: **không có trong historical-quotes** → bị skip (dòng 240)
4. Với track_date=2026-03-30, 2026-03-31, ...: đều là tương lai → bị skip
5. **Kết quả**: không POST bất kỳ price update nào
6. **Thông báo**: AI in ra "Không có price tracking cần update — tất cả track dates đều là tương lai (2026-03-30 trở đi)"
7. T+1 (2026-03-27) bỏ trống mãi vì lần chạy kế tiếp (2026-03-28), `/price-updates/pending` cho signal run_date=2026-03-26 vẫn trả về track_dates=[2026-03-27, 2026-03-30, ...] — lúc này 2026-03-27 đã là quá khứ và CÓ trong historical-quotes → sẽ được update

**Vậy T+1 có tự được update vào ngày 2026-03-28 không?** Có — nhưng chỉ nếu prompt chạy lại. Nếu không chạy lại, T+1 mãi bỏ trống.

### Root Cause / What Needs to Change
| File | Line | Current | Should Be | Reason |
|------|------|---------|-----------|--------|
| main-prompt.txt | 239-241 | Bỏ qua track_date nếu không có trong historical-quotes (gồm cả ngày hiện tại nếu chưa chốt) | Thêm logic: sau khi bỏ qua T+1 vì chưa chốt phiên, print thông báo rõ ràng hơn rằng T+1 sẽ được cập nhật tự động khi prompt chạy lại vào ngày hôm sau | Tránh confusion cho user |
| main-prompt.txt | 233-235 | Khi pending trả [] → in "Không có price tracking cần update" và bỏ qua | Phân biệt 2 trường hợp: (a) pending rỗng hoàn toàn, (b) pending có dates nhưng tất cả bị skip vì chưa có data | Root cause rõ hơn |
| backend/routers/price_updates.py | 43 | `track_dates = await get_trading_days_needed(db, signal.run_date, 20)` | Thêm filter `needed = [d for d in needed if d <= date.today()]` tại dòng 51 để chỉ trả về dates đã hoặc đang trong ngày | Khi prompt lấy pending, chỉ nhận dates có thể có data thực tế |

### Final Proposed Changes v1

1. **[main-prompt.txt:239-241]** — Sửa logic bỏ qua track_date: thêm 1 dòng phân biệt "bỏ qua vì ngày tương lai" vs "bỏ qua vì hôm nay chưa chốt phiên (T+1 sẽ tự cập nhật ngày mai)"
2. **[main-prompt.txt:233-235]** — Sửa thông báo khi pending=[]: thêm case riêng khi tất cả dates bị skip vì chưa có data, với hướng dẫn rõ là T+1 sẽ có khi chạy lại vào ngày hôm sau
3. **[backend/routers/price_updates.py:51]** — Thêm filter `date.today()` vào `needed` list trong `get_pending_updates()` để endpoint chỉ trả về dates có thể có data thực tế, tránh prompt nhận T+1-hôm-nay rồi bỏ qua

---

## Review v1 — AI B

### Feedback
- [FB-1-001] Root cause CORRECT — T+1=2026-03-27 bị skip vì Fireant historical-quotes không có data cho ngày chưa chốt phiên. Flow chain chính xác.
- [FB-1-002] Fix #3 (date.today() filter tại price_updates.py:51) — ĐÚNG hướng, không có side effect hại. Khi chạy ngày 2026-03-28, endpoint sẽ trả về 2026-03-27 (là <= today) và historical-quotes đã có data → sẽ được update.
- [FB-1-003] Fix #1 và #2 (main-prompt.txt) — Chỉ là UX/communication improvement, nhưng cần thiết để user hiểu tại sao T+1 bỏ trống và khi nào được fix.

> NO NEW FEEDBACK — Analysis complete, proceed to implementation

---

## Implementation Summary — AI C
### Files Changed
- [backend/routers/price_updates.py:51](backend/routers/price_updates.py#L51) — Thêm `and d <= date.today()` vào filter `needed`
- [main-prompt.txt:233-241](main-prompt.txt#L233) — Thêm note về T+1 auto-update; làm rõ "chưa chốt phiên" vs "ngày tương lai"
### Notes / Deviations
- none
### Status: DONE

---

## Verification — AI A v1
- Fix #3 (`d <= date.today()`) đã được implement tại price_updates.py:51.
- Main-prompt.txt notes đã được thêm tại dòng 236-237.
- Logic: ngày 2026-03-27, filter cho phép T+1=2026-03-27 (vì `<=`). Ngày 2026-03-28, filter cho phép 2026-03-27 (đã là quá khứ) → historical-quotes có data → được update.

**Verdict: APPROVED**

---

## Verification — AI B v1
- **Issue**: Filter `d <= date.today()` vẫn trả về T+1=hôm-nay trong pending. Nhưng Fireant historical-quotes không có data cho ngày hôm nay (phiên chưa chốt). Prompt vẫn bỏ qua T+1-hôm-nay → thông báo "không có price tracking cần update" vẫn xuất hiện.
- **Fix đúng phải là**: `d < date.today()` (strict less than) để T+1-hôm-nay không bao giờ xuất hiện trong pending. T+1 sẽ xuất hiện trong pending từ ngày D+2 trở đi khi phiên đã chốt.

**Verdict: REJECTED — filter `<=` không đủ, cần dùng `<` (strict less than) để loại bỏ ngày hôm nay khỏi pending**

## Verification Feedback v1 — AI B
- [price_updates.py:51] Expected: `d < date.today()` (strict), Actual: `d <= date.today()` (inclusive) — T+1-hôm-nay vẫn lọt vào pending nhưng Fireant không có data → prompt bỏ qua, thông báo lỗi vẫn xuất hiện

---

## Implementation Summary — AI C v1
### Files Changed
- [backend/routers/price_updates.py:51](backend/routers/price_updates.py#L51) — Sửa `d <= date.today()` thành `d < date.today()` (strict less than)
- [main-prompt.txt:236](main-prompt.txt#L236) — Sửa note từ "<= hôm nay" thành "< hôm nay" để nhất quán với code
### Notes / Deviations
- Với `d < date.today()`: khi chạy ngày 2026-03-27, T+1=2026-03-27 bị filter → pending không trả về nó → thông báo "Không có price tracking cần update" xuất hiện nhưng là đúng behavior. Khi chạy ngày 2026-03-28, T+1=2026-03-27 (< 2026-03-28) được trả về → Fireant có data → được update.
### Status: DONE

---

## Verification — AI A v2
- `d < date.today()` confirmed tại price_updates.py:51
- main-prompt.txt dòng 236 nói "< hôm nay" — nhất quán với code
- Logic trace đúng: T+1-hôm-nay bị filter, tự xuất hiện ngày hôm sau

**Verdict: APPROVED**

## Verification — AI B v2
- Strict `<` confirmed, không phải `<=`
- Documentation nhất quán với implementation
- Không còn vấn đề gì

**Verdict: APPROVED**

## Final Verification — APPROVED

---
