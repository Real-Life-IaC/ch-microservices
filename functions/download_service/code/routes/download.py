from code.db import get_session
from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge, get_eventbridge
from code.models import DownloadCreate, DownloadStatistics
from code.repos.download import DownloadRepo
from typing import Annotated

from aws_lambda_powertools import Logger, Tracer
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Path,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)

router = APIRouter()


@router.get("/download/{token}", status_code=status.HTTP_303_SEE_OTHER)
async def download_book(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    token: Annotated[str, Path(description="Token to download the file")],
) -> RedirectResponse:
    """Exchange a token for a presigned URL to download the book"""

    download_repo = DownloadRepo(session=session, eventbridge=eventbridge)
    download = await download_repo.get(token)

    return RedirectResponse(url=download.presigned_url)


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def request_book(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    body: Annotated[DownloadCreate, Body(description="Download request details")],
) -> None:
    """Request a book copy by giving email and name"""

    download_repo = DownloadRepo(session=session, eventbridge=eventbridge)
    await download_repo.request(new=body)


@router.get("/statistics")
async def download_statistics(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
) -> DownloadStatistics:
    """Get the statistics of number of requested and downloaded ebooks"""

    download_repo = DownloadRepo(session=session, eventbridge=eventbridge)
    return await download_repo.get_statistics()
