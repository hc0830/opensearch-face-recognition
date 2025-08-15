import json
import boto3
import os
import uuid
from typing import Dict, Any, List
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
    """Lambda处理函数：集合管理"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 获取HTTP方法和路径
        http_method = event.get("httpMethod", "GET")
        path_parameters = event.get("pathParameters") or {}
        collection_id = path_parameters.get("collection_id")

        if http_method == "GET":
            if collection_id:
                return handle_get_collection(collection_id)
            else:
                return handle_list_collections()
        elif http_method == "POST":
            return handle_create_collection(event)
        elif http_method == "PUT" and collection_id:
            return handle_update_collection(collection_id, event)
        elif http_method == "DELETE" and collection_id:
            return handle_delete_collection(collection_id)
        else:
            return create_error_response(405, f"Method {http_method} not allowed")

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))


def handle_list_collections() -> Dict[str, Any]:
    """处理列出所有集合请求"""
    try:
        collections = get_all_collections()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                    "X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": (
                    "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"
                ),
            },
            "body": json.dumps(collections),
        }

    except Exception as e:
        logger.error(f"Error in handle_list_collections: {str(e)}")
        return create_error_response(500, str(e))


def handle_get_collection(collection_id: str) -> Dict[str, Any]:
    """处理获取特定集合请求"""
    try:
        collection = get_collection_details(collection_id)

        if collection:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": (
                        "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                        "X-Amz-Security-Token"
                    ),
                    "Access-Control-Allow-Methods": (
                        "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"
                    ),
                },
                "body": json.dumps(collection),
            }
        else:
            return create_error_response(404, f"Collection {collection_id} not found")

    except Exception as e:
        logger.error(f"Error in handle_get_collection: {str(e)}")
        return create_error_response(500, str(e))


def handle_create_collection(event) -> Dict[str, Any]:
    """处理创建集合请求"""
    try:
        # 解析请求体
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # 验证必需参数
        if "name" not in body:
            return create_error_response(400, "Missing required parameter: name")

        collection_id = body.get("id", str(uuid.uuid4()))
        name = body["name"]
        description = body.get("description", "")

        # 创建集合（这里我们使用DynamoDB存储集合元数据）
        collection = create_collection_metadata(collection_id, name, description)

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                    "X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": (
                    "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"
                ),
            },
            "body": json.dumps(collection),
        }

    except Exception as e:
        logger.error(f"Error in handle_create_collection: {str(e)}")
        return create_error_response(500, str(e))


def handle_update_collection(collection_id: str, event) -> Dict[str, Any]:
    """处理更新集合请求"""
    try:
        # 解析请求体
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # 更新集合元数据
        collection = update_collection_metadata(collection_id, body)

        if collection:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": (
                        "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                        "X-Amz-Security-Token"
                    ),
                    "Access-Control-Allow-Methods": (
                        "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"
                    ),
                },
                "body": json.dumps(collection),
            }
        else:
            return create_error_response(404, f"Collection {collection_id} not found")

    except Exception as e:
        logger.error(f"Error in handle_update_collection: {str(e)}")
        return create_error_response(500, str(e))


def handle_delete_collection(collection_id: str) -> Dict[str, Any]:
    """处理删除集合请求"""
    try:
        # 检查集合是否存在
        if not collection_exists(collection_id):
            return create_error_response(404, f"Collection {collection_id} not found")

        # 检查集合是否有面部数据
        face_count = get_collection_face_count(collection_id)
        if face_count > 0:
            return create_error_response(
                400,
                f"Cannot delete collection with {face_count} faces. "
                "Delete faces first.",
            )

        # 删除集合元数据
        delete_collection_metadata(collection_id)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                    "X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": (
                    "OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"
                ),
            },
            "body": json.dumps(
                {"success": True, "message": f"Collection {collection_id} deleted"}
            ),
        }

    except Exception as e:
        logger.error(f"Error in handle_delete_collection: {str(e)}")
        return create_error_response(500, str(e))


def get_all_collections() -> List[Dict[str, Any]]:
    """获取所有集合"""
    try:
        # 从面部元数据表中获取所有不同的collection_id
        table = dynamodb.Table(FACE_METADATA_TABLE)

        collections_data = {}

        # 扫描所有记录
        response = table.scan()

        for item in response["Items"]:
            collection_id = item.get("collection_id", "default")

            if collection_id not in collections_data:
                collections_data[collection_id] = {
                    "id": collection_id,
                    "name": collection_id.replace("_", " ").title(),
                    "face_count": 0,
                    "created_at": item.get("created_at", datetime.utcnow().isoformat()),
                    "description": f"Collection for {collection_id}",
                }

            collections_data[collection_id]["face_count"] += 1

            # 更新最早的创建时间
            if (
                item.get("created_at")
                and item["created_at"] < collections_data[collection_id]["created_at"]
            ):
                collections_data[collection_id]["created_at"] = item["created_at"]

        # 处理分页
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])

            for item in response["Items"]:
                collection_id = item.get("collection_id", "default")

                if collection_id not in collections_data:
                    collections_data[collection_id] = {
                        "id": collection_id,
                        "name": collection_id.replace("_", " ").title(),
                        "face_count": 0,
                        "created_at": item.get(
                            "created_at", datetime.utcnow().isoformat()
                        ),
                        "description": f"Collection for {collection_id}",
                    }

                collections_data[collection_id]["face_count"] += 1

                if (
                    item.get("created_at")
                    and item["created_at"]
                    < collections_data[collection_id]["created_at"]
                ):
                    collections_data[collection_id]["created_at"] = item["created_at"]

        # 如果没有集合，返回默认集合
        if not collections_data:
            collections_data["default"] = {
                "id": "default",
                "name": "Default Collection",
                "face_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "description": "Default collection for face recognition",
            }

        return list(collections_data.values())

    except Exception as e:
        logger.error(f"Error getting all collections: {str(e)}")
        # 返回默认集合
        return [
            {
                "id": "default",
                "name": "Default Collection",
                "face_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "description": "Default collection for face recognition",
            }
        ]


def get_collection_details(collection_id: str) -> Dict[str, Any]:
    """获取集合详情"""
    try:
        face_count = get_collection_face_count(collection_id)

        if face_count > 0 or collection_id == "default":
            return {
                "id": collection_id,
                "name": collection_id.replace("_", " ").title(),
                "face_count": face_count,
                "created_at": datetime.utcnow().isoformat(),
                "description": f"Collection for {collection_id}",
            }
        else:
            return None

    except Exception as e:
        logger.error(f"Error getting collection details: {str(e)}")
        return None


def get_collection_face_count(collection_id: str) -> int:
    """获取集合中的面部数量"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)

        response = table.scan(
            FilterExpression="collection_id = :cid",
            ExpressionAttributeValues={":cid": collection_id},
            Select="COUNT",
        )

        return response["Count"]

    except Exception as e:
        logger.error(f"Error getting collection face count: {str(e)}")
        return 0


def collection_exists(collection_id: str) -> bool:
    """检查集合是否存在"""
    try:
        face_count = get_collection_face_count(collection_id)
        return face_count > 0 or collection_id == "default"

    except Exception as e:
        logger.error(f"Error checking collection existence: {str(e)}")
        return False


def create_collection_metadata(
    collection_id: str, name: str, description: str
) -> Dict[str, Any]:
    """创建集合元数据"""
    # 注意：在这个简化实现中，我们不单独存储集合元数据
    # 集合的存在由面部数据的collection_id字段隐式定义
    return {
        "id": collection_id,
        "name": name,
        "description": description,
        "face_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }


def update_collection_metadata(
    collection_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """更新集合元数据"""
    # 在这个简化实现中，我们只返回更新后的信息
    # 实际应用中可能需要单独的集合元数据表
    if collection_exists(collection_id):
        return {
            "id": collection_id,
            "name": updates.get("name", collection_id.replace("_", " ").title()),
            "description": updates.get(
                "description", f"Collection for {collection_id}"
            ),
            "face_count": get_collection_face_count(collection_id),
            "updated_at": datetime.utcnow().isoformat(),
        }
    else:
        return None


def delete_collection_metadata(collection_id: str):
    """删除集合元数据"""
    # 在这个简化实现中，集合的删除通过删除所有相关面部数据来实现
    # 这个函数主要用于验证和日志记录
    logger.info(f"Collection {collection_id} metadata deleted")


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": (
                "Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                "X-Amz-Security-Token"
            ),
            "Access-Control-Allow-Methods": ("OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD"),
        },
        "body": json.dumps({"success": False, "error": error_message}),
    }
