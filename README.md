# VNINDEX Signal

Website hiển thị tín hiệu mua/bán cổ phiếu HOSE, nhận dữ liệu từ prompt phân tích chạy thủ công mỗi ngày, và theo dõi hiệu suất (PnL) của từng tín hiệu theo thời gian.

## 1. Tổng quan

| Layer | Công nghệ | Ghi chú |
|-------|-----------|---------|
| Backend | FastAPI (Python 3.11) | Async, SQLAlchemy 2.0 + asyncpg |
| Frontend | Next.js 14 App Router | ISR revalidate=3600, Tailwind + shadcn/ui |
| Database | PostgreSQL 16 | Railway managed, 1GB free tier |
| Auth | bcrypt (cost 12) | API key hash lưu DB, không plain text |
| Rate limit | slowapi | GET 60/min, POST 10/min |
| Deploy | Railway | 2 services + PostgreSQL plugin |

---

## 2. Kiến trúc

```
┌─────────────────────────────────────────────────────┐
│                   RAILWAY DEPLOYMENT                 │
│                                                      │
│  ┌──────────────┐    ┌──────────────┐               │
│  │   Frontend   │    │   Backend    │               │
│  │  Next.js 14  │◄──►│  FastAPI     │               │
│  │  (App Router)│    │  (Python)    │               │
│  └──────────────┘    └──────┬───────┘               │
│                             │                        │
│                      ┌──────▼───────┐               │
│                      │  PostgreSQL   │               │
│                      │  (Railway DB) │               │
│                      └──────────────┘               │
└─────────────────────────────────────────────────────┘
        ▲
        │ POST /api/v1/signals (API key auth)
        │
┌───────┴───────────────┐
│  Claude Code Prompt    │
│  (chạy thủ công/ngày) │
│  - Playwright → Fireant│
│  - Tính điểm TC/SS/KT/DT│
│  - Gọi API ghi kết quả │
└───────────────────────┘
```

Luồng dữ liệu:
1. Chạy `main-prompt.txt` thủ công mỗi ngày giao dịch
2. Prompt lấy dữ liệu từ Fireant qua Playwright, tính điểm, gọi API
3. Backend upsert vào PostgreSQL, validate `run_date` phải là trading day
4. Frontend đọc qua ISR — cache 1 giờ, tự invalidate

---

## 3. Chạy local với Docker Compose

**Yêu cầu:** Docker Desktop đang chạy.

```bash
# 1. Clone repo
git clone <repo-url>
cd vnindex-signal

# 2. Khởi động toàn bộ stack
docker compose up -d

# 3. Chờ postgres healthy, chạy migration
docker compose exec backend alembic upgrade head

# (Tuỳ chọn) Trang /admin/feedback: tạo API key, ghi vào .env ở root repo rồi restart frontend
# cp .env.example .env
# docker compose exec backend python scripts/create_api_key.py --label "admin-feedback"
# echo 'ADMIN_API_KEY=<dán_raw_key_vừa_in>' >> .env
# docker compose up -d --build frontend

# 4. Seed trading calendar (2015–2027)
docker compose exec backend python scripts/seed_trading_calendar.py

# 5. Kiểm tra backend hoạt động
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}

# 6. Mở frontend
open http://localhost:3000
```

**Dừng và xoá data:**
```bash
docker compose down -v   # -v xoá cả volume postgres
```

**Xem log:**
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

> Backend chạy với `--reload` — thay đổi code trong `./backend/` tự động restart.

---

## 4. Chạy local thủ công (không Docker)

**Yêu cầu:** Python 3.11+, Node.js 20+, PostgreSQL 16 đang chạy local.

### Backend

```bash
# 1. Tạo database
psql -U postgres -c "CREATE DATABASE vnindex_signal;"

# 2. Cài dependencies
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Tạo file .env trong backend/
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vnindex_signal
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/vnindex_signal
API_SECRET_KEY=dev-secret-key-change-in-prod
CORS_ORIGINS=["http://localhost:3000"]
EOF

# 4. Chạy migration
alembic upgrade head

# 5. Seed trading calendar
python scripts/seed_trading_calendar.py

# 6. Khởi động backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
# Mở terminal mới
cd frontend
npm install

# Tạo file .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Khởi động frontend
npm run dev
```

Frontend chạy tại `http://localhost:3000`, backend tại `http://localhost:8000`.

API docs (Swagger): `http://localhost:8000/docs`

---

## 5. Deploy lên Railway

### Bước 1 — Chuẩn bị

```bash
# Cài Railway CLI
npm install -g @railway/cli

# Đăng nhập
railway login
```

### Bước 2 — Tạo project và PostgreSQL

```bash
# Tạo project mới
railway init

# Thêm PostgreSQL plugin
railway add --plugin postgresql
```

### Bước 3 — Deploy backend

```bash
# Từ thư mục gốc repo
railway up --service backend
```

Sau khi deploy xong, chạy migration và seed:

```bash
# Lấy shell vào backend service
railway run --service backend bash

# Bên trong shell Railway
alembic upgrade head
python scripts/seed_trading_calendar.py
exit
```

### Bước 4 — Set environment variables

Vào Railway Dashboard → service `backend` → tab **Variables**, thêm:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway tự inject) |
| `API_SECRET_KEY` | Chuỗi random dài ≥32 ký tự |
| `PORT` | `8000` |
| `CORS_ORIGINS` | `["https://<frontend-domain>.railway.app"]` |

### Bước 5 — Deploy frontend

```bash
railway up --service frontend
```

Vào Railway Dashboard → service `frontend` → tab **Variables**, thêm:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | URL public của backend service (lấy từ Railway dashboard) |
| `PORT` | `3000` |

### Bước 6 — Kiểm tra

```bash
# Health check backend
curl https://<backend-domain>.railway.app/api/v1/health
# → {"status": "ok"}

# Mở frontend
open https://<frontend-domain>.railway.app
```

> Railway free tier: 500 giờ CPU/tháng cho 2 services, PostgreSQL 1GB. Đủ cho workload 1 run/ngày.

---

## 6. Tạo API Key

API key dùng để prompt xác thực khi gọi `POST /api/v1/signals` và `POST /api/v1/price-updates`.

### Tạo key mới

```bash
# Chạy script tạo key (trong môi trường backend đang hoạt động)
# Local với Docker:
docker compose exec backend python scripts/create_api_key.py --label "main-prompt"

# Local thủ công (đã activate venv):
python scripts/create_api_key.py --label "main-prompt"

# Railway:
railway run --service backend python scripts/create_api_key.py --label "main-prompt"
```

Script in ra:

```
API Key (lưu lại, chỉ hiển thị 1 lần):
sk-vnindex-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Key ID: 3 | Label: main-prompt | Created: 2026-03-24
```

### Lưu key vào main-prompt.txt

Mở `main-prompt.txt`, tìm phần Bước 6 và điền:

```
WEBSITE_URL = "https://<backend-domain>.railway.app"
API_KEY = "sk-vnindex-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

> Key chỉ hiển thị một lần khi tạo. Nếu mất key, tạo key mới và vô hiệu hoá key cũ qua DB: `UPDATE api_keys SET is_active = FALSE WHERE id = <id>;`

---

## 7. Tích hợp với prompt phân tích

Thêm **Bước 6** vào cuối `main-prompt.txt`, sau bước tính điểm:

```
## BƯỚC 6 — GHI KẾT QUẢ LÊN WEBSITE

WEBSITE_URL = "https://<backend-domain>.railway.app"
API_KEY = "<api-key>"

### 6A. Ghi tín hiệu hôm nay

POST {WEBSITE_URL}/api/v1/signals
Authorization: Bearer {API_KEY}
Content-Type: application/json

Body JSON:
{
  "run_date": "<ngày hôm nay YYYY-MM-DD>",
  "top_n": TOP_N,
  "hold_days": HOLD_DAYS,
  "signals": [
    {
      "symbol": "VIC",
      "score_financial": 2,
      "score_seasonal": 1,
      "score_technical": 0,
      "score_cashflow": -1,
      "score_total": 2,
      "recommendation": "BUY",
      "price_close_signal_date": 45200.0,
      "market_cap_bil": 1125081,
      "detail_financial": {"quarter": "Q3/2025", "lnstYoY": -5.2, "salesYoY": 3.1, "marginDelta": 1.2, "earningsAccel": 8.5},
      "detail_technical": {"vsMa20": -1.5, "rsi14": 48.2, "bbPos": 0.42, "ma20": 45893, "ma60": 44100},
      "detail_cashflow":  {"fgNet5d": 1250000, "propNet5d": 850000000, "fgNet5dZ": 0.8},
      "detail_seasonal":  {"month": 3, "dayOfWeek": 1, "reason": "neutral"}
    }
    // ... các mã khác
  ]
}

### 6B. Update giá follow-up cho tín hiệu cũ

1. GET {WEBSITE_URL}/api/v1/price-updates/pending
   → Nhận danh sách symbol/ngày cần cập nhật giá

2. Map price_open + price_close từ historical-quotes đã lấy ở Bước 2A

3. POST {WEBSITE_URL}/api/v1/price-updates với dữ liệu giá

✅ In ra: "Đã ghi {N} tín hiệu (insert: X, update: Y). Update {M} price tracking records."
```

### Response 6A — Ghi tín hiệu

```json
{
  "run_id": 42,
  "run_date": "2026-03-24",
  "inserted": 28,
  "updated": 2,
  "errors": [
    {"symbol": "XYZ", "reason": "run_date is not a trading day"}
  ]
}
```

`errors` trả về danh sách mã bị bỏ qua — thường rỗng. Nếu có lỗi, kiểm tra:
- `run_date` có phải trading day không (xem bảng `trading_calendar`)
- `score_total` có bằng tổng 4 thành phần không

---

## 8. Cập nhật giá follow-up

Quy trình này chạy tự động trong **Bước 6B** của prompt, nhưng cũng có thể chạy thủ công khi cần.

### Bước 1 — Lấy danh sách pending

```bash
curl -H "Authorization: Bearer <API_KEY>" \
  "https://<backend-domain>.railway.app/api/v1/price-updates/pending?limit=50"
```

Response:

```json
[
  {
    "signal_id": 123,
    "symbol": "VIC",
    "run_date": "2026-03-20",
    "track_dates_needed": ["2026-03-21", "2026-03-25"],
    "needs_price_open_t1": true
  }
]
```

`needs_price_open_t1: true` nghĩa là tín hiệu này chưa có giá mở cửa T+1 — PnL chưa tính được.

### Bước 2 — Ghi giá

```bash
curl -X POST \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "track_date": "2026-03-25",
    "prices": [
      {"symbol": "VIC", "price_open": 45500.0, "price_close": 46100.0},
      {"symbol": "VCB", "price_open": null,    "price_close": 89500.0}
    ]
  }' \
  "https://<backend-domain>.railway.app/api/v1/price-updates"
```

Server tự động:
1. Tính `days_after` dùng `trading_calendar` (đếm ngày giao dịch từ `run_date` đến `track_date`)
2. Populate `signals.price_open_t1` khi `days_after = 1`
3. Tính `pnl_pct = (price_close / price_open_t1 - 1) * 100`
4. Flag `has_corporate_action = TRUE` nếu `abs(pnl_pct) > 30%`
5. Refresh materialized view `signal_pnl_summary`

> `price_open` có thể `null` cho các ngày sau T+1 (chỉ cần `price_close` để tính PnL). `price_open` bắt buộc cho T+1 vì đây là giá tham chiếu tính PnL.

---

## 9. API Reference

### Endpoints ghi (yêu cầu `Authorization: Bearer <API_KEY>`)

| Method | Path | Mô tả |
|--------|------|-------|
| `POST` | `/api/v1/signals` | Ghi tín hiệu một ngày phân tích (upsert) |
| `POST` | `/api/v1/price-updates` | Cập nhật giá follow-up cho tín hiệu cũ |

### Endpoints đọc (public, rate limit 60/min)

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/api/v1/health` | Health check (Railway dùng) |
| `GET` | `/api/v1/runs?limit=30&offset=0` | Danh sách ngày đã phân tích |
| `GET` | `/api/v1/signals/{run_date}` | Tín hiệu ngày đó. Query: `?recommendation=BUY&sort_by=score_total&order=desc` |
| `GET` | `/api/v1/signals/{run_date}/{symbol}` | Chi tiết tín hiệu + lịch sử PnL |
| `GET` | `/api/v1/price-updates/pending?limit=50` | Danh sách symbol/ngày cần update giá |
| `GET` | `/api/v1/stats/pnl?days=60` | Thống kê PnL tổng hợp |
| `GET` | `/api/v1/stats/accuracy` | Win rate theo recommendation |
| `GET` | `/api/v1/export/csv?from=2026-01-01` | Export CSV toàn bộ tín hiệu |

### Feedback (góp ý người dùng)

| Method | Path | Mô tả |
|--------|------|-------|
| `POST` | `/api/v1/feedback` | Gửi góp ý (JSON: `message`, `page_url`, optional `name`, `contact`). Public. |
| `GET` | `/api/v1/admin/feedback?limit=200&offset=0` | Danh sách góp ý mới nhất (yêu cầu `Authorization: Bearer <API_KEY>`). |

Trang xem trên website: `/admin/feedback` — đặt `ADMIN_API_KEY` trong file `.env` ở **root repo** (Docker Compose truyền vào container frontend; giá trị là raw key in ra một lần từ `scripts/create_api_key.py`). Backend trong Compose tự chạy `alembic upgrade head` khi start nên bảng `feedback` được tạo khi cần.

### Giá trị hợp lệ

| Field | Giá trị |
|-------|---------|
| `recommendation` | `BUY_STRONG` \| `BUY` \| `HOLD` \| `AVOID` \| `SELL` |
| `score_financial` | -2 đến +2 |
| `score_seasonal` | -2 đến +2 |
| `score_technical` | -1 đến +1 |
| `score_cashflow` | -1 đến +1 |
| `score_total` | phải bằng tổng 4 thành phần |

---

## 10. Maintain hàng năm — Cập nhật trading calendar

Bảng `trading_calendar` là single source of truth để tính `days_after`. Phải cập nhật hàng năm trước khi năm mới bắt đầu.

### Khi nào cần update

- Trước tháng 12 hàng năm: thêm lịch giao dịch năm tới
- Khi HOSE công bố thêm ngày nghỉ bất thường (thiên tai, sự kiện quốc gia)
- Convention: seed **tất cả** ngày trong năm (365 rows), đặt `is_trading = FALSE` cho cuối tuần và ngày lễ

### Cách cập nhật

Mở file `backend/scripts/seed_trading_calendar.py`, tìm phần khai báo ngày nghỉ, thêm năm mới:

```python
HOLIDAYS = {
    # ... năm hiện tại ...
    2027: [
        date(2027, 1, 1),   # Tết Dương lịch
        date(2027, 1, 26),  # Tết Nguyên Đán (nghỉ bù) — kiểm tra thông báo HOSE
        date(2027, 1, 27),  # Tết Nguyên Đán
        date(2027, 1, 28),  # Tết Nguyên Đán
        date(2027, 1, 29),  # Tết Nguyên Đán
        date(2027, 1, 30),  # Tết Nguyên Đán
        date(2027, 2, 1),   # Tết Nguyên Đán (nếu nghỉ bù)
        date(2027, 4, 21),  # Giỗ Tổ Hùng Vương
        date(2027, 4, 30),  # Giải phóng Miền Nam
        date(2027, 5, 1),   # Quốc tế Lao Động
        date(2027, 9, 2),   # Quốc khánh
    ]
}
```

> **Nguồn tham khảo:** Thông báo chính thức từ [HOSE](https://www.hsx.vn) và [Sở Giao dịch Chứng khoán Việt Nam](https://www.ssc.gov.vn) về lịch giao dịch năm mới. Thường công bố tháng 11-12 năm trước.

Sau khi cập nhật, chạy lại seed (script dùng upsert, không tạo duplicate):

```bash
# Local Docker
docker compose exec backend python scripts/seed_trading_calendar.py --year 2027

# Railway
railway run --service backend python scripts/seed_trading_calendar.py --year 2027
```

Kiểm tra:

```sql
-- Xem số ngày giao dịch năm 2027 (kỳ vọng ~250)
SELECT COUNT(*) FROM trading_calendar
WHERE EXTRACT(YEAR FROM trade_date) = 2027
  AND is_trading = TRUE;
```
