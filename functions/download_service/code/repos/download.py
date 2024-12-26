import datetime as dt
from code.environment import BACKOFF_SECONDS, SERVICE_NAME
from code.eventbridge import EventBridge
from code.models import Download, DownloadCreate, DownloadStatistics

from aws_lambda_powertools import Logger, Tracer
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select


tracer = Tracer(service=SERVICE_NAME)
logger = Logger(service=SERVICE_NAME)


class DownloadRepo:
    """Download repository"""

    def __init__(self, session: AsyncSession, eventbridge: EventBridge) -> None:
        self.__session = session
        self.__eventbridge = eventbridge
        self.__event_source = "downloadService"
        self.__event_prefix = "book"

    @tracer.capture_method(capture_response=False)
    async def get(self, token: str) -> Download:
        """Get a new book download link"""

        current_timestamp = dt.datetime.now(tz=dt.UTC)
        stmt = select(Download).where(Download.token == token)
        result = await self.__session.execute(stmt)
        record = result.scalars().one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid link.",
            )

        if record.is_downloaded:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Link already used.",
            )

        if current_timestamp > record.expires_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Link expired.",
            )

        record.downloaded_at = current_timestamp
        record.is_downloaded = True

        logger.info("Updating record", record=record.model_dump_json())

        await self.__session.commit()
        await self.__session.refresh(record)
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="completed",
            detail=record.model_dump_json(),
        )

        return record

    @tracer.capture_method(capture_response=False)
    async def request(
        self,
        new: DownloadCreate,
    ) -> Download:
        """Create a new download request"""

        new_record = Download(**new.model_dump())

        stmt = select(Download).where(
            Download.email == new_record.email,
            Download.created_at >= dt.datetime.now(dt.UTC) - dt.timedelta(seconds=BACKOFF_SECONDS),
        )
        result = await self.__session.execute(stmt)
        record = result.scalars().one_or_none()

        if record:
            remaining_time = BACKOFF_SECONDS - (dt.datetime.now(tz=dt.UTC) - record.created_at).seconds
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You have already requested a download link. Please check your email inbox or try again in {remaining_time} seconds.",
            )

        self.__session.add(new_record)

        logger.info("Creating download", download=new_record.model_dump_json())

        await self.__session.commit()
        await self.__session.refresh(new_record)
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="requested",
            detail=new_record.model_dump_json(),
        )

        return new_record

    @tracer.capture_method(capture_response=False)
    async def get_statistics(
        self,
    ) -> DownloadStatistics:
        """Count the number of requested and downloaded books"""
        stmt = select(func.count()).select_from(Download).where(Download.is_downloaded)
        result = await self.__session.execute(stmt)
        downloaded_count = result.scalar_one()

        stmt = select(func.count()).select_from(Download)
        result = await self.__session.execute(stmt)
        requested_count = result.scalar_one()

        return DownloadStatistics(requested=requested_count, downloaded=downloaded_count)
