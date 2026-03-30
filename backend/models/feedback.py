from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message = Column(Text, nullable=False)
    name = Column(String(200), nullable=True)
    contact = Column(String(200), nullable=True)
    page_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
