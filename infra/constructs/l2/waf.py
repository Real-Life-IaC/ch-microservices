from enum import StrEnum
from typing import Optional

import aws_cdk as cdk

from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct


class WebAclAction(StrEnum):
    """Enum to hold Web ACL actions"""

    ALLOW = "allow"
    BLOCK = "block"


class WebAclScope(StrEnum):
    """Enum to hold Web ACL scopes"""

    REGIONAL = "REGIONAL"


class AwsManagedRule(StrEnum):
    """Enum to hold AWS managed rules names"""

    IP_REPUTATION_LIST = "AWSManagedRulesAmazonIpReputationList"
    COMMON_RULE_SET = "AWSManagedRulesCommonRuleSet"
    KNOWN_BAD_INPUTS_RULE_SET = "AWSManagedRulesKnownBadInputsRuleSet"


class WebAclAwsRule(wafv2.CfnWebACL.RuleProperty):
    """Create a Web ACL rule from AWS managed rules"""

    def __init__(
        self,
        name: AwsManagedRule,
        priority: int,
        excluded_rules: Optional[list[str]] = None,
    ) -> None:
        excluded_rules = excluded_rules or []

        super().__init__(
            name=f"AWS-{name}",
            priority=priority,
            override_action=wafv2.CfnWebACL.OverrideActionProperty(
                none={}
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"AWS-{name}",
                sampled_requests_enabled=True,
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    excluded_rules=[
                        {"name": rule_name} for rule_name in excluded_rules
                    ],
                    name=name,
                    vendor_name="AWS",
                )
            ),
        )


class ThrottleStatement(wafv2.CfnWebACL.StatementProperty):
    """Create a Web ACL rule from AWS managed rules"""

    def __init__(
        self,
        rate_limit: int,
    ) -> None:
        super().__init__(
            rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                limit=rate_limit,
                aggregate_key_type="IP",
            ),
        )


class WebAclCustomRule(wafv2.CfnWebACL.RuleProperty):
    """Create a Web ACL rule from AWS managed rules"""

    def __init__(
        self,
        name: str,
        priority: int,
        statement: wafv2.CfnWebACL.StatementProperty,
    ) -> None:
        super().__init__(
            name=f"Custom-{name}",
            priority=priority,
            action=wafv2.CfnWebACL.RuleActionProperty(block={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"Custom-{name}",
                sampled_requests_enabled=True,
            ),
            statement=statement,
        )


class WebAcl(wafv2.CfnWebACL):
    """Create v2 WAF Web ACL"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        metric_name: str,
        web_acl_scope: WebAclScope,
        default_action: WebAclAction = WebAclAction.ALLOW,
        rules: Optional[list[WebAclAwsRule | WebAclCustomRule]] = None,
    ) -> None:
        super().__init__(
            scope_=scope,
            id=id,
            default_action={default_action: {}},
            scope=web_acl_scope,
            visibility_config={
                "sampledRequestsEnabled": True,
                "cloudWatchMetricsEnabled": True,
                "metricName": metric_name,
            },
            rules=rules,
        )

    def associate(self, api: apigateway.LambdaRestApi) -> None:
        """Associate the WebACL to a rest API"""
        wafv2.CfnWebACLAssociation(
            scope=self,
            id="Association",
            resource_arn=f"arn:aws:apigateway:{cdk.Aws.REGION}::/apis/{api.rest_api_id}",
            web_acl_arn=self.web_acl_arn,
        )

    @property
    def web_acl_arn(self) -> str:
        """Return the web acl arn"""
        return self.attr_arn
