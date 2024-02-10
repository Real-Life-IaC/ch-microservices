import os

import boto3
from aws_lambda_powertools import Logger

from mypy_boto3_dynamodb import DynamoDBServiceResource

logger = Logger()


def initialize_db() -> DynamoDBServiceResource:
    """Initialize DynamoDB."""

    if os.getenv("DYNAMO_ENDPOINT"):
        logger.info("Running locally. Initializing DynamoDB locally.")
        ddb = boto3.resource(
            service_name="dynamodb",
            endpoint_url=os.getenv("DYNAMO_ENDPOINT"),
            region_name="local",  # nosec
            aws_access_key_id="local",  # nosec
            aws_secret_access_key="local",  # nosec
        )
    else:
        logger.info("Running on AWS. Initializing DynamoDB on AWS.")
        ddb = boto3.resource(service_name="dynamodb")

    logger.info("DynamoDB initialized.")

    return ddb
