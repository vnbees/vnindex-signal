# VNINDEX Signal - Team Context

## Project
Website hiển thị tín hiệu mua/bán cổ phiếu HOSE, nhận dữ liệu từ prompt phân tích chạy thủ công mỗi ngày, theo dõi PnL.

## Tech Stack
- Backend: FastAPI (Python 3.11), SQLAlchemy async, Alembic, PostgreSQL
- Frontend: Next.js 14 App Router, Tailwind CSS, shadcn/ui, Recharts
- Auth: bcrypt (cost 12) for API keys
- Deploy: Railway

## Conventions
- Python: snake_case, type hints everywhere, async/await
- TypeScript: strict mode, camelCase components, kebab-case files
- API prefix: /api/v1/
- All monetary values: DECIMAL(12,2)
- Dates: ISO 8601 (YYYY-MM-DD)

## Key Design Decisions
- PnL reference: price_open_t1 (NOT price_close_signal_date)
- trading_calendar: seed ALL days (365/year), is_trading=FALSE for weekends/holidays
- signal_type derived from recommendation (BUY_STRONG/BUY→BUY, AVOID/SELL→SELL, HOLD→HOLD)
- score_total validated server-side = sum(4 scores)
- Materialized view uses LATERAL JOIN (not correlated subquery)
- Composite index on price_tracking(signal_id, days_after)
- REFRESH CONCURRENTLY only once after all price updates (not per batch)

## File Structure
```
vnindex-signal/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── signal.py
│   │   ├── price_tracking.py
│   │   └── trading_calendar.py
│   ├── routers/
│   │   ├── health.py
│   │   ├── signals.py
│   │   ├── price_updates.py
│   │   ├── stats.py
│   │   └── export.py
│   ├── schemas/
│   │   ├── signal_input.py
│   │   └── signal_output.py
│   ├── services/
│   │   ├── signal_service.py
│   │   ├── pnl_service.py
│   │   └── calendar_service.py
│   ├── alembic/
│   │   └── versions/
│   ├── scripts/
│   │   └── seed_trading_calendar.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── signals/
│   │   │   ├── page.tsx
│   │   │   └── [date]/
│   │   │       ├── page.tsx
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
├── main-prompt.txt (exists)
├── IMPLEMENTATION_PLAN.md (exists)
├── railway.toml
└── docker-compose.yml
```

## Loop & Loop History
- Version 1: Basic context draft
- Critique: Missing signal_type derivation rule, trading_calendar convention, review feedback items
- Version 2 (final): Added all review feedback fixes from IMPLEMENTATION_PLAN.md §11
