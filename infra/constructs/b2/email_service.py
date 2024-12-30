from aws_cdk import aws_ec2 as ec2, aws_events as events, aws_events_targets as targets, aws_iam as iam, aws_ssm as ssm
from constructs import Construct

from infra.constructs.b1.api_gateway import B1ApiGateway
from infra.constructs.b1.aurora_db import B1AuroraDB
from infra.constructs.b1.docker_lambda import B1DockerLambdaFunction


class B2EmailService(Construct):
    """Creates the email service."""

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

        # Lambda function to handle the events
        events_lambda = B1DockerLambdaFunction(
            scope=self,
            id="EventsLambda",
            timeout_seconds=30,
            memory_size=256,
            directory="functions/email_service",
            dockerfile="Dockerfile.lambda",
            cmd=["code.event_handler.handler"],
            service_name=f"{service_name}/events/lambda",
            subscription_teams=subscription_teams,
            vpc=vpc,
            security_group=self.security_group,
            dead_letter_queue_enabled=True,
            environment_vars={
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "DB_SECRET_NAME": aurora_db.credentials.secret_name,
                "CORS_ORIGINS": ",".join(api_gateway.cors_options.allow_origins),
            },
        )

        aurora_db.security_group.add_ingress_rule(peer=self.security_group, connection=ec2.Port.tcp(5432))
        aurora_db.cluster.secret.grant_read(events_lambda.function)
        event_bus.grant_put_events_to(events_lambda.function)

        events_lambda.function.role.add_to_principal_policy(
            statement=iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            ),
        )

        trigger_rule = events.Rule(
            scope=self,
            id="TriggerRule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=events.Match.exact_string("downloadService"),
                detail_type=events.Match.any_of(
                    "book.requested",
                    "book.downloaded",
                ),
            ),
        )

        trigger_rule.add_target(target=targets.LambdaFunction(events_lambda.function))

        # Lambda function to handle the API Gateway requests
        api_lambda = B1DockerLambdaFunction(
            scope=self,
            id="ApiLambda",
            timeout_seconds=30,
            memory_size=256,
            directory="functions/email_service",
            dockerfile="Dockerfile.lambda",
            cmd=["code.api_handler.handler"],
            service_name=f"{service_name}/api/lambda",
            subscription_teams=subscription_teams,
            vpc=vpc,
            security_group=self.security_group,
            environment_vars={
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "DB_SECRET_NAME": aurora_db.credentials.secret_name,
            },
        )

        aurora_db.security_group.add_ingress_rule(peer=self.security_group, connection=ec2.Port.tcp(5432))
        aurora_db.cluster.secret.grant_read(api_lambda.function)
        event_bus.grant_put_events_to(api_lambda.function)

        api_gateway.add_lambda_route(path="email", handler=api_lambda.function)
