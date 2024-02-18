import os

import boto3
import botocore

from aws_lambda_powertools import Logger
from mypy_boto3_dynamodb import DynamoDBServiceResource


logger = Logger()


def initialize_db() -> DynamoDBServiceResource:
    """Initialize DynamoDB."""

    logger.info("Initializing DynamoDB.")
    ddb = boto3.resource(
        service_name="dynamodb",
        endpoint_url=os.getenv("LOCALSTACK_ENDPOINT"),
    )
    if os.getenv("LOCALSTACK_ENDPOINT"):
        try:
            logger.info("Creating table 'downloads' in DynamoDB.")
            ddb.create_table(
                TableName="downloads",
                KeySchema=[
                    {"AttributeName": "order_id", "KeyType": "HASH"},
                    {"AttributeName": "email", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "order_id", "AttributeType": "S"},
                    {"AttributeName": "email", "AttributeType": "S"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 2,
                    "WriteCapacityUnits": 2,
                },
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                logger.info(
                    "Table 'downloads' already exists in DynamoDB."
                )
            else:
                raise

    logger.info("DynamoDB initialized.")

    return ddb
