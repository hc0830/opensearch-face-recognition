import json
import boto3
import base64
import os
from typing import Dict, Any, List
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

# 环境变量
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
FACE_METADATA_TABLE = os.environ['FACE_METADATA_TABLE']
USER_VECTORS_TABLE = os.environ['USER_VECTORS_TABLE']

def lambda_handler(event, context):
    """Lambda处理函数：搜索面部"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 解析请求体
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # 验证必需参数
        search_type = body.get('search_type')
        if not search_type or search_type not in ['by_image', 'by_face_id']:
            return create_error_response(400, 'Invalid or missing search_type. Must be "by_image" or "by_face_id"')
        
        # 获取搜索参数
        collection_id = body.get('collection_id')
        max_faces = body.get('max_faces', 10)
        similarity_threshold = body.get('similarity_threshold', 0.8)
        
        # 验证参数范围
        if max_faces < 1 or max_faces > 100:
            return create_error_response(400, 'max_faces must be between 1 and 100')
        
        if similarity_threshold < 0.0 or similarity_threshold > 1.0:
            return create_error_response(400, 'similarity_threshold must be between 0.0 and 1.0')
        
        # 根据搜索类型执行搜索
        if search_type == 'by_image':
            if 'image' not in body:
                return create_error_response(400, 'Missing required parameter: image')
            
            results = search_faces_by_image(
                body['image'],
                collection_id,
                max_faces,
                similarity_threshold
            )
        else:  # by_face_id
            if 'face_id' not in body:
                return create_error_response(400, 'Missing required parameter: face_id')
            
            results = search_faces_by_face_id(
                body['face_id'],
                collection_id,
                max_faces,
                similarity_threshold
            )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'search_type': search_type,
                'matches': results,
                'count': len(results),
                'parameters': {
                    'collection_id': collection_id,
                    'max_faces': max_faces,
                    'similarity_threshold': similarity_threshold
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))

def search_faces_by_image(
    image_base64: str,
    collection_id: str = None,
    max_faces: int = 10,
    similarity_threshold: float = 0.8
) -> List[Dict[str, Any]]:
    """通过图像搜索相似面部"""
    try:
        # 解码图像
        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise ValueError(f"Invalid base64 image: {str(e)}")
        
        # 提取查询图像的面部向量
        query_vector = extract_face_vector_from_image(image_bytes)
        if not query_vector:
            return []
        
        # 在OpenSearch中搜索
        matches = search_in_opensearch(
            query_vector=query_vector,
            collection_id=collection_id,
            max_faces=max_faces,
            similarity_threshold=similarity_threshold
        )
        
        return matches
        
    except Exception as e:
        logger.error(f"Error in search_faces_by_image: {str(e)}")
        raise

def search_faces_by_face_id(
    face_id: str,
    collection_id: str = None,
    max_faces: int = 10,
    similarity_threshold: float = 0.8
) -> List[Dict[str, Any]]:
    """通过面部ID搜索相似面部"""
    try:
        # 从OpenSearch获取源面部向量
        query_vector = get_face_vector_from_opensearch(face_id)
        if not query_vector:
            return []
        
        # 在OpenSearch中搜索（排除源面部）
        matches = search_in_opensearch(
            query_vector=query_vector,
            collection_id=collection_id,
            max_faces=max_faces + 1,  # 多获取一个用于排除自身
            similarity_threshold=similarity_threshold,
            exclude_face_id=face_id
        )
        
        return matches[:max_faces]
        
    except Exception as e:
        logger.error(f"Error in search_faces_by_face_id: {str(e)}")
        raise

def extract_face_vector_from_image(image_bytes: bytes) -> List[float]:
    """从图像提取面部向量"""
    try:
        # 使用Rekognition检测面部
        detect_response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['DEFAULT']
        )
        
        if not detect_response['FaceDetails']:
            logger.warning("No faces detected in query image")
            return None
        
        # 生成面部向量（这里使用模拟实现）
        face_vector = generate_face_vector(image_bytes)
        return face_vector
        
    except Exception as e:
        logger.error(f"Error extracting face vector: {str(e)}")
        return None

def generate_face_vector(image_bytes: bytes) -> List[float]:
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

def get_face_vector_from_opensearch(face_id: str) -> List[float]:
    """从OpenSearch获取面部向量"""
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from aws_requests_auth.aws_auth import AWSRequestsAuth
        
        # 创建OpenSearch客户端
        credentials = boto3.Session().get_credentials()
        awsauth = AWSRequestsAuth(credentials, os.environ['AWS_REGION'], 'es')
        
        client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # 获取文档
        response = client.get(
            index='face-vectors',
            id=face_id
        )
        
        if response['found']:
            return response['_source']['face_vector']
        else:
            logger.warning(f"Face ID not found: {face_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting face vector from OpenSearch: {str(e)}")
        return None

def search_in_opensearch(
    query_vector: List[float],
    collection_id: str = None,
    max_faces: int = 10,
    similarity_threshold: float = 0.8,
    exclude_face_id: str = None
) -> List[Dict[str, Any]]:
    """在OpenSearch中搜索相似面部"""
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from aws_requests_auth.aws_auth import AWSRequestsAuth
        
        # 创建OpenSearch客户端
        credentials = boto3.Session().get_credentials()
        awsauth = AWSRequestsAuth(credentials, os.environ['AWS_REGION'], 'es')
        
        client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # 构建搜索查询
        search_body = {
            "size": max_faces * 2,  # 获取更多结果用于过滤
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "face_vector": {
                                    "vector": query_vector,
                                    "k": max_faces * 2
                                }
                            }
                        }
                    ]
                }
            },
            "_source": [
                "face_id", "user_id", "collection_id", "confidence", 
                "bounding_box", "external_image_id", "image_s3_key", "created_at"
            ]
        }
        
        # 添加过滤条件
        filters = []
        
        if collection_id:
            filters.append({"term": {"collection_id": collection_id}})
        
        if exclude_face_id:
            search_body["query"]["bool"]["must_not"] = [
                {"term": {"face_id": exclude_face_id}}
            ]
        
        if filters:
            search_body["query"]["bool"]["filter"] = filters
        
        # 执行搜索
        response = client.search(
            index='face-vectors',
            body=search_body
        )
        
        # 处理结果
        matches = []
        for hit in response['hits']['hits']:
            similarity = hit['_score']
            
            # 应用相似度阈值
            if similarity >= similarity_threshold:
                source = hit['_source']
                matches.append({
                    'face_id': source['face_id'],
                    'user_id': source['user_id'],
                    'collection_id': source['collection_id'],
                    'similarity': similarity,
                    'confidence': source['confidence'],
                    'bounding_box': source['bounding_box'],
                    'external_image_id': source.get('external_image_id'),
                    'image_s3_key': source.get('image_s3_key'),
                    'created_at': source['created_at']
                })
        
        # 按相似度排序并返回指定数量
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:max_faces]
        
    except Exception as e:
        logger.error(f"Error searching in OpenSearch: {str(e)}")
        raise

def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': error_message
        })
    }
