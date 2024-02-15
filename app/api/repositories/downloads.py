import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from mypy_boto3_dynamodb import DynamoDBServiceResource


TABLE_NAME = os.getenv("TABLE_NAME", "downloads")

tracer = Tracer()
logger = Logger()


class DownloadsRepository:
    """Repository for downloads."""

    def __init__(self, db: DynamoDBServiceResource) -> None:
        self.__db = db

    @tracer.capture_method(capture_response=False)
    def get_count(self) -> int:
        """Get the count of downloads from the database."""
        logger.info("Getting count of downloads.")
        table = self.__db.Table(TABLE_NAME)
        response = table.scan(
            ScanFilter={
                "verified": {
                    "AttributeValueList": [True],
                    "ComparisonOperator": "EQ",
                }
            }
        )
        count = len(response["Items"])
        return count

    @tracer.capture_method(capture_response=False)
    def create_download(self, data: dict) -> dict:
        """Create a download in the database."""
        logger.info("Creating download.")
        table = self.__db.Table(TABLE_NAME)
        response = table.put_item(Item=data)
        return response
