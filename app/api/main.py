import os

from typing import Any

from api.db import initialize_db
from api.models.downloads import DownloadsDomain
from api.repositories.downloads import DownloadsRepository
from api.routes.downloads import DownloadsRouter
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from fastapi import FastAPI
from mangum import Mangum
from mangum.types import LambdaContext


logger = Logger()
tracer = Tracer()


app = FastAPI(
    title="Real-Life-IaC API",
    description="API of Real-Life IaC application",
    version="0.1.0",
)

db = initialize_db()
downloads_repository = DownloadsRepository(db)
downloads_domain = DownloadsDomain(downloads_repository)
downloads_router = DownloadsRouter(downloads_domain)

app.include_router(downloads_router.router)


mangum_handler = Mangum(app)


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)  # type: ignore
def handler(event: dict, context: LambdaContext) -> Any:
    """Lambda handler"""
    if (
        isinstance(event, dict)
        and event.get("detail-type") == "Scheduled Event"
        and event.get("source") == "aws.events"
        and event.get("detail") == {}
    ):
        logger.info("Keep warm event.")
        return

    return mangum_handler(event, context)
