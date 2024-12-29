import asyncio
from code.db import get_session_context
from code.environment import SERVICE_NAME
from code.eventbridge import get_eventbridge_context
from code.models import BookRequest, MailingCreate
from code.repos.book_request import BookRequestRepo
from code.repos.mailing import MailingRepo
from code.ses import get_ses_context
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)


@tracer.capture_method(capture_response=False)
async def process(parsed_event: EventBridgeEvent) -> None:
    """Process events."""

    async with get_eventbridge_context() as eventbridge, get_ses_context() as ses, get_session_context() as session:

        book_request_repo = BookRequestRepo(eventbridge=eventbridge, ses=ses)
        mailing_repo = MailingRepo(eventbridge=eventbridge, session=session)

        if parsed_event.detail_type == "book.requested":
            await book_request_repo.send(BookRequest(**parsed_event.detail))
            await mailing_repo.create(new=MailingCreate(**parsed_event.detail))

        elif parsed_event.detail_type == "book.downloaded":
            await mailing_repo.validate(email=parsed_event.detail["email"])

        else:
            msg = "Unhandled event type"
            logger.exception("Unhandled event type", event_type=parsed_event.detail_type)
            raise RuntimeError(msg)


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
def handler(event: dict[str, Any], _context: LambdaContext) -> None:
    """AWS Lambda handler for cloud events."""
    if (
        isinstance(event, dict)
        and event.get("detail-type") == "Scheduled Event"
        and event.get("source") == "aws.events"
        and event.get("detail") == {}
    ):
        logger.info("Keep warm event.")
        return

    parsed_event = EventBridgeEvent(event)

    asyncio.run(process(parsed_event))
