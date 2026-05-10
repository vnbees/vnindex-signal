from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class NewsfeedComment(Base):
    __tablename__ = "newsfeed_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_entry_id = Column(
        Integer,
        ForeignKey("signal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commenter_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    display_name = Column(String(80), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
