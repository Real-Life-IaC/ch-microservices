import aws_cdk as cdk
from aws_cdk import (
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.alarm import B1Alarm


class B1DockerLambdaFunction(Construct):
    """Creates a Lambda function

    The function is created in the provided VPC and security group, inside a private subnet.
    Lambda Insights is enabled for the function only in the production stage.
    The function is automatically triggered every 4 minutes to keep it warm.
    It also creates alarms for the function errors, throttles, duration and concurrent executions.

    Attributes
    ----------
        function (_lambda.DockerImageFunction): The Lambda function


    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        timeout_seconds: int,
        memory_size: int,
        directory: str,
        service_name: str,
        subscription_teams: list[str],
        vpc: ec2.IVpc,
        security_group: ec2.SecurityGroup,
        cmd: list[str],
        environment_vars: dict | None = None,
        log_retention: logs.RetentionDays = logs.RetentionDays.ONE_MONTH,
        dockerfile: str = "Dockerfile",
        build_secrets: dict | None = None,
        build_args: dict | None = None,
        dead_letter_queue_enabled: bool = False,
    ) -> None:
        """Initialize the DockerLambdaFunction construct

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            timeout_seconds (int): Timeout for the function in seconds
            memory_size (int): Memory size for the function
            directory (str): Directory of the Dockerfile
            service_name (str): Name of the service (if you need to separate domains, use /, for example: "service/subservice")
            subscription_teams (list[str]): List of teams to subscribe to the alarms
            vpc (ec2.IVpc): VPC for the function
            security_group (ec2.SecurityGroup): Security group for the function
            environment_vars (dict, optional): Extra environment variables for the function (default: None)
            log_retention (logs.RetentionDays, optional): Log retention for the function (default: logs.RetentionDays.ONE_MONTH)
            dockerfile (str, optional): Dockerfile for the function (default: "Dockerfile")
            cmd (list[str]): Command to run in the Dockerfile
            build_secrets (dict, optional): Extra build secrets for the function (default: None)
            build_args (dict, optional): Extra build args for the function (default: None)
            dead_letter_queue_enabled (bool, optional): Whether to enable the dead letter queue for the function (default: False)

        """
        super().__init__(scope, id)

        environment_vars = environment_vars or {}
        build_secrets = build_secrets or {}
        build_args = build_args or {}

        # Import existing resources
        stage_name = ssm.StringParameter.value_from_lookup(scope=self, parameter_name="/platform/stage")

        kms_key = kms.Key.from_key_arn(
            scope=self,
            id="KmsKey",
            key_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name="/platform/kms/default-key/arn",
            ),
        )

        self.function = _lambda.DockerImageFunction(
            scope=self,
            id="Function",
            description="Lambda Function",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=directory,
                file=dockerfile,
                cmd=cmd,
                platform=ecr_assets.Platform.LINUX_AMD64,
                build_args={
                    **build_args,
                },
                build_secrets={
                    **build_secrets,
                },
            ),
            timeout=cdk.Duration.seconds(amount=timeout_seconds),
            memory_size=memory_size,
            log_retention=log_retention,
            dead_letter_queue_enabled=dead_letter_queue_enabled,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="PrivateSubnet"),
            security_groups=[security_group],
            tracing=_lambda.Tracing.ACTIVE,
            environment_encryption=kms_key,
            environment={
                "SERVICE_NAME": service_name,
                "STAGE": stage_name,
                **environment_vars,
            },
        )

        if stage_name == "production":
            # Add the CloudWatch Lambda Insights policy
            self.function.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLambdaInsightsExecutionRolePolicy"),
            )

        # Trigger lambda every 4 minutes to keep it warm
        event_rule = events.Rule(
            scope=self,
            id="KeepWarmSchedule",
            schedule=events.Schedule.rate(cdk.Duration.minutes(4)),
        )
        event_rule.add_target(targets.LambdaFunction(handler=self.function))

        ssm.StringParameter(
            scope=self,
            id="FunctionArn",
            parameter_name=f"/{service_name}/arn",
            string_value=self.function.function_arn,
        )

        B1Alarm(
            scope=self,
            id="ErrorsAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Internal error",
            metric=self.function.metric_errors(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
            threshold=0,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="ThrottlesAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Lambda is throttled",
            metric=self.function.metric_throttles(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
            threshold=0,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="DurationAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Duration is greater than 80pct of the timeout",
            metric=self.function.metric_duration(period=cdk.Duration.minutes(5), statistic=cw.Stats.AVERAGE),
            threshold=timeout_seconds * 0.8 * 1000,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        cdk.CfnOutput(scope=self, id="FunctionArnOutput", value=self.function.function_arn)
        cdk.CfnOutput(scope=self, id="FunctionNameOutput", value=self.function.function_name)
        cdk.CfnOutput(scope=self, id="FunctionRoleOutput", value=self.function.role.role_arn)
        cdk.Tags.of(self).add(key="service-name", value=service_name)
