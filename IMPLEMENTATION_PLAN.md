# Kế hoạch Triển khai: VNINDEX Signal Website

## Tổng quan

Website hiển thị tín hiệu mua/bán cổ phiếu HOSE, nhận dữ liệu từ prompt phân tích chạy thủ công mỗi ngày, và theo dõi hiệu suất (PnL) của từng tín hiệu theo thời gian.

---

## 1. Kiến trúc hệ thống

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
        │ POST /api/signals (API key auth)
        │
┌───────┴───────────────┐
│  Claude Code Prompt    │
│  (chạy thủ công/ngày) │
│  - Playwright → Fireant│
│  - Tính điểm TC/SS/KT/DT│
│  - Gọi API ghi kết quả │
└───────────────────────┘
```

### Tech stack

| Layer | Công nghệ | Lý do |
|-------|-----------|-------|
| Backend | FastAPI (Python) | Cùng ngôn ngữ với prompt, async-native, nhẹ |
| Frontend | Next.js 14 App Router | ISR, Tailwind + shadcn/ui sẵn có |
| Database | PostgreSQL (Railway) | Free 1GB, quan hệ rõ ràng, JSON support |
| Deploy | Railway | Yêu cầu của user, free tier đủ dùng |

---

## 2. Database Schema

### Quyết định thiết kế quan trọng

**Giá tham chiếu cho PnL:** Signal sinh ra sau giờ đóng cửa — giá actionable thực tế là giá **mở cửa T+1**, không phải giá đóng ngày phân tích. Lưu cả hai:
- `price_close_signal_date`: giá đóng cửa ngày phân tích (để biết context)
- `price_open_t1`: giá mở cửa ngày T+1 (dùng để tính PnL, nullable cho đến khi có dữ liệu)

**Tính `days_after`:** Dùng bảng `trading_calendar` làm reference duy nhất, tránh mỗi nơi tự tính theo cách khác.

```sql
-- Lịch giao dịch HOSE (trading days reference)
-- Cần seed dữ liệu khi khởi tạo và maintain hàng năm
CREATE TABLE trading_calendar (
    trade_date  DATE PRIMARY KEY,
    is_trading  BOOLEAN NOT NULL DEFAULT TRUE,
    note        VARCHAR(100)  -- tên ngày lễ nếu là ngày nghỉ
);

-- Mỗi lần chạy prompt = 1 run
CREATE TABLE analysis_runs (
    id          SERIAL PRIMARY KEY,
    run_date    DATE NOT NULL UNIQUE,
    top_n       INTEGER NOT NULL DEFAULT 30,
    hold_days   INTEGER NOT NULL DEFAULT 20,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    notes       TEXT
);

-- Tín hiệu của từng mã trong mỗi run
CREATE TABLE signals (
    id              SERIAL PRIMARY KEY,
    run_id          INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    run_date        DATE NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    -- ENUM: active | suspended | delisted | expired

    -- Điểm thành phần
    score_financial INTEGER NOT NULL,   -- -2 đến +2
    score_seasonal  INTEGER NOT NULL,   -- -2 đến +2
    score_technical INTEGER NOT NULL,   -- -1 đến +1
    score_cashflow  INTEGER NOT NULL,   -- -1 đến +1
    score_total     INTEGER NOT NULL,   -- -7 đến +6

    -- Khuyến nghị
    recommendation  VARCHAR(20) NOT NULL,
    -- BUY_STRONG | BUY | HOLD | AVOID | SELL
    signal_type     VARCHAR(10) NOT NULL,
    -- BUY | SELL | HOLD

    -- Giá tham chiếu (tách rõ để tính PnL đúng)
    price_close_signal_date DECIMAL(12,2) NOT NULL,
    -- giá đóng cửa ngày phân tích (context)
    price_open_t1           DECIMAL(12,2),
    -- giá mở cửa T+1 (dùng tính PnL) — nullable đến khi có data
    market_cap_bil          DECIMAL(15,2),

    -- Cờ cảnh báo corporate actions
    has_corporate_action    BOOLEAN DEFAULT FALSE,
    -- set TRUE khi phát hiện giá biến động >30% bất thường

    -- Chi tiết dạng JSON
    detail_financial JSONB, -- {lnstYoY, salesYoY, marginDelta, earningsAccel, quarter}
    detail_technical JSONB, -- {vsMa20, rsi14, bbPos, ma20, ma60}
    detail_cashflow  JSONB, -- {fgNet5d, propNet5d, fgNet5dZ}
    detail_seasonal  JSONB, -- {month, dayOfWeek, reason}

    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(run_date, symbol)
);

-- Trigger tự cập nhật updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER signals_updated_at
    BEFORE UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX idx_signals_run_date       ON signals(run_date DESC);
CREATE INDEX idx_signals_symbol         ON signals(symbol);
CREATE INDEX idx_signals_recommendation ON signals(recommendation);
CREATE INDEX idx_signals_status         ON signals(status);

-- Theo dõi giá T+N để tính PnL
-- PnL tính từ price_open_t1 (giá thực tế có thể mua)
CREATE TABLE price_tracking (
    id          SERIAL PRIMARY KEY,
    signal_id   INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    run_date    DATE NOT NULL,
    symbol      VARCHAR(10) NOT NULL,
    track_date  DATE NOT NULL,
    days_after  INTEGER NOT NULL,
    -- số ngày giao dịch sau signal (dùng trading_calendar để tính)
    price_close DECIMAL(12,2),
    pnl_pct     DECIMAL(8,4),
    -- (price_close / price_open_t1 - 1) * 100
    -- NULL nếu price_open_t1 chưa có
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(signal_id, track_date)
);

CREATE INDEX idx_price_tracking_signal ON price_tracking(signal_id);
CREATE INDEX idx_price_tracking_dates  ON price_tracking(run_date, track_date);

-- Materialized view (thay vì regular view) — nhanh hơn khi query
CREATE MATERIALIZED VIEW signal_pnl_summary AS
SELECT
    s.run_date, s.symbol, s.score_total, s.recommendation, s.status,
    s.price_close_signal_date,
    s.price_open_t1,
    s.has_corporate_action,
    pt_1.pnl_pct  AS pnl_d1,
    pt_5.pnl_pct  AS pnl_d5,
    pt_10.pnl_pct AS pnl_d10,
    pt_20.pnl_pct AS pnl_d20,
    (SELECT pnl_pct FROM price_tracking
     WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1) AS latest_pnl_pct
FROM signals s
LEFT JOIN price_tracking pt_1  ON pt_1.signal_id = s.id AND pt_1.days_after = 1
LEFT JOIN price_tracking pt_5  ON pt_5.signal_id = s.id AND pt_5.days_after = 5
LEFT JOIN price_tracking pt_10 ON pt_10.signal_id = s.id AND pt_10.days_after = 10
LEFT JOIN price_tracking pt_20 ON pt_20.signal_id = s.id AND pt_20.days_after = 20;

CREATE UNIQUE INDEX ON signal_pnl_summary(run_date, symbol);
-- Cần unique index để REFRESH CONCURRENTLY hoạt động

-- Refresh sau mỗi đợt price update (gọi từ backend service)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY signal_pnl_summary;

-- API keys (bcrypt hash — không dùng SHA256)
CREATE TABLE api_keys (
    id          SERIAL PRIMARY KEY,
    key_hash    VARCHAR(72) NOT NULL UNIQUE,
    -- bcrypt hash (72 char)
    label       VARCHAR(100),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_used   TIMESTAMPTZ
);

-- Audit log (ghi nhẹ, không block)
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    action      VARCHAR(50) NOT NULL, -- signals.write | price.update | key.auth
    run_date    DATE,
    symbol      VARCHAR(10),
    api_key_id  INTEGER REFERENCES api_keys(id),
    details     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
```

---

## 3. API Endpoints

### 3.1 Ghi tín hiệu (prompt gọi sau phân tích)

```
POST /api/v1/signals
Authorization: Bearer {API_KEY}
```

**Request body:**
```json
{
  "run_date": "2026-03-24",
  "top_n": 30,
  "hold_days": 20,
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
      "detail_financial": {
        "quarter": "Q3/2025",
        "lnstYoY": -5.2,
        "salesYoY": 3.1,
        "marginDelta": 1.2,
        "earningsAccel": 8.5
      },
      "detail_technical": {
        "vsMa20": -1.5,
        "rsi14": 48.2,
        "bbPos": 0.42,
        "ma20": 45893,
        "ma60": 44100
      },
      "detail_cashflow": {
        "fgNet5d": 1250000,
        "propNet5d": 850000000,
        "fgNet5dZ": 0.8
      },
      "detail_seasonal": {
        "month": 3,
        "dayOfWeek": 1,
        "reason": "neutral"
      }
    }
  ]
}
```

**Response — rõ ràng insert/update/error:**
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

> Dùng `UPSERT` (ON CONFLICT). Validate `run_date` phải có trong `trading_calendar.is_trading = TRUE`.

### 3.2 Update giá follow-up

```
GET  /api/v1/price-updates/pending?limit=50   -- danh sách cần update
POST /api/v1/price-updates                    -- ghi giá mới
```

**POST body — hỗ trợ cả `price_open` (cho T+1) và `price_close`:**
```json
{
  "track_date": "2026-03-25",
  "prices": [
    {"symbol": "VIC", "price_open": 45500.0, "price_close": 46100.0},
    {"symbol": "VCB", "price_open": null,    "price_close": 89500.0}
  ]
}
```

Server tự:
1. Tính `days_after` dùng `trading_calendar` (đếm ngày giao dịch từ `run_date` đến `track_date`)
2. Populate `signals.price_open_t1` khi `days_after = 1`
3. Tính `pnl_pct = (price_close / price_open_t1 - 1) * 100`
4. Flag `has_corporate_action = TRUE` nếu `abs(pnl_pct) > 30`
5. Gọi `REFRESH MATERIALIZED VIEW CONCURRENTLY signal_pnl_summary`

### 3.3 Endpoints đọc (frontend)

```
GET /api/v1/health                                    -- health check (Railway)
GET /api/v1/runs?limit=30&offset=0                    -- danh sách ngày đã phân tích
GET /api/v1/signals/{run_date}?recommendation=BUY     -- tín hiệu ngày đó
GET /api/v1/signals/{run_date}/{symbol}               -- chi tiết + PnL history
GET /api/v1/stats/pnl?days=60                        -- thống kê PnL tổng hợp
GET /api/v1/stats/accuracy                           -- win rate theo recommendation
GET /api/v1/export/csv?from=2026-01-01               -- export CSV
```

**Rate limiting:**
- GET (unauthenticated): 60 req/min
- POST (authenticated): 10 req/min

---

## 4. Frontend Pages

### Cấu trúc

```
/                        → redirect đến ngày mới nhất
/signals                 → danh sách các ngày đã phân tích
/signals/[date]          → bảng tín hiệu của ngày [date]
/signals/[date]/[symbol] → chi tiết + PnL chart
/stats                   → thống kê tổng hợp
```

> **ISR thay SSR:** Dùng `revalidate = 3600` (1 giờ) cho tất cả signal pages. Signal chỉ thay đổi 1 lần/ngày, không cần SSR mỗi request.

### Trang `/signals/[date]` (trang chính)

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 VNINDEX Signal  │  [Chọn ngày ▼]                           │
├─────────────────────────────────────────────────────────────────┤
│  📅 24/03/2026 │ 30 mã │ HOSE Top 30                           │
├─────────────────────────────────────────────────────────────────┤
│  [Tất cả] [🟢🟢 Mua mạnh] [🟢 Mua] [🟡 Theo dõi] [🔴 Tránh]   │
├─────────────────────────────────────────────────────────────────┤
│ Vốn hoá │ Mã  │ TC │ SS │ KT │ DT │ Tổng │ KN │ Giá đóng │ T+1 │ T+5 │ T+20│
│ 1,125B  │ VIC │ +2 │ +1 │  0 │ -1 │  +2  │ 🟢 │   45.2K  │+2.0%│ ... │ ... │
│   505B  │ VCB │ -1 │  0 │ +1 │ +1 │  +1  │ 🟡 │   89.5K  │-0.5%│ ... │ ... │
│   ⚠️ HPG│ ...                                  │ ⚠️ Corp.action│ — │  —  │  —  │
└─────────────────────────────────────────────────────────────────┘
```

- Màu PnL: xanh (dương), đỏ (âm), `—` xám (chưa có dữ liệu)
- Icon ⚠️ nếu `has_corporate_action = TRUE`
- Tooltip giải thích khi hover vào T+1, T+5, T+20: "Tính từ giá mở cửa T+1"

### Trang `/stats`

- PnL trung bình theo nhóm khuyến nghị (bar chart)
- Win rate (PnL > 0) theo T+1, T+5, T+20
- Top mã hiệu suất tốt nhất/kém nhất
- Nút "Export CSV"

---

## 5. Quy trình Update Giá Follow-up

### Phương án khuyến nghị: Tích hợp vào prompt

Prompt đã lấy `historical-quotes` 1000 phiên từ Fireant (bước 2A) — dữ liệu giá `priceOpen` + `priceClose` các ngày trước đã sẵn có. Thêm **Bước 6** vào `main-prompt.txt`:

```
## BƯỚC 6 — GHI KẾT QUẢ LÊN WEBSITE

WEBSITE_URL = "https://vnindex-signal.railway.app"
API_KEY = "[API key]"

### 6A. Ghi tín hiệu hôm nay
POST {WEBSITE_URL}/api/v1/signals
Authorization: Bearer {API_KEY}
Body: JSON kết quả bước 4-5 (dùng price_close_signal_date từ giá đóng cửa hôm nay)

### 6B. Update giá follow-up cho tín hiệu cũ
1. GET {WEBSITE_URL}/api/v1/price-updates/pending
   → Nhận danh sách {symbol, run_date, track_dates_needed}
2. Với mỗi symbol/ngày, map price_open + price_close từ historical-quotes bước 2A
3. POST {WEBSITE_URL}/api/v1/price-updates
   (Server tự tính days_after, populate price_open_t1, tính pnl_pct)

✅ In ra: "Đã ghi {N} tín hiệu (insert: X, update: Y). Update {M} price tracking records"
```

**Phương án dự phòng:** Railway Cron job 17:00 mỗi ngày giao dịch, tự gọi Fireant API.

---

## 6. Backup Strategy

Railway free tier không có automated backup. Cần setup thủ công:

```bash
# Railway Cron job: chạy 2:00 AM hàng ngày
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz
# Upload lên Google Cloud Storage (free 5GB) hoặc S3
gsutil cp backup_*.sql.gz gs://vnindex-signal-backups/
```

Giữ 30 ngày backup gần nhất, xóa cũ hơn.

---

## 7. Cấu trúc Project

```
vnindex-signal/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── signal.py
│   │   ├── price_tracking.py
│   │   └── trading_calendar.py
│   ├── routers/
│   │   ├── health.py             # GET /health
│   │   ├── signals.py            # POST/GET tín hiệu
│   │   ├── price_updates.py      # Update + pending logic
│   │   ├── stats.py              # PnL stats
│   │   └── export.py             # CSV export
│   ├── schemas/
│   │   ├── signal_input.py
│   │   └── signal_output.py
│   ├── services/
│   │   ├── signal_service.py
│   │   ├── pnl_service.py        # tính pnl_pct, detect corp actions
│   │   └── calendar_service.py   # days_after dùng trading_calendar
│   ├── alembic/
│   │   └── versions/             # migrations
│   ├── scripts/
│   │   └── seed_trading_calendar.py  # seed ngày giao dịch HOSE
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── signals/
│   │   │   ├── page.tsx
│   │   │   └── [date]/
│   │   │       ├── page.tsx          # ISR revalidate=3600
│   │   │       └── [symbol]/page.tsx
│   │   └── stats/page.tsx
│   ├── components/
│   │   ├── SignalTable.tsx
│   │   ├── PnlBadge.tsx
│   │   ├── RecommendationBadge.tsx
│   │   ├── CorporateActionWarning.tsx
│   │   └── PnlChart.tsx
│   ├── lib/api.ts
│   ├── package.json
│   └── Dockerfile
├── main-prompt.txt
├── railway.toml
└── docker-compose.yml
```

---

## 8. Railway Deployment

```toml
# railway.toml
[[services]]
name = "backend"
source = "backend/"
[services.variables]
DATABASE_URL = "${{Postgres.DATABASE_URL}}"
API_SECRET_KEY = "${{API_SECRET_KEY}}"
PORT = "8000"

[[services]]
name = "frontend"
source = "frontend/"
[services.variables]
NEXT_PUBLIC_API_URL = "https://${{backend.RAILWAY_PUBLIC_DOMAIN}}"
PORT = "3000"
```

Railway free tier đủ dùng: 500 giờ/tháng cho 2 services, PostgreSQL 1GB.

---

## 9. Các bước triển khai

### Phase 1 — Backend (~4-5 giờ)
- [ ] Khởi tạo FastAPI, SQLAlchemy async, Alembic
- [ ] Migration: `trading_calendar`, `analysis_runs`, `signals`, `price_tracking`, `api_keys`, `audit_log`
- [ ] Seed `trading_calendar` với ngày giao dịch HOSE (2015–2027)
- [ ] `calendar_service.py`: hàm `trading_days_between(start, end)` và `is_trading_day(date)`
- [ ] `POST /api/v1/signals`: upsert + validate trading day + bcrypt auth + audit log
- [ ] `GET/POST /api/v1/price-updates`: pending logic + populate `price_open_t1` + corp action flag
- [ ] `GET /api/v1/health`
- [ ] GET endpoints với pagination (`limit`/`offset`)
- [ ] Rate limiting (slowapi)
- [ ] Dockerfile + test local

### Phase 2 — Frontend (~4-5 giờ)
- [ ] Khởi tạo Next.js 14, shadcn/ui, Tailwind
- [ ] API client `lib/api.ts`
- [ ] `SignalTable` với filter, sort, PnL columns, corp action warning icon
- [ ] Trang `/signals/[date]` — ISR `revalidate=3600`
- [ ] Trang `/stats` (Recharts), nút Export CSV
- [ ] Dockerfile

### Phase 3 — Deploy Railway (~1-2 giờ)
- [ ] Tạo Railway project + PostgreSQL plugin
- [ ] Deploy backend, chạy Alembic migration + seed calendar
- [ ] Deploy frontend
- [ ] Set environment variables
- [ ] Generate API key (bcrypt), update `main-prompt.txt`
- [ ] Setup backup cron (pg_dump → GCS)

### Phase 4 — Tích hợp Prompt (~1 giờ)
- [ ] Thêm Bước 6 vào `main-prompt.txt`
- [ ] Chạy thử, kiểm tra response `{inserted, updated, errors}`
- [ ] Verify PnL tính từ `price_open_t1` đúng

---

## 10. Lưu ý quan trọng

**PnL reference price:**
- `price_close_signal_date`: giá đóng cửa ngày phân tích (chỉ để hiển thị context)
- `price_open_t1`: giá mở cửa T+1 — **đây là giá dùng tính PnL**
- Nếu `price_open_t1` chưa có (T+1 chưa xảy ra), tất cả PnL columns hiển thị `—`

**Corporate actions:**
- Backend flag `has_corporate_action = TRUE` khi `abs(pnl_pct) > 30%`
- Frontend hiển thị icon ⚠️ và tooltip "Có thể có split/dividend — cần review thủ công"
- PnL vẫn hiển thị nhưng cần review trước khi dùng để phân tích

**Trading calendar:**
- Là single source of truth cho `days_after`
- Cần seed đủ data và maintain hàng năm (thêm ngày lễ mới)
- Validate `run_date` phải là trading day trước khi insert

**Security:**
- API key hash bằng `bcrypt` (cost factor 12), không dùng SHA256
- CORS whitelist chỉ domain frontend
- Rate limit: GET 60/min, POST 10/min

**Database integrity:**
- `UNIQUE(run_date, symbol)` + upsert ngăn duplicate khi re-run
- `MATERIALIZED VIEW REFRESH CONCURRENTLY` sau mỗi price update batch
- Backup daily qua `pg_dump` → GCS (giữ 30 ngày)

---

## 11. Review Feedback #2 (2026-03-24)

> Phiên bản này đã sửa tốt tất cả 16 feedback items từ review #1. Dưới đây là các vấn đề mới phát hiện.

### 🟡 MEDIUM

**1. Materialized view có correlated subquery — chậm khi scale**
- Dòng `(SELECT pnl_pct FROM price_tracking WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1) AS latest_pnl_pct` là correlated subquery, chạy 1 lần cho mỗi row trong `signals`
- Với 15K signals → 15K subqueries mỗi lần REFRESH
- **Khuyến nghị:** Thay bằng `LATERAL JOIN` hoặc `DISTINCT ON`:
  ```sql
  LEFT JOIN LATERAL (
      SELECT pnl_pct FROM price_tracking
      WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1
  ) pt_latest ON TRUE
  ```

**2. `price_tracking` thiếu index cho `(signal_id, days_after)`**
- Materialized view join trên `signal_id AND days_after = N` nhưng chỉ có index trên `signal_id` đơn lẻ
- **Khuyến nghị:** Thêm composite index:
  ```sql
  CREATE INDEX idx_price_tracking_signal_days ON price_tracking(signal_id, days_after);
  ```
  (Có thể thay thế index `idx_price_tracking_signal` đơn lẻ)

**3. `trading_calendar` chỉ chứa ngày giao dịch hay tất cả ngày?**
- Schema có `is_trading BOOLEAN DEFAULT TRUE` nhưng không rõ: seed tất cả ngày trong năm (365 rows/năm) hay chỉ ngày giao dịch (~250 rows/năm)?
- Nếu chỉ seed ngày giao dịch → `is_trading` luôn TRUE → column vô nghĩa
- Nếu seed tất cả ngày → function `trading_days_between()` phải đếm `WHERE is_trading = TRUE`
- **Khuyến nghị:** Seed tất cả ngày (365/năm) với `is_trading = FALSE` cho weekends + holidays. Ghi rõ convention trong schema comment

**4. `POST /api/v1/price-updates` thiếu validate `track_date` là trading day**
- Endpoint validate `run_date` là trading day, nhưng `track_date` trong price update cũng phải là trading day (không có giá đóng cửa ngày nghỉ)
- **Khuyến nghị:** Validate `track_date` tương tự `run_date`

**5. `signal_type` column có vẻ redundant với `recommendation`**
- `recommendation`: BUY_STRONG | BUY | HOLD | AVOID | SELL
- `signal_type`: BUY | SELL | HOLD
- `signal_type` có thể suy ra từ `recommendation` (BUY_STRONG/BUY → BUY, AVOID/SELL → SELL, HOLD → HOLD)
- **Khuyến nghị:** Hoặc bỏ `signal_type` và derive trong code/view, hoặc ghi rõ mapping rule để tránh inconsistency khi upsert

**6. Backup script chạy trên Railway cron — nhưng `gsutil` không có sẵn**
- Railway container không có `gsutil` pre-installed
- **Khuyến nghị:** Dùng Python script với `boto3` (S3) hoặc `google-cloud-storage` SDK thay vì shell script. Hoặc backup bằng cách gọi API endpoint nội bộ trigger pg_dump

### 🟢 LOW

**7. `score_total` có thể tính sai khi upsert**
- `score_total` lưu trong DB nhưng cũng có thể tính từ `score_financial + score_seasonal + score_technical + score_cashflow`
- Nếu client gửi `score_total` không khớp tổng 4 thành phần → data inconsistent
- **Khuyến nghị:** Validate `score_total == sum(4 scores)` trong Pydantic schema, hoặc tính server-side và bỏ qua giá trị client gửi

**8. `GET /api/v1/signals/{run_date}` thiếu sort parameter**
- UI wireframe cho thấy sort theo tổng điểm mặc định, nhưng API không có `?sort=score_total&order=desc`
- **Khuyến nghị:** Thêm `?sort_by=score_total|symbol|market_cap&order=asc|desc`

**9. Thiếu `GET /api/v1/price-updates/pending` response format**
- Endpoint được define nhưng response contract chưa rõ
- **Khuyến nghị:** Document response:
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

**10. `REFRESH MATERIALIZED VIEW CONCURRENTLY` chạy sau mỗi price update batch — có thể chậm**
- Nếu prompt gọi nhiều batch price updates liên tiếp → refresh nhiều lần không cần thiết
- **Khuyến nghị:** Chỉ refresh 1 lần sau khi tất cả batches hoàn thành. Thêm param `?skip_refresh=true` cho intermediate batches, hoặc tách thành `POST /api/v1/admin/refresh-views`

### Tóm tắt

| Ưu tiên | # | Vấn đề | Effort |
|---------|---|--------|--------|
| 🟡 MED | 1 | Correlated subquery trong materialized view | Nhỏ |
| 🟡 MED | 2 | Thiếu composite index `(signal_id, days_after)` | 1 dòng SQL |
| 🟡 MED | 3 | Clarify `trading_calendar` seed convention | Doc only |
| 🟡 MED | 4 | Validate `track_date` là trading day | Nhỏ |
| 🟡 MED | 5 | `signal_type` redundant với `recommendation` | Design decision |
| 🟡 MED | 6 | Backup script cần Python SDK, không phải gsutil | Nhỏ |
| 🟢 LOW | 7 | Validate `score_total` consistency | Nhỏ |
| 🟢 LOW | 8 | Thiếu sort parameter cho signals endpoint | Nhỏ |
| 🟢 LOW | 9 | Document pending response format | Doc only |
| 🟢 LOW | 10 | Optimize materialized view refresh frequency | Nhỏ |

> **Đánh giá tổng thể:** Plan đã ở trạng thái tốt, sẵn sàng implement. Không có vấn đề HIGH nào. Các items trên đều có thể fix trong quá trình build mà không cần thay đổi architecture.
