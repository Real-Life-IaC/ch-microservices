import json

import aws_cdk as cdk
from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_certificatemanager as acm,
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.alarm import B1Alarm


class B1ApiGateway(Construct):
    """Creates an API Gateway REST API with a Lambda function as the handler

    The API Gateway also contains alarms for client errors, server errors, latency, and integration latency.
    It creates an A record in the provided hosted zone for the subdomain.
    All requests on the root are handled by a proxy resource.

    Attributes
    ----------
        rest_api (apigateway.RestApi): The API Gateway REST API
        hosted_zone (route53.HostedZone): The hosted zone for the domain

    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        service_name: str,
        subscription_teams: list[str],
        domain_name: str,
        subdomain_name: str,
        throttling_rate_limit: int = 20,
        throttling_burst_limit: int = 40,
        hosted_zone_type: str | None = None,
        cors_origins: list[str] | None = None,
        latency_alarm_threshold_seconds: int = 90,
        client_error_alarm_threshold: int = 10,
        server_error_alarm_threshold: int = 10,
    ) -> None:
        """Initialize the LambdaApi construct

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            service_name (str): Name of the service
            subscription_teams (list[str]): List of teams to subscribe to the alarms
            domain_name (str): The domain name for the API
            subdomain_name (str): The subdomain name for the API
            hosted_zone_type (str): The type of hosted zone for the domain
            log_retention (logs.RetentionDays, optional): Retention duration for the logs. Defaults to logs.RetentionDays.ONE_MONTH.
            throttling_rate_limit (int, optional): The rate limit for the API. Defaults to 20.
            throttling_burst_limit (int, optional): The burst limit for the API. Defaults to 40.
            cors_origins (list[str], optional): List of CORS origins. Defaults to ["*"].
            latency_alarm_threshold_seconds (int, optional): The threshold for the latency alarm in seconds. Defaults to 90.
            client_error_alarm_threshold (int, optional): The threshold for the client error alarm. Defaults to 10.
            server_error_alarm_threshold (int, optional): The threshold for the server error alarm. Defaults to 10.

        """
        super().__init__(scope, id)

        cors_origins = cors_origins or []
        hosted_zone_type = hosted_zone_type or "private"

        stage_name = ssm.StringParameter.value_from_lookup(
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

        self.hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
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

        certificate = acm.Certificate.from_certificate_arn(
            scope=self,
            id="Certificate",
            certificate_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"/platform/dns/{domain_name}/{hosted_zone_type}-hosted-zone/certificate/arn",
            ),
        )

        self.security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            description="Security group for the API Gateway",
        )

        log_group = logs.LogGroup(
            scope=self,
            id="LogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        self.cors_options = apigwv2.CorsPreflightOptions(
            allow_origins=[f"https://{self.hosted_zone.zone_name}", *cors_origins],
            allow_methods=[apigwv2.CorsHttpMethod.ANY],
            allow_headers=["*"],
            allow_credentials=True,
        )

        api_domain_name = apigwv2.DomainName(
            scope=self,
            id="DomainName",
            certificate=certificate,
            domain_name=f"{subdomain_name}.{self.hosted_zone.zone_name}",
            security_policy=apigwv2.SecurityPolicy.TLS_1_2,
        )

        self.http_api = apigwv2.HttpApi(
            scope=self,
            id="HttpApi",
            cors_preflight=self.cors_options,
            default_domain_mapping=apigwv2.DomainMappingOptions(
                domain_name=api_domain_name,
            ),
            description="API Gateway aggregating all microservices",
            disable_execute_api_endpoint=True,
        )

        self.http_api.add_vpc_link(
            vpc=vpc,
            security_groups=[self.security_group],
            subnets=ec2.SubnetSelection(subnet_group_name="PrivateSubnet"),
        )

        stage = self.http_api.add_stage(
            id=stage_name,
            stage_name=stage_name,
            auto_deploy=True,
            throttle=apigwv2.ThrottleSettings(
                burst_limit=throttling_burst_limit,
                rate_limit=throttling_rate_limit,
            ),
        )

        cfn_stage: apigwv2.CfnStage = stage.node.default_child
        cfn_stage.access_log_settings = apigwv2.CfnStage.AccessLogSettingsProperty(
            destination_arn=log_group.log_group_arn,
            format=json.dumps(
                {
                    "requestId": "$context.requestId",
                    "userAgent": "$context.identity.userAgent",
                    "sourceIp": "$context.identity.sourceIp",
                    "requestTime": "$context.requestTime",
                    "requestTimeEpoch": "$context.requestTimeEpoch",
                    "httpMethod": "$context.httpMethod",
                    "path": "$context.path",
                    "status": "$context.status",
                    "protocol": "$context.protocol",
                    "responseLength": "$context.responseLength",
                    "domainName": "$context.domainName",
                },
            ),
        )

        role = iam.Role(
            scope=self,
            id="LogsRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

        log_group.grant_write(role)

        route53.ARecord(
            scope=self,
            id="ARecord",
            zone=self.hosted_zone,
            record_name=subdomain_name,
            target=route53.RecordTarget.from_alias(
                alias_target=route53_targets.ApiGatewayv2DomainProperties(
                    regional_domain_name=api_domain_name.regional_domain_name,
                    regional_hosted_zone_id=api_domain_name.regional_hosted_zone_id,
                ),
            ),
        )

        ssm.StringParameter(
            scope=self,
            id="HttpApiIdParameter",
            parameter_name=f"/{service_name}/http-api/id",
            string_value=self.http_api.api_id,
        )

        ssm.StringParameter(
            scope=self,
            id="HttpApiUrlParameter",
            parameter_name=f"/{service_name}/http-api/url",
            string_value=f"https://{subdomain_name}.{self.hosted_zone.zone_name}",
        )

        B1Alarm(
            scope=self,
            id="ClientErrorAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Client error",
            metric=self.http_api.metric_client_error(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
            threshold=client_error_alarm_threshold,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="ServerErrorAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Server error",
            metric=self.http_api.metric_server_error(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
            threshold=server_error_alarm_threshold,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="LatencyAlarm",
            subscription_teams=subscription_teams,
            alarm_description=f"Latency is greater than {latency_alarm_threshold_seconds}s",
            metric=self.http_api.metric_latency(period=cdk.Duration.minutes(10), statistic=cw.Stats.AVERAGE),
            threshold=latency_alarm_threshold_seconds * 1000,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="IntegrationLatencyAlarm",
            subscription_teams=subscription_teams,
            alarm_description=f"Integration latency is greater than {latency_alarm_threshold_seconds * 0.8}s",
            metric=self.http_api.metric_integration_latency(period=cdk.Duration.minutes(10), statistic=cw.Stats.AVERAGE),
            threshold=latency_alarm_threshold_seconds * 1000 * 0.8,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        cdk.CfnOutput(scope=self, id="ApiUrlOutput", value=f"https://{subdomain_name}.{self.hosted_zone.zone_name}")
        cdk.CfnOutput(scope=self, id="ApiIdOutput", value=self.http_api.api_id)

        cdk.Tags.of(self).add(key="service-name", value=service_name)

    def add_lambda_route(self, path: str, handler: lambda_.IFunction) -> list[apigwv2.HttpRoute]:
        """Add a Lambda function as a route to the API Gateway

        Args:
        ----
            path (str): The path for the route
            handler (lambda_.IFunction): The Lambda function to be called

        Returns:
        -------
            list[apigwv2.HttpRoute]: The routes added to the API Gateway

        """

        routes = []

        routes.extend(
            self.http_api.add_routes(
                path=f"/{path}",
                methods=[apigwv2.HttpMethod.ANY],
                integration=integrations.HttpLambdaIntegration(id=f"{path}", handler=handler),
            ),
        )

        routes.extend(
            self.http_api.add_routes(
                path=f"/{path}/{{proxy+}}",
                methods=[apigwv2.HttpMethod.ANY],
                integration=integrations.HttpLambdaIntegration(id=f"{path}.proxy", handler=handler),
            ),
        )

        return routes
