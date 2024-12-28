import os


SERVICE_NAME = os.environ.get("SERVICE_NAME", "download-service")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DB_SECRET_NAME = os.environ.get("DB_SECRET_NAME", "/postgres")
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
