import json
import boto3
import base64
import os
import uuid
from datetime import datetime
from typing import Dict, Any
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client("rekognition")
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# 环境变量
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "").replace("https://", "")
FACE_METADATA_TABLE = os.environ.get("FACE_METADATA_TABLE")
USER_VECTORS_TABLE = os.environ.get("USER_VECTORS_TABLE")
IMAGES_BUCKET = os.environ.get("IMAGES_BUCKET")
REKOGNITION_COLLECTION_ID = os.environ.get(
    "REKOGNITION_COLLECTION_ID", "face-recognition-collection"
)


# 初始化OpenSearch客户端
def get_opensearch_client():
    """获取OpenSearch客户端"""
    if not OPENSEARCH_ENDPOINT:
        raise ValueError("OpenSearch endpoint not configured")

    # AWS认证
    region = "ap-southeast-1"
    service = "es"
    credentials = boto3.Session().get_credentials()
    awsauth = AWSRequestsAuth(credentials, region, service)

    # 创建OpenSearch客户端
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    return client


def lambda_handler(event, context):
    """Lambda处理函数：使用真实AWS服务索引面部"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 解析请求
        if "body" in event:
            body = (
                json.loads(event["body"])
                if isinstance(event["body"], str)
                else event["body"]
            )
        else:
            body = event

        # 验证必需参数
        if "image" not in body:
            return error_response("Missing required parameter: image")

        if "user_id" not in body:
            return error_response("Missing required parameter: user_id")

        image_data = body["image"]
        user_id = body["user_id"]
        collection_id = body.get("collection_id", "default")

        # 1. 将图像上传到S3
        image_key = upload_image_to_s3(image_data, user_id)
        logger.info(f"Image uploaded to S3: {image_key}")

        # 2. 使用Rekognition进行面部检测和索引
        face_data = index_face_with_rekognition(image_data, user_id, collection_id)
        logger.info(f"Face indexed with Rekognition: {face_data['FaceId']}")

        # 3. 存储元数据到DynamoDB
        metadata = store_face_metadata(face_data, user_id, collection_id, image_key)
        logger.info(f"Metadata stored in DynamoDB")

        # 4. 索引到OpenSearch用于搜索
        opensearch_doc = index_to_opensearch(face_data, metadata)
        logger.info(f"Document indexed in OpenSearch")

        # 5. 更新用户向量表
        update_user_vectors(user_id, face_data["FaceId"], collection_id)
        logger.info(f"User vectors updated")

        return success_response(
            {
                "face_id": face_data["FaceId"],
                "user_id": user_id,
                "collection_id": collection_id,
                "confidence": face_data["Face"]["Confidence"],
                "bounding_box": face_data["Face"]["BoundingBox"],
                "image_key": image_key,
                "opensearch_id": opensearch_doc["_id"],
                "message": "Face indexed successfully with real AWS services",
            }
        )

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return error_response(str(e))


def upload_image_to_s3(image_data: str, user_id: str) -> str:
    """上传图像到S3"""
    try:
        # 解码base64图像
        image_bytes = base64.b64decode(image_data)

        # 生成唯一的文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        image_key = f"faces/{user_id}/{timestamp}_{uuid.uuid4().hex[:8]}.jpg"

        # 上传到S3
        s3.put_object(
            Bucket=IMAGES_BUCKET,
            Key=image_key,
            Body=image_bytes,
            ContentType="image/jpeg",
            Metadata={"user_id": user_id, "upload_time": datetime.utcnow().isoformat()},
        )

        return image_key

    except Exception as e:
        logger.error(f"Error uploading image to S3: {e}")
        raise


def index_face_with_rekognition(
    image_data: str, user_id: str, collection_id: str
) -> Dict[str, Any]:
    """使用Rekognition索引面部"""
    try:
        # 解码base64图像
        image_bytes = base64.b64decode(image_data)

        # 调用Rekognition IndexFaces API
        response = rekognition.index_faces(
            CollectionId=REKOGNITION_COLLECTION_ID,
            Image={"Bytes": image_bytes},
            ExternalImageId=f"{user_id}_{uuid.uuid4().hex[:8]}",
            MaxFaces=1,
            QualityFilter="AUTO",
            DetectionAttributes=["ALL"],
        )

        if not response["FaceRecords"]:
            raise ValueError("No faces detected in the image")

        face_record = response["FaceRecords"][0]
        return face_record

    except Exception as e:
        logger.error(f"Error indexing face with Rekognition: {e}")
        raise


def store_face_metadata(
    face_data: Dict[str, Any], user_id: str, collection_id: str, image_key: str
) -> Dict[str, Any]:
    """存储面部元数据到DynamoDB"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)

        face_id = face_data["FaceId"]
        face_info = face_data["Face"]

        metadata = {
            "face_id": face_id,
            "collection_id": collection_id,
            "user_id": user_id,
            "confidence": float(face_info["Confidence"]),
            "bounding_box": {
                "Width": float(face_info["BoundingBox"]["Width"]),
                "Height": float(face_info["BoundingBox"]["Height"]),
                "Left": float(face_info["BoundingBox"]["Left"]),
                "Top": float(face_info["BoundingBox"]["Top"]),
            },
            "landmarks": [
                {
                    "Type": landmark["Type"],
                    "X": float(landmark["X"]),
                    "Y": float(landmark["Y"]),
                }
                for landmark in face_info.get("Landmarks", [])
            ],
            "pose": {
                "Roll": float(face_info["Pose"]["Roll"]),
                "Yaw": float(face_info["Pose"]["Yaw"]),
                "Pitch": float(face_info["Pose"]["Pitch"]),
            },
            "quality": {
                "Brightness": float(face_info["Quality"]["Brightness"]),
                "Sharpness": float(face_info["Quality"]["Sharpness"]),
            },
            "image_key": image_key,
            "created_at": datetime.utcnow().isoformat(),
            "external_image_id": face_data.get("Face", {}).get("ExternalImageId", ""),
        }

        # 存储到DynamoDB
        table.put_item(Item=metadata)

        return metadata

    except Exception as e:
        logger.error(f"Error storing face metadata: {e}")
        raise


def index_to_opensearch(
    face_data: Dict[str, Any], metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """索引面部数据到OpenSearch"""
    try:
        client = get_opensearch_client()

        # 准备OpenSearch文档
        doc = {
            "face_id": face_data["FaceId"],
            "user_id": metadata["user_id"],
            "collection_id": metadata["collection_id"],
            "confidence": metadata["confidence"],
            "bounding_box": metadata["bounding_box"],
            "landmarks": metadata["landmarks"],
            "pose": metadata["pose"],
            "quality": metadata["quality"],
            "image_key": metadata["image_key"],
            "created_at": metadata["created_at"],
            "timestamp": datetime.utcnow().timestamp(),
        }

        # 索引文档
        index_name = f"face-recognition-{metadata['collection_id'].lower()}"
        response = client.index(index=index_name, id=face_data["FaceId"], body=doc)

        return response

    except Exception as e:
        logger.error(f"Error indexing to OpenSearch: {e}")
        raise


def update_user_vectors(user_id: str, face_id: str, collection_id: str):
    """更新用户向量表"""
    try:
        table = dynamodb.Table(USER_VECTORS_TABLE)

        # 获取现有记录或创建新记录
        try:
            response = table.get_item(Key={"user_id": user_id})
            item = response.get(
                "Item",
                {
                    "user_id": user_id,
                    "face_ids": [],
                    "collections": {},
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        except:
            item = {
                "user_id": user_id,
                "face_ids": [],
                "collections": {},
                "created_at": datetime.utcnow().isoformat(),
            }

        # 更新面部ID列表
        if face_id not in item["face_ids"]:
            item["face_ids"].append(face_id)

        # 更新collection统计
        if collection_id not in item["collections"]:
            item["collections"][collection_id] = []
        if face_id not in item["collections"][collection_id]:
            item["collections"][collection_id].append(face_id)

        item["updated_at"] = datetime.utcnow().isoformat()
        item["total_faces"] = len(item["face_ids"])

        # 保存更新
        table.put_item(Item=item)

    except Exception as e:
        logger.error(f"Error updating user vectors: {e}")
        raise


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """成功响应"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": json.dumps(
            {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "region": "ap-southeast-1",
                **data,
            }
        ),
    }


def error_response(error_message: str) -> Dict[str, Any]:
    """错误响应"""
    return {
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": json.dumps(
            {
                "success": False,
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    }
