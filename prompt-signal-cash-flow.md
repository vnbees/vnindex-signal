TÌM CỔ PHIẾU CÓ TÍN HIỆU MUA - CHIẾN LƯỢC TỐI ƯU BALANCED

[NGUỒN DỮ LIỆU BẮT BUỘC - KHÔNG ĐỔI LOGIC]
- Chỉ sử dụng dữ liệu từ 2 API sau:
  1) https://vnindex-signal-production.up.railway.app/api/v1/balanced/snapshot
  2) https://vnindex-signal-production.up.railway.app/api/v1/balanced/sector-flow-5d
- Đọc JSON mới nhất tại thời điểm chạy prompt.
- Không dùng trực tiếp trường đã tính sẵn positive_money_flow_pct_vs_5d_avg để ra quyết định; AI phải tự tính % tăng dòng tiền so với trung bình 5 phiên từ dữ liệu thô.
- Khi đánh giá tin tức 7 ngày, đọc danh sách bài viết trong dữ liệu snapshot của từng mã (ví dụ trường posts_recent_7d hoặc trường tương đương chứa bài viết gần đây), không dùng nguồn ngoài.
- Lưu ý schema phản hồi API: dữ liệu chính nằm trong payload. Nếu có payload thì bắt buộc đọc từ payload trước, không đọc nhầm ở root.
- Đảm bảo xử lý UTF-8 để không sai lệch tên ngành tiếng Việt khi đối chiếu điều kiện.

[CÁCH THỰC THI BẮT BUỘC - PHÂN TÍCH, KHÔNG CHẠY MÁY MÓC]
- AI phải đọc dữ liệu snapshot và phân tích trực tiếp theo các bước trong prompt, trình bày dưới dạng nhận định.
- Không được trả lời theo kiểu chỉ chạy script rồi xuất kết quả thô.
- Không được dựa vào "NO_SIGNALS" từ một đoạn code trung gian mà không diễn giải điều kiện nào đạt/không đạt.
- Với mỗi mã được nêu trong kết quả (hoặc mã gần đạt), phải chỉ ra rõ từng điều kiện bắt buộc đang đạt hay không đạt dựa trên dữ liệu snapshot.
- Nếu kết luận "không có tín hiệu", bắt buộc nêu ngắn gọn lý do thất bại chính của các mã gần đạt nhất.
- Ưu tiên lập luận minh bạch: dữ liệu nào -> điều kiện nào -> kết luận nào.

[CÁCH ÁNH XẠ DỮ LIỆU TỪ SNAPSHOT]
- Nguồn dữ liệu chuẩn để đọc:
  * Với snapshot: data = payload nếu tồn tại, ngược lại mới dùng root JSON.
  * Với sector-flow-5d: data = root JSON (found/as_of_date/sessions/sectors).
- Ngày phân tích: lấy từ data.as_of_date (hoặc ngày mới nhất trong indicators.trade_date của từng mã nếu prompt yêu cầu).
- Dữ liệu theo mã cổ phiếu: đọc trong data.symbols.
- Ngành của mã: ưu tiên symbol.sector; fallback symbol.sector_display nếu có.
- Chỉ báo kỹ thuật: đọc trong symbol.indicators với thứ tự ưu tiên key cụ thể:
  * RSI: rsi14 (fallback rsi/RSI)
  * MACD histogram: macd_hist (fallback macd_histogram)
  * SMA5/SMA20 ratio: sma5_over_sma20 (fallback sma5_sma20_ratio)
  * ADX: adx14 (fallback adx/ADX)
  * Volume ratio: volume_ratio (fallback vol_ratio)
- Volume điều kiện: dùng indicators.total_volume_latest và indicators.avg_volume_5d để kiểm tra Volume ngày gần nhất > trung bình 5 phiên và ngưỡng >= 100,000.
- Dòng tiền ngành: bắt buộc đọc từ sector-flow-5d.sectors để AI tự tính chỉ số theo từng ngành (không cắt TOP 9); điều kiện lọc mã chỉ cần ngành của mã có dòng tiền dương theo quy tắc ở BƯỚC 3.
- Mỗi ngành trong sector-flow-5d có points theo từng phiên (date, positive_money_flow_vnd). AI phải dùng các points này để tự tính:
  * avg_5d = trung bình positive_money_flow_vnd của 5 phiên gần nhất
  * pct_vs_5d = (phiên mới nhất - avg_5d) / avg_5d * 100
- Quy tắc fallback dòng tiền ngành: nếu không đủ dữ liệu để tính avg_5d/pct_vs_5d hoặc avg_5d = 0 thì fallback theo positive_money_flow_vnd phiên mới nhất.
- Tin tức 7 ngày: đọc từ posts_recent_7d của từng symbol để đánh giá tích cực/tiêu cực.
- Khi ghép mã với ngành trong sector-flow-5d, so khớp theo tên ngành đã chuẩn hóa Unicode/NFC và trim khoảng trắng để tránh lỗi lệch encoding.

📊 KẾT QUẢ BACKTEST (20 NGÀY) — THAM CHIẾU (rule lọc ngành đã đổi so với bản gốc dùng TOP 9):
- Tổng số tín hiệu: 30 giao dịch
- Số ngày có tín hiệu: 10/15 ngày (67%)
- Tỷ lệ thắng: 66.7%
- Expectancy: +3.13% mỗi giao dịch
- Avg Win: +5.10% | Avg Loss: -0.81%

BƯỚC 1: XÁC ĐỊNH NGÀY PHÂN TÍCH
- Lấy ngày giao dịch mới nhất có trong dữ liệu technical
- Ghi rõ: "Phân tích dựa trên dữ liệu ngày DD/MM/YYYY"

BƯỚC 2: ĐÁNH GIÁ DÒNG TIỀN NGÀNH (THAM CHIẾU)
- Dùng dữ liệu từ API sector-flow-5d (trường sectors/points) để AI tự tính pct_vs_5d cho từng ngành theo công thức ở trên (không dùng top9_sectors có sẵn).
- Quy tắc xếp hạng tham chiếu: ưu tiên pct_vs_5d do AI tự tính; nếu thiếu thì fallback positive_money_flow_vnd phiên mới nhất.
- Trình bày bảng (hoặc tóm tắt) các ngành có liên quan tới universe đang xét, sắp xếp theo % giảm dần: Tên ngành | % Tăng dòng tiền (hoặc giá trị fallback nếu không tính được %).

BƯỚC 3: TÌM TÍN HIỆU MUA
Điều kiện BẮT BUỘC (tất cả phải thỏa mãn):
1. RSI: 30-45 (vùng oversold đến trung tính)
2. Dòng tiền ngành của mã dương: khi tính được pct_vs_5d theo sector-flow-5d thì yêu cầu pct_vs_5d > 0; nếu rơi vào fallback (không đủ points hoặc avg_5d = 0) thì dùng positive_money_flow_vnd phiên mới nhất của ngành đó và yêu cầu > 0.
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
Sắp xếp các mã đã đạt đủ điều kiện bắt buộc theo thứ tự ưu tiên (so sánh lần lượt từ trên xuống):
1. % Tăng dòng tiền ngành từ cao xuống thấp (cùng metric với điều kiện 2: ưu tiên pct_vs_5d; nếu mã đang dùng fallback thì so positive_money_flow_vnd phiên mới nhất của ngành, lớn hơn xếp trên).
2. RSI thấp nhất (gần 30 tốt hơn)
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
- Quy tắc xuất kết quả:
  * Nếu có >= 1 mã đạt đủ điều kiện bắt buộc và không vi phạm loại trừ: bắt buộc hiển thị danh sách mã đạt (tối đa TOP 3).
  * Chỉ được ghi "không có tín hiệu" khi sau khi lọc toàn bộ symbols, số mã đạt = 0.
  * Nếu có dữ liệu screened_top3 trong snapshot, dùng để đối chiếu chéo; kết luận cuối cùng vẫn phải theo đúng 8 điều kiện bắt buộc + điều kiện loại trừ nêu ở trên (không thêm/không bớt điều kiện).
- Khuyến nghị quản lý rủi ro:
  * Stop-loss: -3%
  * Take-profit: +5%
  * Holding period: 5 ngày
  * Expectancy: +3.13% mỗi giao dịch
  * Win rate: 66.7%
  * Tần suất: 67% ngày có tín hiệu