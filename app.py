import aws_cdk as cdk
from constructs_package.constants import AwsAccountId, AwsRegion, AwsStage

from infra.stack import MicroservicesStack


app = cdk.App()


MicroservicesStack(
    scope=app,
    id=f"Microservices-{AwsStage.SANDBOX}",
    env=cdk.Environment(account=AwsAccountId.SANDBOX, region=AwsRegion.US_EAST_1),
)

MicroservicesStack(
    scope=app,
    id=f"Microservices-{AwsStage.STAGING}",
    env=cdk.Environment(account=AwsAccountId.STAGING, region=AwsRegion.US_EAST_1),
)

MicroservicesStack(
    scope=app,
    id=f"Microservices-{AwsStage.PRODUCTION}",
    env=cdk.Environment(account=AwsAccountId.PRODUCTION, region=AwsRegion.US_EAST_1),
    hosted_zone_type="public",
)

app.synth()
