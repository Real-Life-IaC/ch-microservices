from datetime import date
from datetime import datetime
from typing import Optional
from uuid import uuid4

from api.repositories.downloads import DownloadsRepository
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import HttpUrl


class InputDownloadsModel(BaseModel):
    """Input Downloads model"""

    email: EmailStr = Field(
        title="The email of the user",
        description="The email of the user",
    )
    order_id: str = Field(
        min_length=19,
        max_length=19,
        pattern=r"^\d{3}-\d{7}-\d{7}$",
        title="The order ID",
        description="The order ID",
    )
    purchase_date: date | str = Field(
        title="The purchase date",
        description="The purchase date",
    )


class DownloadsModel(InputDownloadsModel):
    """Downloads model"""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        title="The ID of the download",
        description="The ID of the download",
    )

    created_at: datetime | str = Field(
        default=str(datetime.utcnow()),
        title="The creation date of the download",
        description="The creation date of the download",
    )

    updated_at: datetime | str = Field(
        default=str(datetime.utcnow()),
        title="The update date of the download",
        description="The update date of the download",
    )

    verified: bool = Field(
        default=False,
        title="If the order is valid",
        description="A flag indicating if the order is valid",
    )

    file_url: Optional[HttpUrl] = Field(
        default=None,
        title="The URL of the file for download",
        description="The URL of the file for download",
    )


class DownloadsDomain:
    """Downloads domain model"""

    def __init__(self, repository: DownloadsRepository) -> None:
        self.__repository = repository

    def get_count(self) -> int:
        """Get the count of downloads"""
        return self.__repository.get_count()

    def create_download(self, data: InputDownloadsModel) -> DownloadsModel:
        """Create a download"""
        data_model = DownloadsModel(**data.model_dump())
        self.__repository.create_download(data_model.model_dump())
        return data_model
