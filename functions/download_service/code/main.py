from code.environment import SERVICE_NAME
from code.routes import router
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from mangum.types import LambdaContext
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)

app = FastAPI(
    title="Download Service - REST API",
    description="""This API provides a set of endpoints for the download service.""",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router)

mangum_handler = Mangum(app)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict:
    """Health check route"""
    return {"status": "healthy"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Any, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""

    message = str(exc.detail)
    return JSONResponse({"message": message}, status_code=exc.status_code)


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
def handler(event: dict, context: LambdaContext) -> Any:
    """Lambda handler"""

    if (
        isinstance(event, dict)
        and event.get("detail-type") == "Scheduled Event"
        and event.get("source") == "aws.events"
        and event.get("detail") == {}
    ):
        logger.info("Keep warm event.")
        return None

    return mangum_handler(event, context)
