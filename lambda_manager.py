#!/usr/bin/env python3
"""
Lambda 函数管理器
整合所有 Lambda 函数的创建、更新和管理功能
"""

import os
import json
import zipfile
import io
import boto3
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class LambdaManager:
    """Lambda 函数管理器"""
    
    def __init__(self, region: str = 'ap-southeast-1'):
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
    
    def create_lambda_zip(self, code: str, handler_name: str = 'lambda_function.py') -> bytes:
        """创建 Lambda 部署包"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(handler_name, code)
        
        return zip_buffer.getvalue()
    
    def get_opensearch_index_lambda_code(self) -> str:
        """获取 OpenSearch 索引 Lambda 函数代码"""
        return '''
import json
import boto3
import base64
import os
import re
import uuid
from datetime import datetime
import logging
import requests
from requests_aws4auth import AWS4Auth
import numpy as np

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 环境变量
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
FACE_METADATA_TABLE = os.environ.get('FACE_METADATA_TABLE', 'face-recognition-face-metadata-dev')
IMAGES_BUCKET = os.environ.get('IMAGES_BUCKET', 'face-recognition-images-dev-010438470467')
OPENSEARCH_INDEX = os.environ.get('OPENSEARCH_INDEX', 'face-vectors')

# 初始化AWS客户端
rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def get_opensearch_auth():
    """获取OpenSearch认证"""
    region = 'ap-southeast-1'
    service = 'es'
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token
    )

def lambda_handler(event, context):
    """Lambda 处理函数"""
    try:
        logger.info(f"收到事件: {json.dumps(event)}")
        
        # 解析请求
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # 处理面部索引请求
        if 'image' in body:
            result = index_face(body)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result, ensure_ascii=False)
            }
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': '缺少图像数据'}, ensure_ascii=False)
            }
    
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }

def index_face(data):
    """索引面部"""
    try:
        # 解码图像
        image_data = base64.b64decode(data['image'])
        user_id = data.get('user_id', str(uuid.uuid4()))
        collection_id = data.get('collection_id', 'default')
        metadata = data.get('metadata', {})
        
        # 使用 Rekognition 检测面部
        response = rekognition.detect_faces(
            Image={'Bytes': image_data},
            Attributes=['ALL']
        )
        
        if not response['FaceDetails']:
            return {'error': '未检测到面部'}
        
        # 提取面部特征
        face_response = rekognition.search_faces_by_image(
            CollectionId='face-recognition-collection',
            Image={'Bytes': image_data},
            MaxFaces=1,
            FaceMatchThreshold=80
        )
        
        # 生成面部ID
        face_id = str(uuid.uuid4())
        
        # 保存到 DynamoDB
        table = dynamodb.Table(FACE_METADATA_TABLE)
        table.put_item(
            Item={
                'face_id': face_id,
                'user_id': user_id,
                'collection_id': collection_id,
                'metadata': metadata,
                'created_at': datetime.now().isoformat(),
                'confidence': response['FaceDetails'][0]['Confidence']
            }
        )
        
        # 保存图像到 S3
        s3_key = f"faces/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{face_id[:8]}.jpg"
        s3.put_object(
            Bucket=IMAGES_BUCKET,
            Key=s3_key,
            Body=image_data,
            ContentType='image/jpeg'
        )
        
        return {
            'face_id': face_id,
            'user_id': user_id,
            'collection_id': collection_id,
            's3_key': s3_key,
            'confidence': response['FaceDetails'][0]['Confidence']
        }
        
    except Exception as e:
        logger.error(f"索引面部时出错: {str(e)}")
        raise e
'''
    
    def get_opensearch_search_lambda_code(self) -> str:
        """获取 OpenSearch 搜索 Lambda 函数代码"""
        return '''
import json
import boto3
import base64
import os
import logging
import requests
from requests_aws4auth import AWS4Auth

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 环境变量
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
FACE_METADATA_TABLE = os.environ.get('FACE_METADATA_TABLE', 'face-recognition-face-metadata-dev')
OPENSEARCH_INDEX = os.environ.get('OPENSEARCH_INDEX', 'face-vectors')

# 初始化AWS客户端
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

def get_opensearch_auth():
    """获取OpenSearch认证"""
    region = 'ap-southeast-1'
    service = 'es'
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token
    )

def lambda_handler(event, context):
    """Lambda 处理函数"""
    try:
        logger.info(f"收到搜索请求: {json.dumps(event)}")
        
        # 解析请求
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # 处理面部搜索请求
        if 'image' in body or 'search_type' in body:
            result = search_faces(body)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result, ensure_ascii=False)
            }
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': '缺少搜索参数'}, ensure_ascii=False)
            }
    
    except Exception as e:
        logger.error(f"处理搜索请求时出错: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }

def search_faces(data):
    """搜索面部"""
    try:
        search_type = data.get('search_type', 'by_image')
        collection_id = data.get('collection_id', 'default')
        max_faces = data.get('max_faces', 10)
        similarity_threshold = data.get('similarity_threshold', 0.8)
        
        if search_type == 'by_image' and 'image' in data:
            # 通过图像搜索
            image_data = base64.b64decode(data['image'])
            
            # 使用 Rekognition 搜索相似面部
            response = rekognition.search_faces_by_image(
                CollectionId='face-recognition-collection',
                Image={'Bytes': image_data},
                MaxFaces=max_faces,
                FaceMatchThreshold=similarity_threshold * 100
            )
            
            # 获取匹配的面部详细信息
            matches = []
            table = dynamodb.Table(FACE_METADATA_TABLE)
            
            for match in response.get('FaceMatches', []):
                face_id = match['Face']['FaceId']
                similarity = match['Similarity'] / 100.0
                
                # 从 DynamoDB 获取元数据
                try:
                    db_response = table.get_item(Key={'face_id': face_id})
                    if 'Item' in db_response:
                        item = db_response['Item']
                        matches.append({
                            'face_id': face_id,
                            'user_id': item.get('user_id'),
                            'similarity': similarity,
                            'metadata': item.get('metadata', {}),
                            'created_at': item.get('created_at')
                        })
                except Exception as e:
                    logger.warning(f"无法获取面部 {face_id} 的元数据: {str(e)}")
            
            return {
                'search_type': search_type,
                'collection_id': collection_id,
                'matches': matches,
                'total_matches': len(matches)
            }
        
        else:
            return {'error': '不支持的搜索类型或缺少参数'}
        
    except Exception as e:
        logger.error(f"搜索面部时出错: {str(e)}")
        raise e
'''
    
    def get_health_check_lambda_code(self) -> str:
        """获取健康检查 Lambda 函数代码"""
        return '''
import json
import boto3
import os
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 环境变量
FACE_METADATA_TABLE = os.environ.get('FACE_METADATA_TABLE', 'face-recognition-face-metadata-dev')
REKOGNITION_COLLECTION_ID = os.environ.get('REKOGNITION_COLLECTION_ID', 'face-recognition-collection')

# 初始化AWS客户端
dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')

def lambda_handler(event, context):
    """Lambda 处理函数"""
    try:
        health_status = check_system_health()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(health_status, ensure_ascii=False)
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False)
        }

def check_system_health():
    """检查系统健康状态"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }
    
    # 检查 DynamoDB
    try:
        table = dynamodb.Table(FACE_METADATA_TABLE)
        table.load()
        health_status['services']['dynamodb'] = {
            'status': 'healthy',
            'table_name': FACE_METADATA_TABLE
        }
    except Exception as e:
        health_status['services']['dynamodb'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # 检查 Rekognition
    try:
        collections = rekognition.list_collections()
        if REKOGNITION_COLLECTION_ID in collections['CollectionIds']:
            health_status['services']['rekognition'] = {
                'status': 'healthy',
                'collection_id': REKOGNITION_COLLECTION_ID
            }
        else:
            health_status['services']['rekognition'] = {
                'status': 'warning',
                'message': 'Collection not found'
            }
    except Exception as e:
        health_status['services']['rekognition'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    return health_status
'''
    
    def deploy_lambda_function(self, function_name: str, code: str, 
                             environment_vars: Dict[str, str] = None,
                             role_arn: str = None) -> bool:
        """部署 Lambda 函数"""
        try:
            # 创建部署包
            zip_data = self.create_lambda_zip(code)
            
            # 默认环境变量
            if environment_vars is None:
                environment_vars = {}
            
            # 默认角色 ARN
            if role_arn is None:
                role_arn = f"arn:aws:iam::{self.account_id}:role/FaceRecognitionLambdaRole"
            
            # 检查函数是否存在
            try:
                self.lambda_client.get_function(FunctionName=function_name)
                # 函数存在，更新代码
                logger.info(f"更新 Lambda 函数: {function_name}")
                self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_data
                )
                
                # 更新环境变量
                if environment_vars:
                    self.lambda_client.update_function_configuration(
                        FunctionName=function_name,
                        Environment={'Variables': environment_vars}
                    )
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                # 函数不存在，创建新函数
                logger.info(f"创建 Lambda 函数: {function_name}")
                self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_data},
                    Environment={'Variables': environment_vars},
                    Timeout=300,
                    MemorySize=1024
                )
            
            logger.info(f"✅ Lambda 函数 {function_name} 部署成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 部署 Lambda 函数 {function_name} 失败: {str(e)}")
            return False
    
    def deploy_all_functions(self, environment: str = 'dev') -> bool:
        """部署所有 Lambda 函数"""
        logger.info("🚀 开始部署所有 Lambda 函数")
        
        account_id = self.account_id
        
        # 环境变量配置
        common_env_vars = {
            'FACE_METADATA_TABLE': f'face-recognition-face-metadata-{environment}',
            'USER_VECTORS_TABLE': f'face-recognition-user-vectors-{environment}',
            'IMAGES_BUCKET': f'face-recognition-images-{environment}-{account_id}',
            'OPENSEARCH_INDEX': 'face-vectors',
            'REKOGNITION_COLLECTION_ID': 'face-recognition-collection'
        }
        
        # 函数配置
        functions = [
            {
                'name': 'face-recognition-index',
                'code': self.get_opensearch_index_lambda_code(),
                'env_vars': {
                    **common_env_vars,
                    'OPENSEARCH_ENDPOINT': 'https://search-face-recognition-search-6jnoypgqjbpemnuakjuauffrqi.ap-southeast-1.es.amazonaws.com'
                }
            },
            {
                'name': 'face-recognition-search',
                'code': self.get_opensearch_search_lambda_code(),
                'env_vars': {
                    **common_env_vars,
                    'OPENSEARCH_ENDPOINT': 'https://search-face-recognition-search-6jnoypgqjbpemnuakjuauffrqi.ap-southeast-1.es.amazonaws.com'
                }
            },
            {
                'name': 'face-recognition-health',
                'code': self.get_health_check_lambda_code(),
                'env_vars': common_env_vars
            }
        ]
        
        success_count = 0
        for func_config in functions:
            if self.deploy_lambda_function(
                func_config['name'],
                func_config['code'],
                func_config['env_vars']
            ):
                success_count += 1
        
        logger.info(f"📊 部署结果: {success_count}/{len(functions)} 个函数成功")
        return success_count == len(functions)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lambda 函数管理器')
    parser.add_argument('--region', default='ap-southeast-1', help='AWS区域')
    parser.add_argument('--environment', default='dev', help='环境')
    parser.add_argument('--action', choices=['deploy'], default='deploy', help='操作')
    
    args = parser.parse_args()
    
    manager = LambdaManager(region=args.region)
    
    if args.action == 'deploy':
        success = manager.deploy_all_functions(environment=args.environment)
        exit(0 if success else 1)

if __name__ == '__main__':
    main()
