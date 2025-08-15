import json
import boto3
import base64
import os
import uuid
from datetime import datetime
from typing import Dict, Any
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client("rekognition")
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# 环境变量
OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"]
FACE_METADATA_TABLE = os.environ["FACE_METADATA_TABLE"]
USER_VECTORS_TABLE = os.environ["USER_VECTORS_TABLE"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]


def lambda_handler(event, context):
    """Lambda处理函数：索引面部"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 处理不同类型的事件
        if "Records" in event:
            # S3触发的事件
            return handle_s3_event(event)
        else:
            # API Gateway触发的事件
            return handle_api_event(event, context)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"success": False, "error": str(e)}),
        }


def handle_s3_event(event) -> Dict[str, Any]:
    """处理S3触发的事件"""
    results = []

    for record in event["Records"]:
        try:
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            logger.info(f"Processing S3 object: s3://{bucket}/{key}")

            # 从S3获取图像
            response = s3.get_object(Bucket=bucket, Key=key)
            image_bytes = response["Body"].read()

            # 从文件路径提取用户ID
            user_id = extract_user_id_from_key(key)

            # 索引面部
            result = index_face_from_bytes(
                image_bytes=image_bytes,
                user_id=user_id,
                s3_key=f"s3://{bucket}/{key}",
                collection_id="default",
            )

            results.append({"s3_key": f"s3://{bucket}/{key}", "result": result})

        except Exception as e:
            logger.error(f"Error processing S3 record: {str(e)}")
            results.append({"s3_key": f"s3://{bucket}/{key}", "error": str(e)})

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"success": True, "processed": len(results), "results": results}
        ),
    }


def handle_api_event(event, context) -> Dict[str, Any]:
    """处理API Gateway触发的事件"""
    try:
        # 解析请求体
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # 验证必需参数
        if "image" not in body or "user_id" not in body:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Missing required parameters: image, user_id",
                    }
                ),
            }

        # 解码图像
        try:
            image_bytes = base64.b64decode(body["image"])
        except Exception as e:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"success": False, "error": f"Invalid base64 image: {str(e)}"}
                ),
            }

        # 获取可选参数
        user_id = body["user_id"]
        collection_id = body.get("collection_id", "default")
        external_image_id = body.get("external_image_id")

        # 索引面部
        result = index_face_from_bytes(
            image_bytes=image_bytes,
            user_id=user_id,
            collection_id=collection_id,
            external_image_id=external_image_id,
        )

        if result["success"]:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(result),
            }
        else:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(result),
            }

    except Exception as e:
        logger.error(f"Error in handle_api_event: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"success": False, "error": str(e)}),
        }


def index_face_from_bytes(
    image_bytes: bytes,
    user_id: str,
    collection_id: str = "default",
    external_image_id: str = None,
    s3_key: str = None,
) -> Dict[str, Any]:
    """从字节数据索引面部"""
    try:
        # 使用Rekognition检测面部
        detect_response = rekognition.detect_faces(
            Image={"Bytes": image_bytes}, Attributes=["ALL"]
        )

        if not detect_response["FaceDetails"]:
            return {"success": False, "error": "No faces detected in the image"}

        # 创建临时collection用于获取面部向量
        temp_collection = f"temp-{uuid.uuid4().hex[:8]}"

        try:
            # 创建临时collection
            rekognition.create_collection(CollectionId=temp_collection)

            # 索引面部到临时collection
            index_response = rekognition.index_faces(
                CollectionId=temp_collection,
                Image={"Bytes": image_bytes},
                MaxFaces=1,
                QualityFilter="AUTO",
            )

            if not index_response["FaceRecords"]:
                return {"success": False, "error": "No faces could be indexed"}

            face_record = index_response["FaceRecords"][0]
            face_detail = detect_response["FaceDetails"][0]

            # 生成面部ID
            face_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # 获取面部向量（这里使用模拟向量，实际需要实现向量提取）
            face_vector = generate_face_vector(image_bytes)

            # 准备OpenSearch文档
            opensearch_doc = {
                "face_id": face_id,
                "face_vector": face_vector,
                "user_id": user_id,
                "collection_id": collection_id,
                "confidence": face_record["Face"]["Confidence"],
                "bounding_box": face_record["Face"]["BoundingBox"],
                "landmarks": face_detail.get("Landmarks", []),
                "emotions": face_detail.get("Emotions", []),
                "quality": face_detail.get("Quality", {}),
                "created_at": timestamp,
                "updated_at": timestamp,
                "external_image_id": external_image_id,
                "image_s3_key": s3_key,
            }

            # 索引到OpenSearch
            index_to_opensearch(face_id, opensearch_doc)

            # 存储元数据到DynamoDB
            store_face_metadata(face_id, user_id, collection_id, opensearch_doc)

            logger.info(f"Successfully indexed face: {face_id}")

            return {
                "success": True,
                "face_id": face_id,
                "user_id": user_id,
                "confidence": face_record["Face"]["Confidence"],
                "bounding_box": face_record["Face"]["BoundingBox"],
            }

        finally:
            # 清理临时collection
            try:
                rekognition.delete_collection(CollectionId=temp_collection)
            except:
                pass

    except Exception as e:
        logger.error(f"Error indexing face: {str(e)}")
        return {"success": False, "error": str(e)}


def generate_face_vector(image_bytes: bytes) -> list:
    """
    生成面部向量
    注意：这是一个模拟实现，实际应该使用专门的面部识别模型
    """
    import hashlib
    import numpy as np

    # 使用图像哈希作为种子生成一致的向量
    image_hash = hashlib.md5(image_bytes).hexdigest()
    np.random.seed(int(image_hash[:8], 16))

    # 生成512维向量
    vector = np.random.rand(512).tolist()
    return vector


def index_to_opensearch(face_id: str, doc: Dict[str, Any]):
    """索引文档到OpenSearch"""
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from aws_requests_auth.aws_auth import AWSRequestsAuth

        # 创建OpenSearch客户端
        credentials = boto3.Session().get_credentials()
        awsauth = AWSRequestsAuth(credentials, os.environ["AWS_REGION"], "es")

        client = OpenSearch(
            hosts=[{"host": OPENSEARCH_ENDPOINT.replace("https://", ""), "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

        # 索引文档
        response = client.index(
            index="face-vectors", id=face_id, body=doc, refresh=True
        )

        logger.info(f"Indexed to OpenSearch: {response}")

    except Exception as e:
        logger.error(f"Error indexing to OpenSearch: {str(e)}")
        raise


def store_face_metadata(
    face_id: str, user_id: str, collection_id: str, doc: Dict[str, Any]
):
    """存储面部元数据到DynamoDB"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)

        item = {
            "face_id": face_id,
            "collection_id": collection_id,
            "user_id": user_id,
            "confidence": doc["confidence"],
            "created_at": doc["created_at"],
            "external_image_id": doc.get("external_image_id"),
            "image_s3_key": doc.get("image_s3_key"),
            "bounding_box": doc["bounding_box"],
        }

        table.put_item(Item=item)
        logger.info(f"Stored metadata for face: {face_id}")

    except Exception as e:
        logger.error(f"Error storing face metadata: {str(e)}")
        raise


def extract_user_id_from_key(s3_key: str) -> str:
    """从S3键提取用户ID"""
    # 假设文件路径格式为: uploads/{user_id}/{filename}
    parts = s3_key.split("/")
    if len(parts) >= 2 and parts[0] == "uploads":
        return parts[1]

    # 如果无法提取，返回默认值
    return "unknown"
