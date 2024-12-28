from code.environment import SERVICE_NAME
from code.eventbridge import EventBridge
from code.models import BookRequest
from code.ses import Ses
from pathlib import Path

import jinja2
from aws_lambda_powertools import Logger, Tracer


tracer = Tracer(service=SERVICE_NAME)
logger = Logger(service=SERVICE_NAME)


template = Path(__file__).parent.parent / "email" / "template.html"

email_template = jinja2.Template(template.read_text())


class BookRequestRepo:
    """Email repository"""

    def __init__(self, eventbridge: EventBridge, ses: Ses) -> None:
        self.__eventbridge = eventbridge
        self.__ses = ses
        self.__event_source = "emailService"
        self.__event_prefix = "ebookEmail"

    @tracer.capture_method(capture_response=False)
    async def send(self, book_request: BookRequest) -> None:
        """Generate a token, a pre-signed URL, and send an email to the reader"""

        rendered_email = email_template.render(
            name=book_request.name,
            file_link=book_request.link,
            email=book_request.email,
        )

        message_id = await self.__ses.send_email(
            to=book_request.email,
            subject="Your eBook - Real-Life IaC with AWS CDK",
            body=rendered_email,
        )

        book_request.message_id = message_id

        logger.info("Email sent", message_id=message_id)

        await self.__eventbridge.put_event(
            source=self.__event_source,
            prefix=self.__event_prefix,
            type="sent",
            detail=book_request.model_dump_json(),
        )
