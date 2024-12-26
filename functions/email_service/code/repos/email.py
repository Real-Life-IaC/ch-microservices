from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge
from code.models.email import Email
from typing import cast

import boto3
from aws_lambda_powertools import Logger, Tracer
from mypy_boto3_ses import SESClient


tracer = Tracer(service=SERVICE_NAME)
logger = Logger(service=SERVICE_NAME)

ses_client = cast(SESClient, boto3.client("ses"))


class EmailRepo:
    """Email repository"""

    def __init__(self, eventbridge: EventBridge) -> None:
        self.__eventbridge = eventbridge
        self.__event_source = "emailService"
        self.__event_prefix = "email"

    @tracer.capture_method(capture_response=False)
    async def send(self, email_data: Email) -> None:
        """Generate a token, a pre-signed URL, and send an email to the reader"""

        response = ses_client.send_email(
            Source="ebook@real-life-iac.com",
            Destination={"ToAddresses": [email_data.email]},
            Message={
                "Subject": {"Data": "Real Life IaC - Download Link"},
                "Body": {
                    "Html": {
                        "Data": f"Hi {email_data.name}, here is the download link: {email_data.link}",
                    },
                },
            },
            ReplyToAddresses=["noreply@real-life-iac.com"],
        )

        email_data.message_id = response["MessageId"]

        logger.info("Email sent", message_id=email_data.message_id)

        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="sent",
            detail=email_data.model_dump_json(),
        )
