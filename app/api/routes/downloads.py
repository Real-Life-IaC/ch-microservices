from api.models.downloads import DownloadsDomain
from api.models.downloads import DownloadsModel
from api.models.downloads import InputDownloadsModel
from fastapi import APIRouter


class DownloadsRouter:
    """Downloads router"""

    def __init__(self, downloads_domain: DownloadsDomain) -> None:
        self.__downloads_domain = downloads_domain

    @property
    def router(self) -> APIRouter:
        """Router property"""
        api_router = APIRouter(prefix="/downloads", tags=["downloads"])

        @api_router.get(":count")
        def get_count() -> int:
            """Count of verified request to download. I.e. those with valid order_id."""
            return self.__downloads_domain.get_count()

        @api_router.post("/")
        def create_download(
            downloads_model: InputDownloadsModel,
        ) -> DownloadsModel:
            """Send data to request the download of a pdf version of the book"""
            return self.__downloads_domain.create_download(downloads_model)

        return api_router
