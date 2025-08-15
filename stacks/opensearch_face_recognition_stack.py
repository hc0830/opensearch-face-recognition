import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_elasticsearch as elasticsearch,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ec2 as ec2,
    RemovalPolicy,
    Duration,
)
from constructs import Construct
import os


class OpenSearchFaceRecognitionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 环境配置
        env_name = os.getenv("ENVIRONMENT", "dev")
        project_name = "face-recognition"

        # 创建VPC
        self.vpc = self._create_vpc(project_name, env_name)

        # 创建OpenSearch域
        self.opensearch_domain = self._create_opensearch_domain(project_name, env_name)

        # 创建DynamoDB表
        self.face_metadata_table = self._create_face_metadata_table(
            project_name, env_name
        )
        self.user_vectors_table = self._create_user_vectors_table(
            project_name, env_name
        )

        # 创建S3存储桶
        self.images_bucket = self._create_images_bucket(project_name, env_name)

        # 创建IAM角色
        self.lambda_execution_role = self._create_lambda_execution_role()

        # 输出重要资源信息
        self._create_outputs()

    def _create_vpc(self, project_name: str, env_name: str) -> ec2.Vpc:
        """创建VPC"""
        return ec2.Vpc(
            self,
            "FaceRecognitionVPC",
            vpc_name=f"{project_name}-vpc-{env_name}",
            max_azs=2,
            cidr="10.0.0.0/16",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

    def _create_opensearch_domain(
        self, project_name: str, env_name: str
    ) -> elasticsearch.Domain:
        """创建OpenSearch域"""

        # 根据环境选择实例类型
        instance_type = (
            "t3.small.elasticsearch" if env_name == "dev" else "r6g.large.elasticsearch"
        )
        instance_count = 1 if env_name == "dev" else 3

        domain = elasticsearch.Domain(
            self,
            "FaceRecognitionDomain",
            version=elasticsearch.ElasticsearchVersion.V7_10,
            domain_name=f"{project_name}-{env_name}",
            capacity=elasticsearch.CapacityConfig(
                data_nodes=instance_count, data_node_instance_type=instance_type
            ),
            ebs=elasticsearch.EbsOptions(
                volume_size=100 if env_name == "dev" else 500,
                volume_type=ec2.EbsDeviceVolumeType.GP3,
            ),
            vpc=self.vpc,
            vpc_subnets=[
                ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    availability_zones=[self.vpc.availability_zones[0]],
                )
            ],
            security_groups=[self._create_opensearch_security_group()],
            node_to_node_encryption=True,
            encryption_at_rest=elasticsearch.EncryptionAtRestOptions(enabled=True),
            enforce_https=True,
            removal_policy=(
                RemovalPolicy.DESTROY if env_name == "dev" else RemovalPolicy.RETAIN
            ),
        )

        # 添加访问策略 - 对于VPC域，不使用IP限制，而是依赖安全组
        domain.add_access_policies(
            iam.PolicyStatement(
                principals=[iam.AnyPrincipal()],
                actions=["es:*"],
                resources=[f"{domain.domain_arn}/*"],
                # 移除IP条件，因为VPC域不支持IP基础的策略
                # VPC域的访问控制通过安全组实现
            )
        )

        return domain

    def _create_opensearch_security_group(self) -> ec2.SecurityGroup:
        """创建OpenSearch安全组"""
        sg = ec2.SecurityGroup(
            self,
            "OpenSearchSecurityGroup",
            vpc=self.vpc,
            description="Security group for OpenSearch domain",
            allow_all_outbound=True,
        )

        # 允许HTTPS访问
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="HTTPS access from VPC",
        )

        return sg

    def _create_face_metadata_table(
        self, project_name: str, env_name: str
    ) -> dynamodb.Table:
        """创建面部元数据表"""
        table = dynamodb.Table(
            self,
            "FaceMetadataTable",
            table_name=f"{project_name}-face-metadata-{env_name}",
            partition_key=dynamodb.Attribute(
                name="face_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="collection_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.DESTROY if env_name == "dev" else RemovalPolicy.RETAIN
            ),
        )

        # 添加GSI用于按用户ID查询
        table.add_global_secondary_index(
            index_name="UserIdIndex",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
        )

        return table

    def _create_user_vectors_table(
        self, project_name: str, env_name: str
    ) -> dynamodb.Table:
        """创建用户向量表"""
        return dynamodb.Table(
            self,
            "UserVectorsTable",
            table_name=f"{project_name}-user-vectors-{env_name}",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.DESTROY if env_name == "dev" else RemovalPolicy.RETAIN
            ),
        )

    def _create_images_bucket(self, project_name: str, env_name: str) -> s3.Bucket:
        """创建图像存储桶"""
        bucket = s3.Bucket(
            self,
            "ImagesBucket",
            bucket_name=f"{project_name}-images-{env_name}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=(
                RemovalPolicy.DESTROY if env_name == "dev" else RemovalPolicy.RETAIN
            ),
        )

        # 添加CORS配置
        bucket.add_cors_rule(
            allowed_methods=[
                s3.HttpMethods.GET,
                s3.HttpMethods.POST,
                s3.HttpMethods.PUT,
            ],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3000,
        )

        return bucket

    def _create_lambda_execution_role(self) -> iam.Role:
        """创建Lambda执行角色"""
        role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            ],
        )

        # 添加OpenSearch访问权限
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "es:ESHttpGet",
                    "es:ESHttpPost",
                    "es:ESHttpPut",
                    "es:ESHttpDelete",
                    "es:ESHttpHead",
                ],
                resources=[f"{self.opensearch_domain.domain_arn}/*"],
            )
        )

        # 添加DynamoDB访问权限
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=[
                    self.face_metadata_table.table_arn,
                    f"{self.face_metadata_table.table_arn}/index/*",
                    self.user_vectors_table.table_arn,
                ],
            )
        )

        # 添加S3访问权限
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources=[f"{self.images_bucket.bucket_arn}/*"],
            )
        )

        # 添加Rekognition访问权限
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "rekognition:DetectFaces",
                    "rekognition:IndexFaces",
                    "rekognition:SearchFaces",
                    "rekognition:SearchFacesByImage",
                    "rekognition:CreateCollection",
                    "rekognition:DeleteCollection",
                    "rekognition:ListCollections",
                    "rekognition:ListFaces",
                ],
                resources=["*"],
            )
        )

        return role

    def _create_outputs(self):
        """创建CloudFormation输出"""
        cdk.CfnOutput(
            self,
            "OpenSearchDomainEndpoint",
            value=self.opensearch_domain.domain_endpoint,
            description="OpenSearch domain endpoint",
        )

        cdk.CfnOutput(
            self,
            "OpenSearchDomainArn",
            value=self.opensearch_domain.domain_arn,
            description="OpenSearch domain ARN",
        )

        cdk.CfnOutput(
            self,
            "FaceMetadataTableName",
            value=self.face_metadata_table.table_name,
            description="Face metadata DynamoDB table name",
        )

        cdk.CfnOutput(
            self,
            "UserVectorsTableName",
            value=self.user_vectors_table.table_name,
            description="User vectors DynamoDB table name",
        )

        cdk.CfnOutput(
            self,
            "ImagesBucketName",
            value=self.images_bucket.bucket_name,
            description="Images S3 bucket name",
        )

        cdk.CfnOutput(self, "VpcId", value=self.vpc.vpc_id, description="VPC ID")
