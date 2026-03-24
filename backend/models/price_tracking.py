from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class PriceTracking(Base):
    __tablename__ = "price_tracking"
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id", ondelete="CASCADE"))
    run_date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    track_date = Column(Date, nullable=False)
    days_after = Column(Integer, nullable=False)
    price_close = Column(Numeric(12, 2), nullable=True)
    pnl_pct = Column(Numeric(8, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    signal = relationship("Signal", back_populates="price_trackings")
    __table_args__ = (UniqueConstraint("signal_id", "track_date", name="uq_price_tracking_signal_date"),)
