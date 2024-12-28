from code.environment import LOCALSTACK_ENDPOINT, SERVICE_NAME
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_ses import SESClient


logger = Logger(service=SERVICE_NAME)


class Ses:
    """Ses client."""

    def __init__(self) -> None:
        """Initialize EventBridge.

        If LOCALSTACK_ENDPOINT is not defined, the client will be initialized with the default endpoint (AWS account).
        """

        self.client = cast(
            SESClient,
            boto3.client(
                service_name="ses",
                endpoint_url=LOCALSTACK_ENDPOINT,
            ),
        )
        logger.info("Ses initialized.")

    async def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email using SES.

        * email: the recipient email
        * subject: the email subject
        * html_content: the email content in HTML format

        Returns
        -------
            str: the SES message ID

        """
        response = self.client.send_email(
            Source="ebook@real-life-iac.com",
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {
                        "Data": body,
                    },
                },
            },
            ReplyToAddresses=["noreply@real-life-iac.com"],
        )

        return response["MessageId"]


@asynccontextmanager
async def get_ses() -> AsyncGenerator[Ses]:
    """Get Ses instance."""
    yield Ses()
