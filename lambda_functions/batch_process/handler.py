import json
import boto3
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
import logging
import time

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client("rekognition")
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# 环境变量
OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"]
FACE_METADATA_TABLE = os.environ["FACE_METADATA_TABLE"]
USER_VECTORS_TABLE = os.environ["USER_VECTORS_TABLE"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]


def lambda_handler(event, context):
    """Lambda处理函数：批处理面部索引"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 解析请求体
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        operation = body.get("operation", "batch_index")

        if operation == "batch_index":
            return handle_batch_index(body)
        elif operation == "migrate_collection":
            return handle_migrate_collection(body)
        else:
            return create_error_response(400, f"Unknown operation: {operation}")

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))


def handle_batch_index(body: Dict[str, Any]) -> Dict[str, Any]:
    """处理批量索引请求"""
    try:
        # 获取参数
        s3_prefix = body.get("s3_prefix", "uploads/")
        collection_id = body.get("collection_id", "default")
        max_workers = body.get("max_workers", 5)
        batch_size = body.get("batch_size", 10)

        # 列出S3对象
        objects = list_s3_objects(IMAGES_BUCKET, s3_prefix)

        if not objects:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": True,
                        "message": "No objects found to process",
                        "processed": 0,
                        "failed": 0,
                    }
                ),
            }

        # 批量处理
        results = batch_process_images(
            objects=objects,
            collection_id=collection_id,
            max_workers=max_workers,
            batch_size=batch_size,
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "total_objects": len(objects),
                    "processed": results["processed"],
                    "failed": results["failed"],
                    "processing_time": results["processing_time"],
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in handle_batch_index: {str(e)}")
        raise


def handle_migrate_collection(body: Dict[str, Any]) -> Dict[str, Any]:
    """处理Rekognition Collection迁移请求"""
    try:
        source_collection_id = body.get("source_collection_id")
        target_collection_id = body.get("target_collection_id", "migrated")

        if not source_collection_id:
            return create_error_response(400, "Missing source_collection_id")

        # 执行迁移
        results = migrate_rekognition_collection(
            source_collection_id, target_collection_id
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "source_collection": source_collection_id,
                    "target_collection": target_collection_id,
                    "migrated": results["migrated"],
                    "failed": results["failed"],
                    "processing_time": results["processing_time"],
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in handle_migrate_collection: {str(e)}")
        raise


def list_s3_objects(bucket: str, prefix: str) -> List[str]:
    """列出S3对象"""
    try:
        objects = []
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    # 只处理图像文件
                    if key.lower().endswith((".jpg", ".jpeg", ".png")):
                        objects.append(key)

        logger.info(f"Found {len(objects)} image objects with prefix {prefix}")
        return objects

    except Exception as e:
        logger.error(f"Error listing S3 objects: {str(e)}")
        raise


def batch_process_images(
    objects: List[str], collection_id: str, max_workers: int = 5, batch_size: int = 10
) -> Dict[str, Any]:
    """批量处理图像"""
    start_time = time.time()
    processed = 0
    failed = 0

    # 分批处理
    batches = [objects[i : i + batch_size] for i in range(0, len(objects), batch_size)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for batch in batches:
            future = executor.submit(process_image_batch, batch, collection_id)
            futures.append(future)

        # 收集结果
        for future in as_completed(futures):
            try:
                result = future.result()
                processed += result["processed"]
                failed += result["failed"]
            except Exception as e:
                logger.error(f"Batch processing failed: {str(e)}")
                failed += batch_size

    processing_time = time.time() - start_time

    return {
        "processed": processed,
        "failed": failed,
        "processing_time": processing_time,
    }


def process_image_batch(objects: List[str], collection_id: str) -> Dict[str, Any]:
    """处理一批图像"""
    processed = 0
    failed = 0

    for obj_key in objects:
        try:
            # 从S3获取图像
            response = s3.get_object(Bucket=IMAGES_BUCKET, Key=obj_key)
            image_bytes = response["Body"].read()

            # 提取用户ID
            user_id = extract_user_id_from_key(obj_key)

            # 索引面部
            result = index_face_from_bytes(
                image_bytes=image_bytes,
                user_id=user_id,
                collection_id=collection_id,
                s3_key=f"s3://{IMAGES_BUCKET}/{obj_key}",
            )

            if result["success"]:
                processed += 1
                logger.info(f"Successfully processed: {obj_key}")
            else:
                failed += 1
                logger.warning(f"Failed to process {obj_key}: {result['error']}")

        except Exception as e:
            failed += 1
            logger.error(f"Error processing {obj_key}: {str(e)}")

    return {"processed": processed, "failed": failed}


def migrate_rekognition_collection(
    source_collection_id: str, target_collection_id: str
) -> Dict[str, Any]:
    """迁移Rekognition Collection到OpenSearch"""
    start_time = time.time()
    migrated = 0
    failed = 0

    try:
        # 获取源collection中的所有面部
        faces = list_collection_faces(source_collection_id)

        if not faces:
            logger.warning(f"No faces found in collection: {source_collection_id}")
            return {"migrated": 0, "failed": 0, "processing_time": 0}

        logger.info(f"Found {len(faces)} faces to migrate from {source_collection_id}")

        # 批量迁移
        batch_size = 50
        batches = [faces[i : i + batch_size] for i in range(0, len(faces), batch_size)]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []

            for batch in batches:
                future = executor.submit(
                    migrate_face_batch, batch, target_collection_id
                )
                futures.append(future)

            # 收集结果
            for future in as_completed(futures):
                try:
                    result = future.result()
                    migrated += result["migrated"]
                    failed += result["failed"]
                except Exception as e:
                    logger.error(f"Batch migration failed: {str(e)}")
                    failed += len(batch)

        processing_time = time.time() - start_time

        return {
            "migrated": migrated,
            "failed": failed,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error(f"Error migrating collection: {str(e)}")
        raise


def list_collection_faces(collection_id: str) -> List[Dict[str, Any]]:
    """列出collection中的所有面部"""
    faces = []
    next_token = None

    try:
        while True:
            params = {"CollectionId": collection_id, "MaxResults": 4096}

            if next_token:
                params["NextToken"] = next_token

            response = rekognition.list_faces(**params)
            faces.extend(response["Faces"])

            next_token = response.get("NextToken")
            if not next_token:
                break

    except Exception as e:
        logger.error(f"Error listing faces from collection {collection_id}: {str(e)}")
        raise

    return faces


def migrate_face_batch(
    faces: List[Dict[str, Any]], target_collection_id: str
) -> Dict[str, Any]:
    """迁移一批面部数据"""
    migrated = 0
    failed = 0

    for face in faces:
        try:
            # 注意：这里需要重新获取原始图像来提取向量
            # 由于Rekognition不提供原始向量，这是迁移的主要挑战
            # 在实际实现中，需要：
            # 1. 存储原始图像的引用
            # 2. 使用自定义模型重新提取向量
            # 3. 或者使用其他方法获取向量

            # 这里使用模拟数据作为示例
            face_doc = create_migrated_face_doc(face, target_collection_id)

            # 索引到OpenSearch
            index_to_opensearch(face["FaceId"], face_doc)

            # 存储元数据
            store_face_metadata(
                face["FaceId"],
                face.get("UserId", "unknown"),
                target_collection_id,
                face_doc,
            )

            migrated += 1

        except Exception as e:
            logger.error(f"Failed to migrate face {face['FaceId']}: {str(e)}")
            failed += 1

    return {"migrated": migrated, "failed": failed}


def create_migrated_face_doc(
    face: Dict[str, Any], collection_id: str
) -> Dict[str, Any]:
    """创建迁移的面部文档"""
    import numpy as np
    from datetime import datetime

    # 生成模拟向量（实际需要重新提取）
    np.random.seed(hash(face["FaceId"]) % (2**32))
    face_vector = np.random.rand(512).tolist()

    return {
        "face_id": face["FaceId"],
        "face_vector": face_vector,
        "user_id": face.get("UserId", "unknown"),
        "collection_id": collection_id,
        "confidence": face["Confidence"],
        "bounding_box": face["BoundingBox"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "migrated_from": "rekognition_collection",
    }


# 重用其他Lambda函数中的辅助函数
def index_face_from_bytes(
    image_bytes: bytes, user_id: str, collection_id: str, s3_key: str = None
) -> Dict[str, Any]:
    """索引面部（简化版本）"""
    # 这里应该调用完整的索引逻辑
    # 为了简化，返回模拟结果
    return {"success": True, "face_id": "mock_face_id"}


def index_to_opensearch(face_id: str, doc: Dict[str, Any]):
    """索引到OpenSearch（简化版本）"""
    # 实际实现应该与index_face函数中的相同
    pass


def store_face_metadata(
    face_id: str, user_id: str, collection_id: str, doc: Dict[str, Any]
):
    """存储面部元数据（简化版本）"""
    # 实际实现应该与index_face函数中的相同
    pass


def extract_user_id_from_key(s3_key: str) -> str:
    """从S3键提取用户ID"""
    parts = s3_key.split("/")
    if len(parts) >= 2 and parts[0] == "uploads":
        return parts[1]
    return "unknown"


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"success": False, "error": error_message}),
    }
