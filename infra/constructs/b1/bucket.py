import aws_cdk as cdk
from aws_cdk import aws_iam as iam, aws_s3 as s3, aws_ssm as ssm
from constructs import Construct


class B1Bucket(s3.Bucket):
    """Creates custom S3 Bucket with sensible defaults.

    This bucket will have:
        - S3 Managed Encryption
        - Block all public access
        - Versioning enabled
        - Event bridge enabled
        - Object ownership enforced
        - Server access logs enabled

    By default, the bucket will have the following lifecycle rules enabled:
        - Abort incomplete multipart uploads after 2 days
        - Retain 5 noncurrent versions
        - Transition noncurrent versions to IA after 60 days
        - Transition noncurrent versions to Glacier after 180 days
        - Retain 1 noncurrent version after transitioning to Glacier
        - Transition current versions to Intelligent Tiering after 60 days
        - Transition current versions to IA after 180 days
        - Transition current versions to Glacier after 365 days

    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        service_name: str,
        default_metrics: bool = True,
        default_lifecycle_rules: bool = True,
        transfer_acceleration: bool = False,
        auto_delete_objects: bool = False,
        removal_policy: cdk.RemovalPolicy = cdk.RemovalPolicy.RETAIN,
    ) -> None:
        """Initialize the bucket construct.

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            service_name (str): Name of the service
            default_metrics (bool, optional): Enable CloudWatch metrics for all objects (default: True)
            default_lifecycle_rules (bool, optional): Enable default lifecycle rules (default: True)
            transfer_acceleration (bool, optional): Enable transfer acceleration (default: False)
            auto_delete_objects (bool, optional): Auto delete objects before deleting the bucket (default: False). The bucket won't be deleted if it contains objects when `auto_delete_objects=False` and `removal_policy=cdk.RemovalPolicy.DESTROY`.
            removal_policy (cdk.RemovalPolicy, optional): Removal policy for the bucket (default: cdk.RemovalPolicy.RETAIN)

        """

        access_logs_bucket = s3.Bucket.from_bucket_arn(
            scope=scope,
            id="AccessLogsBucket",
            bucket_arn=ssm.StringParameter.value_for_string_parameter(
                scope=scope,
                parameter_name="/platform/access-logs/bucket/arn",
            ),
        )

        super().__init__(
            scope=scope,
            id=id,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            event_bridge_enabled=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix=f"S3Logs/{service_name}/bucket/",
            transfer_acceleration=transfer_acceleration,
            auto_delete_objects=auto_delete_objects,
            removal_policy=removal_policy,
        )

        # Denies HTTP traffic
        self.add_to_resource_policy(
            permission=iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["s3:*"],
                resources=[self.arn_for_objects("*"), self.bucket_arn],
                principals=[iam.AnyPrincipal()],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            ),
        )

        if default_metrics:
            self.add_metric(id="AllObjects")

        if default_lifecycle_rules:
            self.add_lifecycle_rule(
                abort_incomplete_multipart_upload_after=cdk.Duration.days(amount=2),
                noncurrent_versions_to_retain=5,
                noncurrent_version_transitions=[
                    s3.NoncurrentVersionTransition(
                        storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                        transition_after=cdk.Duration.days(amount=60),
                    ),
                    s3.NoncurrentVersionTransition(
                        storage_class=s3.StorageClass.GLACIER,
                        transition_after=cdk.Duration.days(amount=180),
                        noncurrent_versions_to_retain=1,
                    ),
                ],
            )
