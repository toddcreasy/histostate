#!/usr/bin/env python3
import os

import aws_cdk as cdk
from stacks.batch_stack import BatchStack

app = cdk.App()

BatchStack(
    app,
    "HistostateBatchStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
