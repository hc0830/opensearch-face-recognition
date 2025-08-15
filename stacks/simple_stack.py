import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct
import os


class SimpleFaceRecognitionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 环境配置
        env_name = os.getenv("ENVIRONMENT", "dev")
        project_name = "face-recognition"

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
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
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

        cdk.CfnOutput(
            self,
            "LambdaExecutionRoleArn",
            value=self.lambda_execution_role.role_arn,
            description="Lambda execution role ARN",
        )
