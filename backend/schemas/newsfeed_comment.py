from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsfeedCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commenter_id: UUID
    body: str = Field(..., min_length=1, max_length=2000)

    @field_validator("body", mode="before")
    @classmethod
    def strip_body(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class NewsfeedCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_entry_id: int
    display_name: str
    body: str
    created_at: datetime


class NewsfeedCommentListResponse(BaseModel):
    items: list[NewsfeedCommentOut]


class NewsfeedCommenterIdentityOut(BaseModel):
    display_name: str
