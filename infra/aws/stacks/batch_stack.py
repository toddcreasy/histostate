"""AWS Batch infrastructure for histostate training runs: GPU queues plus a CPU Spot queue.

Mirrors the `aws` profile in nextflow.config: a job queue + S3 work dir
that Nextflow's awsbatch executor points at, and an instance AMI that carries
the AWS CLI at /home/ec2-user/miniconda/bin/aws (aws.batch.cliPath).
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_batch as batch
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

# One NVIDIA GPU, 4 vCPUs, 16 GB each: T4 (g4dn) and A10G (g5). Exact sizes, not whole
# families, so Batch never picks a multi-GPU instance. Two types give Spot more capacity pools.
GPU_INSTANCE_TYPES = [
    ec2.InstanceType("g4dn.xlarge"),
    ec2.InstanceType("g5.xlarge"),
]

# 8 vCPUs, 16 GB each, for training without a GPU (e.g. while the G instance quota is 0).
CPU_INSTANCE_TYPES = [
    ec2.InstanceType("c6i.2xlarge"),
    ec2.InstanceType("c7i.2xlarge"),
    ec2.InstanceType("m6i.2xlarge"),
]

MINICONDA_INSTALL_DIR = "/home/ec2-user/miniconda"


class BatchStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        max_vcpus = int(self.node.try_get_context("max_vcpus") or 16)
        cpu_max_vcpus = int(self.node.try_get_context("cpu_max_vcpus") or 64)
        root_volume_gb = int(self.node.try_get_context("root_volume_gb") or 100)

        # --- S3: work dir + results ---------------------------------------
        bucket = self._create_bucket()
        work_dir = f"s3://{bucket.bucket_name}/work"
        out_dir = f"s3://{bucket.bucket_name}/results"

        # --- Network: public-subnet-only VPC, no NAT ------------------------
        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
            gateway_endpoints={
                "S3": ec2.GatewayVpcEndpointOptions(
                    service=ec2.GatewayVpcEndpointAwsService.S3,
                )
            },
        )

        security_group = ec2.SecurityGroup(
            self,
            "ComputeSg",
            vpc=vpc,
            description="AWS Batch compute instances: no inbound, egress only",
            allow_all_outbound=True,
        )

        # --- IAM: EC2 instance role -----------------------------------------
        instance_role = iam.Role(
            self,
            "InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonEC2ContainerServiceforEC2Role"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )
        bucket.grant_read_write(instance_role)

        # --- Launch templates: AL2023 ECS-optimized AMI (GPU variant ships the NVIDIA
        # driver) + Miniforge (conda-forge only, avoids Anaconda default-channel
        # licensing) at the miniconda path ----
        # Batch merges its own ECS bootstrap user data with this one, so it
        # must be MIME multipart.
        def launch_template(construct_id: str, hardware: ecs.AmiHardwareType) -> ec2.LaunchTemplate:
            install_commands = ec2.UserData.for_linux()
            install_commands.add_commands(
                "curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/"
                "Miniforge3-Linux-x86_64.sh -o /tmp/miniconda.sh",
                f"bash /tmp/miniconda.sh -b -p {MINICONDA_INSTALL_DIR}",
                f"{MINICONDA_INSTALL_DIR}/bin/conda install -y awscli",
                "rm -f /tmp/miniconda.sh",
                f"chown -R ec2-user:ec2-user {MINICONDA_INSTALL_DIR}",
            )
            user_data = ec2.MultipartUserData()
            user_data.add_user_data_part(
                install_commands, ec2.MultipartBody.SHELL_SCRIPT, make_default=True
            )
            return ec2.LaunchTemplate(
                self,
                construct_id,
                machine_image=ecs.EcsOptimizedImage.amazon_linux2023(hardware),
                block_devices=[
                    ec2.BlockDevice(
                        device_name="/dev/xvda",
                        volume=ec2.BlockDeviceVolume.ebs(
                            root_volume_gb,
                            volume_type=ec2.EbsDeviceVolumeType.GP3,
                            encrypted=True,
                        ),
                    )
                ],
                user_data=user_data,
            )

        gpu_template = launch_template("GpuLaunchTemplate", ecs.AmiHardwareType.GPU)
        cpu_template = launch_template("CpuLaunchTemplate", ecs.AmiHardwareType.STANDARD)

        # --- Batch: GPU SPOT + ON_DEMAND, CPU SPOT compute environments -----
        common_env_props = dict(
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[security_group],
            instance_role=instance_role,
            use_optimal_instance_classes=False,
            minv_cpus=0,
        )
        gpu_env_props = dict(
            launch_template=gpu_template,
            instance_types=GPU_INSTANCE_TYPES,
            maxv_cpus=max_vcpus,
            **common_env_props,
        )

        spot_env = batch.ManagedEc2EcsComputeEnvironment(
            self,
            "SpotComputeEnvironment",
            spot=True,
            allocation_strategy=batch.AllocationStrategy.SPOT_PRICE_CAPACITY_OPTIMIZED,
            **gpu_env_props,
        )

        ondemand_env = batch.ManagedEc2EcsComputeEnvironment(
            self,
            "OnDemandComputeEnvironment",
            spot=False,
            allocation_strategy=batch.AllocationStrategy.BEST_FIT_PROGRESSIVE,
            **gpu_env_props,
        )

        cpu_spot_env = batch.ManagedEc2EcsComputeEnvironment(
            self,
            "CpuSpotComputeEnvironment",
            spot=True,
            allocation_strategy=batch.AllocationStrategy.SPOT_PRICE_CAPACITY_OPTIMIZED,
            launch_template=cpu_template,
            instance_types=CPU_INSTANCE_TYPES,
            maxv_cpus=cpu_max_vcpus,
            **common_env_props,
        )

        # Batch pins the launch template version it saw at creation; track the
        # latest version so template changes (e.g. root volume size) reach new instances.
        for env, template in (
            (spot_env, gpu_template),
            (ondemand_env, gpu_template),
            (cpu_spot_env, cpu_template),
        ):
            env.node.default_child.add_property_override(
                "ComputeResources.LaunchTemplate.Version",
                template.latest_version_number,
            )

        spot_queue = batch.JobQueue(
            self,
            "SpotJobQueue",
            job_queue_name="histostate-gpu-spot",
            compute_environments=[
                batch.OrderedComputeEnvironment(compute_environment=spot_env, order=1)
            ],
        )

        ondemand_queue = batch.JobQueue(
            self,
            "OnDemandJobQueue",
            job_queue_name="histostate-gpu-ondemand",
            compute_environments=[
                batch.OrderedComputeEnvironment(compute_environment=ondemand_env, order=1)
            ],
        )

        cpu_spot_queue = batch.JobQueue(
            self,
            "CpuSpotJobQueue",
            job_queue_name="histostate-cpu-spot",
            compute_environments=[
                batch.OrderedComputeEnvironment(compute_environment=cpu_spot_env, order=1)
            ],
        )

        # --- Outputs ----------------------------------------------------------
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "WorkDir", value=work_dir)
        CfnOutput(self, "OutDir", value=out_dir)
        CfnOutput(self, "SpotQueue", value=spot_queue.job_queue_name)
        CfnOutput(self, "OnDemandQueue", value=ondemand_queue.job_queue_name)
        CfnOutput(self, "CpuSpotQueue", value=cpu_spot_queue.job_queue_name)
        CfnOutput(self, "Region", value=self.region)
        CfnOutput(
            self,
            "EnvSnippet",
            value=(
                f"AWS_REGION={self.region} "
                f"AWS_BATCH_GPU_QUEUE={spot_queue.job_queue_name} "
                f"AWS_BATCH_CPU_QUEUE={cpu_spot_queue.job_queue_name} "
                f"AWS_S3_WORKDIR={work_dir} "
                f"AWS_S3_OUTDIR={out_dir}"
            ),
        )

    def _create_bucket(self) -> s3.Bucket:
        return s3.Bucket(
            self,
            "Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireWork",
                    prefix="work/",
                    expiration=Duration.days(30),
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                )
            ],
        )
