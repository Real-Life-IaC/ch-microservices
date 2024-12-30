from code.environment import BUCKET_NAME, EBOOK_OBJECT_KEY, LOCALSTACK_ENDPOINT, SERVICE_NAME, TOKEN_EXPIRATION_HOURS
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_s3 import S3Client


logger = Logger(service=SERVICE_NAME)
session = boto3.Session()


class S3:
    """S3 client."""

    def __init__(self) -> None:
        """Initialize S3.

        If LOCALSTACK_ENDPOINT is not defined, the client will be initialized with the default endpoint (AWS account).
        """

        self.client = cast(
            S3Client,
            session.client(
                service_name="s3",
                endpoint_url=LOCALSTACK_ENDPOINT,
            ),
        )
        logger.info("S3 initialized.")

    async def generate_ebook_presigned_url(self) -> str:
        """Generate a pre-signed URL to download the file"""
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": EBOOK_OBJECT_KEY,
            },
            ExpiresIn=TOKEN_EXPIRATION_HOURS * 60 * 60 + 10,  # To seconds + 10 seconds
        )


async def get_s3() -> AsyncGenerator[S3]:
    """Get EventBridge instance."""
    yield S3()


get_s3_context = asynccontextmanager(get_s3)
