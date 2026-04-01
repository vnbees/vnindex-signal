from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from database import get_db
from models.signal import Signal, AnalysisRun, ApiKey, AuditLog
from schemas.signal_input import SignalBatchInput
from schemas.signal_output import (
    SignalListItem,
    SignalDetail,
    RunListItem,
    AllocationSuggestionResponse,
    AllocationSuggestionItem,
    SymbolStatSummary,
)
from services.signal_service import upsert_signals
from services.auth import verify_api_key

router = APIRouter(tags=["signals"])

@router.post("/api/v1/signals")
async def write_signals(
    payload: SignalBatchInput,
    db: AsyncSession = Depends(get_db),
    api_key_id: int = Depends(verify_api_key)
):
    return await upsert_signals(db, payload, api_key_id)

@router.get("/api/v1/runs")
async def list_runs(
    limit: int = 30,
    offset: int = 0,
    portfolio_kind: str = "top_cap",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.portfolio_kind == portfolio_kind)
        .order_by(AnalysisRun.run_date.desc())
        .limit(limit)
        .offset(offset)
    )
    runs = result.scalars().all()
    items = []
    for run in runs:
        count_result = await db.execute(
            select(func.count()).where(Signal.run_id == run.id)
        )
        count = count_result.scalar_one()
        items.append(RunListItem(
            id=run.id,
            run_date=run.run_date,
            portfolio_kind=run.portfolio_kind,
            top_n=run.top_n,
            hold_days=run.hold_days,
            signal_count=count
        ))
    return items

@router.get("/api/v1/signals/{run_date}")
async def get_signals_for_date(
    run_date: date,
    recommendation: Optional[str] = None,
    symbol: Optional[str] = None,
    sort_by: str = "score_total",
    order: str = "desc",
    portfolio_kind: str = "top_cap",
    db: AsyncSession = Depends(get_db)
):
    allowed_sort_columns = {
        "score_total": Signal.score_total,
        "symbol": Signal.symbol,
        "market_cap_bil": Signal.market_cap_bil,
    }
    sort_col = allowed_sort_columns.get(sort_by, Signal.score_total)
    sort_dir = "DESC" if order.lower() == "desc" else "ASC"

    result = await db.execute(
        select(Signal).join(AnalysisRun).where(
            Signal.run_date == run_date,
            AnalysisRun.portfolio_kind == portfolio_kind,
            *([Signal.recommendation == recommendation] if recommendation else []),
            *([Signal.symbol.ilike(f"%{symbol.strip().upper()}%")] if symbol and symbol.strip() else []),
        ).order_by(
            sort_col.desc() if sort_dir == "DESC" else sort_col.asc()
        )
    )
    signals = result.scalars().all()

    # Get PnL data from materialized view
    pnl_result = await db.execute(
        text(
            "SELECT signal_id, pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct "
            "FROM signal_pnl_summary WHERE run_date = :run_date AND portfolio_kind = :portfolio_kind"
        ),
        {"run_date": run_date, "portfolio_kind": portfolio_kind},
    )
    pnl_map = {row.signal_id: row for row in pnl_result.fetchall()}

    items = []
    for s in signals:
        pnl = pnl_map.get(s.id)
        items.append(SignalListItem(
            id=s.id,
            run_date=s.run_date,
            symbol=s.symbol,
            status=s.status,
            score_financial=s.score_financial,
            score_seasonal=s.score_seasonal,
            score_technical=s.score_technical,
            score_cashflow=s.score_cashflow,
            score_total=s.score_total,
            recommendation=s.recommendation,
            signal_type=s.signal_type,
            price_close_signal_date=s.price_close_signal_date,
            price_open_t1=s.price_open_t1,
            market_cap_bil=s.market_cap_bil,
            has_corporate_action=s.has_corporate_action or False,
            pnl_d3=pnl.pnl_d3 if pnl else None,
            pnl_d10=pnl.pnl_d10 if pnl else None,
            pnl_d20=pnl.pnl_d20 if pnl else None,
            latest_pnl_pct=pnl.latest_pnl_pct if pnl else None,
        ))
    return items


@router.get("/api/v1/search/signals-by-symbol")
async def search_signals_by_symbol(
    symbol: str,
    limit: int = 50,
    portfolio_kind: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    raw_symbol = (symbol or "").strip().upper()
    if not raw_symbol:
        return {"symbol": "", "signals": [], "stats": None}

    symbol_list = [s.strip() for s in raw_symbol.replace(";", ",").split(",") if s.strip()]
    symbol_list = list(dict.fromkeys(symbol_list))
    if not symbol_list:
        return {"symbol": "", "signals": [], "stats": None}

    params = {
        "limit": max(1, min(limit, 200)),
        "symbols_csv": ",".join(symbol_list),
    }
    portfolio_sql = ""
    if portfolio_kind and portfolio_kind.strip():
        portfolio_sql = " AND sps.portfolio_kind = :portfolio_kind "
        params["portfolio_kind"] = portfolio_kind.strip()

    signal_rows = await db.execute(
        text(
            f"""
            SELECT
                s.id, s.run_date, s.symbol, s.status, s.score_financial, s.score_seasonal,
                s.score_technical, s.score_cashflow, s.score_total, s.recommendation,
                s.signal_type, s.price_close_signal_date, s.price_open_t1, s.market_cap_bil,
                s.has_corporate_action, sps.pnl_d3, sps.pnl_d10, sps.pnl_d20, sps.latest_pnl_pct
            FROM signals s
            LEFT JOIN signal_pnl_summary sps ON sps.signal_id = s.id
            WHERE UPPER(s.symbol) = ANY(string_to_array(:symbols_csv, ','))
            {portfolio_sql}
            ORDER BY s.run_date DESC, s.score_total DESC
            LIMIT :limit
            """
        ),
        params,
    )
    signals = [SignalListItem(**dict(row._mapping)) for row in signal_rows.fetchall()]

    stats_rows = await db.execute(
        text(
            f"""
            SELECT
                COUNT(*) AS total_signals,
                SUM(CASE WHEN sps.recommendation = 'BUY_STRONG' THEN 1 ELSE 0 END) AS buy_strong_count,
                SUM(CASE WHEN sps.recommendation = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
                SUM(CASE WHEN sps.recommendation = 'HOLD' THEN 1 ELSE 0 END) AS hold_count,
                ROUND(AVG(sps.pnl_d3), 2) AS avg_pnl_d3,
                ROUND(AVG(sps.pnl_d10), 2) AS avg_pnl_d10,
                ROUND(AVG(sps.pnl_d20), 2) AS avg_pnl_d20,
                ROUND(AVG(sps.latest_pnl_pct), 2) AS avg_latest_pnl,
                ROUND(100.0 * SUM(CASE WHEN sps.pnl_d3 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(sps.pnl_d3), 0), 1) AS winrate_d3,
                ROUND(100.0 * SUM(CASE WHEN sps.pnl_d10 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(sps.pnl_d10), 0), 1) AS winrate_d10,
                ROUND(100.0 * SUM(CASE WHEN sps.pnl_d20 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(sps.pnl_d20), 0), 1) AS winrate_d20
            FROM signal_pnl_summary sps
            WHERE UPPER(sps.symbol) = ANY(string_to_array(:symbols_csv, ','))
            {portfolio_sql}
            """
        ),
        params,
    )
    stat_row = stats_rows.fetchone()
    stats = None
    if stat_row and stat_row.total_signals:
        stats = SymbolStatSummary(symbol=", ".join(symbol_list), **dict(stat_row._mapping))

    return {"symbol": ", ".join(symbol_list), "signals": signals, "stats": stats}


@router.get("/api/v1/allocation/suggest", response_model=AllocationSuggestionResponse)
async def suggest_allocation(
    capital: Decimal,
    run_date: Optional[date] = None,
    portfolio_kind: str = "top_cap",
    lot_size: int = 100,
    max_items: int = 8,
    db: AsyncSession = Depends(get_db),
):
    if capital <= 0:
        raise HTTPException(status_code=400, detail="capital must be > 0")
    if lot_size <= 0:
        raise HTTPException(status_code=400, detail="lot_size must be > 0")

    chosen_date = run_date
    if chosen_date is None:
        latest_date_result = await db.execute(
            select(func.max(AnalysisRun.run_date)).where(AnalysisRun.portfolio_kind == portfolio_kind)
        )
        chosen_date = latest_date_result.scalar_one_or_none()
        if chosen_date is None:
            raise HTTPException(status_code=404, detail="No run data found")

    candidate_result = await db.execute(
        text(
            """
            SELECT
                s.id,
                s.symbol,
                s.recommendation,
                s.price_close_signal_date,
                s.score_total,
                ps.avg_pnl_d10 AS avg_pnl_d10,
                ps.avg_pnl_d3 AS avg_pnl_d3,
                ps.avg_pnl_d20 AS avg_pnl_d20,
                ps.avg_latest_pnl AS avg_latest_pnl,
                ps.winrate_d3 AS winrate_d3,
                ps.winrate_d10 AS winrate_d10,
                ps.winrate_d20 AS winrate_d20,
                ps.samples_d3 AS samples_d3,
                ps.samples_d10 AS samples_d10,
                ps.samples_d20 AS samples_d20
            FROM signals s
            JOIN analysis_runs ar ON ar.id = s.run_id
            LEFT JOIN (
                SELECT
                    symbol,
                    portfolio_kind,
                    COUNT(pnl_d3) AS samples_d3,
                    COUNT(pnl_d10) AS samples_d10,
                    COUNT(pnl_d20) AS samples_d20,
                    ROUND(AVG(pnl_d10), 2) AS avg_pnl_d10,
                    ROUND(AVG(pnl_d3), 2) AS avg_pnl_d3,
                    ROUND(AVG(pnl_d20), 2) AS avg_pnl_d20,
                    ROUND(AVG(latest_pnl_pct), 2) AS avg_latest_pnl,
                    ROUND(100.0 * SUM(CASE WHEN pnl_d3 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d3), 0), 1) AS winrate_d3,
                    ROUND(100.0 * SUM(CASE WHEN pnl_d10 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d10), 0), 1) AS winrate_d10,
                    ROUND(100.0 * SUM(CASE WHEN pnl_d20 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d20), 0), 1) AS winrate_d20
                FROM signal_pnl_summary
                WHERE run_date >= :since_date
                GROUP BY symbol, portfolio_kind
            ) ps ON ps.symbol = s.symbol AND ps.portfolio_kind = ar.portfolio_kind
            WHERE s.run_date = :run_date
              AND ar.portfolio_kind = :portfolio_kind
              AND s.price_close_signal_date > 0
              AND (
                s.recommendation IN ('BUY_STRONG', 'BUY')
                OR (s.recommendation = 'HOLD' AND COALESCE(ps.avg_pnl_d10, ps.avg_pnl_d20, -999) >= 1.0)
              )
            ORDER BY s.score_total DESC
            LIMIT :max_items
            """
        ),
        {
            "run_date": chosen_date,
            "portfolio_kind": portfolio_kind,
            "since_date": chosen_date - timedelta(days=365),
            "max_items": max(1, min(max_items, 20)),
        },
    )
    rows = [dict(r._mapping) for r in candidate_result.fetchall()]
    if not rows:
        return AllocationSuggestionResponse(
            run_date=chosen_date,
            portfolio_kind=portfolio_kind,
            capital=capital,
            total_planned=Decimal("0"),
            cash_left=capital,
            lot_size=lot_size,
            min_required_capital=None,
            min_required_symbol=None,
            min_required_reference_price=None,
            no_result_message="Không tìm thấy mã phù hợp theo điều kiện hiện tại.",
            suggestions=[],
        )

    def clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    def val_or_none(v) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def weighted_avg(values: list[tuple[float | None, float]]) -> float | None:
        numerator = 0.0
        denominator = 0.0
        for v, w in values:
            if v is None:
                continue
            numerator += v * w
            denominator += w
        if denominator == 0:
            return None
        return numerator / denominator

    def signal_factor(rec: str) -> float:
        return {"BUY_STRONG": 1.00, "BUY": 0.97, "HOLD": 0.92}.get(rec, 0.9)

    scored = []
    for row in rows:
        avg_pnl_d3 = val_or_none(row.get("avg_pnl_d3"))
        avg_pnl_d10 = val_or_none(row.get("avg_pnl_d10"))
        avg_pnl_d20 = val_or_none(row.get("avg_pnl_d20"))
        avg_latest = val_or_none(row.get("avg_latest_pnl"))
        winrate_d3 = val_or_none(row.get("winrate_d3"))
        winrate_d10 = val_or_none(row.get("winrate_d10"))
        winrate_d20 = val_or_none(row.get("winrate_d20"))
        samples_d3 = int(row.get("samples_d3") or 0)
        samples_d10 = int(row.get("samples_d10") or 0)
        samples_d20 = int(row.get("samples_d20") or 0)
        total_samples = samples_d3 + samples_d10 + samples_d20

        short_term_pnl = weighted_avg([(avg_pnl_d3, 0.45), (avg_pnl_d10, 0.45), (avg_pnl_d20, 0.10)])
        short_term_winrate = weighted_avg([(winrate_d3, 0.5), (winrate_d10, 0.4), (winrate_d20, 0.1)])

        # Confidence grows with real observed samples; no history => strong penalty.
        confidence = clamp01(total_samples / 30.0)
        pnl_base = short_term_pnl if short_term_pnl is not None else avg_latest
        pnl_score = clamp01(((pnl_base or 0.0) + 5.0) / 15.0) * max(confidence, 0.2)
        winrate_score = clamp01((short_term_winrate or 0.0) / 100.0) * max(confidence, 0.2)
        recency_signal_score = clamp01(float(row["score_total"]) / 100.0)
        base_score = 0.65 * pnl_score + 0.25 * winrate_score + 0.10 * recency_signal_score
        final_score = max(base_score * signal_factor(row["recommendation"]), 0.001)
        scored.append({**row, "final_score": final_score})

    score_sum = sum(item["final_score"] for item in scored)
    remaining = Decimal(capital)
    suggestions: list[AllocationSuggestionItem] = []
    min_lot_capital: Decimal | None = None
    min_lot_symbol: str | None = None
    min_lot_price: Decimal | None = None
    min_lot_item: dict | None = None

    for item in scored:
        # Stored prices are in "nghin VND"; convert to VND for sizing and amount.
        price = (Decimal(item["price_close_signal_date"]) * Decimal("1000")).quantize(Decimal("0.01"))
        if price <= 0:
            continue
        lot_cost = (price * lot_size).quantize(Decimal("0.01"))
        if min_lot_capital is None or lot_cost < min_lot_capital:
            min_lot_capital = lot_cost
            min_lot_symbol = item["symbol"]
            min_lot_price = price
            min_lot_item = item
        allocated = (Decimal(capital) * Decimal(str(item["final_score"] / score_sum))).quantize(Decimal("0.01"))
        qty_raw = int(allocated / price)
        qty_lot = (qty_raw // lot_size) * lot_size
        if qty_lot <= 0:
            continue
        amount_to_buy = (price * qty_lot).quantize(Decimal("0.01"))
        remaining -= amount_to_buy
        avg_pnl_d3 = val_or_none(item.get("avg_pnl_d3"))
        avg_pnl_d10 = val_or_none(item.get("avg_pnl_d10"))
        avg_pnl_d20 = val_or_none(item.get("avg_pnl_d20"))
        winrate_d3 = val_or_none(item.get("winrate_d3"))
        winrate_d10 = val_or_none(item.get("winrate_d10"))
        winrate_d20 = val_or_none(item.get("winrate_d20"))
        rec = item["recommendation"]

        rec_label_map = {
            "BUY_STRONG": "Mua mạnh",
            "BUY": "Mua",
            "HOLD": "Theo dõi",
            "AVOID": "Tránh",
            "SELL": "Bán",
        }
        rec_label = rec_label_map.get(rec, rec)

        reasons: list[str] = [f"Tín hiệu hiện tại: {rec_label}."]

        if (avg_pnl_d3 is not None and avg_pnl_d3 > 0) or (avg_pnl_d10 is not None and avg_pnl_d10 > 0):
            reasons.append(
                f"Hiệu suất ngắn hạn tích cực (T+3: {(avg_pnl_d3 if avg_pnl_d3 is not None else 0):.2f}%, T+10: {(avg_pnl_d10 if avg_pnl_d10 is not None else 0):.2f}%)."
            )
        elif (avg_pnl_d3 is not None and avg_pnl_d10 is not None and avg_pnl_d3 < 0 and avg_pnl_d10 < 0):
            reasons.append(
                f"Hiệu suất ngắn hạn còn yếu (T+3: {avg_pnl_d3:.2f}%, T+10: {avg_pnl_d10:.2f}%), hệ thống hạ tỷ trọng."
            )
        else:
            reasons.append(
                "Dữ liệu ngắn hạn T+3/T+10 còn hạn chế, hệ thống kết hợp tín hiệu hiện tại với bộ lọc rủi ro."
            )

        if (winrate_d3 is not None and winrate_d3 > 0) or (winrate_d10 is not None and winrate_d10 > 0):
            reasons.append(
                f"Winrate ngắn hạn (T+3: {(winrate_d3 if winrate_d3 is not None else 0):.1f}%, T+10: {(winrate_d10 if winrate_d10 is not None else 0):.1f}%)."
            )
        elif winrate_d20 is not None and winrate_d20 > 0:
            reasons.append(f"Winrate T+20 tham khảo khoảng {winrate_d20:.1f}% khi dữ liệu ngắn hạn chưa đủ.")
        else:
            reasons.append("Chưa đủ dữ liệu winrate ngắn hạn đáng tin cậy cho mã này.")

        if avg_pnl_d20 is not None and avg_pnl_d20 > 0:
            reasons.append(f"Tham khảo thêm: T+20 trung bình dương ({avg_pnl_d20:.2f}%).")

        if item["recommendation"] == "HOLD":
            reasons.append("Mã HOLD vẫn được chọn vì điểm hiệu suất lịch sử đủ cao theo ngưỡng hệ thống.")
        suggestions.append(
            AllocationSuggestionItem(
                symbol=item["symbol"],
                recommendation=item["recommendation"],
                reference_price=price,
                final_score=Decimal(str(round(item["final_score"], 6))),
                allocated_amount=allocated,
                quantity=qty_lot,
                amount_to_buy=amount_to_buy,
                reasons=reasons,
            )
        )

    # Guarantee: if capital reaches reported minimum, there is at least one actionable suggestion.
    if not suggestions and min_lot_capital is not None and Decimal(capital) >= min_lot_capital and min_lot_item is not None:
        fallback_rec = min_lot_item["recommendation"]
        fallback_reasons = [
            "Vốn hiện tại phù hợp để mua tối thiểu 1 lô chẵn cho mã này.",
            "Hệ thống ưu tiên gợi ý khả thi khi vốn chưa đủ để phân bổ theo tỷ trọng chuẩn.",
        ]
        if fallback_rec == "HOLD":
            fallback_reasons.append("Mã HOLD vẫn được giữ lại vì hiệu suất lịch sử đạt ngưỡng lọc.")

        suggestions.append(
            AllocationSuggestionItem(
                symbol=min_lot_item["symbol"],
                recommendation=fallback_rec,
                reference_price=min_lot_price,
                final_score=Decimal(str(round(min_lot_item["final_score"], 6))),
                allocated_amount=min_lot_capital,
                quantity=lot_size,
                amount_to_buy=min_lot_capital,
                reasons=fallback_reasons,
            )
        )

    # Reallocate leftover cash by buying additional full lots, prioritizing higher-score symbols.
    # This improves capital utilization after rounding to lot size.
    if suggestions:
        remaining = max(
            Decimal(capital) - sum((s.amount_to_buy for s in suggestions), Decimal("0")),
            Decimal("0.00"),
        )
        symbol_to_idx = {s.symbol: i for i, s in enumerate(suggestions)}
        scored_by_priority = sorted(scored, key=lambda x: x["final_score"], reverse=True)

        while True:
            picked = None
            picked_lot_cost = None
            picked_price = None
            picked_gap = None
            for item in scored_by_priority:
                price = (Decimal(item["price_close_signal_date"]) * Decimal("1000")).quantize(Decimal("0.01"))
                if price <= 0:
                    continue
                lot_cost = (price * lot_size).quantize(Decimal("0.01"))
                if lot_cost <= remaining:
                    gap = (remaining - lot_cost).quantize(Decimal("0.01"))
                    # Best-fit pass: spend as much as possible without crossing capital.
                    # Tie-break by higher score to preserve ranking preference.
                    if (
                        picked is None
                        or picked_gap is None
                        or gap < picked_gap
                        or (gap == picked_gap and float(item["final_score"]) > float(picked["final_score"]))
                    ):
                        picked = item
                        picked_lot_cost = lot_cost
                        picked_price = price
                        picked_gap = gap

            if picked is None or picked_lot_cost is None or picked_price is None:
                break

            existing_idx = symbol_to_idx.get(picked["symbol"])
            if existing_idx is not None:
                current = suggestions[existing_idx]
                current.quantity += lot_size
                current.amount_to_buy = (current.amount_to_buy + picked_lot_cost).quantize(Decimal("0.01"))
                current.allocated_amount = (current.allocated_amount + picked_lot_cost).quantize(Decimal("0.01"))
            else:
                extra_reasons = [
                    "Được bổ sung thêm do còn tiền mặt sau khi làm tròn lô chẵn.",
                    "Ưu tiên theo điểm tổng hợp cao trong các mã còn mua được.",
                ]
                suggestions.append(
                    AllocationSuggestionItem(
                        symbol=picked["symbol"],
                        recommendation=picked["recommendation"],
                        reference_price=picked_price,
                        final_score=Decimal(str(round(picked["final_score"], 6))),
                        allocated_amount=picked_lot_cost,
                        quantity=lot_size,
                        amount_to_buy=picked_lot_cost,
                        reasons=extra_reasons,
                    )
                )
                symbol_to_idx[picked["symbol"]] = len(suggestions) - 1

            remaining = (remaining - picked_lot_cost).quantize(Decimal("0.01"))
            if remaining <= 0:
                remaining = Decimal("0.00")
                break

    total_planned = sum((s.amount_to_buy for s in suggestions), Decimal("0"))
    no_result_message = None
    if not suggestions:
        if min_lot_capital is not None:
            no_result_message = "Không tìm thấy kết quả với số vốn hiện tại. Vui lòng tăng vốn tối thiểu để mua 1 lô chẵn."
        else:
            no_result_message = "Không tìm thấy kết quả phù hợp ở thời điểm hiện tại."
    return AllocationSuggestionResponse(
        run_date=chosen_date,
        portfolio_kind=portfolio_kind,
        capital=capital,
        total_planned=total_planned,
        cash_left=max(Decimal(capital) - total_planned, Decimal("0.00")),
        lot_size=lot_size,
        min_required_capital=min_lot_capital,
        min_required_symbol=min_lot_symbol,
        min_required_reference_price=min_lot_price,
        no_result_message=no_result_message,
        suggestions=suggestions,
    )

@router.get("/api/v1/signals/{run_date}/{symbol}")
async def get_signal_detail(
    run_date: date,
    symbol: str,
    portfolio_kind: str = "top_cap",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Signal).join(AnalysisRun).where(
            Signal.run_date == run_date,
            Signal.symbol == symbol.upper(),
            AnalysisRun.portfolio_kind == portfolio_kind,
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    pnl_result = await db.execute(
        text(
            "SELECT pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct FROM signal_pnl_summary "
            "WHERE signal_id = :signal_id"
        ),
        {"signal_id": signal.id},
    )
    pnl = pnl_result.fetchone()

    return SignalDetail(
        id=signal.id,
        run_date=signal.run_date,
        symbol=signal.symbol,
        status=signal.status,
        score_financial=signal.score_financial,
        score_seasonal=signal.score_seasonal,
        score_technical=signal.score_technical,
        score_cashflow=signal.score_cashflow,
        score_total=signal.score_total,
        recommendation=signal.recommendation,
        signal_type=signal.signal_type,
        price_close_signal_date=signal.price_close_signal_date,
        price_open_t1=signal.price_open_t1,
        market_cap_bil=signal.market_cap_bil,
        has_corporate_action=signal.has_corporate_action or False,
        detail_financial=signal.detail_financial,
        detail_technical=signal.detail_technical,
        detail_cashflow=signal.detail_cashflow,
        detail_seasonal=signal.detail_seasonal,
        pnl_d3=pnl.pnl_d3 if pnl else None,
        pnl_d10=pnl.pnl_d10 if pnl else None,
        pnl_d20=pnl.pnl_d20 if pnl else None,
        latest_pnl_pct=pnl.latest_pnl_pct if pnl else None,
    )
