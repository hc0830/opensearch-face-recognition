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
            env=cdk.Environment(account="123456789012", region="us-east-1"),
        )
        template = Template.from_stack(stack)

        # Check that Elasticsearch domain is created (the stack uses deprecated elasticsearch module)
        # This will be migrated to OpenSearch in the future
        template.has_resource_properties(
            "AWS::Elasticsearch::Domain", {"ElasticsearchVersion": "7.10"}
        )

    def test_stack_has_vpc(self):
        """Test that stack creates VPC"""
        app = cdk.App()
        stack = OpenSearchFaceRecognitionStack(
            app,
            "TestStack",
            env=cdk.Environment(account="123456789012", region="us-east-1"),
        )
        template = Template.from_stack(stack)

        # Check that VPC is created
        template.has_resource_properties("AWS::EC2::VPC", {})


class TestBasicFunctionality:
    """Basic functionality tests"""

    def test_environment_variables_with_defaults(self):
        """Test environment variable handling with defaults"""
        import os

        # Test that we get default region when not set
        original_region = os.environ.get("CDK_DEFAULT_REGION")

        # Temporarily remove region environment variable
        if "CDK_DEFAULT_REGION" in os.environ:
            del os.environ["CDK_DEFAULT_REGION"]

        # Test default behavior
        from app import get_environment

        env = get_environment()

        assert env.region == "ap-southeast-1"  # Default region

        # Restore original value
        if original_region:
            os.environ["CDK_DEFAULT_REGION"] = original_region

    def test_environment_variables_with_values(self):
        """Test environment variable handling with set values"""
        import os

        # Set test values
        os.environ["CDK_DEFAULT_ACCOUNT"] = "123456789012"
        os.environ["CDK_DEFAULT_REGION"] = "us-west-2"

        from app import get_environment

        env = get_environment()

        assert env.account == "123456789012"
        assert env.region == "us-west-2"

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
