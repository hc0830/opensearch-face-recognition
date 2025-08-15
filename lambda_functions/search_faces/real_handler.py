import json
import boto3
import base64
import os
from datetime import datetime
from typing import Dict, Any, List
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

# 环境变量
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', '').replace('https://', '')
FACE_METADATA_TABLE = os.environ.get('FACE_METADATA_TABLE')
REKOGNITION_COLLECTION_ID = os.environ.get('REKOGNITION_COLLECTION_ID', 'face-recognition-collection')

def get_opensearch_client():
    """获取OpenSearch客户端"""
    if not OPENSEARCH_ENDPOINT:
        raise ValueError("OpenSearch endpoint not configured")
    
    region = 'ap-southeast-1'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWSRequestsAuth(credentials, region, service)
    
    client = OpenSearch(
        hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    
    return client

def lambda_handler(event, context):
    """Lambda处理函数：使用真实AWS服务搜索面部"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 解析请求
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # 验证必需参数
        if 'search_type' not in body:
            return error_response('Missing required parameter: search_type')
        
        search_type = body['search_type']
        max_faces = body.get('max_faces', 10)
        similarity_threshold = body.get('similarity_threshold', 0.8)
        collection_id = body.get('collection_id', 'default')
        
        if search_type == 'by_image':
            if 'image' not in body:
                return error_response('Missing required parameter: image for image search')
            
            # 通过图像搜索
            matches = search_by_image(
                body['image'], 
                max_faces, 
                similarity_threshold, 
                collection_id
            )
            
        elif search_type == 'by_face_id':
            if 'face_id' not in body:
                return error_response('Missing required parameter: face_id for face ID search')
            
            # 通过Face ID搜索
            matches = search_by_face_id(
                body['face_id'], 
                max_faces, 
                similarity_threshold, 
                collection_id
            )
            
        else:
            return error_response('Invalid search_type. Must be "by_image" or "by_face_id"')
        
        # 增强搜索结果（从DynamoDB和OpenSearch获取详细信息）
        enhanced_matches = enhance_search_results(matches)
        
        return success_response({
            'search_type': search_type,
            'matches': enhanced_matches,
            'count': len(enhanced_matches),
            'parameters': {
                'collection_id': collection_id,
                'max_faces': max_faces,
                'similarity_threshold': similarity_threshold
            },
            'message': 'Search completed using real AWS Rekognition'
        })
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return error_response(str(e))

def search_by_image(image_data: str, max_faces: int, similarity_threshold: float, collection_id: str) -> List[Dict[str, Any]]:
    """通过图像搜索相似面部"""
    try:
        # 解码base64图像
        image_bytes = base64.b64decode(image_data)
        
        # 使用Rekognition SearchFacesByImage API
        response = rekognition.search_faces_by_image(
            CollectionId=REKOGNITION_COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=max_faces,
            FaceMatchThreshold=similarity_threshold * 100  # Rekognition使用0-100的范围
        )
        
        matches = []
        for face_match in response['FaceMatches']:
            match = {
                'face_id': face_match['Face']['FaceId'],
                'similarity': face_match['Similarity'] / 100.0,  # 转换为0-1范围
                'confidence': face_match['Face']['Confidence'],
                'external_image_id': face_match['Face'].get('ExternalImageId', ''),
                'bounding_box': face_match['Face']['BoundingBox']
            }
            matches.append(match)
        
        logger.info(f"Found {len(matches)} matches using Rekognition SearchFacesByImage")
        return matches
        
    except Exception as e:
        logger.error(f"Error searching by image: {e}")
        raise

def search_by_face_id(face_id: str, max_faces: int, similarity_threshold: float, collection_id: str) -> List[Dict[str, Any]]:
    """通过Face ID搜索相似面部"""
    try:
        # 使用Rekognition SearchFaces API
        response = rekognition.search_faces(
            CollectionId=REKOGNITION_COLLECTION_ID,
            FaceId=face_id,
            MaxFaces=max_faces,
            FaceMatchThreshold=similarity_threshold * 100  # Rekognition使用0-100的范围
        )
        
        matches = []
        
        # 首先添加查询的面部本身（100%相似度）
        try:
            face_response = rekognition.describe_collection(CollectionId=REKOGNITION_COLLECTION_ID)
            # 注意：Rekognition没有直接获取单个面部信息的API
            # 我们需要从DynamoDB获取面部信息
            face_metadata = get_face_metadata_from_dynamodb(face_id)
            if face_metadata:
                matches.append({
                    'face_id': face_id,
                    'similarity': 1.0,  # 自己和自己100%相似
                    'confidence': face_metadata.get('confidence', 99.0),
                    'external_image_id': face_metadata.get('external_image_id', ''),
                    'bounding_box': face_metadata.get('bounding_box', {})
                })
        except Exception as e:
            logger.warning(f"Could not add self-match for face_id {face_id}: {e}")
        
        # 添加其他匹配的面部
        for face_match in response['FaceMatches']:
            match = {
                'face_id': face_match['Face']['FaceId'],
                'similarity': face_match['Similarity'] / 100.0,  # 转换为0-1范围
                'confidence': face_match['Face']['Confidence'],
                'external_image_id': face_match['Face'].get('ExternalImageId', ''),
                'bounding_box': face_match['Face']['BoundingBox']
            }
            matches.append(match)
        
        logger.info(f"Found {len(matches)} matches using Rekognition SearchFaces")
        return matches
        
    except Exception as e:
        logger.error(f"Error searching by face ID: {e}")
        raise

def get_face_metadata_from_dynamodb(face_id: str) -> Dict[str, Any]:
    """从DynamoDB获取面部元数据"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 查询面部元数据（需要使用GSI或scan，因为face_id不是主键）
        response = table.scan(
            FilterExpression='face_id = :face_id',
            ExpressionAttributeValues={':face_id': face_id},
            Limit=1
        )
        
        if response['Items']:
            return response['Items'][0]
        return None
        
    except Exception as e:
        logger.error(f"Error getting face metadata from DynamoDB: {e}")
        return None

def enhance_search_results(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """增强搜索结果，添加详细的元数据信息"""
    enhanced_matches = []
    
    for match in matches:
        face_id = match['face_id']
        
        # 从DynamoDB获取详细元数据
        metadata = get_face_metadata_from_dynamodb(face_id)
        
        enhanced_match = {
            'face_id': face_id,
            'similarity': match['similarity'],
            'confidence': match['confidence'],
            'bounding_box': match['bounding_box']
        }
        
        if metadata:
            enhanced_match.update({
                'user_id': metadata.get('user_id', ''),
                'collection_id': metadata.get('collection_id', ''),
                'image_key': metadata.get('image_key', ''),
                'created_at': metadata.get('created_at', ''),
                'landmarks': metadata.get('landmarks', []),
                'pose': metadata.get('pose', {}),
                'quality': metadata.get('quality', {})
            })
        
        # 尝试从OpenSearch获取额外信息
        try:
            opensearch_data = get_opensearch_data(face_id)
            if opensearch_data:
                enhanced_match['opensearch_score'] = opensearch_data.get('_score', 0)
        except Exception as e:
            logger.warning(f"Could not get OpenSearch data for face_id {face_id}: {e}")
        
        enhanced_matches.append(enhanced_match)
    
    # 按相似度排序
    enhanced_matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    return enhanced_matches

def get_opensearch_data(face_id: str) -> Dict[str, Any]:
    """从OpenSearch获取面部数据"""
    try:
        client = get_opensearch_client()
        
        # 搜索所有索引中的face_id
        response = client.search(
            index='face-recognition-*',
            body={
                'query': {
                    'term': {
                        'face_id': face_id
                    }
                }
            }
        )
        
        if response['hits']['hits']:
            return response['hits']['hits'][0]
        return None
        
    except Exception as e:
        logger.error(f"Error getting OpenSearch data: {e}")
        return None

def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """成功响应"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'region': 'ap-southeast-1',
            **data
        })
    }

def error_response(error_message: str) -> Dict[str, Any]:
    """错误响应"""
    return {
        'statusCode': 500,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps({
            'success': False,
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
    }
