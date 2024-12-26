import asyncio
from code.environment import SERVICE_NAME
from code.eventbridge import get_eventbridge
from code.models.email import Email
from code.repos.email import EmailRepo
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)


@tracer.capture_method(capture_response=False)
async def process(parsed_event: EventBridgeEvent) -> None:
    """Process events."""

    eventbridge = await anext(get_eventbridge())
    email_repo = EmailRepo(eventbridge=eventbridge)

    if parsed_event.detail_type == "book.requested":
        await email_repo.send(Email(**parsed_event.detail))
    else:
        logger.warning("Unhandled event type", event_type=parsed_event.detail_type)


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], _context: LambdaContext) -> None:
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
