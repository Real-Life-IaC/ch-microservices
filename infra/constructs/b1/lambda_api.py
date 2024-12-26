import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_cloudwatch as cw,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.alarm import B1Alarm


class B1LambdaApi(Construct):
    """Creates an API Gateway REST API with a Lambda function as the handler

    The API Gateway also contains alarms for client errors, server errors, latency, and integration latency.
    It creates an A record in the provided hosted zone for the subdomain.
    All requests on the root are handled by a proxy resource.

    Attributes
    ----------
        api (apigateway.LambdaRestApi): The API Gateway REST API

    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        function: lambda_.DockerImageFunction | lambda_.Function,
        service_name: str,
        subscription_teams: list[str],
        domain_name: str,
        subdomain_name: str,
        hosted_zone_type: str,
        log_retention: logs.RetentionDays = logs.RetentionDays.ONE_MONTH,
        throttling_rate_limit: int = 20,
        throttling_burst_limit: int = 40,
        cors_origins: list[str] | None = None,
        caching_enabled: bool = False,
        latency_alarm_threshold_ms: int = 1500,
        client_error_alarm_threshold: int = 10,
        server_error_alarm_threshold: int = 10,
    ) -> None:
        """Initialize the LambdaApi construct

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            function (lambda_.DockerImageFunction | lambda_.IFunction): The Lambda function to be used as the handler for the API
            service_name (str): Name of the service
            subscription_teams (list[str]): List of teams to subscribe to the alarms
            domain_name (str): The domain name for the API
            subdomain_name (str): The subdomain name for the API
            hosted_zone_type (str): The type of hosted zone for the domain
            log_retention (logs.RetentionDays, optional): Retention duration for the logs. Defaults to logs.RetentionDays.ONE_MONTH.
            throttling_rate_limit (int, optional): The rate limit for the API. Defaults to 20.
            throttling_burst_limit (int, optional): The burst limit for the API. Defaults to 40.
            cors_origins (list[str], optional): List of CORS origins. Defaults to ["*"].
            caching_enabled (bool, optional): Enable caching for the API. Defaults to False.
            latency_alarm_threshold_ms (int, optional): The threshold for the latency alarm in milliseconds. Defaults to 1500.
            client_error_alarm_threshold (int, optional): The threshold for the client error alarm. Defaults to 10.
            server_error_alarm_threshold (int, optional): The threshold for the server error alarm. Defaults to 10.

        """
        super().__init__(scope, id)

        cors_origins = cors_origins or ["*"]

        stage_name = ssm.StringParameter.value_from_lookup(
            scope=self,
            parameter_name="/platform/stage",
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

        certificate = acm.Certificate.from_certificate_arn(
            scope=self,
            id="Certificate",
            certificate_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"/platform/dns/{domain_name}/{hosted_zone_type}-hosted-zone/certificate/arn",
            ),
        )

        access_logs__log_group = logs.LogGroup(
            scope=self,
            id="AccessLogs",
            retention=log_retention,
        )

        self.api = apigateway.LambdaRestApi(
            scope=self,
            id="Api",
            handler=function,
            domain_name=apigateway.DomainNameOptions(
                domain_name=f"{subdomain_name}.{hosted_zone.zone_name}",
                certificate=certificate,
                endpoint_type=apigateway.EndpointType.REGIONAL,
                security_policy=apigateway.SecurityPolicy.TLS_1_2,
            ),
            proxy=False,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
            cloud_watch_role=True,
            api_key_source_type=apigateway.ApiKeySourceType.HEADER,
            deploy_options=apigateway.StageOptions(
                stage_name=stage_name,
                cache_cluster_enabled=caching_enabled,
                caching_enabled=caching_enabled,
                access_log_destination=apigateway.LogGroupLogDestination(log_group=access_logs__log_group),
                access_log_format=apigateway.AccessLogFormat.clf(),
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True,
                throttling_rate_limit=throttling_rate_limit,
                throttling_burst_limit=throttling_burst_limit,
            ),
        )

        route53.ARecord(
            scope=self,
            id="ARecord",
            zone=hosted_zone,
            record_name=subdomain_name,
            target=route53.RecordTarget.from_alias(
                route53_targets.ApiGateway(self.api),
            ),
        )

        self.api.root.add_resource("openapi.json").add_method("GET", authorization_type=None)
        self.api.root.add_resource("docs").add_method("GET", authorization_type=None)

        # Add a proxy resource to handle all other requests on root
        self.api.root.add_proxy(any_method=True)

        ssm.StringParameter(
            scope=self,
            id="RestApiNameParameter",
            parameter_name=f"/{service_name}/rest-api/name",
            string_value=self.api.rest_api_name,
        )

        ssm.StringParameter(
            scope=self,
            id="RestApiIdParameter",
            parameter_name=f"/{service_name}/rest-api/id",
            string_value=self.api.rest_api_id,
        )

        ssm.StringParameter(
            scope=self,
            id="RestApiRootResourceIdParameter",
            parameter_name=f"/{service_name}/rest-api/root-resource-id",
            string_value=self.api.rest_api_root_resource_id,
        )

        ssm.StringParameter(
            scope=self,
            id="RestApiUrlParameter",
            parameter_name=f"/{service_name}/rest-api/url",
            string_value=f"https://{subdomain_name}.{hosted_zone.zone_name}",
        )

        B1Alarm(
            scope=self,
            id="ClientErrorAlarm",
            subscription_teams=subscription_teams,
            alarm_description="Client error",
            metric=self.api.metric_client_error(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
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
            metric=self.api.metric_server_error(period=cdk.Duration.minutes(5), statistic=cw.Stats.SUM),
            threshold=server_error_alarm_threshold,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="LatencyAlarm",
            subscription_teams=subscription_teams,
            alarm_description=f"Latency is greater than {latency_alarm_threshold_ms}ms",
            metric=self.api.metric_latency(period=cdk.Duration.minutes(10), statistic=cw.Stats.AVERAGE),
            threshold=latency_alarm_threshold_ms,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="IntegrationLatencyAlarm",
            subscription_teams=subscription_teams,
            alarm_description=f"Integration latency is greater than {latency_alarm_threshold_ms * 0.8}ms",
            metric=self.api.metric_integration_latency(period=cdk.Duration.minutes(10), statistic=cw.Stats.AVERAGE),
            threshold=latency_alarm_threshold_ms * 0.8,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        cdk.CfnOutput(scope=self, id="ApiUrlOutput", value=f"https://{subdomain_name}.{hosted_zone.zone_name}")
        cdk.CfnOutput(scope=self, id="ApiIdOutput", value=self.api.rest_api_id)
        cdk.CfnOutput(scope=self, id="ApiNameOutput", value=self.api.rest_api_name)
        cdk.CfnOutput(scope=self, id="ApiRootResourceIdOutput", value=self.api.rest_api_root_resource_id)

        cdk.Tags.of(self).add(key="service-name", value=service_name)
