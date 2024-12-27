from aws_cdk import (
    aws_ec2 as ec2,
    aws_events as events,
    aws_route53 as route53,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.aurora_db import B1AuroraDB
from infra.constructs.b1.bucket import B1Bucket
from infra.constructs.b1.docker_lambda import B1DockerLambdaFunction
from infra.constructs.b1.firewall import B1ApiGatewayFirewall
from infra.constructs.b1.lambda_api import B1LambdaApi


class B2DownloadService(Construct):
    """Creates the download service API."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        hosted_zone_type: str | None = None,
    ) -> None:
        super().__init__(scope, id)

        service_name = "download"
        subscription_teams = ["platform"]
        ebook_object_key = "real-life-iac-with-aws-cdk.pdf"
        hosted_zone_type = hosted_zone_type or "private"

        stage = ssm.StringParameter.value_from_lookup(
            scope=self,
            parameter_name="/platform/stage",
        )

        vpc = ec2.Vpc.from_lookup(
            scope=self,
            id="Vpc",
            vpc_id=ssm.StringParameter.value_from_lookup(
                scope=self,
                parameter_name="/platform/vpc/id",
            ),
        )

        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            scope=self,
            id="HostedZone",
            hosted_zone_id=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"/platform/dns/{domain_name}/{hosted_zone_type}-hosted-zone/id",
            ),
            zone_name=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"/platform/dns/{domain_name}/{hosted_zone_type}-hosted-zone/name",
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

        security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            description="Security group for the download service",
        )

        aurora_db = B1AuroraDB(
            scope=self,
            id="AuroraDb",
            vpc=vpc,
            security_group=security_group,
            subscription_teams=subscription_teams,
            service_name=service_name,
            database_name="download",
        )

        bucket = B1Bucket(
            scope=self,
            id="Bucket",
            service_name=service_name,
        )

        docker_lambda = B1DockerLambdaFunction(
            scope=self,
            id="Lambda",
            timeout_seconds=30,
            memory_size=256,
            directory="functions/download_service",
            dockerfile="Dockerfile.lambda",
            service_name=service_name,
            subscription_teams=subscription_teams,
            vpc=vpc,
            security_group=security_group,
            environment_vars={
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "DB_SECRET_NAME": aurora_db.credentials.secret_name,
                "BUCKET_NAME": bucket.bucket_name,
                "EBOOK_OBJECT_KEY": ebook_object_key,
                "FRONTEND_URL": f"{hosted_zone.zone_name}",
            },
        )

        aurora_db.cluster.secret.grant_read(docker_lambda.function)
        bucket.grant_read(docker_lambda.function, objects_key_pattern=ebook_object_key)
        event_bus.grant_put_events_to(docker_lambda.function)

        lambda_api = B1LambdaApi(
            scope=self,
            id="Api",
            function=docker_lambda.function,
            service_name=service_name,
            subscription_teams=subscription_teams,
            domain_name=domain_name,
            subdomain_name="api",
            hosted_zone_type=hosted_zone_type,
        )

        if stage == "production":
            firewall = B1ApiGatewayFirewall(
                scope=self,
                id="Firewall",
                service_name=service_name,
            )

            firewall.web_acl.associate(api=lambda_api.api)
