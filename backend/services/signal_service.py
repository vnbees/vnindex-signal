from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from models.signal import AnalysisRun, Signal, AuditLog
from services.calendar_service import is_trading_day
from services.pnl_service import derive_signal_type
from schemas.signal_input import SignalInput, SignalBatchInput

async def upsert_signals(db: AsyncSession, payload: SignalBatchInput, api_key_id: int) -> dict:
    run_date = payload.run_date

    # Validate run_date is trading day
    if not await is_trading_day(db, run_date):
        return {"run_id": None, "run_date": str(run_date), "inserted": 0, "updated": 0,
                "errors": [{"symbol": "*", "reason": "run_date is not a trading day"}]}

    # Upsert analysis_run
    run_stmt = pg_insert(AnalysisRun).values(
        run_date=run_date,
        portfolio_kind=payload.portfolio_kind,
        top_n=payload.top_n,
        hold_days=payload.hold_days,
    ).on_conflict_do_update(
        constraint="uq_analysis_runs_run_date_portfolio_kind",
        set_={"top_n": payload.top_n, "hold_days": payload.hold_days},
    ).returning(AnalysisRun.id)
    run_result = await db.execute(run_stmt)
    run_id = run_result.scalar_one()

    inserted = 0
    updated = 0
    errors = []

    for sig in payload.signals:
        try:
            # Validate score_total
            expected_total = sig.score_financial + sig.score_seasonal + sig.score_technical + sig.score_cashflow
            if sig.score_total != expected_total:
                errors.append({"symbol": sig.symbol, "reason": f"score_total mismatch: got {sig.score_total}, expected {expected_total}"})
                continue

            signal_type = derive_signal_type(sig.recommendation)

            # Check if record already exists before upsert to track insert vs update
            existing_result = await db.execute(
                select(Signal.id).where(
                    Signal.run_id == run_id,
                    Signal.symbol == sig.symbol,
                )
            )
            is_new = existing_result.scalar_one_or_none() is None

            stmt = pg_insert(Signal).values(
                run_id=run_id,
                run_date=run_date,
                symbol=sig.symbol,
                status="active",
                score_financial=sig.score_financial,
                score_seasonal=sig.score_seasonal,
                score_technical=sig.score_technical,
                score_cashflow=sig.score_cashflow,
                score_total=sig.score_total,
                recommendation=sig.recommendation,
                signal_type=signal_type,
                price_close_signal_date=sig.price_close_signal_date,
                market_cap_bil=sig.market_cap_bil,
                detail_financial=sig.detail_financial,
                detail_technical=sig.detail_technical,
                detail_cashflow=sig.detail_cashflow,
                detail_seasonal=sig.detail_seasonal,
            ).on_conflict_do_update(
                constraint="uq_signals_run_id_symbol",
                set_={
                    "score_financial": sig.score_financial,
                    "score_seasonal": sig.score_seasonal,
                    "score_technical": sig.score_technical,
                    "score_cashflow": sig.score_cashflow,
                    "score_total": sig.score_total,
                    "recommendation": sig.recommendation,
                    "signal_type": signal_type,
                    "price_close_signal_date": sig.price_close_signal_date,
                    "market_cap_bil": sig.market_cap_bil,
                    "detail_financial": sig.detail_financial,
                    "detail_technical": sig.detail_technical,
                    "detail_cashflow": sig.detail_cashflow,
                    "detail_seasonal": sig.detail_seasonal,
                }
            )
            await db.execute(stmt)
            if is_new:
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            errors.append({"symbol": sig.symbol, "reason": str(e)})

    # Audit log
    await db.execute(
        AuditLog.__table__.insert().values(
            action="signals.write",
            run_date=run_date,
            api_key_id=api_key_id,
            details={
                "inserted": inserted,
                "updated": updated,
                "errors_count": len(errors),
                "portfolio_kind": payload.portfolio_kind,
            },
        )
    )
    await db.commit()
    return {"run_id": run_id, "run_date": str(run_date), "inserted": inserted, "updated": updated, "errors": errors}
