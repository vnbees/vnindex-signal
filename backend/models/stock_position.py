from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, func

from database import Base


class StockPosition(Base):
    __tablename__ = "stock_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    signal_date = Column(Date, nullable=False, index=True)
    valuation_price = Column(Numeric(14, 2), nullable=True)
    buy_price = Column(Numeric(14, 2), nullable=False)
    sell_price = Column(Numeric(14, 2), nullable=True)
    sell_date = Column(Date, nullable=True)
    current_price = Column(Numeric(14, 2), nullable=True)
    price_as_of = Column(Date, nullable=True)
    unrealized_pnl_pct = Column(Numeric(10, 4), nullable=True)
    realized_pnl_pct = Column(Numeric(10, 4), nullable=True)
    pnl_3d_pct = Column(Numeric(10, 4), nullable=True)
    pnl_5d_pct = Column(Numeric(10, 4), nullable=True)
    pnl_10d_pct = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
