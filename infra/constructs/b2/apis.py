from typing import Optional

from constructs import Construct
from infra.constructs.b1.lambda_api import B1LambdaApi
from infra.constructs.b1.sns_topic import B1LambdaSnsTopic


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
        events = ["DownloadCreated"]

        for event in events:
            B1LambdaSnsTopic(
                scope=self,
                id=f"{event}Topic",
                function=lambda_api.function,
                event_name=event,
            )
