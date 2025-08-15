#!/usr/bin/env python3
"""
独立的 WAF 栈 - 用于解决 API Gateway 关联问题
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_wafv2 as wafv2,
    aws_apigateway as apigateway,
)
from constructs import Construct
import os


class WAFStack(Stack):
    """独立的 WAF 栈，可以在 API Gateway 创建后单独部署"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_gateway_id: str,
        stage_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.api_gateway_id = api_gateway_id
        self.stage_name = stage_name

        # 创建 WAF WebACL
        self.web_acl = self._create_web_acl()

        # 关联到 API Gateway
        self._associate_with_api_gateway()

    def _create_web_acl(self) -> wafv2.CfnWebACL:
        """创建 WAF Web ACL"""
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
                # AWS托管规则 - 已知坏输入规则集
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesKnownBadInputsRuleSet",
                    priority=3,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS", name="AWSManagedRulesKnownBadInputsRuleSet"
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="KnownBadInputsMetric",
                    ),
                ),
            ],
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="FaceRecognitionWebACL",
            ),
        )

        # 输出 WebACL ARN
        cdk.CfnOutput(
            self, "WebACLArn", value=web_acl.attr_arn, description="WAF WebACL ARN"
        )

        return web_acl

    def _associate_with_api_gateway(self):
        """关联 WAF 到 API Gateway"""
        # 构建 API Gateway Stage ARN
        stage_arn = f"arn:aws:apigateway:{self.region}::/restapis/{self.api_gateway_id}/stages/{self.stage_name}"

        # 创建关联
        association = wafv2.CfnWebACLAssociation(
            self,
            "WebACLAssociation",
            resource_arn=stage_arn,
            web_acl_arn=self.web_acl.attr_arn,
        )

        # 确保 WebACL 创建完成后再创建关联
        association.add_dependency(self.web_acl)

        # 输出关联信息
        cdk.CfnOutput(
            self,
            "WebACLAssociationTarget",
            value=stage_arn,
            description="WAF Association Target ARN",
        )

        cdk.CfnOutput(
            self,
            "WebACLAssociationStatus",
            value="Associated",
            description="WAF Association Status",
        )


class WAFStackApp(cdk.App):
    """独立的 WAF 应用，用于在 API Gateway 创建后部署 WAF"""

    def __init__(self):
        super().__init__()

        # 从环境变量获取配置
        api_gateway_id = os.environ.get("API_GATEWAY_ID")
        stage_name = os.environ.get("STAGE_NAME", "prod")
        account_id = os.environ.get("CDK_DEFAULT_ACCOUNT")
        region = os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-1")

        if not api_gateway_id:
            raise ValueError("API_GATEWAY_ID environment variable is required")

        if not account_id:
            raise ValueError("CDK_DEFAULT_ACCOUNT environment variable is required")

        # 创建 WAF 栈
        WAFStack(
            self,
            f"FaceRecognitionWAF-{stage_name.title()}",
            api_gateway_id=api_gateway_id,
            stage_name=stage_name,
            env=cdk.Environment(account=account_id, region=region),
        )


if __name__ == "__main__":
    app = WAFStackApp()
    app.synth()
