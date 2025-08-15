import json
import boto3
import base64
import os
from datetime import datetime
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client("rekognition")
dynamodb = boto3.resource("dynamodb")

# 环境变量
FACE_METADATA_TABLE = os.environ.get(
    "FACE_METADATA_TABLE", "face-recognition-face-metadata-dev"
)
REKOGNITION_COLLECTION_ID = os.environ.get(
    "REKOGNITION_COLLECTION_ID", "face-recognition-collection"
)


def lambda_handler(event, context):
    """简化的Lambda处理函数：使用真实AWS Rekognition进行面部搜索"""
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
        if "search_type" not in body:
            return error_response("Missing required parameter: search_type")

        search_type = body["search_type"]
        max_faces = body.get("max_faces", 10)
        similarity_threshold = body.get("similarity_threshold", 0.8)
        collection_id = body.get("collection_id", "default")

        logger.info(f"Processing face search: {search_type}")

        if search_type == "by_image":
            if "image" not in body:
                return error_response(
                    "Missing required parameter: image for image search"
                )

            # 通过图像搜索
            matches = search_by_image(body["image"], max_faces, similarity_threshold)

        elif search_type == "by_face_id":
            if "face_id" not in body:
                return error_response(
                    "Missing required parameter: face_id for face ID search"
                )

            # 通过Face ID搜索
            matches = search_by_face_id(
                body["face_id"], max_faces, similarity_threshold
            )

        else:
            return error_response(
                'Invalid search_type. Must be "by_image" or "by_face_id"'
            )

        # 增强搜索结果
        enhanced_matches = enhance_search_results(matches)

        return success_response(
            {
                "search_type": search_type,
                "matches": enhanced_matches,
                "count": len(enhanced_matches),
                "parameters": {
                    "collection_id": collection_id,
                    "max_faces": max_faces,
                    "similarity_threshold": similarity_threshold,
                },
                "message": "Search completed using real AWS Rekognition",
            }
        )

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return error_response(str(e))


def search_by_image(image_data: str, max_faces: int, similarity_threshold: float):
    """通过图像搜索相似面部"""
    try:
        # 解码base64图像
        image_bytes = base64.b64decode(image_data)

        # 使用Rekognition SearchFacesByImage API
        response = rekognition.search_faces_by_image(
            CollectionId=REKOGNITION_COLLECTION_ID,
            Image={"Bytes": image_bytes},
            MaxFaces=max_faces,
            FaceMatchThreshold=similarity_threshold * 100,  # Rekognition使用0-100的范围
        )

        matches = []
        for face_match in response["FaceMatches"]:
            match = {
                "face_id": face_match["Face"]["FaceId"],
                "similarity": face_match["Similarity"] / 100.0,  # 转换为0-1范围
                "confidence": face_match["Face"]["Confidence"],
                "external_image_id": face_match["Face"].get("ExternalImageId", ""),
                "bounding_box": face_match["Face"]["BoundingBox"],
            }
            matches.append(match)

        logger.info(
            f"Found {len(matches)} matches using Rekognition SearchFacesByImage"
        )
        return matches

    except Exception as e:
        logger.error(f"Error searching by image: {e}")
        raise


def search_by_face_id(face_id: str, max_faces: int, similarity_threshold: float):
    """通过Face ID搜索相似面部"""
    try:
        # 使用Rekognition SearchFaces API
        response = rekognition.search_faces(
            CollectionId=REKOGNITION_COLLECTION_ID,
            FaceId=face_id,
            MaxFaces=max_faces,
            FaceMatchThreshold=similarity_threshold * 100,  # Rekognition使用0-100的范围
        )

        matches = []

        # 首先添加查询的面部本身（100%相似度）
        try:
            face_metadata = get_face_metadata_from_dynamodb(face_id)
            if face_metadata:
                matches.append(
                    {
                        "face_id": face_id,
                        "similarity": 1.0,  # 自己和自己100%相似
                        "confidence": face_metadata.get("confidence", 99.0),
                        "external_image_id": face_metadata.get("external_image_id", ""),
                        "bounding_box": face_metadata.get("bounding_box", {}),
                    }
                )
        except Exception as e:
            logger.warning(f"Could not add self-match for face_id {face_id}: {e}")

        # 添加其他匹配的面部
        for face_match in response["FaceMatches"]:
            match = {
                "face_id": face_match["Face"]["FaceId"],
                "similarity": face_match["Similarity"] / 100.0,  # 转换为0-1范围
                "confidence": face_match["Face"]["Confidence"],
                "external_image_id": face_match["Face"].get("ExternalImageId", ""),
                "bounding_box": face_match["Face"]["BoundingBox"],
            }
            matches.append(match)

        logger.info(f"Found {len(matches)} matches using Rekognition SearchFaces")
        return matches

    except Exception as e:
        logger.error(f"Error searching by face ID: {e}")
        raise


def get_face_metadata_from_dynamodb(face_id: str):
    """从DynamoDB获取面部元数据"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)

        # 查询面部元数据
        response = table.scan(
            FilterExpression="face_id = :face_id",
            ExpressionAttributeValues={":face_id": face_id},
            Limit=1,
        )

        if response["Items"]:
            return response["Items"][0]
        return None

    except Exception as e:
        logger.error(f"Error getting face metadata from DynamoDB: {e}")
        return None


def enhance_search_results(matches):
    """增强搜索结果，添加详细的元数据信息"""
    enhanced_matches = []

    for match in matches:
        face_id = match["face_id"]

        # 从DynamoDB获取详细元数据
        metadata = get_face_metadata_from_dynamodb(face_id)

        enhanced_match = {
            "face_id": face_id,
            "similarity": match["similarity"],
            "confidence": match["confidence"],
            "bounding_box": match["bounding_box"],
        }

        if metadata:
            enhanced_match.update(
                {
                    "user_id": metadata.get("user_id", ""),
                    "collection_id": metadata.get("collection_id", ""),
                    "image_key": metadata.get("image_key", ""),
                    "created_at": metadata.get("created_at", ""),
                }
            )

        enhanced_matches.append(enhanced_match)

    # 按相似度排序
    enhanced_matches.sort(key=lambda x: x["similarity"], reverse=True)

    return enhanced_matches


def success_response(data):
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


def error_response(error_message: str):
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
