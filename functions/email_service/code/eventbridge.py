from code.environment import EVENT_BUS_NAME, LOCALSTACK_ENDPOINT, SERVICE_NAME
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_events import EventBridgeClient


logger = Logger(service=SERVICE_NAME)


class EventBridge:
    """EventBridge client."""

    def __init__(self) -> None:
        """Initialize EventBridge.

        If LOCALSTACK_ENDPOINT is not defined, the client will be initialized with the default endpoint (AWS account).
        """

        self.client = cast(
            EventBridgeClient,
            boto3.client(
                service_name="events",
                endpoint_url=LOCALSTACK_ENDPOINT,
            ),
        )
        logger.info("EventBridge initialized.")

    async def put_event(self, prefix: str, type: str, detail: str, source: str) -> str:
        """Put an event in the EventBridge.

        * prefix and type: used to define the DetailType of the event in the form of "{prefix}.{type}"
        * detail: a JSON string that contains the event data
        * source: the source of the event (optional). If not provided, the source will be "Api", otherwise "Api:{source}"

        Returns
        -------
            str: eventbridge event ID

        """
        detail_type = f"{prefix}.{type}"

        response = self.client.put_events(
            Entries=[
                {
                    "Source": source,
                    "EventBusName": EVENT_BUS_NAME,
                    "DetailType": detail_type,
                    "Detail": detail,
                },
            ],
        )
        event_id = response["Entries"][0]["EventId"]

        logger.info(
            "EventBridge event put",
            event_id=event_id,
            source=source,
            detail_type=detail_type,
        )

        return event_id


async def get_eventbridge() -> AsyncGenerator[EventBridge]:
    """Get EventBridge instance."""
    yield EventBridge()


get_eventbridge_context = asynccontextmanager(get_eventbridge)
