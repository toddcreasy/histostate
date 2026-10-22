import json

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template
from stacks.batch_stack import BatchStack


@pytest.fixture(scope="module")
def template() -> Template:
    app = cdk.App()
    # Without cached context, the default-VPC lookup returns a placeholder VPC.
    env = cdk.Environment(account="123456789012", region="us-east-1")
    stack = BatchStack(app, "TestBatchStack", env=env)
    return Template.from_stack(stack)


def test_bucket_is_private_and_encrypted(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_bucket_retained_on_delete(template: Template) -> None:
    template.has_resource(
        "AWS::S3::Bucket",
        {"DeletionPolicy": "Retain", "UpdateReplacePolicy": "Retain"},
    )


def test_bucket_enforces_ssl(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Effect": "Deny",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                            }
                        )
                    ]
                )
            }
        },
    )


def test_bucket_lifecycle_rule(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": [
                    Match.object_like(
                        {
                            "Prefix": "work/",
                            "ExpirationInDays": 30,
                            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
                            "Status": "Enabled",
                        }
                    )
                ]
            }
        },
    )


def test_no_nat_gateway(template: Template) -> None:
    template.resource_count_is("AWS::EC2::NatGateway", 0)


def test_uses_existing_vpc(template: Template) -> None:
    template.resource_count_is("AWS::EC2::VPC", 0)
    template.resource_count_is("AWS::EC2::Subnet", 0)


def test_three_compute_environments_min_zero(template: Template) -> None:
    template.resource_count_is("AWS::Batch::ComputeEnvironment", 3)
    template.has_resource_properties(
        "AWS::Batch::ComputeEnvironment",
        {"ComputeResources": Match.object_like({"MinvCpus": 0, "Type": "SPOT"})},
    )
    template.has_resource_properties(
        "AWS::Batch::ComputeEnvironment",
        {"ComputeResources": Match.object_like({"MinvCpus": 0, "Type": "EC2"})},
    )


def test_three_job_queues(template: Template) -> None:
    template.resource_count_is("AWS::Batch::JobQueue", 3)
    for name in ("histostate-gpu-spot", "histostate-gpu-ondemand", "histostate-cpu-spot"):
        template.has_resource_properties("AWS::Batch::JobQueue", {"JobQueueName": name})


def test_launch_templates_install_miniconda(template: Template) -> None:
    launch_templates = template.find_resources("AWS::EC2::LaunchTemplate")
    assert len(launch_templates) == 2
    for launch_template in launch_templates.values():
        user_data_json = json.dumps(launch_template)
        assert "miniconda" in user_data_json
        assert "conda install" in user_data_json
        assert "awscli" in user_data_json


def test_root_volume_is_encrypted_gp3(template: Template) -> None:
    template.has_resource_properties(
        "AWS::EC2::LaunchTemplate",
        {
            "LaunchTemplateData": Match.object_like(
                {
                    "BlockDeviceMappings": [
                        Match.object_like(
                            {
                                "Ebs": Match.object_like(
                                    {"Encrypted": True, "VolumeType": "gp3", "VolumeSize": 100}
                                )
                            }
                        )
                    ]
                }
            )
        },
    )


def test_outputs_present(template: Template) -> None:
    outputs = template.to_json().get("Outputs", {})
    for name in (
        "BucketName",
        "WorkDir",
        "OutDir",
        "SpotQueue",
        "OnDemandQueue",
        "CpuSpotQueue",
        "Region",
    ):
        assert name in outputs


def test_compute_environments_track_latest_launch_template_version(template: Template) -> None:
    envs = template.find_resources("AWS::Batch::ComputeEnvironment")
    assert len(envs) == 3
    for env in envs.values():
        version = env["Properties"]["ComputeResources"]["LaunchTemplate"]["Version"]
        assert version["Fn::GetAtt"][1] == "LatestVersionNumber"


def _instance_types_to_max_vcpus(template: Template) -> dict[tuple[str, ...], list[int]]:
    found: dict[tuple[str, ...], list[int]] = {}
    for env in template.find_resources("AWS::Batch::ComputeEnvironment").values():
        resources = env["Properties"]["ComputeResources"]
        found.setdefault(tuple(sorted(resources["InstanceTypes"])), []).append(
            resources["MaxvCpus"]
        )
    return found


def test_gpu_and_cpu_instance_types(template: Template) -> None:
    found = _instance_types_to_max_vcpus(template)
    assert set(found) == {
        ("g4dn.xlarge", "g5.xlarge"),
        ("c6i.2xlarge", "c7i.2xlarge", "m6i.2xlarge"),
    }


def test_gpu_vcpu_ceiling_matches_gpu_quota(template: Template) -> None:
    found = _instance_types_to_max_vcpus(template)
    assert found[("g4dn.xlarge", "g5.xlarge")] == [8, 8]
    assert found[("c6i.2xlarge", "c7i.2xlarge", "m6i.2xlarge")] == [64]


def test_launch_templates_use_gpu_and_standard_amis(template: Template) -> None:
    parameters = json.dumps(template.to_json().get("Parameters", {}))
    assert "amazon-linux-2023/gpu" in parameters
    assert "amazon-linux-2023/recommended" in parameters
