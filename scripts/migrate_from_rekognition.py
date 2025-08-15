#!/usr/bin/env python3
"""
Rekognition Collection to OpenSearch Migration Script

This script helps migrate existing Rekognition Collections to the new OpenSearch-based system.
"""

import boto3
import json
import argparse
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RekognitionMigrator:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.rekognition = boto3.client('rekognition', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
        # Get function name from environment or use default
        self.batch_function_name = os.getenv(
            'BATCH_FUNCTION_NAME', 
            'FaceRecognitionLambdaStack-BatchProcessFunction'
        )
    
    def list_collections(self) -> List[str]:
        """List all Rekognition collections"""
        try:
            response = self.rekognition.list_collections()
            collections = response['CollectionIds']
            logger.info(f"Found {len(collections)} collections: {collections}")
            return collections
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def get_collection_info(self, collection_id: str) -> Dict[str, Any]:
        """Get information about a collection"""
        try:
            # Get collection description
            desc_response = self.rekognition.describe_collection(CollectionId=collection_id)
            
            # Count faces
            faces_response = self.rekognition.list_faces(
                CollectionId=collection_id,
                MaxResults=1
            )
            
            # Get approximate face count (this is a limitation of the API)
            face_count = "Unknown (API limitation)"
            
            return {
                'collection_id': collection_id,
                'creation_timestamp': desc_response['CreationTimestamp'],
                'face_model_version': desc_response['FaceModelVersion'],
                'collection_arn': desc_response['CollectionARN'],
                'face_count': face_count
            }
        except Exception as e:
            logger.error(f"Error getting collection info for {collection_id}: {e}")
            return {}
    
    def migrate_collection(self, collection_id: str, target_collection_id: str = None) -> Dict[str, Any]:
        """Migrate a single collection"""
        if not target_collection_id:
            target_collection_id = f"{collection_id}-migrated"
        
        logger.info(f"Starting migration of collection: {collection_id}")
        
        try:
            # Call the batch processing Lambda function
            payload = {
                'body': json.dumps({
                    'operation': 'migrate_collection',
                    'source_collection_id': collection_id,
                    'target_collection_id': target_collection_id
                })
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.batch_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                body = json.loads(result['body'])
                if body['success']:
                    logger.info(f"Successfully migrated collection {collection_id}")
                    return body
                else:
                    logger.error(f"Migration failed for {collection_id}: {body.get('error')}")
                    return {'success': False, 'error': body.get('error')}
            else:
                logger.error(f"Lambda invocation failed: {result}")
                return {'success': False, 'error': 'Lambda invocation failed'}
                
        except Exception as e:
            logger.error(f"Error migrating collection {collection_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def migrate_all_collections(self, max_workers: int = 3) -> Dict[str, Any]:
        """Migrate all collections"""
        collections = self.list_collections()
        
        if not collections:
            logger.info("No collections found to migrate")
            return {'success': True, 'collections': {}}
        
        results = {}
        
        logger.info(f"Starting migration of {len(collections)} collections")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit migration tasks
            futures = {
                executor.submit(self.migrate_collection, cid): cid 
                for cid in collections
            }
            
            # Process results with progress bar
            with tqdm(total=len(futures), desc="Migrating collections") as pbar:
                for future in as_completed(futures):
                    collection_id = futures[future]
                    try:
                        result = future.result()
                        results[collection_id] = result
                        
                        if result.get('success'):
                            pbar.set_postfix({
                                'current': collection_id,
                                'status': 'SUCCESS'
                            })
                        else:
                            pbar.set_postfix({
                                'current': collection_id,
                                'status': 'FAILED'
                            })
                    except Exception as e:
                        results[collection_id] = {'success': False, 'error': str(e)}
                        pbar.set_postfix({
                            'current': collection_id,
                            'status': 'ERROR'
                        })
                    
                    pbar.update(1)
        
        # Summary
        successful = sum(1 for r in results.values() if r.get('success'))
        failed = len(results) - successful
        
        logger.info(f"Migration completed: {successful} successful, {failed} failed")
        
        return {
            'success': True,
            'summary': {
                'total': len(collections),
                'successful': successful,
                'failed': failed
            },
            'collections': results
        }
    
    def validate_migration(self, collection_id: str) -> Dict[str, Any]:
        """Validate that migration was successful"""
        # This would involve checking OpenSearch for the migrated data
        # For now, return a placeholder
        return {
            'collection_id': collection_id,
            'validation_status': 'not_implemented',
            'message': 'Validation not yet implemented'
        }

def main():
    parser = argparse.ArgumentParser(description='Migrate Rekognition Collections to OpenSearch')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--collection-id', help='Specific collection to migrate')
    parser.add_argument('--target-collection-id', help='Target collection ID for migration')
    parser.add_argument('--list-only', action='store_true', help='Only list collections, do not migrate')
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of worker threads')
    parser.add_argument('--batch-function-name', help='Name of the batch processing Lambda function')
    
    args = parser.parse_args()
    
    # Set batch function name if provided
    if args.batch_function_name:
        os.environ['BATCH_FUNCTION_NAME'] = args.batch_function_name
    
    migrator = RekognitionMigrator(region=args.region)
    
    if args.list_only:
        # List collections and their info
        collections = migrator.list_collections()
        
        if not collections:
            print("No collections found.")
            return
        
        print(f"\nFound {len(collections)} collections:\n")
        
        for collection_id in collections:
            info = migrator.get_collection_info(collection_id)
            if info:
                print(f"Collection: {collection_id}")
                print(f"  Created: {info.get('creation_timestamp')}")
                print(f"  Face Model Version: {info.get('face_model_version')}")
                print(f"  ARN: {info.get('collection_arn')}")
                print(f"  Face Count: {info.get('face_count')}")
                print()
    
    elif args.collection_id:
        # Migrate specific collection
        result = migrator.migrate_collection(
            args.collection_id, 
            args.target_collection_id
        )
        
        if result.get('success'):
            print(f"✅ Successfully migrated collection: {args.collection_id}")
            print(f"   Migrated: {result.get('migrated', 0)} faces")
            print(f"   Failed: {result.get('failed', 0)} faces")
            print(f"   Processing time: {result.get('processing_time', 0):.2f} seconds")
        else:
            print(f"❌ Failed to migrate collection: {args.collection_id}")
            print(f"   Error: {result.get('error')}")
    
    else:
        # Migrate all collections
        print("Starting migration of all collections...")
        results = migrator.migrate_all_collections(max_workers=args.max_workers)
        
        if results.get('success'):
            summary = results['summary']
            print(f"\n✅ Migration completed!")
            print(f"   Total collections: {summary['total']}")
            print(f"   Successful: {summary['successful']}")
            print(f"   Failed: {summary['failed']}")
            
            # Show detailed results
            print(f"\nDetailed results:")
            for collection_id, result in results['collections'].items():
                status = "✅" if result.get('success') else "❌"
                print(f"  {status} {collection_id}")
                if result.get('success'):
                    print(f"      Migrated: {result.get('migrated', 0)} faces")
                    print(f"      Failed: {result.get('failed', 0)} faces")
                else:
                    print(f"      Error: {result.get('error')}")
        else:
            print("❌ Migration failed")

if __name__ == '__main__':
    main()
