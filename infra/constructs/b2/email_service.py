from aws_cdk import (
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.docker_lambda import B1DockerLambdaFunction


class B2EmailService(Construct):
    """Creates the email service."""

    def __init__(
        self,
        scope: Construct,
        id: str,
    ) -> None:
        super().__init__(scope, id)

        service_name = "email"
        subscription_teams = ["platform"]

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

        security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            description="Security group for the download service",
        )

        docker_lambda = B1DockerLambdaFunction(
            scope=self,
            id="Lambda",
            timeout_seconds=30,
            memory_size=256,
            directory="functions/email_service",
            dockerfile="Dockerfile",
            service_name=service_name,
            subscription_teams=subscription_teams,
            vpc=vpc,
            security_group=security_group,
            environment_vars={
                "EVENT_BUS_NAME": event_bus.event_bus_name,
            },
        )
        event_bus.grant_put_events_to(docker_lambda.function)

        docker_lambda.function.role.add_to_principal_policy(
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
                    "book.completed",
                ),
            ),
        )

        trigger_rule.add_target(target=targets.LambdaFunction(docker_lambda.function))
