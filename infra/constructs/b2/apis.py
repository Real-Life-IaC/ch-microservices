from typing import Optional

from aws_cdk import aws_ssm as ssm
from constructs import Construct
from infra.constructs.b1.firewall import B1ApiGatewayFirewall
from infra.constructs.b1.lambda_api import B1LambdaApi


class B2Apis(Construct):
    """Real Life IaC Book Static Site"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        hosted_zone_type: Optional[str],
    ) -> None:
        super().__init__(scope, id)

        lambda_api = B1LambdaApi(
            scope=self,
            id="RealLifeIac",
            timeout_seconds=6,
            memory_size=256,
            domain_name="real-life-iac.com",
            hosted_zone_type=hosted_zone_type,
        )

        # Add Resources / Endpoints
        root = lambda_api.rest_api.root
        downloads = root.add_resource("downloads")
        downloads.add_method("POST", api_key_required=False)
        downloads_count = root.add_resource("downloads:count")
        downloads_count.add_method("GET", api_key_required=False)

        docs = root.add_resource("docs")
        docs.add_method("GET", api_key_required=False)
        openapi = root.add_resource("openapi.json")
        openapi.add_method("GET", api_key_required=False)

        stage = ssm.StringParameter.value_from_lookup(
            scope=self,
            parameter_name="/platform/stage",
        )

        if stage == "production":
            # Add a firewall to the API
            firewall = B1ApiGatewayFirewall(
                scope=self,
                id="Firewall",
            )
            firewall.web_acl.associate(
                api=lambda_api.rest_api,
            )
