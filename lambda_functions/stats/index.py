import json
import boto3
import os
from typing import Dict, Any
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
dynamodb = boto3.resource("dynamodb")

# 环境变量
OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"]
FACE_METADATA_TABLE = os.environ["FACE_METADATA_TABLE"]
USER_VECTORS_TABLE = os.environ["USER_VECTORS_TABLE"]


def lambda_handler(event, context):
    """Lambda处理函数：获取系统统计信息"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 获取HTTP方法
        http_method = event.get("httpMethod", "GET")
        
        if http_method == "GET":
            return handle_get_stats()
        else:
            return create_error_response(405, f"Method {http_method} not allowed")

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))


def handle_get_stats() -> Dict[str, Any]:
    """处理获取统计信息请求"""
    try:
        # 获取面部总数
        total_faces = get_total_faces()
        
        # 获取用户总数
        total_users = get_total_users()
        
        # 获取集合总数
        total_collections = get_total_collections()
        
        # 获取最近活动时间
        last_activity = get_last_activity()

        stats = {
            "total_faces": total_faces,
            "total_users": total_users,
            "total_collections": total_collections,
            "last_activity": last_activity,
            "last_updated": datetime.utcnow().isoformat(),
            "system_status": "healthy"
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD",
            },
            "body": json.dumps(stats),
        }

    except Exception as e:
        logger.error(f"Error in handle_get_stats: {str(e)}")
        return create_error_response(500, str(e))


def get_total_faces() -> int:
    """获取面部总数"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 使用scan获取总数（对于大数据集，应该使用更高效的方法）
        response = table.scan(Select='COUNT')
        return response['Count']
        
    except Exception as e:
        logger.error(f"Error getting total faces: {str(e)}")
        return 0


def get_total_users() -> int:
    """获取用户总数"""
    try:
        table = dynamodb.Table(USER_VECTORS_TABLE)
        
        # 使用scan获取总数
        response = table.scan(Select='COUNT')
        return response['Count']
        
    except Exception as e:
        logger.error(f"Error getting total users: {str(e)}")
        return 0


def get_total_collections() -> int:
    """获取集合总数"""
    try:
        # 从面部元数据表中获取不同的collection_id数量
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 扫描所有记录并统计不同的collection_id
        collections = set()
        
        response = table.scan(
            ProjectionExpression='collection_id'
        )
        
        for item in response['Items']:
            if 'collection_id' in item:
                collections.add(item['collection_id'])
        
        # 处理分页
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression='collection_id',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            for item in response['Items']:
                if 'collection_id' in item:
                    collections.add(item['collection_id'])
        
        return len(collections)
        
    except Exception as e:
        logger.error(f"Error getting total collections: {str(e)}")
        return 1  # 至少有一个默认集合


def get_last_activity() -> str:
    """获取最近活动时间"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 获取最近创建的记录
        response = table.scan(
            ProjectionExpression='created_at',
            Limit=1
        )
        
        if response['Items']:
            # 找到最新的时间戳
            latest_time = None
            for item in response['Items']:
                if 'created_at' in item:
                    if latest_time is None or item['created_at'] > latest_time:
                        latest_time = item['created_at']
            
            return latest_time if latest_time else datetime.utcnow().isoformat()
        else:
            return datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Error getting last activity: {str(e)}")
        return datetime.utcnow().isoformat()


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
