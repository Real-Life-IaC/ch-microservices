import aws_cdk as cdk
from aws_cdk import aws_cloudwatch as cw, aws_cloudwatch_actions as cw_actions, aws_sns as sns, aws_ssm as ssm
from constructs import Construct


class B1Alarm(cw.Alarm):
    """Creates an alarm in AWS and send notifications to the relevant teams SNS topics.

    Attributes
    ----------
        actions (list[cw.IAlarmAction]): List of actions to perform when the alarm is triggered

    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        subscription_teams: list[str],
        alarm_description: str,
        metric: cw.Metric,
        threshold: float,
        evaluation_periods: int = 1,
        datapoints_to_alarm: int = 1,
        comparison_operator: cw.ComparisonOperator = cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        evaluate_low_sample_count_percentile: str | None = None,
        treat_missing_data: cw.TreatMissingData = cw.TreatMissingData.MISSING,
    ) -> None:
        """Initialize the alarm construct.

        Args:
        ----
            scope (cdk.Construct): Parent of this construct
            id (str): Identifier for this construct
            subscription_teams (list[str]): List of teams to subscribe to the alarm
            alarm_description (str): Description of the alarm
            metric (cw.Metric): Metric to monitor
            threshold (int): Threshold value for the alarm
            evaluation_periods (int): Number of periods to evaluate
            datapoints_to_alarm (int, optional): Number of datapoints to alarm (default: evaluation_periods)
            comparison_operator (cw.ComparisonOperator, optional): Comparison operator for the alarm (default: GREATER_THAN_OR_EQUAL_TO_THRESHOLD)
            evaluate_low_sample_count_percentile (str, optional): Evaluate low sample count percentile (default: None)
            treat_missing_data (cw.TreatMissingData, optional): Treat missing data (default: MISSING)

        """

        super().__init__(
            scope=scope,
            id=id,
            alarm_description=alarm_description,
            metric=metric,
            threshold=threshold,
            evaluation_periods=evaluation_periods,
            datapoints_to_alarm=datapoints_to_alarm,
            comparison_operator=comparison_operator,
            evaluate_low_sample_count_percentile=evaluate_low_sample_count_percentile,
            treat_missing_data=treat_missing_data,
        )

        self.actions: list[cw.IAlarmAction] = []

        for team in subscription_teams:
            sns_topic = sns.Topic.from_topic_arn(
                scope=self,
                id=f"{team}AlarmTopic",
                topic_arn=ssm.StringParameter.value_for_string_parameter(
                    scope=scope,
                    parameter_name=f"/platform/alarms/{team}/sns/arn",
                ),
            )

            action = cw_actions.SnsAction(topic=sns_topic)
            self.add_alarm_action(action)
            self.actions.append(action)

        cdk.CfnOutput(scope=self, id="AlarmNameOutput", value=self.alarm_name)
