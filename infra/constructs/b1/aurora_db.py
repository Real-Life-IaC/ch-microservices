import aws_cdk as cdk
from aws_cdk import (
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_kms as kms,
    aws_logs as logs,
    aws_rds as rds,
    aws_ssm as ssm,
)
from constructs import Construct

from infra.constructs.b1.alarm import B1Alarm


class B1AuroraDB(Construct):
    """Creates an Aurora Serverless database

    The database is placed in the private subnet with a security group that allows access from the VPN.
    It also creates alarms for the database.


    Attributes
    ----------
        database_name (str): Name of the database
        credentials (rds.Credentials): The credentials used to access the database
        bucket (s3.Bucket): The bucket used to migrate data into the database
        cluster (rds.DatabaseCluster): The database cluster

    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        subscription_teams: list[str],
        service_name: str,
        database_name: str,
        port: int = 5432,
        engine_version: rds.AuroraPostgresEngineVersion = rds.AuroraPostgresEngineVersion.VER_16_3,
        backup_retention_days: cdk.Duration = cdk.Duration.days(15),
        log_retention: logs.RetentionDays = logs.RetentionDays.ONE_MONTH,
        monitoring_interval_seconds: int = 60,
        num_reader_instances: int = 0,
        max_capacity: float = 1,
        min_capacity: float = 0,
        iops_alarm_threshold: int = 1500,
    ) -> None:
        """Initialize the AuroraDB construct

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            subscription_teams (list[str]): List of teams to subscribe to the alarm
            service_name (str): Name of the service
            database_name (str): Name of the database
            port (int, optional): Port for the database (default: 5432)
            engine_version (rds.AuroraPostgresEngineVersion, optional): Engine version for the database (default: rds.AuroraPostgresEngineVersion.VER_16_2)
            backup_retention_days (cdk.Duration, optional): Backup retention days for the database (default: cdk.Duration.days(15))
            log_retention (logs.RetentionDays, optional): Log retention for the database (default: logs.RetentionDays.ONE_MONTH)
            monitoring_interval_seconds (int, optional): Monitoring interval for the database (default: 60)
            num_reader_instances (int, optional): Number of reader instances for the database (default: 0)
            max_capacity (float, optional): Maximum capacity for the database (default: 2)
            min_capacity (float, optional): Minimum capacity for the database (default: 0.5)
            iops_alarm_threshold (int, optional): IOPS alarm threshold for the database (default: 1000)

        """
        super().__init__(scope, id)

        self.database_name = database_name

        vpc = ec2.Vpc.from_lookup(
            scope=self,
            id="Vpc",
            vpc_id=ssm.StringParameter.value_from_lookup(
                scope=self,
                parameter_name="/platform/vpc/id",
            ),
        )

        kms_key = kms.Key.from_key_arn(
            scope=self,
            id="KmsKey",
            key_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name="/platform/kms/default-key/arn",
            ),
        )

        # # CIDR block of the VPN
        # vpn_cidr_block = ssm.StringParameter.value_for_string_parameter(
        #     scope=self,
        #     parameter_name="/vpn/transit-gateway/cidr-block",
        # )

        self.security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            description="Security group for the database",
        )

        # # Add ingress rules to the security group
        # self.security_group.add_ingress_rule(
        #     peer=ec2.Peer.ipv4(vpn_cidr_block),
        #     connection=ec2.Port.tcp(port),
        #     description="Allow access to the database from VPN",
        # )

        # Credentials used to access the database
        self.credentials = rds.Credentials.from_generated_secret(  # nosec
            username="postgres",
            secret_name=f"/{service_name}/storage/cluster/credentials",
            exclude_characters="%+~`#$&*()|[]{}:;<>?!'/@\"",
        )

        # Parameter group used on the database
        parameter_group = rds.ParameterGroup(
            scope=self,
            id="ParameterGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=engine_version),
        )

        # Subnet group used on the database
        subnet_group = rds.SubnetGroup(
            scope=self,
            id="SubnetGroup",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="PrivateSubnet"),
            description="Subnet group for the database",
        )

        # The database cluster using AWS Aurora
        self.cluster = rds.DatabaseCluster(
            scope=self,
            id="Database",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=engine_version),
            backup=rds.BackupProps(retention=backup_retention_days),
            cloudwatch_logs_exports=["postgresql"],
            cloudwatch_logs_retention=log_retention,
            credentials=self.credentials,
            default_database_name=self.database_name,
            deletion_protection=False,  # Usually true in real-life
            iam_authentication=True,
            parameter_group=parameter_group,
            port=port,
            monitoring_interval=cdk.Duration.seconds(amount=monitoring_interval_seconds),
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Usually RETAIN in real-life
            serverless_v2_max_capacity=max_capacity,
            serverless_v2_min_capacity=min_capacity,
            security_groups=[self.security_group],
            storage_encrypted=True,
            storage_encryption_key=kms_key,
            storage_type=rds.DBClusterStorageType.AURORA,
            subnet_group=subnet_group,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="PrivateSubnet"),
            readers=[
                rds.ClusterInstance.serverless_v2(
                    id=f"Reader{idx}",
                    allow_major_version_upgrade=False,
                    auto_minor_version_upgrade=True,
                    enable_performance_insights=False,
                    publicly_accessible=False,
                    # It is recommended that at least one reader has `scaleWithWriter` set to true
                    scale_with_writer=idx == 0,
                )
                for idx in range(num_reader_instances)
            ],
            writer=rds.ClusterInstance.serverless_v2(
                id="Writer",
                allow_major_version_upgrade=False,
                auto_minor_version_upgrade=True,
                enable_performance_insights=False,
                publicly_accessible=False,
            ),
        )

        ssm.StringParameter(
            scope=self,
            id="ClusterArnParameter",
            parameter_name=f"/{service_name}/storage/cluster/arn",
            description="API Database Cluster Arn",
            string_value=self.cluster.cluster_arn,
        )

        ssm.StringParameter(
            scope=self,
            id="ClusterEndpointParameter",
            parameter_name=f"/{service_name}/storage/cluster/endpoint",
            description="API Database Cluster Endpoint",
            string_value=self.cluster.cluster_endpoint.hostname,
        )

        ssm.StringParameter(
            scope=self,
            id="ClusterResourceIdentifierParameter",
            parameter_name=f"/{service_name}/storage/cluster/resource-identifier",
            description="API Database Cluster Resource Identifier",
            string_value=self.cluster.cluster_resource_identifier,
        )

        ssm.StringParameter(
            scope=self,
            id="ClusterSecurityGroupIdParameter",
            parameter_name=f"/{service_name}/storage/cluster/security-group/id",
            description="API Database Cluster Security Group Id",
            string_value=self.security_group.security_group_id,
        )

        # Alarm if available memory is below 256mb in 5/15 of 1 minute periods
        B1Alarm(
            scope=self,
            id="AvailableMemoryBelow256mb",
            subscription_teams=subscription_teams,
            alarm_description="Memory available is below 256mb",
            metric=self.cluster.metric_freeable_memory(period=cdk.Duration.minutes(amount=10), statistic=cw.Stats.AVERAGE),
            threshold=256 * 1024 * 1024,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        # Alarm in number of connections is above 100 in a 5 minute period
        B1Alarm(
            scope=self,
            id="ConnectionsAbove100",
            subscription_teams=subscription_teams,
            alarm_description="Number of connections is above 100",
            metric=self.cluster.metric_database_connections(period=cdk.Duration.minutes(amount=10), statistic=cw.Stats.AVERAGE),
            threshold=100,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarm if CPU utilization is above 90% in 10/15 of 1 minute periods
        B1Alarm(
            scope=self,
            id="CPUUtilizationAbove90",
            subscription_teams=subscription_teams,
            alarm_description="CPU utilization is above 90pct",
            metric=self.cluster.metric_cpu_utilization(period=cdk.Duration.minutes(amount=10), statistic=cw.Stats.AVERAGE),
            threshold=90,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarm if the available storage space is below 1GB in a 5 minute period
        B1Alarm(
            scope=self,
            id="FreeStorageSpaceBelow1GB",
            subscription_teams=subscription_teams,
            alarm_description="Available storage space is below 1GB",
            metric=self.cluster.metric_free_local_storage(period=cdk.Duration.minutes(amount=10), statistic=cw.Stats.AVERAGE),
            threshold=1 * 1024 * 1024 * 1024,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        # Alarm if the number of deadlocks is above 0 in a 1 minute period
        B1Alarm(
            scope=self,
            id="DeadlocksAbove0",
            subscription_teams=subscription_teams,
            alarm_description="Deadlocks is above 0",
            metric=self.cluster.metric_deadlocks(period=cdk.Duration.minutes(amount=5), statistic=cw.Stats.SUM),
            threshold=0,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarm if ACU Utilization is greater than 90% in 5/10 of a 3 minute period
        B1Alarm(
            scope=self,
            id="ACUUtilizationAbove90",
            subscription_teams=subscription_teams,
            alarm_description="ACU utilization is above 90pct",
            metric=self.cluster.metric_acu_utilization(period=cdk.Duration.minutes(amount=10), statistic=cw.Stats.AVERAGE),
            threshold=90,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarm if database capacity is greater than 6 in 2/5 a 20 minute period
        B1Alarm(
            scope=self,
            id="DatabaseCapacityAbove6ACUs",
            subscription_teams=subscription_teams,
            alarm_description="The database capacity is above 6 ACUs",
            metric=self.cluster.metric_serverless_database_capacity(
                period=cdk.Duration.minutes(amount=20),
                statistic=cw.Stats.AVERAGE,
            ),
            threshold=6,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="DatabaseIOPSReads",
            subscription_teams=subscription_teams,
            alarm_description="Database IO Reads",
            metric=self.cluster.metric_volume_read_io_ps(period=cdk.Duration.minutes(amount=5), statistic=cw.Stats.AVERAGE),
            threshold=iops_alarm_threshold,
            evaluation_periods=4,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        B1Alarm(
            scope=self,
            id="DatabaseIOPSWrites",
            subscription_teams=subscription_teams,
            alarm_description="Database IO Writes",
            metric=self.cluster.metric_volume_write_io_ps(period=cdk.Duration.minutes(amount=5), statistic=cw.Stats.AVERAGE),
            threshold=iops_alarm_threshold,
            evaluation_periods=4,
            datapoints_to_alarm=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Output the database name, cluster ARN, cluster endpoint, bucket name, and credentials secret name
        cdk.CfnOutput(scope=self, id="DatabaseNameOutput", value=self.database_name)
        cdk.CfnOutput(scope=self, id="ClusterArnOutput", value=self.cluster.cluster_arn)
        cdk.CfnOutput(scope=self, id="ClusterEndpointOutput", value=self.cluster.cluster_endpoint.hostname)
        cdk.Tags.of(self).add(key="service-name", value=service_name)
