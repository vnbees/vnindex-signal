from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    name: Optional[str] = Field(None, max_length=200)
    contact: Optional[str] = Field(None, max_length=200)
    page_url: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message", "name", "contact", "page_url", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("name", "contact", mode="after")
    @classmethod
    def empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v


class FeedbackOut(BaseModel):
    id: int
    message: str
    name: Optional[str]
    contact: Optional[str]
    page_url: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at_utc_z(self, v: datetime) -> str:
        """Luôn trả ISO8601 UTC có hậu tố Z để client parse đúng (tránh naive local)."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        u = v.astimezone(timezone.utc)
        return u.isoformat(timespec="milliseconds").replace("+00:00", "Z")
