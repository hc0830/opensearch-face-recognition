import json
import boto3
import os
from typing import Dict, Any
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
dynamodb = boto3.resource('dynamodb')

# 环境变量
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
FACE_METADATA_TABLE = os.environ['FACE_METADATA_TABLE']
USER_VECTORS_TABLE = os.environ['USER_VECTORS_TABLE']

def lambda_handler(event, context):
    """Lambda处理函数：删除面部"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 从路径参数获取face_id
        face_id = event.get('pathParameters', {}).get('face_id')
        
        if not face_id:
            return create_error_response(400, 'Missing face_id in path parameters')
        
        # 删除面部
        result = delete_face(face_id)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
        else:
            return create_error_response(404, result['error'])
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, str(e))

def delete_face(face_id: str) -> Dict[str, Any]:
    """删除面部数据"""
    try:
        # 首先从DynamoDB获取面部元数据
        face_metadata = get_face_metadata(face_id)
        if not face_metadata:
            return {
                'success': False,
                'error': f'Face not found: {face_id}'
            }
        
        # 从OpenSearch删除
        delete_from_opensearch(face_id)
        
        # 从DynamoDB删除元数据
        delete_face_metadata(face_id, face_metadata['collection_id'])
        
        logger.info(f"Successfully deleted face: {face_id}")
        
        return {
            'success': True,
            'face_id': face_id,
            'message': 'Face deleted successfully'
        }
        
    except Exception as e:
        logger.error(f"Error deleting face {face_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_face_metadata(face_id: str) -> Dict[str, Any]:
    """从DynamoDB获取面部元数据"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 由于我们只有face_id，需要扫描表来找到对应的记录
        # 在生产环境中，建议添加GSI来优化这个查询
        response = table.scan(
            FilterExpression='face_id = :face_id',
            ExpressionAttributeValues={':face_id': face_id},
            Limit=1
        )
        
        if response['Items']:
            return response['Items'][0]
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error getting face metadata: {str(e)}")
        return None

def delete_from_opensearch(face_id: str):
    """从OpenSearch删除面部向量"""
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
        
        # 删除文档
        response = client.delete(
            index='face-vectors',
            id=face_id,
            refresh=True
        )
        
        logger.info(f"Deleted from OpenSearch: {response}")
        
    except Exception as e:
        logger.error(f"Error deleting from OpenSearch: {str(e)}")
        raise

def delete_face_metadata(face_id: str, collection_id: str):
    """从DynamoDB删除面部元数据"""
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        
        # 删除项目
        response = table.delete_item(
            Key={
                'face_id': face_id,
                'collection_id': collection_id
            }
        )
        
        logger.info(f"Deleted metadata for face: {face_id}")
        
    except Exception as e:
        logger.error(f"Error deleting face metadata: {str(e)}")
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
