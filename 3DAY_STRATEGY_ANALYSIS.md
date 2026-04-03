# Phân Tích Chiến Lược Mua-Lãi Sau 3 Ngày

> **Ngày phân tích:** 03/04/2026
> **Dữ liệu:** Top 100 cổ phiếu vốn hóa lớn nhất HOSE | 80,734 phiên giao dịch (2023-2026)
> **Nguồn:** Fireant API | **Số chiến lược backtest:** 53

---

## 1. Tổng Quan

Backtest 53 chiến lược kỹ thuật trên 100 cổ phiếu vốn hóa lớn nhất sàn HOSE, mỗi chiến lược được kiểm tra theo logic: **mua cuối phiên hôm nay → bán cuối phiên sau 3 ngày giao dịch**.

**Kết luận chính:** Các chiến lược **mean reversion** (mua khi giá giảm sâu + oversold) cho xác suất lãi cao nhất, đặc biệt khi kết hợp với tín hiệu dòng tiền nước ngoài.

---

## 2. Top 10 Chiến Lược Tốt Nhất

| # | Chiến lược | Win Rate | Avg Return | Số lệnh | Profit Factor |
|---|-----------|----------|------------|---------|---------------|
| 1 | **4 phiên giảm liên tiếp + RSI < 35** | **59.5%** | **+1.24%** | 945 | 1.94 |
| 2 | 3 phiên giảm + RSI < 40 | 56.7% | +0.88% | 2,870 | 1.69 |
| 3 | Dưới MA20 >5% + Nước ngoài mua ròng | 56.4% | +0.78% | 3,684 | 1.49 |
| 4 | Giảm >3% + Nước ngoài mua ròng | 56.0% | +0.76% | 2,093 | 1.41 |
| 5 | Giá dưới MA20 >5% | 55.6% | +0.49% | 10,390 | 1.30 |
| 6 | Giảm >5% trong phiên | 55.1% | +0.44% | 2,258 | 1.18 |
| 7 | Giảm >3% trong phiên | 54.8% | +0.47% | 5,275 | 1.24 |
| 8 | BB<0.15 + Tự doanh mua + RSI<40 | 54.6% | +0.35% | 2,987 | 1.25 |
| 9 | 3 phiên giảm + NN mua ròng | 54.5% | +0.78% | 2,165 | 1.63 |
| 10 | RSI < 30 (Oversold) | 54.0% | +0.60% | 3,462 | 1.36 |

---

## 3. Phương Pháp Tốt Nhất: "4 Phiên Giảm + RSI < 35"

### Nguyên tắc

Mua cổ phiếu khi **đồng thời** thỏa 2 điều kiện:
1. Giá đóng cửa giảm **4 phiên giao dịch liên tiếp** trở lên
2. Chỉ số RSI(14) **dưới 35** (vùng oversold)

### Kết quả backtest

| Chỉ số | Giá trị |
|--------|---------|
| Win Rate | **59.5%** (cứ 10 lần mua, ~6 lần có lãi) |
| Return trung bình | **+1.24%** mỗi giao dịch |
| Median return | **+0.80%** |
| TB lãi khi thắng | +4.30% |
| TB lỗ khi thua | -3.24% |
| Profit Factor | **1.94** (tổng lãi gần gấp đôi tổng lỗ) |
| Số giao dịch | 945 (đủ tin cậy thống kê) |

### Tại sao chiến lược này hiệu quả?

- **Mean reversion mạnh:** Sau 4 phiên giảm liên tiếp, xác suất hồi phục kỹ thuật (technical bounce) rất cao
- **RSI < 35 lọc thêm:** Chỉ mua khi thực sự oversold, loại bỏ những đợt giảm nhẹ không đủ sâu
- **Risk/Reward tốt:** TB lãi (+4.3%) lớn hơn TB lỗ (-3.2%), Profit Factor 1.94

---

## 4. Các Chiến Lược Đáng Chú Ý Khác

### 4.1 Chiến lược có Profit Factor cao nhất

| Chiến lược | Win Rate | Profit Factor | Giải thích |
|-----------|----------|---------------|------------|
| 4 giảm + RSI<35 | 59.5% | **1.94** | Mean reversion cực mạnh |
| 3 giảm + RSI<40 | 56.7% | **1.69** | Bản nhẹ hơn, nhiều cơ hội hơn |
| 3 giảm + NN mua ròng | 54.5% | **1.63** | Smart money xác nhận đáy |
| Dưới MA20 >5% + NN mua | 56.4% | **1.49** | Giá sâu + nước ngoài gom |
| Mua thứ 2 (Monday) | 52.4% | **1.44** | Seasonality effect |

### 4.2 Chiến lược đơn giản nhất (1 điều kiện)

| Chiến lược | Win Rate | Số lệnh | Avg Return |
|-----------|----------|---------|------------|
| Giá dưới MA20 >5% | 55.6% | 10,390 | +0.49% |
| Giảm >5% trong phiên | 55.1% | 2,258 | +0.44% |
| Giảm >3% trong phiên | 54.8% | 5,275 | +0.47% |
| RSI < 30 | 54.0% | 3,462 | +0.60% |

### 4.3 Seasonality (ngày trong tuần)

| Ngày mua | Win Rate | Avg Return |
|----------|----------|------------|
| **Thứ 2 (Monday)** | **52.4%** | **+0.49%** |
| Thứ 6 (Friday) | 51.9% | +0.45% |
| Thứ 3 (Tuesday) | 48.9% | +0.24% |
| Thứ 5 (Thursday) | 47.3% | -0.07% |
| **Thứ 4 (Wednesday)** | **44.7%** | **-0.23%** |

> Thứ 2 là ngày mua tốt nhất, thứ 4 là ngày tệ nhất.

---

## 5. Chiến Lược Nên Tránh

| Chiến lược | Win Rate | Avg Return | Lý do |
|-----------|----------|------------|-------|
| RSI<40 + Volume >2x | 43.7% | -0.67% | Volume spike khi oversold = sell-off mạnh, chưa đến đáy |
| Mua thứ 4 (Wednesday) | 44.7% | -0.23% | Seasonality xấu nhất trong tuần |
| BB > 0.9 (gần upper band) | 45.3% | +0.11% | Mua đỉnh, xác suất điều chỉnh cao |
| Volume tăng đột biến >2x | 46.1% | +0.04% | Thường là tin tức, không bền vững |
| Giá trên MA20 2-5% | 46.7% | +0.09% | Vùng "no man's land", không rõ xu hướng |

---

## 6. Cổ Phiếu Khớp Tín Hiệu Hôm Nay (03/04/2026)

### Ưu tiên cao (khớp 3 chiến lược)

| Mã | Giá | RSI | vs MA20 | Chiến lược khớp |
|----|-----|-----|---------|----------------|
| **OIL** | 15,400 | 41.4 | -11.3% | Dưới MA20 >5% + NN mua, Giá dưới MA20 >5%, 3 giảm + NN mua ròng |
| **PVT** | 21,350 | 41.0 | -9.7% | Dưới MA20 >5% + NN mua, Giá dưới MA20 >5%, 3 giảm + NN mua ròng |
| **GEE** | 194,000 | 58.8 | +16.4% | Giảm >3% + NN mua, Giảm >5%, Giảm >3% |

### Ưu tiên trung bình (khớp 2 chiến lược)

| Mã | Giá | RSI | vs MA20 | Chiến lược khớp |
|----|-----|-----|---------|----------------|
| **DGC** | 56,200 | 43.2 | -8.0% | Dưới MA20 >5% + NN mua, Giá dưới MA20 >5% |
| **MBS** | 20,450 | 30.6 | -15.4% | Dưới MA20 >5% + NN mua, Giá dưới MA20 >5% |
| **APG** | 6,470 | 23.1 | -13.0% | Dưới MA20 >5% + NN mua, Giá dưới MA20 >5% |
| **MWG** | 79,000 | 43.2 | -1.8% | Giảm >3% + NN mua, Giảm >3% |
| **GMD** | 71,000 | 40.8 | -6.7% | Giá dưới MA20 >5%, Giảm >3% |
| **TCH** | 16,400 | 55.5 | +6.8% | Giảm >3% + NN mua, Giảm >3% |
| **DGW** | 44,250 | 45.4 | +0.1% | Giảm >3% + NN mua, Giảm >3% |

---

## 7. Tổng Hợp Insight

### Quy luật chung

1. **Mean reversion là chiến lược chủ đạo** — Mua sau khi giá giảm sâu (nhiều phiên liên tiếp + RSI thấp) cho xác suất lãi cao nhất trong 3 ngày
2. **Nước ngoài mua ròng là tín hiệu xác nhận mạnh** — Kết hợp "giá giảm sâu + NN mua ròng 5 phiên" tăng win rate thêm 1-2%
3. **Giá càng xa MA20 (theo hướng giảm), xác suất hồi phục càng cao** — Dưới MA20 >5% có win rate 55.6% vs dưới 1-3% chỉ 48.4%
4. **Profit Factor quan trọng hơn Win Rate** — Chiến lược "3 giảm + NN mua" có PF 1.63 dù win rate chỉ 54.5%

### Quy tắc nên tránh

1. **Không mua khi volume spike + oversold** — Đây thường là đợt bán tháo chưa dừng (win rate chỉ 43.7%)
2. **Tránh mua thứ 4** — Ngày có xác suất lãi thấp nhất trong tuần (44.7%)
3. **Không đuổi giá khi BB > 0.9** — Mua gần Bollinger Band trên chỉ có win rate 45.3%
4. **Volume tăng đột biến không phải lúc nào cũng tốt** — Win rate chỉ 46.1%, thường là biến động do tin tức

### Cách áp dụng thực tế

```
Bước 1: Lọc cổ phiếu đã giảm >= 3-4 phiên liên tiếp
Bước 2: Kiểm tra RSI(14) < 35-40
Bước 3: Xác nhận nước ngoài đang mua ròng 5 phiên gần nhất
Bước 4: Ưu tiên mua vào thứ 2 hoặc thứ 6
Bước 5: Bán sau 3 ngày giao dịch (không tham, không sợ)
```

---

## 8. Bảng Đầy Đủ 53 Chiến Lược (Sắp Theo Win Rate)

| Chiến lược | Số lệnh | Thắng | Win% | TB Ret% | Median% | TB Win% | TB Loss% | PF |
|-----------|---------|-------|------|---------|---------|---------|----------|-----|
| 4 giảm + RSI<35 | 945 | 562 | 59.5 | +1.240 | +0.800 | +4.296 | -3.243 | 1.94 |
| Uptrend (>MA60) + RSI<40 | 102 | 58 | 56.9 | +0.015 | +0.675 | +4.154 | -5.440 | 1.01 |
| 3 giảm + RSI<40 | 2,870 | 1,628 | 56.7 | +0.877 | +0.647 | +3.787 | -2.939 | 1.69 |
| Dưới MA20 >5% + NN mua | 3,684 | 2,078 | 56.4 | +0.782 | +0.828 | +4.206 | -3.649 | 1.49 |
| Giảm >3% + NN mua ròng | 2,093 | 1,172 | 56.0 | +0.761 | +0.771 | +4.644 | -4.181 | 1.41 |
| Giá dưới MA20 >5% | 10,390 | 5,776 | 55.6 | +0.489 | +0.706 | +3.845 | -3.714 | 1.30 |
| Giảm >5% trong phiên | 2,258 | 1,244 | 55.1 | +0.441 | +0.814 | +5.238 | -5.444 | 1.18 |
| Giảm >3% trong phiên | 5,275 | 2,889 | 54.8 | +0.473 | +0.680 | +4.426 | -4.313 | 1.24 |
| BB<0.15 + TD mua + RSI<40 | 2,987 | 1,632 | 54.6 | +0.348 | +0.458 | +3.227 | -3.119 | 1.25 |
| 3 giảm + NN mua ròng | 2,165 | 1,180 | 54.5 | +0.783 | +0.440 | +3.724 | -2.741 | 1.63 |
| 5 phiên giảm liên tiếp | 979 | 533 | 54.4 | +0.327 | +0.366 | +3.006 | -2.875 | 1.25 |
| RSI < 30 | 3,462 | 1,870 | 54.0 | +0.600 | +0.473 | +4.235 | -3.669 | 1.36 |
| RSI < 35 | 7,600 | 4,098 | 53.9 | +0.433 | +0.437 | +3.564 | -3.231 | 1.29 |
| RSI<40 + NN mua ròng | 4,511 | 2,431 | 53.9 | +0.576 | +0.431 | +3.588 | -2.945 | 1.42 |
| 4 phiên giảm liên tiếp | 2,643 | 1,420 | 53.7 | +0.386 | +0.366 | +3.238 | -2.924 | 1.29 |
| RSI<35 + Giảm>3% + Vol>1.5x | 680 | 365 | 53.7 | +0.417 | +0.579 | +5.827 | -5.851 | 1.15 |
| BB pos < 0.1 (gần lower) | 7,879 | 4,173 | 53.0 | +0.268 | +0.377 | +3.422 | -3.283 | 1.17 |
| 3 phiên giảm liên tiếp | 6,632 | 3,508 | 52.9 | +0.415 | +0.309 | +3.255 | -2.774 | 1.32 |
| Mua thứ 2 (Monday) | 15,387 | 8,064 | 52.4 | +0.490 | +0.295 | +3.075 | -2.357 | 1.44 |
| RSI < 40 | 14,932 | 7,787 | 52.1 | +0.255 | +0.288 | +3.183 | -2.936 | 1.18 |
| BB pos < 0.2 | 14,466 | 7,521 | 52.0 | +0.135 | +0.293 | +3.118 | -3.096 | 1.09 |
| Mua thứ 6 (Friday) | 15,787 | 8,189 | 51.9 | +0.452 | +0.266 | +3.077 | -2.377 | 1.40 |
| RSI 30-40 | 11,470 | 5,917 | 51.6 | +0.151 | +0.245 | +2.851 | -2.726 | 1.11 |
| NN+TD cùng bán ròng 5d | 16,019 | 8,155 | 50.9 | +0.206 | +0.176 | +3.040 | -2.734 | 1.15 |
| RSI<35 + Vol>1.5x | 1,307 | 665 | 50.9 | +0.153 | +0.157 | +4.813 | -4.674 | 1.07 |
| MA5 < MA20 (downtrend) | 38,210 | 19,348 | 50.6 | +0.173 | +0.162 | +2.984 | -2.711 | 1.13 |
| 3 phiên tăng liên tiếp | 6,906 | 3,484 | 50.5 | +0.367 | +0.146 | +3.508 | -2.832 | 1.26 |
| NN+TD cùng mua ròng 5d | 11,129 | 5,591 | 50.2 | +0.283 | +0.114 | +3.152 | -2.614 | 1.22 |
| Giá dưới MA20 3-5% | 7,394 | 3,712 | 50.2 | -0.104 | +0.129 | +2.715 | -2.945 | 0.93 |
| Tự doanh bán ròng 5d | 29,190 | 14,652 | 50.2 | +0.159 | +0.118 | +3.049 | -2.754 | 1.12 |
| Gần MA20 + NN+TD mua | 3,400 | 1,699 | 50.0 | +0.241 | +0.000 | +2.746 | -2.262 | 1.21 |
| Tự doanh mua ròng 5d | 26,053 | 13,001 | 49.9 | +0.169 | +0.000 | +2.978 | -2.628 | 1.13 |
| Vol thấp <0.5x | 10,415 | 5,180 | 49.7 | +0.261 | +0.000 | +3.071 | -2.519 | 1.21 |
| NN bán ròng 5d | 40,816 | 20,254 | 49.6 | +0.153 | +0.000 | +3.059 | -2.709 | 1.11 |
| Giá < MA60 (long-term down) | 38,786 | 19,237 | 49.6 | +0.196 | +0.000 | +2.923 | -2.488 | 1.16 |
| Uptrend + Pullback MA20 + Vol>1.5x | 364 | 179 | 49.2 | -0.383 | +0.000 | +2.718 | -3.385 | 0.78 |
| NN mua ròng 5d | 33,048 | 16,235 | 49.1 | +0.202 | +0.000 | +3.256 | -2.747 | 1.14 |
| Mua thứ 3 (Tuesday) | 15,786 | 7,713 | 48.9 | +0.242 | +0.000 | +3.195 | -2.579 | 1.18 |
| Giá trên MA20 0-2% | 13,904 | 6,754 | 48.6 | +0.235 | +0.000 | +2.863 | -2.248 | 1.20 |
| Giá > MA60 (long-term up) | 39,632 | 19,206 | 48.5 | +0.155 | +0.000 | +3.384 | -2.881 | 1.10 |
| Giá dưới MA20 1-3% | 12,947 | 6,271 | 48.4 | +0.028 | +0.000 | +2.531 | -2.323 | 1.02 |
| RSI > 70 (overbought) | 5,342 | 2,557 | 47.9 | +0.415 | +0.000 | +4.377 | -3.222 | 1.25 |
| MA5 > MA20 (uptrend) | 40,085 | 19,037 | 47.5 | +0.176 | +0.000 | +3.325 | -2.673 | 1.12 |
| BB<0.2 + Vol>1.5x | 1,987 | 942 | 47.4 | -0.271 | +0.000 | +4.168 | -4.271 | 0.88 |
| Giá>MA20 + Vol>2x + RSI 40-60 | 1,272 | 602 | 47.3 | -0.045 | +0.000 | +3.151 | -2.917 | 0.97 |
| Tăng >3% trong phiên | 6,558 | 3,103 | 47.3 | +0.356 | +0.000 | +4.454 | -3.324 | 1.20 |
| Mua thứ 5 (Thursday) | 15,787 | 7,470 | 47.3 | -0.071 | +0.000 | +3.074 | -2.896 | 0.95 |
| Vol tăng >1.5x | 11,907 | 5,611 | 47.1 | +0.059 | +0.000 | +3.749 | -3.229 | 1.04 |
| Giá trên MA20 2-5% | 13,519 | 6,312 | 46.7 | +0.091 | +0.000 | +3.081 | -2.528 | 1.07 |
| Vol tăng đột biến >2x | 5,214 | 2,404 | 46.1 | +0.044 | +0.000 | +4.068 | -3.399 | 1.02 |
| BB pos > 0.9 (gần upper) | 9,807 | 4,444 | 45.3 | +0.111 | -0.137 | +3.759 | -2.911 | 1.07 |
| Mua thứ 4 (Wednesday) | 15,687 | 7,012 | 44.7 | -0.233 | -0.150 | +3.371 | -3.147 | 0.87 |
| RSI<40 + Vol>2x | 795 | 347 | 43.6 | -0.668 | -0.211 | +4.976 | -5.040 | 0.77 |

---

## 9. Giải Thích Các Chỉ Số

| Chỉ số | Ý nghĩa |
|--------|---------|
| **Win Rate** | Tỷ lệ giao dịch có lãi (%) |
| **Avg Return** | Lợi nhuận trung bình mỗi giao dịch (%) |
| **Median Return** | Lợi nhuận trung vị — phản ánh trường hợp "điển hình" hơn mean |
| **Avg Win** | Lợi nhuận trung bình khi thắng (%) |
| **Avg Loss** | Thua lỗ trung bình khi thua (%) |
| **Profit Factor (PF)** | Tổng lãi / Tổng lỗ. PF > 1.5 là tốt, > 2.0 là xuất sắc |
| **RSI(14)** | Relative Strength Index 14 phiên. < 30 = oversold, > 70 = overbought |
| **MA20** | Đường trung bình 20 phiên |
| **BB** | Bollinger Band — vị trí giá trong dải Bollinger (0 = lower band, 1 = upper band) |
| **NN mua ròng** | Nước ngoài mua ròng tổng 5 phiên gần nhất |
| **TD mua ròng** | Tự doanh (proprietary trading) mua ròng 5 phiên gần nhất |

---

*Kết quả backtest dựa trên dữ liệu lịch sử, không đảm bảo lợi nhuận trong tương lai. Đây không phải khuyến nghị đầu tư. Luôn kết hợp phân tích riêng và quản lý rủi ro phù hợp.*
