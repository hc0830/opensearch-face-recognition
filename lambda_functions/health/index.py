import json
import os
from typing import Dict, Any
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Lambda处理函数：健康检查"""
    try:
        logger.info(f"Health check request: {json.dumps(event)}")

        # 获取HTTP方法
        http_method = event.get("httpMethod", "GET")
        
        if http_method == "GET":
            return handle_health_check()
        else:
            return create_error_response(405, f"Method {http_method} not allowed")

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))


def handle_health_check() -> Dict[str, Any]:
    """处理健康检查请求"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "OpenSearch Face Recognition API",
            "version": "1.0.0",
            "environment": os.environ.get("ENVIRONMENT", "unknown")
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD",
            },
            "body": json.dumps(health_status),
        }

    except Exception as e:
        logger.error(f"Error in handle_health_check: {str(e)}")
        return create_error_response(500, str(e))


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD",
        },
        "body": json.dumps({"success": False, "error": error_message}),
    }
