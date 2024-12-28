import datetime as dt
import uuid

from pydantic import ConfigDict
from sqlmodel import DateTime, Field, SQLModel


class UuidModel(SQLModel):
    """Base model with created_at and id fields"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    created_at: dt.datetime = Field(
        sa_type=DateTime(timezone=True),
        default=None,
        index=True,
        nullable=False,
    )

    updated_at: dt.datetime = Field(
        sa_type=DateTime(timezone=True),
        default=None,
        index=True,
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: dt.datetime.now(dt.UTC)},
    )

    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=lambda: uuid.uuid4(),
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = dt.datetime.now(dt.UTC)
        if self.updated_at is None:
            self.updated_at = self.created_at
