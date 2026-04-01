# Logic gợi ý vốn (Capital Allocation)

Tài liệu này mô tả chi tiết cách hệ thống chọn mã và phân bổ vốn trong endpoint:

- `GET /api/v1/allocation/suggest`

Mục tiêu hiện tại: ưu tiên xác suất thắng ổn định theo ngữ cảnh giá (winrate-first), vẫn giữ PnL làm tín hiệu phụ.

## 1) Đầu vào chính

- `capital`: số vốn cần phân bổ (bắt buộc, > 0)
- `run_date`: ngày tín hiệu (nếu không truyền thì lấy ngày chạy mới nhất)
- `portfolio_kind`: nhóm danh mục (mặc định `top_cap`)
- `lot_size`: bước khớp lệnh theo lô (mặc định `100`)
- `max_items`: số mã tối đa trong shortlist
- `price_min`, `price_max` (nghìn VND): lọc khoảng giá thủ công (optional)
- `days`: số ngày dùng để tính thống kê PnL bucket (mặc định `60`)

## 2) Chọn ngữ cảnh giá (price bucket)

### 2.1 Người dùng chọn tay
Nếu có `price_min` hoặc `price_max`, hệ thống dùng trực tiếp khoảng giá người dùng chọn.

### 2.2 Tự động chọn bucket (khi người dùng không chọn)
Hệ thống thử các bucket cố định:

- Dưới 10k
- 10-20k
- 20-30k
- 30-50k
- 50-100k
- Trên 100k

Với mỗi bucket, hệ thống lấy thống kê theo `recommendation` từ `signal_pnl_summary`:

- PnL ngắn hạn: `avg_pnl_d3`, `avg_pnl_d10`, `avg_pnl_d20`, `avg_latest_pnl`
- Winrate: `winrate_d3`, `winrate_d10`, `winrate_d20`
- Số mẫu: `total`

Sau đó tính điểm bucket theo hướng **winrate-first**:

- điểm chính theo winrate trung bình có trọng số số mẫu
- PnL dùng như tie-break phụ
- cộng nhẹ bonus theo độ dày dữ liệu (sample size)

Bucket có điểm cao nhất sẽ được chọn cho phiên gợi ý hiện tại.

## 3) Lọc ứng viên tín hiệu

Tập ứng viên lấy từ `signals` của `run_date` và `portfolio_kind`, có:

- `price_close_signal_date > 0`
- nằm trong bucket giá đang áp dụng (nếu có)
- thuộc nhóm khuyến nghị:
  - luôn lấy `BUY_STRONG`, `BUY`
  - `HOLD` chỉ được giữ khi hiệu suất tối thiểu đạt ngưỡng:
    - ưu tiên dùng số liệu bucket `HOLD`
    - nếu bucket thiếu thì fallback về số liệu lịch sử theo mã

## 4) Nguồn dữ liệu chấm điểm cho từng mã

Khi chấm 1 mã cụ thể:

- Nếu bucket giá có dữ liệu cho `recommendation` của mã đó:
  - dùng số liệu bucket (theo loại tín hiệu)
- Nếu bucket thiếu dữ liệu:
  - fallback về số liệu lịch sử của chính mã đó (`ps` aggregate)

Ưu tiên horizon:

- PnL: T+3 -> T+10 -> T+20 -> latest
- Winrate: T+3 -> T+10 -> T+20

## 5) Công thức chấm điểm mã (Winrate-first)

Các thành phần:

- `winrate_score`: từ winrate ngắn hạn, có nhân `confidence`
- `pnl_score`: từ PnL ngắn hạn, có nhân `confidence`
- `recency_signal_score`: từ `score_total` tín hiệu hiện tại
- `confidence`: tăng theo số lượng mẫu (sample count)

Trọng số hiện tại:

- `70% winrate_score`
- `25% pnl_score`
- `5% recency_signal_score`

Ràng buộc an toàn:

- nếu winrate ngắn hạn `< 50%`, hệ thống phạt thêm điểm (nhân `0.7`)
- có `signal_factor` nhẹ theo loại tín hiệu để tie-break (`BUY_STRONG` > `BUY` > `HOLD`)

## 6) Chọn shortlist và phân bổ vốn

1. Sắp xếp mã theo `final_score` giảm dần.
2. Giữ tối đa `max_items`.
3. Chia vốn theo tỷ trọng điểm.
4. Quy đổi khối lượng theo lô chẵn:
   - giá trong DB đang ở đơn vị nghìn, hệ thống nhân `1000` để ra VND trước khi tính tiền.
   - số lượng mua luôn làm tròn xuống theo `lot_size`.
5. Tối ưu tiền dư:
   - dùng vòng best-fit để mua thêm lô cho mã ưu tiên cao, miễn không vượt vốn.

## 7) Hành vi fallback khi vốn nhỏ

- Nếu sau làm tròn chưa mua được mã nào nhưng vốn vẫn đủ mua tối thiểu 1 lô của một mã khả thi:
  - hệ thống vẫn trả tối thiểu 1 gợi ý để đảm bảo tính khả dụng.

## 8) Trường dữ liệu phản hồi mới để minh bạch

Response có thêm:

- `selected_price_label`
- `selected_price_min`
- `selected_price_max`
- `auto_selected_price_filter`

Ý nghĩa:

- hiển thị rõ hệ thống đang dùng bucket nào
- phân biệt rõ do user chọn hay auto chọn

## 9) Diễn giải ngắn cho người dùng cuối

- Không chọn khoảng giá: hệ thống tự tìm bucket giá có xác suất thắng tốt hơn rồi mới gợi ý mã.
- Có chọn khoảng giá: hệ thống bám đúng bucket người dùng chọn.
- Danh sách gợi ý không chỉ nhìn PnL theo từng mã, mà kết hợp hiệu suất theo loại tín hiệu trong đúng ngữ cảnh giá.
