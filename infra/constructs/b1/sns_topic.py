from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class B1LambdaSnsTopic(Construct):
    """
    SNS Topics and Kinesis Firehose subscription

    - Allow lambda to publish to SNS topic
    - Subscribe to Kinesis Firehose to save events to S3
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        function: _lambda.DockerImageFunction,
        event_name: str,
    ) -> None:
        super().__init__(scope, id)

        # Loads firehose delivery stream ARN
        delivery_stream_arn = (
            ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name="/platform/events/s3-delivery-stream/arn",
            )
        )

        # Load subscription role ARN that allows SNS to publish events to Firehose
        subscription_role_arn = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name="/platform/events/firehose-subscription-role/arn",
        )

        # Creates topic to receive event from lambda
        self.topic = sns.Topic(
            scope=self,
            id="Topic",
            display_name=f"api-{event_name}",
            master_key=kms.Alias.from_alias_name(
                scope=self,
                id="SnsEncryptionKey",
                alias_name="alias/aws/sns",
            ),
        )

        # Allows lambda to publish to topic
        self.topic.grant_publish(function)

        # Adds topic ARN to lambda environment
        function.add_environment(
            key=f"{event_name.upper()}_TOPIC_ARN",
            value=self.topic.topic_arn,
        )

        # Create a Firehose subscription in SNS
        sns.Subscription(
            scope=self,
            id="S3DeliveryStreamSubscription",
            topic=self.topic,  # type:ignore
            endpoint=delivery_stream_arn,
            protocol=sns.SubscriptionProtocol.FIREHOSE,
            subscription_role_arn=subscription_role_arn,
            raw_message_delivery=True,
        )

        # Add topic ARN to SSM
        ssm.StringParameter(
            scope=self,
            id="TopicArn",
            parameter_name=f"/pubsub/{event_name}/topic/arn",
            string_value=self.topic.topic_arn,
        )
