import os

import boto3

from aws_lambda_powertools import Logger
from mypy_boto3_events import EventBridgeClient


logger = Logger()


def initialize_eventbridge() -> EventBridgeClient:
    """Initialize EventBridge."""

    logger.info("Initializing EventBridge.")
    event_client: EventBridgeClient = boto3.client(
        "events",
        endpoint_url=os.getenv("LOCALSTACK_ENDPOINT"),
    )  # type: ignore

    return event_client
