import os


SERVICE_NAME = os.environ.get("SERVICE_NAME", "download-service")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DB_SECRET_NAME = os.environ.get("DB_SECRET_NAME", "/postgres")
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "real-life-iac")
EBOOK_OBJECT_KEY = os.environ.get("EBOOK_OBJECT_KEY", "ebook.pdf")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
TOKEN_EXPIRATION_HOURS = 48
BACKOFF_SECONDS = 90
