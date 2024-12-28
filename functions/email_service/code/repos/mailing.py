import datetime as dt
from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge
from code.models import Mailing

from aws_lambda_powertools import Logger, Tracer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


tracer = Tracer(service=SERVICE_NAME)
logger = Logger(service=SERVICE_NAME)


class MailingRepo:
    """Mailing List repository"""

    def __init__(self, session: AsyncSession, eventbridge: EventBridge) -> None:
        self.__session = session
        self.__eventbridge = eventbridge
        self.__event_source = "emailService"
        self.__event_prefix = "mailing"

    @tracer.capture_method(capture_response=False)
    async def create(
        self,
        new: Mailing,
    ) -> Mailing:
        """Create a new Mailing deduplicated by email"""

        stmt = select(Mailing).where(Mailing.email == new.email)
        result = await self.__session.execute(stmt)
        record = result.scalars().one_or_none()

        if record:
            logger.info("Mailing already exists", Mailing=new.model_dump_json())
            return record

        logger.info("Creating new Mailing", Mailing=new.model_dump_json())
        self.__session.add(new)

        await self.__session.commit()
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="created",
            detail=new.model_dump_json(),
        )

        return new

    @tracer.capture_method(capture_response=False)
    async def validate(
        self,
        email: str,
    ) -> Mailing:
        """Validate email address"""

        stmt = select(Mailing).where(Mailing.email == email)
        result = await self.__session.execute(stmt)
        record = result.scalars().one()

        record.is_validated = True
        record.validated_at = dt.datetime.now(tz=dt.UTC)

        await self.__session.commit()
        await self.__session.refresh(record)
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="validated",
            detail=record.model_dump_json(),
        )

        return record

    @tracer.capture_method(capture_response=False)
    async def unsubscribe(
        self,
        email: str,
    ) -> Mailing | None:
        """Unsubscribe from the mailing list"""
        stmt = select(Mailing).where(Mailing.email == email)
        result = await self.__session.execute(stmt)
        record = result.scalars().one_or_none()

        # Fail silently if no records are found
        # To not leak information about the existence of the email
        if not record:
            logger.warning("Mailing not found when unsubscribing", email=email)
            return None

        record.is_subscribed = False
        record.unsubscribed_at = dt.datetime.now(tz=dt.UTC)

        await self.__session.commit()
        await self.__session.refresh(record)
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="unsubscribed",
            detail=record.model_dump_json(),
        )

        return record

    @tracer.capture_method(capture_response=False)
    async def resubscribe(
        self,
        email: str,
    ) -> Mailing | None:
        """Resubscribe to the mailing list"""
        stmt = select(Mailing).where(Mailing.email == email)
        result = await self.__session.execute(stmt)
        record = result.scalars().one_or_none()

        # Fail silently if no records are found
        # To not leak information about the existence of the email
        if not record:
            logger.warning("Mailing not found when resubscribing", email=email)
            return None

        record.is_subscribed = True
        record.unsubscribed_at = None

        await self.__session.commit()
        await self.__session.refresh(record)
        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="resubscribed",
            detail=record.model_dump_json(),
        )

        return record
