TÌM CỔ PHIẾU CÓ TÍN HIỆU MUA - CHIẾN LƯỢC TỐI ƯU BALANCED

[NGUỒN DỮ LIỆU BẮT BUỘC - KHÔNG ĐỔI LOGIC]
- Chỉ sử dụng dữ liệu từ API snapshot:
  https://vnindex-signal-production.up.railway.app/api/v1/balanced/snapshot
- Đọc JSON mới nhất tại thời điểm chạy prompt.
- Ưu tiên đọc các trường đã được tính sẵn trong snapshot; nếu cần thì suy luận thêm từ các trường trong cùng JSON.
- Khi đánh giá tin tức 7 ngày, đọc danh sách bài viết trong dữ liệu snapshot của từng mã (ví dụ trường posts_recent_7d hoặc trường tương đương chứa bài viết gần đây), không dùng nguồn ngoài.

[CÁCH ÁNH XẠ DỮ LIỆU TỪ SNAPSHOT]
- Ngày phân tích: lấy từ as_of_date (hoặc ngày mới nhất trong phần technical của từng mã nếu prompt yêu cầu).
- Dữ liệu theo mã cổ phiếu: đọc trong mảng symbols.
- Ngành của mã: đọc trường sector (hoặc sector_display tương đương).
- Chỉ báo kỹ thuật: đọc các trường RSI, MACD histogram, SMA5/SMA20 ratio, ADX, volume ratio trong object indicators (hoặc key tương đương trong mỗi symbol).
- Volume điều kiện: dùng indicators.total_volume_latest và indicators.avg_volume_5d để kiểm tra Volume ngày gần nhất > trung bình 5 phiên và ngưỡng >= 100,000.
- Dòng tiền ngành TOP 9: đọc từ phần top9_sectors; ưu tiên trường positive_money_flow_pct_vs_5d_avg (hoặc pct_change_vs_5d_avg) để xếp hạng theo logic 5 phiên.
- Dữ liệu đầy đủ tất cả ngành để đối chiếu nằm ở all_sectors (mỗi ngành có positive_money_flow_vnd, positive_money_flow_avg_5d_vnd, positive_money_flow_pct_vs_5d_avg).
- Quy tắc fallback dòng tiền ngành: nếu ngành nào chưa có positive_money_flow_pct_vs_5d_avg (thiếu lịch sử 5 phiên) thì dùng positive_money_flow_vnd hoặc sector_flow_pct hiện có.
- Tin tức 7 ngày: đọc từ posts_recent_7d của từng symbol để đánh giá tích cực/tiêu cực.

📊 KẾT QUẢ BACKTEST (20 NGÀY):
- Tổng số tín hiệu: 30 giao dịch
- Số ngày có tín hiệu: 10/15 ngày (67%)
- Tỷ lệ thắng: 66.7%
- Expectancy: +3.13% mỗi giao dịch
- Avg Win: +5.10% | Avg Loss: -0.81%

BƯỚC 1: XÁC ĐỊNH NGÀY PHÂN TÍCH
- Lấy ngày giao dịch mới nhất có trong dữ liệu technical
- Ghi rõ: "Phân tích dựa trên dữ liệu ngày DD/MM/YYYY"

BƯỚC 2: XÁC ĐỊNH NGÀNH HOT
- Sử dụng dữ liệu TOP 9 ngành dòng tiền đã được snapshot tính sẵn trong top9_sectors.
- Hiển thị: Tên ngành | % Tăng dòng tiền

BƯỚC 3: TÌM TÍN HIỆU MUA
Điều kiện BẮT BUỘC (tất cả phải thỏa mãn):
1. RSI: 30-45 (vùng oversold đến trung tính)
2. Thuộc 1 trong TOP 9 ngành dòng tiền mạnh nhất
3. Volume ngày gần nhất > trung bình 5 phiên
4. Volume ratio: 1.0-2.0x (tăng ổn định đến mạnh)
5. Volume tối thiểu >= 100,000 cổ phiếu
6. MACD histogram > 0 (xác nhận momentum tăng)
7. SMA5 >= 92% SMA20 (chấp nhận cả downtrend nhẹ)
8. ADX >= 15 (xu hướng bắt đầu rõ ràng)

Điều kiện LOẠI TRỪ:
- Có tin tiêu cực trong 7 ngày gần nhất

Điều kiện ƯU TIÊN (bonus điểm):
- RSI 30-35: Vùng oversold tốt nhất
- Volume ratio 1.0-1.3x: Tăng ổn định
- Thuộc ngành: Bất động sản, Thực phẩm và đồ uống

BƯỚC 4: XẾP HẠNG VÀ TRÌNH BÀY
Sắp xếp theo thứ tự ưu tiên:
1. RSI thấp nhất (gần 30 tốt hơn)
2. % Tăng dòng tiền ngành cao nhất
3. Volume ratio thấp nhất (gần 1.0 tốt hơn)
4. MACD histogram dương lớn nhất
5. Bonus ngành ưu tiên

YÊU CẦU KẾT QUẢ:
- Tiêu đề: "🎯 TÍN HIỆU MUA BALANCED - NGÀY [DD/MM/YYYY]"
- Bảng kết quả gồm:
  * Mã CP | Ngành | RSI | Giá (VND)
  * Volume ratio (x.xx lần)
  * % Dòng tiền ngành
  * MACD histogram
  * SMA5/SMA20 ratio
- Ghi chú đặc biệt:
  * ⭐ Thuộc ngành ưu tiên (Bất động sản/Thực phẩm)
  * 🎯 RSI trong vùng 30-35 (oversold tốt nhất)
  * 📊 Volume ratio 1.0-1.3x (tăng ổn định)
  * 📈 SMA ratio >= 0.95 (uptrend rõ ràng)
- Giới hạn: TOP 3 tín hiệu tốt nhất mỗi ngày
- Khuyến nghị quản lý rủi ro:
  * Stop-loss: -3%
  * Take-profit: +5%
  * Holding period: 5 ngày
  * Expectancy: +3.13% mỗi giao dịch
  * Win rate: 66.7%
  * Tần suất: 67% ngày có tín hiệu