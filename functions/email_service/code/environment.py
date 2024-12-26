import os


SERVICE_NAME = os.environ.get("SERVICE_NAME", "email-service")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT")
