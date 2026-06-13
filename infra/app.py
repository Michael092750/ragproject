#!/usr/bin/env python3
"""CDK app entry point for ragproject's infrastructure."""

import aws_cdk as cdk
from ragproject_infra.ragproject_stack import RagprojectStack

app = cdk.App()

# SSH is locked to this IP. Pass at deploy time: cdk deploy -c my_ip=1.2.3.4
my_ip = app.node.try_get_context("my_ip") or "0.0.0.0"

RagprojectStack(
    app,
    "RagprojectStack",
    my_ip=my_ip,
    env=cdk.Environment(account="646167486245", region="us-east-1"),
)

app.synth()
