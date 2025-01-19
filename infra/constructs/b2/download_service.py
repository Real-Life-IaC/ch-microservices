import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_events as events,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.api_gateway import B1ApiGateway
from infra.constructs.b1.aurora_db import B1AuroraDB
from infra.constructs.b1.bucket import B1Bucket
from infra.constructs.b1.docker_lambda import B1DockerLambdaFunction


class B2DownloadService(Construct):
    """Creates the download service API."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        subscription_teams: list[str],
        service_name: str,
        api_gateway: B1ApiGateway,
        aurora_db: B1AuroraDB,
    ) -> None:
        super().__init__(scope, id)

        ebook_object_key = "real-life-iac-with-aws-cdk.pdf"

        vpc = ec2.Vpc.from_lookup(
            scope=self,
            id="Vpc",
            vpc_id=ssm.StringParameter.value_from_lookup(
                scope=self,
                parameter_name="/platform/vpc/id",
            ),
        )

        event_bus = events.EventBus.from_event_bus_arn(
            scope=self,
            id="EventBus",
            event_bus_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name="/pubsub/event-bus/arn",
            ),
        )

        self.security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            description="Security group for the download service",
        )

        s3_user = iam.User(scope=self, id="S3User")
        s3_access_key = iam.AccessKey(scope=self, id="S3AccessKey", user=s3_user)
        s3_secret = secretsmanager.Secret(
            scope=self,
            id="S3SecretAccessKeyId",
            secret_object_value={
                "access_key_id": cdk.SecretValue.unsafe_plain_text(s3_access_key.access_key_id),
                "secret_access_key": s3_access_key.secret_access_key,
            },
        )

        bucket = B1Bucket(
            scope=self,
            id="Bucket",
            service_name=f"{service_name}/bucket",
        )

        bucket.grant_read(s3_user, objects_key_pattern=ebook_object_key)

        # Lambda to handle API requests
        api_lambda = B1DockerLambdaFunction(
            scope=self,
            id="ApiLambda",
            timeout_seconds=90,
            memory_size=256,
            directory="functions/download_service",
            dockerfile="Dockerfile.lambda",
            cmd=["code.api_handler.handler"],
            service_name=f"{service_name}/api/lambda",
            subscription_teams=subscription_teams,
            vpc=vpc,
            security_group=self.security_group,
            environment_vars={
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "DB_SECRET_NAME": aurora_db.credentials.secret_name,
                "BUCKET_NAME": bucket.bucket_name,
                "EBOOK_OBJECT_KEY": ebook_object_key,
                "FRONTEND_URL": api_gateway.hosted_zone.zone_name,
                "CORS_ORIGINS": ",".join(api_gateway.cors_options.allow_origins),
                "S3_SECRET_NAME": s3_secret.secret_name,
            },
        )

        aurora_db.security_group.add_ingress_rule(peer=self.security_group, connection=ec2.Port.tcp(5432))

        aurora_db.cluster.secret.grant_read(api_lambda.function)
        event_bus.grant_put_events_to(api_lambda.function)
        s3_secret.grant_read(api_lambda.function)
        api_gateway.add_lambda_route(path="download", handler=api_lambda.function)
