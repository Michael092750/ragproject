#!/usr/bin/env python3
"""CDK app entry point for IndustryIQ's infrastructure."""

import aws_cdk as cdk
from industryiq_infra.industryiq_stack import IndustryIqStack

app = cdk.App()

# SSH is locked to this IP. Pass at deploy time: cdk deploy -c my_ip=1.2.3.4
my_ip = app.node.try_get_context("my_ip") or "0.0.0.0"

IndustryIqStack(
    app,
    # CloudFormation stack name. NOTE: renamed from "RagprojectStack" — a stack
    # already deployed under the old name will NOT update in place; CDK would
    # create a second, separate stack. Destroy the old one first (cdk destroy)
    # or rename it in CloudFormation before deploying under this name.
    "IndustryIqStack",
    my_ip=my_ip,
    env=cdk.Environment(account="646167486245", region="us-east-1"),
)

app.synth()
