import datetime as dt
import secrets
from code.environment import (
    BUCKET_NAME,
    EBOOK_OBJECT_KEY,
    FRONTEND_URL,
    TOKEN_EXPIRATION_HOURS,
)
from code.models.base import UuidModel
from typing import ClassVar, cast

import boto3
from mypy_boto3_s3 import S3Client
from pydantic import BaseModel
from pydantic.networks import EmailStr
from sqlmodel import DateTime, Field


s3_client = cast(S3Client, boto3.client("s3"))


class Download(UuidModel, table=True):
    """Download model"""

    __tablename__: ClassVar = "downloads"
    __table_args__: ClassVar = {"keep_existing": True, "schema": "download"}

    email: EmailStr = Field(
        title="Email address",
        description="The email of the person who requested the download",
    )

    name: str = Field(
        title="Name",
        description="The name of the person who requested the download",
    )

    token: str = Field(
        title="Token",
        description="The token used to download the file",
        index=True,
        default_factory=lambda: secrets.token_urlsafe(16),
    )

    link: str | None = Field(title="Link", description="The link to download the file with the token", default=None)

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
        default_factory=lambda: generate_presigned_url(),
    )

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if not self.link:
            self.link = f"{FRONTEND_URL}/download/{self.token}"


def generate_presigned_url() -> str:
    """Generate a pre-signed URL to download the file"""
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": EBOOK_OBJECT_KEY,
        },
        ExpiresIn=TOKEN_EXPIRATION_HOURS * 60 * 60 + 10,  # To seconds + 10 seconds
    )


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
