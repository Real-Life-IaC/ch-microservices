import datetime as dt
import uuid

from pydantic import ConfigDict
from sqlmodel import DateTime, Field, SQLModel


class UuidModel(SQLModel):
    """Base model with created_at and id fields"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    created_at: dt.datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=lambda: dt.datetime.now(dt.UTC),
        index=True,
    )

    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=lambda: uuid.uuid4(),
    )
