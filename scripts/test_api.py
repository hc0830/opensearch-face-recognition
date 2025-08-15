#!/usr/bin/env python3
"""
API Testing Script for OpenSearch Face Recognition System

This script provides comprehensive testing of the deployed API endpoints.
"""

import requests
import base64
import json
import argparse
import time
from typing import Dict, Any, Optional
import os
from pathlib import Path

class FaceRecognitionAPITester:
    def __init__(self, api_url: str, timeout: int = 30):
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'FaceRecognitionAPITester/1.0'
        })
    
    def encode_image(self, image_path: str) -> str:
        """Encode image file to base64"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to encode image {image_path}: {e}")
    
    def test_health_check(self) -> Dict[str, Any]:
        """Test the health check endpoint"""
        print("🔍 Testing health check endpoint...")
        
        try:
            response = self.session.get(
                f"{self.api_url}/health",
                timeout=self.timeout
            )
            
            result = {
                'endpoint': '/health',
                'method': 'GET',
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
            
            if result['success']:
                print("✅ Health check passed")
            else:
                print(f"❌ Health check failed: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {
                'endpoint': '/health',
                'method': 'GET',
                'success': False,
                'error': str(e)
            }
    
    def test_index_face(self, image_path: str, user_id: str, collection_id: str = 'test') -> Dict[str, Any]:
        """Test face indexing endpoint"""
        print(f"🔍 Testing face indexing with image: {image_path}")
        
        try:
            # Encode image
            image_base64 = self.encode_image(image_path)
            
            # Prepare request
            payload = {
                'image': image_base64,
                'user_id': user_id,
                'collection_id': collection_id,
                'external_image_id': f"test-{int(time.time())}"
            }
            
            # Make request
            response = self.session.post(
                f"{self.api_url}/faces",
                json=payload,
                timeout=self.timeout
            )
            
            result = {
                'endpoint': '/faces',
                'method': 'POST',
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'payload_size': len(json.dumps(payload)),
                'user_id': user_id,
                'collection_id': collection_id
            }
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                result['response'] = response_data
                
                if result['success'] and response_data.get('success'):
                    result['face_id'] = response_data.get('face_id')
                    print(f"✅ Face indexed successfully: {result['face_id']}")
                else:
                    print(f"❌ Face indexing failed: {response_data.get('error', 'Unknown error')}")
            else:
                result['response'] = response.text
                print(f"❌ Face indexing failed: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Face indexing error: {e}")
            return {
                'endpoint': '/faces',
                'method': 'POST',
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'collection_id': collection_id
            }
    
    def test_search_by_image(self, image_path: str, collection_id: str = 'test', 
                           max_faces: int = 10, similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """Test face search by image endpoint"""
        print(f"🔍 Testing face search by image: {image_path}")
        
        try:
            # Encode image
            image_base64 = self.encode_image(image_path)
            
            # Prepare request
            payload = {
                'search_type': 'by_image',
                'image': image_base64,
                'collection_id': collection_id,
                'max_faces': max_faces,
                'similarity_threshold': similarity_threshold
            }
            
            # Make request
            response = self.session.post(
                f"{self.api_url}/search",
                json=payload,
                timeout=self.timeout
            )
            
            result = {
                'endpoint': '/search',
                'method': 'POST',
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'search_type': 'by_image',
                'collection_id': collection_id
            }
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                result['response'] = response_data
                
                if result['success'] and response_data.get('success'):
                    matches = response_data.get('matches', [])
                    result['match_count'] = len(matches)
                    print(f"✅ Search completed: {len(matches)} matches found")
                    
                    # Show top matches
                    for i, match in enumerate(matches[:3]):
                        print(f"   Match {i+1}: User {match.get('user_id')}, Similarity: {match.get('similarity', 0):.3f}")
                else:
                    print(f"❌ Search failed: {response_data.get('error', 'Unknown error')}")
            else:
                result['response'] = response.text
                print(f"❌ Search failed: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {
                'endpoint': '/search',
                'method': 'POST',
                'success': False,
                'error': str(e),
                'search_type': 'by_image',
                'collection_id': collection_id
            }
    
    def test_search_by_face_id(self, face_id: str, collection_id: str = 'test',
                              max_faces: int = 10, similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """Test face search by face ID endpoint"""
        print(f"🔍 Testing face search by face ID: {face_id}")
        
        try:
            # Prepare request
            payload = {
                'search_type': 'by_face_id',
                'face_id': face_id,
                'collection_id': collection_id,
                'max_faces': max_faces,
                'similarity_threshold': similarity_threshold
            }
            
            # Make request
            response = self.session.post(
                f"{self.api_url}/search",
                json=payload,
                timeout=self.timeout
            )
            
            result = {
                'endpoint': '/search',
                'method': 'POST',
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'search_type': 'by_face_id',
                'face_id': face_id,
                'collection_id': collection_id
            }
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                result['response'] = response_data
                
                if result['success'] and response_data.get('success'):
                    matches = response_data.get('matches', [])
                    result['match_count'] = len(matches)
                    print(f"✅ Search completed: {len(matches)} matches found")
                else:
                    print(f"❌ Search failed: {response_data.get('error', 'Unknown error')}")
            else:
                result['response'] = response.text
                print(f"❌ Search failed: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {
                'endpoint': '/search',
                'method': 'POST',
                'success': False,
                'error': str(e),
                'search_type': 'by_face_id',
                'face_id': face_id,
                'collection_id': collection_id
            }
    
    def test_delete_face(self, face_id: str) -> Dict[str, Any]:
        """Test face deletion endpoint"""
        print(f"🔍 Testing face deletion: {face_id}")
        
        try:
            # Make request
            response = self.session.delete(
                f"{self.api_url}/faces/{face_id}",
                timeout=self.timeout
            )
            
            result = {
                'endpoint': f'/faces/{face_id}',
                'method': 'DELETE',
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_time': response.elapsed.total_seconds(),
                'face_id': face_id
            }
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                result['response'] = response_data
                
                if result['success'] and response_data.get('success'):
                    print(f"✅ Face deleted successfully")
                else:
                    print(f"❌ Face deletion failed: {response_data.get('error', 'Unknown error')}")
            else:
                result['response'] = response.text
                print(f"❌ Face deletion failed: {response.status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ Face deletion error: {e}")
            return {
                'endpoint': f'/faces/{face_id}',
                'method': 'DELETE',
                'success': False,
                'error': str(e),
                'face_id': face_id
            }
    
    def run_comprehensive_test(self, test_images_dir: str) -> Dict[str, Any]:
        """Run comprehensive API tests"""
        print("🚀 Starting comprehensive API tests...")
        print("=" * 50)
        
        results = {
            'start_time': time.time(),
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0
            }
        }
        
        # Test 1: Health check
        health_result = self.test_health_check()
        results['tests'].append(health_result)
        
        # Find test images
        test_images = []
        if os.path.exists(test_images_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                test_images.extend(Path(test_images_dir).glob(ext))
        
        if not test_images:
            print(f"⚠️  No test images found in {test_images_dir}")
            print("   Creating sample test data...")
            # You could generate or download sample images here
        
        indexed_faces = []
        
        # Test 2: Index faces
        for i, image_path in enumerate(test_images[:3]):  # Test with first 3 images
            user_id = f"test_user_{i+1}"
            index_result = self.test_index_face(str(image_path), user_id)
            results['tests'].append(index_result)
            
            if index_result.get('success') and index_result.get('face_id'):
                indexed_faces.append(index_result['face_id'])
        
        # Test 3: Search by image
        if test_images:
            search_result = self.test_search_by_image(str(test_images[0]))
            results['tests'].append(search_result)
        
        # Test 4: Search by face ID
        if indexed_faces:
            search_by_id_result = self.test_search_by_face_id(indexed_faces[0])
            results['tests'].append(search_by_id_result)
        
        # Test 5: Delete face
        if indexed_faces:
            delete_result = self.test_delete_face(indexed_faces[-1])
            results['tests'].append(delete_result)
        
        # Calculate summary
        results['end_time'] = time.time()
        results['total_time'] = results['end_time'] - results['start_time']
        
        for test in results['tests']:
            results['summary']['total'] += 1
            if test.get('success'):
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        print(f"Total tests: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']} ✅")
        print(f"Failed: {results['summary']['failed']} ❌")
        print(f"Success rate: {(results['summary']['passed'] / results['summary']['total'] * 100):.1f}%")
        print(f"Total time: {results['total_time']:.2f} seconds")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Test Face Recognition API')
    parser.add_argument('--api-url', required=True, help='API Gateway URL')
    parser.add_argument('--test-images-dir', default='test_images', help='Directory containing test images')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file for test results (JSON)')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = FaceRecognitionAPITester(args.api_url, args.timeout)
    
    # Run tests
    results = tester.run_comprehensive_test(args.test_images_dir)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        exit(1)
    else:
        exit(0)

if __name__ == '__main__':
    main()
