import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as lambda_python,
    aws_elasticsearch as elasticsearch,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    Duration,
)
from constructs import Construct
import os


class LambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: elasticsearch.Domain,
        face_metadata_table: dynamodb.Table,
        user_vectors_table: dynamodb.Table,
        images_bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.opensearch_domain = opensearch_domain
        self.face_metadata_table = face_metadata_table
        self.user_vectors_table = user_vectors_table
        self.images_bucket = images_bucket

        # 环境配置
        self.env_name = os.getenv("ENVIRONMENT", "dev")

        # 创建Lambda层
        self.dependencies_layer = self._create_dependencies_layer()

        # 创建Lambda函数
        self.index_face_function = self._create_index_face_function()
        self.search_faces_function = self._create_search_faces_function()
        self.delete_face_function = self._create_delete_face_function()
        self.batch_process_function = self._create_batch_process_function()

        # 创建lambda_functions字典供其他stack使用
        self.lambda_functions = {
            "index_face": self.index_face_function,
            "search_faces": self.search_faces_function,
            "delete_face": self.delete_face_function,
            "batch_process": self.batch_process_function,
        }

        # 注意：S3触发器需要在所有stack创建完成后单独设置，以避免循环依赖

    def _create_dependencies_layer(self) -> _lambda.LayerVersion:
        """创建依赖层"""
        return lambda_python.PythonLayerVersion(
            self,
            "DependenciesLayer",
            entry="layers/dependencies",
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            description="Dependencies for face recognition functions",
        )

    def _create_index_face_function(self) -> _lambda.Function:
        """创建面部索引函数"""
        function = lambda_python.PythonFunction(
            self,
            "IndexFaceFunction",
            entry="lambda_functions/index_face",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler",
            timeout=Duration.minutes(5),
            memory_size=1024,
            layers=[self.dependencies_layer],
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "FACE_METADATA_TABLE": self.face_metadata_table.table_name,
                "USER_VECTORS_TABLE": self.user_vectors_table.table_name,
                "IMAGES_BUCKET": self.images_bucket.bucket_name,
                "ENVIRONMENT": self.environment,
            },
            tracing=_lambda.Tracing.ACTIVE,
            reserved_concurrent_executions=50 if self.env_name != "dev" else 10,
        )

        # 授予权限
        self._grant_permissions(function)

        return function

    def _create_search_faces_function(self) -> _lambda.Function:
        """创建面部搜索函数"""
        function = lambda_python.PythonFunction(
            self,
            "SearchFacesFunction",
            entry="lambda_functions/search_faces",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler",
            timeout=Duration.minutes(2),
            memory_size=512,
            layers=[self.dependencies_layer],
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "FACE_METADATA_TABLE": self.face_metadata_table.table_name,
                "USER_VECTORS_TABLE": self.user_vectors_table.table_name,
                "ENVIRONMENT": self.environment,
            },
            tracing=_lambda.Tracing.ACTIVE,
            reserved_concurrent_executions=100 if self.env_name != "dev" else 20,
        )

        # 授予权限
        self._grant_permissions(function)

        return function

    def _create_delete_face_function(self) -> _lambda.Function:
        """创建面部删除函数"""
        function = lambda_python.PythonFunction(
            self,
            "DeleteFaceFunction",
            entry="lambda_functions/delete_face",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler",
            timeout=Duration.minutes(1),
            memory_size=256,
            layers=[self.dependencies_layer],
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "FACE_METADATA_TABLE": self.face_metadata_table.table_name,
                "USER_VECTORS_TABLE": self.user_vectors_table.table_name,
                "ENVIRONMENT": self.environment,
            },
            tracing=_lambda.Tracing.ACTIVE,
        )

        # 授予权限
        self._grant_permissions(function)

        return function

    def _create_batch_process_function(self) -> _lambda.Function:
        """创建批处理函数"""
        function = lambda_python.PythonFunction(
            self,
            "BatchProcessFunction",
            entry="lambda_functions/batch_process",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="handler",
            timeout=Duration.minutes(15),
            memory_size=2048,
            layers=[self.dependencies_layer],
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "FACE_METADATA_TABLE": self.face_metadata_table.table_name,
                "USER_VECTORS_TABLE": self.user_vectors_table.table_name,
                "IMAGES_BUCKET": self.images_bucket.bucket_name,
                "ENVIRONMENT": self.environment,
            },
            tracing=_lambda.Tracing.ACTIVE,
            reserved_concurrent_executions=5,
        )

        # 授予权限
        self._grant_permissions(function)

        return function

    def _grant_permissions(self, function: _lambda.Function):
        """为Lambda函数授予必要权限"""

        # OpenSearch权限
        function.add_to_role_policy(
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

        # DynamoDB权限
        self.face_metadata_table.grant_read_write_data(function)
        self.user_vectors_table.grant_read_write_data(function)

        # S3权限
        self.images_bucket.grant_read_write(function)

        # Rekognition权限
        function.add_to_role_policy(
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

    def setup_s3_triggers(self):
        """公共方法：设置S3触发器（在所有stack创建完成后调用）"""
        self._setup_s3_triggers()

    def _setup_s3_triggers(self):
        """设置S3触发器"""
        # 为新上传的图像自动索引面部
        self.images_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.index_face_function),
            s3.NotificationKeyFilter(prefix="uploads/", suffix=".jpg"),
        )

        self.images_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.index_face_function),
            s3.NotificationKeyFilter(prefix="uploads/", suffix=".png"),
        )

        # 输出函数信息
        cdk.CfnOutput(
            self,
            "IndexFaceFunctionArn",
            value=self.index_face_function.function_arn,
            description="Index Face Function ARN",
        )

        cdk.CfnOutput(
            self,
            "SearchFacesFunctionArn",
            value=self.search_faces_function.function_arn,
            description="Search Faces Function ARN",
        )

        cdk.CfnOutput(
            self,
            "DeleteFaceFunctionArn",
            value=self.delete_face_function.function_arn,
            description="Delete Face Function ARN",
        )
