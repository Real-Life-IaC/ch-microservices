from code.db import get_session
from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge, get_eventbridge
from code.models import DownloadCreate, DownloadResponse, DownloadStatistics
from code.repos.download import DownloadRepo
from code.s3 import S3, get_s3
from typing import Annotated
from uuid import UUID

from aws_lambda_powertools import Logger, Tracer
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)

router = APIRouter(prefix="/download")


# The order of the routes is important
# FastAPI processes routes in the order they are defined, so static paths should come first.
@router.get("/statistics")
async def download_statistics(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    s3: Annotated[S3, Depends(get_s3)],
) -> DownloadStatistics:
    """Get the statistics of number of requested and downloaded ebooks"""

    repo = DownloadRepo(session=session, eventbridge=eventbridge, s3=s3)
    return await repo.get_statistics()


@router.get("/{token}", response_model=DownloadResponse)
async def download_book(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    s3: Annotated[S3, Depends(get_s3)],
    token: Annotated[UUID, Path(description="Token to download the file")],
) -> DownloadResponse:
    """Exchange a token for a presigned URL to download the book"""

    repo = DownloadRepo(session=session, eventbridge=eventbridge, s3=s3)
    download = await repo.get(token)

    return DownloadResponse(url=download.presigned_url)


@router.post("", status_code=status.HTTP_201_CREATED)
async def request_book(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    s3: Annotated[S3, Depends(get_s3)],
    body: Annotated[DownloadCreate, Body(description="Download request details")],
) -> None:
    """Request a book copy by giving email and name"""

    repo = DownloadRepo(session=session, eventbridge=eventbridge, s3=s3)
    await repo.request(new=body)
