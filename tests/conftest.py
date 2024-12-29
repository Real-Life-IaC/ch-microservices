import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session", name="context")
def context_fixture() -> dict[str, Any]:
    """Load the context from the cdk.context.json file."""

    # Load context from cdk.context.json
    cdk_context = Path.cwd() / "cdk.context.json"
    with Path.open(cdk_context) as file:
        cdk_context = json.loads(file.read())

    # Load additional context from cdk.json
    cdk_config = Path.cwd() / "cdk.json"
    with Path.open(cdk_config) as file:
        cdk_config = json.loads(file.read())

    # Merge context and config context
    return {**cdk_context, **cdk_config["context"]}
