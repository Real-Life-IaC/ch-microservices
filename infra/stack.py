import aws_cdk as cdk
from constructs import Construct

from infra.constructs.b2.download_service import B2DownloadService
from infra.constructs.b2.email_service import B2EmailService


class ApiStack(cdk.Stack):
    """Create the api resources"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        hosted_zone_type: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        B2DownloadService(
            scope=self,
            id="DownloadService",
            domain_name="real-life-iac.com",
            hosted_zone_type=hosted_zone_type,
        )

        B2EmailService(
            scope=self,
            id="EmailService",
        )

        # Add tags to everything in this stack
        cdk.Tags.of(self).add(key="owner", value="backend")
        cdk.Tags.of(self).add(key="repo", value="ch-microservices")
        cdk.Tags.of(self).add(key="cost-center", value="engineering")
