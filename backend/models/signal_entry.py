from sqlalchemy import Column, Integer, String, Text, Date, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class SignalEntry(Base):
    __tablename__ = "signal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=True, index=True)
    reference_date = Column(Date, nullable=True, index=True)
    title = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    data_extracted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
