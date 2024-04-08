from typing import Optional

import aws_cdk as cdk

from constructs import Construct
from infra.constructs.b2.apis import B2Apis


class ApiStack(cdk.Stack):
    """Create the api resources"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        hosted_zone_type: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        B2Apis(
            scope=self,
            id="Api",
            hosted_zone_type=hosted_zone_type,
        )

        # Add tags to everything in this stack
        cdk.Tags.of(self).add(key="owner", value="backend")
        cdk.Tags.of(self).add(key="repo", value="ch-api")
        cdk.Tags.of(self).add(key="cost-center", value="engineering")
