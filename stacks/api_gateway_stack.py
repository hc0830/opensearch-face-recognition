import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_wafv2 as wafv2,
    Duration,
)
from constructs import Construct
import os


class ApiGatewayStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        index_face_function: _lambda.Function,
        search_faces_function: _lambda.Function,
        delete_face_function: _lambda.Function,
        stats_function: _lambda.Function,
        collections_function: _lambda.Function,
        health_function: _lambda.Function,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.index_face_function = index_face_function
        self.search_faces_function = search_faces_function
        self.delete_face_function = delete_face_function
        self.stats_function = stats_function
        self.collections_function = collections_function
        self.health_function = health_function

        # 环境配置
        env_name = os.getenv("ENVIRONMENT", "dev")
        self.env_name = env_name

        # 创建API Gateway
        self.api = self._create_api_gateway(env_name)

        # 创建API资源和方法
        self._create_api_resources()

        # 创建WAF（生产环境且启用WAF时）
        # 可以通过环境变量 ENABLE_WAF=false 来禁用WAF
        enable_waf = os.environ.get("ENABLE_WAF", "true").lower() == "true"
        if env_name != "dev" and enable_waf:
            try:
                self._create_waf(env_name)
            except Exception as e:
                print(
                    f"Warning: Failed to create WAF, continuing without WAF protection: {e}"
                )
                # 继续部署，但不使用WAF保护

    def _create_api_gateway(self, env_name: str) -> apigateway.RestApi:
        """创建API Gateway"""

        # 创建访问日志组
        log_group = logs.LogGroup(
            self,
            "ApiGatewayLogGroup",
            log_group_name=f"/aws/apigateway/face-recognition-{self.env_name}",
            retention=(
                logs.RetentionDays.ONE_MONTH
                if self.env_name == "dev"
                else logs.RetentionDays.SIX_MONTHS
            ),
        )

        api = apigateway.RestApi(
            self,
            "FaceRecognitionApi",
            rest_api_name=f"face-recognition-api-{self.env_name}",
            description="Face Recognition API using OpenSearch",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.env_name,
                throttling_rate_limit=1000 if self.env_name != "dev" else 100,
                throttling_burst_limit=2000 if self.env_name != "dev" else 200,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                access_log_destination=apigateway.LogGroupLogDestination(log_group),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
                tracing_enabled=True,
                metrics_enabled=True,
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        return api

    def _create_api_resources(self):
        """创建API资源和方法"""

        # 创建请求验证器
        request_validator = self.api.add_request_validator(
            "RequestValidator",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        # 创建通用响应模型
        error_response_model = self.api.add_model(
            "ErrorResponseModel",
            content_type="application/json",
            model_name="ErrorResponse",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "success": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.BOOLEAN
                    ),
                    "error": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    ),
                    "message": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    ),
                },
                required=["success", "error"],
            ),
        )

        # /faces 资源 - 面部管理
        faces_resource = self.api.root.add_resource("faces")

        # POST /faces - 索引面部
        index_face_model = self.api.add_model(
            "IndexFaceRequestModel",
            content_type="application/json",
            model_name="IndexFaceRequest",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "image": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Base64 encoded image",
                    ),
                    "user_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="User identifier",
                    ),
                    "collection_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Collection identifier",
                    ),
                    "external_image_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="External image identifier",
                    ),
                },
                required=["image", "user_id"],
            ),
        )

        faces_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.index_face_function,
                proxy=True,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                    ),
                    apigateway.IntegrationResponse(
                        status_code="400",
                        selection_pattern="4\\d{2}",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                    ),
                    apigateway.IntegrationResponse(
                        status_code="500",
                        selection_pattern="5\\d{2}",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                    ),
                ],
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    },
                ),
                apigateway.MethodResponse(
                    status_code="400",
                    response_models={"application/json": error_response_model},
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    },
                ),
                apigateway.MethodResponse(
                    status_code="500",
                    response_models={"application/json": error_response_model},
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    },
                ),
            ],
            request_validator=request_validator,
            request_models={"application/json": index_face_model},
        )

        # DELETE /faces/{face_id} - 删除面部
        face_id_resource = faces_resource.add_resource("{face_id}")
        face_id_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.delete_face_function, proxy=True),
            request_parameters={"method.request.path.face_id": True},
        )

        # /search 资源 - 面部搜索
        search_resource = self.api.root.add_resource("search")

        # POST /search - 搜索面部
        search_model = self.api.add_model(
            "SearchFacesRequestModel",
            content_type="application/json",
            model_name="SearchFacesRequest",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "search_type": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        enum=["by_image", "by_face_id"],
                        description="Search type",
                    ),
                    "image": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Base64 encoded image (for by_image search)",
                    ),
                    "face_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Face ID (for by_face_id search)",
                    ),
                    "collection_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Collection to search in",
                    ),
                    "max_faces": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.INTEGER,
                        minimum=1,
                        maximum=100,
                        description="Maximum number of results",
                    ),
                    "similarity_threshold": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.NUMBER,
                        minimum=0.0,
                        maximum=1.0,
                        description="Similarity threshold",
                    ),
                },
                required=["search_type"],
            ),
        )

        search_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.search_faces_function, proxy=True),
            request_validator=request_validator,
            request_models={"application/json": search_model},
        )

        # /health 资源 - 健康检查（Lambda集成）
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.health_function, proxy=True),
        )

        # /stats 资源 - 系统统计信息（Lambda集成）
        stats_resource = self.api.root.add_resource("stats")
        stats_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.stats_function, proxy=True),
        )

        # /collections 资源 - 集合管理（Lambda集成）
        collections_resource = self.api.root.add_resource("collections")
        collections_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.collections_function, proxy=True),
        )
        collections_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.collections_function, proxy=True),
        )

        # /collections/{collection_id} 资源 - 特定集合管理
        collection_id_resource = collections_resource.add_resource("{collection_id}")
        collection_id_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.collections_function, proxy=True),
        )
        collection_id_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.collections_function, proxy=True),
        )
        collection_id_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.collections_function, proxy=True),
        )

    def _create_waf(self, env_name: str):
        """创建WAF Web ACL"""
        web_acl = wafv2.CfnWebACL(
            self,
            "FaceRecognitionWebACL",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            rules=[
                # 速率限制规则
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=1,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=2000, aggregate_key_type="IP"
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitRule",
                    ),
                ),
                # AWS托管规则 - 通用规则集
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=2,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS", name="AWSManagedRulesCommonRuleSet"
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSetMetric",
                    ),
                ),
            ],
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="FaceRecognitionWebACL",
            ),
        )

        # 关联WAF到API Gateway - 添加显式依赖
        association = wafv2.CfnWebACLAssociation(
            self,
            "WebACLAssociation",
            resource_arn=f"arn:aws:apigateway:{self.region}::/restapis/{self.api.rest_api_id}/stages/{self.env_name}",
            web_acl_arn=web_acl.attr_arn,
        )

        # 确保 WebACL 创建完成后再创建关联
        association.add_dependency(web_acl)

        # 输出 WebACL ARN 用于调试
        cdk.CfnOutput(
            self, "WebACLArn", value=web_acl.attr_arn, description="WAF WebACL ARN"
        )

        # 输出API信息
        cdk.CfnOutput(
            self, "ApiGatewayUrl", value=self.api.url, description="API Gateway URL"
        )

        cdk.CfnOutput(
            self,
            "ApiGatewayId",
            value=self.api.rest_api_id,
            description="API Gateway ID",
        )
