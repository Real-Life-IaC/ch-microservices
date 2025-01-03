import datetime as dt
from code.environment import (
    FRONTEND_URL,
    TOKEN_EXPIRATION_HOURS,
)
from code.models.base import UuidModel
from typing import ClassVar

from pydantic import BaseModel, EmailStr
from sqlmodel import DateTime, Field


class Download(UuidModel, table=True):
    """Download model"""

    __tablename__: ClassVar = "downloads"
    __table_args__: ClassVar = {"keep_existing": True, "schema": "download"}

    email: EmailStr = Field(
        title="Email address",
        description="The email of the person who requested the download",
        index=True,
    )

    name: str = Field(
        title="Name",
        description="The name of the person who requested the download",
    )

    link: str | None = Field(
        title="Link",
        description="The link to download the file with the token",
        default=None,
    )

    expires_at: dt.datetime = Field(
        title="Expires at",
        sa_type=DateTime(timezone=True),
        description="The date and time until the token is valid",
        default_factory=lambda: dt.datetime.now(dt.UTC) + dt.timedelta(hours=TOKEN_EXPIRATION_HOURS),
    )

    is_downloaded: bool = Field(
        title="Is downloaded",
        description="Flag to indicate if the file was downloaded",
        default=False,
    )

    downloaded_at: dt.datetime | None = Field(
        sa_type=DateTime(timezone=True),
        title="Downloaded at",
        description="The date and time when the file was downloaded",
        default=None,
    )

    presigned_url: str = Field(
        title="Pre-signed URL",
        description="The pre-signed URL to download the file",
    )

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if not self.link:
            self.link = f"https://{FRONTEND_URL}/download/{self.id.hex}"


class DownloadCreate(BaseModel):
    """Pydantic model to create a new download request"""

    name: str
    email: EmailStr


class DownloadStatistics(BaseModel):
    """Pydantic model to count the number of downloads"""

    requested: int
    downloaded: int


class DownloadResponse(BaseModel):
    """Pydantic model to return the presigned URL"""

    url: str
