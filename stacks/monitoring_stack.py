import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_elasticsearch as elasticsearch,
    aws_logs as logs,
    Duration,
)
from constructs import Construct
from typing import List
import os


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: elasticsearch.Domain,
        lambda_functions: List[_lambda.Function],
        api_gateway: apigateway.RestApi,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.opensearch_domain = opensearch_domain
        self.lambda_functions = lambda_functions
        self.api_gateway = api_gateway

        # 环境配置
        self.env_name = os.getenv("ENVIRONMENT", "dev")
        self.alert_email = os.getenv("ALERT_EMAIL", "admin@example.com")

        # 创建SNS主题
        self.alert_topic = self._create_alert_topic()

        # 创建CloudWatch Dashboard
        self.dashboard = self._create_dashboard()

        # 创建告警
        self._create_alarms()

    def _create_alert_topic(self) -> sns.Topic:
        """创建告警SNS主题"""
        topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name=f"face-recognition-alerts-{self.env_name}",
            display_name="Face Recognition System Alerts",
        )

        # 添加邮件订阅
        topic.add_subscription(subs.EmailSubscription(self.alert_email))

        return topic

    def _create_dashboard(self) -> cloudwatch.Dashboard:
        """创建CloudWatch Dashboard"""
        dashboard = cloudwatch.Dashboard(
            self,
            "FaceRecognitionDashboard",
            dashboard_name=f"FaceRecognition-{self.env_name}",
        )

        # API Gateway指标
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="API Gateway - Requests & Errors",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Count",
                        dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                        statistic="Sum",
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="4XXError",
                        dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                        statistic="Sum",
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="5XXError",
                        dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                        statistic="Sum",
                    ),
                ],
                width=12,
            )
        )

        return dashboard

    def _create_alarms(self):
        """创建CloudWatch告警"""

        # API Gateway错误告警
        cloudwatch.Alarm(
            self,
            "ApiGatewayErrorAlarm",
            alarm_name=f"FaceRecognition-API-Errors-{self.environment}",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={"ApiName": self.api_gateway.rest_api_name},
                statistic="Sum",
            ),
            threshold=10,
            evaluation_periods=2,
        ).add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # 输出监控信息
        cdk.CfnOutput(
            self,
            "AlertTopicArn",
            value=self.alert_topic.topic_arn,
            description="SNS Alert Topic ARN",
        )
