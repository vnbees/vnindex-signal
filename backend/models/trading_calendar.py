from sqlalchemy import Column, Date, Boolean, String
from database import Base

class TradingCalendar(Base):
    __tablename__ = "trading_calendar"
    trade_date = Column(Date, primary_key=True)
    is_trading = Column(Boolean, nullable=False, default=True)
    note = Column(String(100))
