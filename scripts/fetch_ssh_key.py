"""Fetch the deployment's EC2 SSH private key from SSM and save it to ~/.ssh.

CDK stores the auto-generated private key for the ``industryiq-cdk-key`` key pair
in SSM Parameter Store. This is the no-AWS-CLI equivalent of the ``aws ssm
get-parameter`` command in DEPLOY.md: it reads your AWS credentials from the
standard chain (environment variables or ``aws configure``), pulls the key,
writes it to ``~/.ssh/industryiq-cdk-key.pem``, and locks the file's permissions
so ``ssh`` will accept it.

Run it in a terminal where your AWS credentials are set::

    pip install boto3            # if boto3 isn't already available
    python scripts/fetch_ssh_key.py
"""

import os
import subprocess
import sys
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
KEY_NAME = "industryiq-cdk-key"


def main() -> None:
    ec2 = boto3.client("ec2", region_name=REGION)
    pairs = ec2.describe_key_pairs(Filters=[{"Name": "key-name", "Values": [KEY_NAME]}]).get(
        "KeyPairs", []
    )
    if not pairs:
        sys.exit(f"No EC2 key pair {KEY_NAME!r} in {REGION}. Is the stack deployed?")
    key_pair_id = pairs[0]["KeyPairId"]

    private_key = boto3.client("ssm", region_name=REGION).get_parameter(
        Name=f"/ec2/keypair/{key_pair_id}", WithDecryption=True
    )["Parameter"]["Value"]

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / f"{KEY_NAME}.pem"
    # ASCII + LF, no BOM: PowerShell's default UTF-16 would corrupt the key.
    key_path.write_text(private_key, encoding="ascii", newline="\n")

    # chmod 600 equivalent so ssh won't refuse the key.
    if os.name == "nt":
        user = os.environ["USERNAME"]
        subprocess.run(["icacls", str(key_path), "/inheritance:r"], check=True)
        subprocess.run(["icacls", str(key_path), "/grant:r", f"{user}:(R)"], check=True)
    else:
        key_path.chmod(0o600)

    print(f"wrote {key_path}")


if __name__ == "__main__":
    main()
