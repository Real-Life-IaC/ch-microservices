from aws_cdk import aws_ssm as ssm
from constructs import Construct
from infra.constructs.l2 import waf


class B1ApiGatewayFirewall(Construct):
    """ApiGateway Firewall"""

    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        self.web_acl = waf.WebAcl(
            scope=self,
            id="WebAcl",
            metric_name="cloudfront",
            web_acl_scope=waf.WebAclScope.REGIONAL,
            default_action=waf.WebAclAction.ALLOW,
            rules=[
                waf.WebAclCustomRule(
                    name="Throttle",
                    priority=0,
                    statement=waf.ThrottleStatement(rate_limit=100),
                ),
                waf.WebAclAwsRule(
                    name=waf.AwsManagedRule.IP_REPUTATION_LIST,
                    priority=1,
                ),
                waf.WebAclAwsRule(
                    name=waf.AwsManagedRule.COMMON_RULE_SET,
                    priority=2,
                ),
                waf.WebAclAwsRule(
                    name=waf.AwsManagedRule.KNOWN_BAD_INPUTS_RULE_SET,
                    priority=3,
                ),
            ],
        )

        ssm.StringParameter(
            scope=self,
            id="WebAclArn",
            string_value=self.web_acl.web_acl_arn,
            description="Web Acl Arn for Api Gateway Waf with 100 rate limit",
            parameter_name="/api/firewall/arn",
        )
