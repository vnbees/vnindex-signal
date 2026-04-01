from sqlalchemy import Column, Integer, String, Date, Boolean, Numeric, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database import Base

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("run_date", "portfolio_kind", name="uq_analysis_runs_run_date_portfolio_kind"),
    )
    id = Column(Integer, primary_key=True)
    run_date = Column(Date, nullable=False)
    portfolio_kind = Column(String(20), nullable=False, server_default="top_cap")
    top_n = Column(Integer, nullable=False, default=30)
    hold_days = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    signals = relationship("Signal", back_populates="run", cascade="all, delete-orphan")

class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("run_id", "symbol", name="uq_signals_run_id_symbol"),
    )
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    score_financial = Column(Integer, nullable=False)
    score_seasonal = Column(Integer, nullable=False)
    score_technical = Column(Integer, nullable=False)
    score_cashflow = Column(Integer, nullable=False)
    score_total = Column(Integer, nullable=False)
    recommendation = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    price_close_signal_date = Column(Numeric(12, 2), nullable=False)
    price_open_t1 = Column(Numeric(12, 2), nullable=True)
    market_cap_bil = Column(Numeric(15, 2), nullable=True)
    has_corporate_action = Column(Boolean, default=False)
    detail_financial = Column(JSONB, nullable=True)
    detail_technical = Column(JSONB, nullable=True)
    detail_cashflow = Column(JSONB, nullable=True)
    detail_seasonal = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    run = relationship("AnalysisRun", back_populates="signals")
    price_trackings = relationship("PriceTracking", back_populates="signal", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    key_hash = Column(String(72), nullable=False, unique=True)
    label = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False)
    run_date = Column(Date, nullable=True)
    symbol = Column(String(10), nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
