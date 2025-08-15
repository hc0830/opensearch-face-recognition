#!/usr/bin/env python3
"""
WAF 部署脚本 - 在 API Gateway 创建后单独部署 WAF
"""

import boto3
import os
import sys
import subprocess
import json
from typing import Optional


def get_api_gateway_id(stack_name: str, region: str) -> Optional[str]:
    """从 CloudFormation 栈输出中获取 API Gateway ID"""
    try:
        cf_client = boto3.client("cloudformation", region_name=region)
        
        response = cf_client.describe_stacks(StackName=stack_name)
        stack = response["Stacks"][0]
        
        for output in stack.get("Outputs", []):
            if output["OutputKey"] == "ApiGatewayId":
                return output["OutputValue"]
        
        print(f"Warning: ApiGatewayId not found in stack {stack_name} outputs")
        return None
        
    except Exception as e:
        print(f"Error getting API Gateway ID from stack {stack_name}: {e}")
        return None


def deploy_waf(api_gateway_id: str, stage_name: str, region: str, account_id: str):
    """部署 WAF 栈"""
    try:
        # 设置环境变量
        env = os.environ.copy()
        env.update({
            "API_GATEWAY_ID": api_gateway_id,
            "STAGE_NAME": stage_name,
            "CDK_DEFAULT_ACCOUNT": account_id,
            "CDK_DEFAULT_REGION": region,
        })
        
        # 部署 WAF 栈
        cmd = [
            "npx", "cdk", "deploy", 
            "--app", "python stacks/waf_stack.py",
            "--require-approval", "never"
        ]
        
        print(f"Deploying WAF for API Gateway {api_gateway_id} in stage {stage_name}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ WAF deployment successful!")
            print(result.stdout)
        else:
            print("❌ WAF deployment failed!")
            print(result.stderr)
            return False
            
        return True
        
    except Exception as e:
        print(f"Error deploying WAF: {e}")
        return False


def main():
    """主函数"""
    # 获取参数
    region = os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-1")
    account_id = os.environ.get("CDK_DEFAULT_ACCOUNT")
    stage_name = os.environ.get("ENVIRONMENT", "prod")
    
    if not account_id:
        print("Error: CDK_DEFAULT_ACCOUNT environment variable is required")
        sys.exit(1)
    
    # API Gateway 栈名称
    api_stack_name = f"OpenSearchFaceRecognition-{stage_name.title()}-API"
    
    print(f"Looking for API Gateway in stack: {api_stack_name}")
    
    # 获取 API Gateway ID
    api_gateway_id = get_api_gateway_id(api_stack_name, region)
    
    if not api_gateway_id:
        print("Error: Could not find API Gateway ID")
        sys.exit(1)
    
    print(f"Found API Gateway ID: {api_gateway_id}")
    
    # 部署 WAF
    success = deploy_waf(api_gateway_id, stage_name, region, account_id)
    
    if not success:
        sys.exit(1)
    
    print("🎉 WAF deployment completed successfully!")


if __name__ == "__main__":
    main()
