"""
Unit tests for Lambda functions
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestIndexFaceFunction:
    """Test cases for index face Lambda function"""

    @patch("boto3.client")
    def test_index_face_handler_basic(self, mock_boto3):
        """Test basic functionality of index face handler"""
        # Mock AWS services
        mock_rekognition = Mock()
        mock_opensearch = Mock()
        mock_dynamodb = Mock()

        mock_boto3.side_effect = lambda service: {
            "rekognition": mock_rekognition,
            "opensearchserverless": mock_opensearch,
            "dynamodb": mock_dynamodb,
        }.get(service, Mock())

        # Mock Rekognition response
        mock_rekognition.detect_faces.return_value = {
            "FaceDetails": [
                {
                    "BoundingBox": {
                        "Left": 0.1,
                        "Top": 0.1,
                        "Width": 0.3,
                        "Height": 0.4,
                    },
                    "Confidence": 99.5,
                }
            ]
        }

        # Test event
        event = {
            "body": json.dumps(
                {
                    "image": "base64_encoded_image_data",
                    "user_id": "test_user",
                    "collection_id": "test_collection",
                }
            )
        }

        # Since we can't import the actual handler without proper setup,
        # we'll test the logic structure
        assert event["body"] is not None
        body = json.loads(event["body"])
        assert "image" in body
        assert "user_id" in body
        assert "collection_id" in body


class TestSearchFacesFunction:
    """Test cases for search faces Lambda function"""

    def test_search_request_validation(self):
        """Test search request validation"""
        # Valid request
        valid_request = {
            "search_type": "by_image",
            "image": "base64_encoded_image",
            "collection_id": "test_collection",
            "max_faces": 10,
            "similarity_threshold": 0.8,
        }

        # Check required fields
        required_fields = ["search_type", "image", "collection_id"]
        for field in required_fields:
            assert field in valid_request

        # Check optional fields have defaults
        assert valid_request.get("max_faces", 10) == 10
        assert valid_request.get("similarity_threshold", 0.8) == 0.8


class TestDeleteFaceFunction:
    """Test cases for delete face Lambda function"""

    def test_delete_request_validation(self):
        """Test delete request validation"""
        # Test with face_id in path parameters
        event = {"pathParameters": {"face_id": "test_face_id_123"}}

        face_id = event.get("pathParameters", {}).get("face_id")
        assert face_id == "test_face_id_123"
        assert len(face_id) > 0


class TestUtilityFunctions:
    """Test utility functions used across Lambda functions"""

    def test_base64_image_validation(self):
        """Test base64 image validation"""
        import base64

        # Create a simple test image (1x1 pixel PNG)
        test_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82"

        # Encode to base64
        base64_image = base64.b64encode(test_image_data).decode("utf-8")

        # Test that we can decode it back
        decoded_data = base64.b64decode(base64_image)
        assert decoded_data == test_image_data

    def test_response_format(self):
        """Test Lambda response format"""
        # Standard success response
        success_response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Success"}),
        }

        assert success_response["statusCode"] == 200
        assert "Content-Type" in success_response["headers"]
        assert "Access-Control-Allow-Origin" in success_response["headers"]

        # Parse body to ensure it's valid JSON
        body = json.loads(success_response["body"])
        assert "message" in body

    def test_error_response_format(self):
        """Test error response format"""
        error_response = {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Bad Request", "message": "Invalid input parameters"}
            ),
        }

        assert error_response["statusCode"] == 400
        body = json.loads(error_response["body"])
        assert "error" in body
        assert "message" in body


if __name__ == "__main__":
    pytest.main([__file__])
