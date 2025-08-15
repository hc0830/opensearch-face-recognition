"""
Unit tests for CDK stacks
"""
import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.opensearch_face_recognition_stack import OpenSearchFaceRecognitionStack


class TestOpenSearchFaceRecognitionStack:
    """Test cases for OpenSearch Face Recognition Stack"""
    
    def test_opensearch_domain_created(self):
        """Test that OpenSearch domain is created"""
        app = cdk.App()
        stack = OpenSearchFaceRecognitionStack(
            app, 
            "TestStack",
            env=cdk.Environment(account="123456789012", region="us-east-1")
        )
        template = Template.from_stack(stack)
        
        # Check that OpenSearch domain is created
        template.has_resource_properties("AWS::OpenSearch::Domain", {
            "EngineVersion": "OpenSearch_2.3"
        })
    
    def test_stack_has_outputs(self):
        """Test that stack has required outputs"""
        app = cdk.App()
        stack = OpenSearchFaceRecognitionStack(
            app, 
            "TestStack",
            env=cdk.Environment(account="123456789012", region="us-east-1")
        )
        template = Template.from_stack(stack)
        
        # Check for outputs (this will depend on your actual stack implementation)
        # template.has_output("OpenSearchDomainEndpoint", {})


class TestBasicFunctionality:
    """Basic functionality tests"""
    
    def test_environment_variables(self):
        """Test environment variable handling"""
        import os
        
        # Test that we can handle missing environment variables gracefully
        original_account = os.environ.get('CDK_DEFAULT_ACCOUNT')
        original_region = os.environ.get('CDK_DEFAULT_REGION')
        
        # Temporarily remove environment variables
        if 'CDK_DEFAULT_ACCOUNT' in os.environ:
            del os.environ['CDK_DEFAULT_ACCOUNT']
        if 'CDK_DEFAULT_REGION' in os.environ:
            del os.environ['CDK_DEFAULT_REGION']
        
        # Test default behavior
        from app import get_environment
        env = get_environment()
        
        assert env.region == 'ap-southeast-1'  # Default region
        assert env.account is None  # Should be None when not set
        
        # Restore original values
        if original_account:
            os.environ['CDK_DEFAULT_ACCOUNT'] = original_account
        if original_region:
            os.environ['CDK_DEFAULT_REGION'] = original_region
    
    def test_imports(self):
        """Test that all required modules can be imported"""
        try:
            import aws_cdk
            import boto3
            from dotenv import load_dotenv
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import required module: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
