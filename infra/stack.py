import aws_cdk as cdk
from constructs import Construct

from infra.constructs.b1.api_gateway import B1ApiGateway
from infra.constructs.b1.aurora_db import B1AuroraDB
from infra.constructs.b2.download_service import B2DownloadService
from infra.constructs.b2.email_service import B2EmailService


class MicroservicesStack(cdk.Stack):
    """Create the microservices resources"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        hosted_zone_type: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        api_gateway = B1ApiGateway(
            scope=self,
            id="Rest",
            service_name="microservices/api-gateway",
            subscription_teams=["platform"],
            domain_name="real-life-iac.com",
            subdomain_name="api",
            hosted_zone_type=hosted_zone_type,
        )

        aurora_db = B1AuroraDB(
            scope=self,
            id="AuroraDb",
            subscription_teams=["platform"],
            service_name="microservices/aurora-db",
            database_name="postgres",
        )

        B2DownloadService(
            scope=self,
            id="DownloadService",
            subscription_teams=["platform"],
            service_name="microservices/download",
            api_gateway=api_gateway,
            aurora_db=aurora_db,
        )

        B2EmailService(
            scope=self,
            id="EmailService",
            subscription_teams=["platform"],
            service_name="microservices/email",
            api_gateway=api_gateway,
            aurora_db=aurora_db,
        )

        # Add tags to everything in this stack
        cdk.Tags.of(self).add(key="owner", value="backend")
        cdk.Tags.of(self).add(key="repo", value="ch-microservices")
        cdk.Tags.of(self).add(key="cost-center", value="engineering")
