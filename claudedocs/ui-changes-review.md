# UI Changes - Yêu cầu & Giải pháp

## Yêu cầu 1: Đổi text PnL footer

**Hiện tại:**
> "* PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi giờ."

**Mong muốn:**
> "* PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi ngày từ 15h30-16h30."

### Files cần sửa

| File | Dòng | Nội dung hiện tại |
|------|------|-------------------|
| `frontend/app/signals/[date]/page.tsx` | 54 | `* PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi giờ.` |
| `frontend/app/signals/[date]/[symbol]/page.tsx` | 124 | `* PnL tính từ giá mở cửa T+1` (text ngắn hơn, không có "Cập nhật mỗi giờ") |

### Giải pháp

- **File 1** (`signals/[date]/page.tsx:54`): Đổi "Cập nhật mỗi giờ" → "Cập nhật mỗi ngày từ 15h30-16h30"
- **File 2** (`signals/[date]/[symbol]/page.tsx:124`): Thêm phần mô tả đầy đủ cho nhất quán, hoặc giữ nguyên text ngắn. **Cần confirm:** có muốn đồng bộ text ở trang detail không?

---

## Yêu cầu 2: Ẩn cột TC, SS, KT, DT, Tổng

### Files cần sửa

| File | Dòng | Mô tả |
|------|------|-------|
| `frontend/components/SignalTable.tsx` | 57-61 | Header columns: TC, SS, KT, DT, Tổng |
| `frontend/components/SignalTable.tsx` | 86-100 | Body cells: ScoreCell cho 5 cột tương ứng |
| `frontend/app/signals/[date]/[symbol]/page.tsx` | 54-81 | Card "Điểm thành phần" hiển thị TC, SS, KT, DT, Tổng |

### Giải pháp

**Option A: Ẩn hoàn toàn (xoá khỏi render)**
- Xoá 5 `<th>` (dòng 57-61) và 5 `<td>` (dòng 86-100) trong `SignalTable.tsx`
- Xoá card "Điểm thành phần" (dòng 54-81) trong trang detail `[symbol]/page.tsx`
- Giữ nguyên data từ API, chỉ không hiển thị

**Option B: Ẩn bằng CSS (hidden nhưng dễ bật lại)**
- Thêm `className="hidden"` vào các `<th>` và `<td>` tương ứng
- Thêm `hidden` vào card "Điểm thành phần"
- Dễ toggle lại bằng cách xoá class

**Khuyến nghị: Option A** — code sạch hơn, không có dead markup. Data vẫn còn trong API response nên bật lại chỉ cần thêm lại JSX.

### Lưu ý

- Cột **KN** (Khuyến nghị) vẫn giữ nguyên — đây là output cuối cùng người dùng cần thấy
- Bảng sau khi ẩn sẽ còn: **Vốn hoá | Mã | KN | Giá đóng | T+1 | T+5 | T+20**
- Trang detail sẽ chỉ còn: card **Giá & PnL**, **Biểu đồ PnL**, **Kỹ thuật**, **Tài chính**

---

## Tóm tắt thay đổi

| # | Thay đổi | Files | Độ phức tạp |
|---|----------|-------|-------------|
| 1 | Đổi text PnL footer | 1-2 files | Thấp |
| 2 | Ẩn cột điểm thành phần | 2 files | Thấp |

Tổng: ~20 dòng code thay đổi, không ảnh hưởng backend/API.

---

## Phân tích feedback & Kết luận (2026-03-25)

### Yêu cầu 1 — Text PnL ✅ Confirmed

- Dòng số khớp chính xác với code hiện tại
- **Quyết định**: Đồng bộ cả File 2 (`[symbol]/page.tsx:124`) thành text đầy đủ:
  `* PnL tính từ giá mở cửa T+1 (giá thực tế có thể mua được). Cập nhật mỗi ngày từ 15h30-16h30.`

### Yêu cầu 2 — Điều chỉnh sau verify code

#### SignalTable.tsx — Dòng số chính xác (đã verify)
- Header `<th>` TC/SS/KT/DT/Tổng: **dòng 57–61** ✅
- Body `<td>` tương ứng: **dòng 86–100** (score_financial → score_total) ✅
- Sau khi xoá, import `ScoreCell` ở dòng 9 sẽ unused → **cần xoá luôn import**

#### [symbol]/page.tsx — Card "Điểm thành phần": Chọn Option C
- Feedback đề xuất: **giữ card nhưng chỉ hiển thị Tổng**
- **Option C (mới)**: Xoá mảng `.map()` 4 thành phần TC/SS/KT/DT (**dòng 58–73**), giữ lại phần Tổng (**dòng 74–79**) + wrapper card
- Lý do: Người dùng vẫn thấy tổng điểm → hiểu context của KN, nhưng không thấy chi tiết từng thành phần
- Tên card "Điểm thành phần" (**dòng 56**) → nên đổi thành "Điểm tổng" cho phù hợp với nội dung còn lại

#### T+10 — Chỉ xuất hiện ở trang detail, không ảnh hưởng bảng
- Verify: `SignalTable.tsx` header chỉ có T+1, T+5, T+20 (**dòng 64–66**) — không có T+10 ✅
- T+10 xuất hiện ở `[symbol]/page.tsx:101` trong card "Giá & PnL" → giữ nguyên, không ẩn
- Tài liệu ban đầu ghi đúng

---

## Giải pháp cuối cùng (sau feedback)

### Thay đổi 1: Text PnL footer
| File | Dòng | Hành động |
|------|------|-----------|
| `signals/[date]/page.tsx` | 54 | Đổi "Cập nhật mỗi giờ" → "Cập nhật mỗi ngày từ 15h30-16h30" |
| `signals/[date]/[symbol]/page.tsx` | 124 | Đổi thành text đầy đủ đồng bộ với trang danh sách |

### Thay đổi 2: Ẩn điểm thành phần
| File | Dòng | Hành động |
|------|------|-----------|
| `SignalTable.tsx` | 57–61 | Xoá 5 `<th>` (TC, SS, KT, DT, Tổng) |
| `SignalTable.tsx` | 86–100 | Xoá 5 `<td>` (ScoreCell tương ứng) |
| `SignalTable.tsx` | 9 | Xoá `import { ScoreCell }` (unused sau khi xoá `<td>`) |
| `[symbol]/page.tsx` | 58–73 | Xoá mảng 4 thành phần, giữ card + Tổng |
| `[symbol]/page.tsx` | 56 | Đổi tiêu đề card "Điểm thành phần" → "Điểm tổng" |

