import datetime as dt
from code.models.base import UuidModel
from typing import ClassVar

from pydantic import EmailStr
from sqlmodel import DateTime, Field


class Mailing(UuidModel, table=True):
    """Mailing model"""

    __tablename__: ClassVar = "mailings"
    __table_args__: ClassVar = {"keep_existing": True, "schema": "email"}

    email: EmailStr = Field(
        title="Email address",
        description="The email of the person who requested the download",
        index=True,
        unique=True,
    )

    name: str = Field(
        title="Name",
        description="The name of the person who requested the download",
    )

    is_validated: bool = Field(
        title="Is validated",
        description="Flag to indicate if the email address was validated",
        default=False,
    )

    validated_at: dt.datetime | None = Field(
        sa_type=DateTime(timezone=True),
        title="Validated at",
        description="The date and time when the email address was validated",
        default=None,
    )

    is_subscribed: bool = Field(
        title="Subscribed",
        description="Flag to indicate if the user subscribed to the mailing list",
        default=True,
    )

    unsubscribed_at: dt.datetime | None = Field(
        sa_type=DateTime(timezone=True),
        title="Unsubscribed at",
        description="The date and time when the user unsubscribed from the mailing list",
        default=None,
    )
