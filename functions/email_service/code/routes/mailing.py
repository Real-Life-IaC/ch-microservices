from code.db import get_session
from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge, get_eventbridge
from code.repos.mailing import MailingRepo
from typing import Annotated

from aws_lambda_powertools import Logger, Tracer
from fastapi import (
    APIRouter,
    Depends,
    Path,
    status,
)
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)

router = APIRouter()


@router.post("/unsubscribe/{email}", status_code=status.HTTP_200_OK)
async def unsubscribe_from_mailing_list(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    email: Annotated[EmailStr, Path(description="Email to unsubscribe from mailing list")],
) -> None:
    """Unsubscribe from the mailing"""

    repo = MailingRepo(session=session, eventbridge=eventbridge)
    await repo.unsubscribe(email=email)


@router.post("/resubscribe/{email}", status_code=status.HTTP_200_OK)
async def resubscribe_to_mailing_list(
    session: Annotated[AsyncSession, Depends(get_session)],
    eventbridge: Annotated[EventBridge, Depends(get_eventbridge)],
    email: Annotated[EmailStr, Path(description="Email to resubscribe to mailing list")],
) -> None:
    """Resubscribe to the mailing"""

    repo = MailingRepo(session=session, eventbridge=eventbridge)
    await repo.resubscribe(email=email)
