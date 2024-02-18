import json
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_events import EventBridgeClient


TABLE_NAME = os.getenv("TABLE_NAME", "downloads")

tracer = Tracer()
logger = Logger()


class DownloadsRepository:
    """Repository for downloads."""

    def __init__(
        self, db: DynamoDBServiceResource, events: EventBridgeClient
    ) -> None:
        self.__db = db
        self.__events = events

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
        table = self.__db.Table(TABLE_NAME)

        # Check if the download already exists
        logger.info("Checking if download already exists.")
        existing_download = table.get_item(
            Key={"order_id": data["order_id"], "email": data["email"]},
        )

        if existing_download.get("Item"):
            logger.info("Download already exists.")
            return existing_download.get("Item")
        else:
            logger.info("Download does not exist. Creating download.")
            table.put_item(Item=data)

            self.__events.put_events(
                Entries=[
                    {
                        "Source": "restApi",
                        "EventBusName": os.getenv(
                            "EVENT_BUS_NAME", "default"
                        ),
                        "DetailType": "downloadCreated",
                        "Detail": json.dumps(data),
                    }
                ]
            )
            return data
