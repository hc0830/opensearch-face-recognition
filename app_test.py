#!/usr/bin/env python3
"""
Simplified CDK Application for Testing

This version skips Docker-dependent components for CI testing.
"""

import os
from aws_cdk import App, Environment
from stacks.opensearch_face_recognition_stack import OpenSearchFaceRecognitionStack

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


def get_environment():
    """Get the CDK environment configuration."""
    return Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "ap-southeast-1"),
    )


def main():
    """Main function to create and deploy the CDK stacks."""
    app = App()

    # Get environment configuration
    env = get_environment()
    environment = os.getenv("ENVIRONMENT", "dev")

    # Create stack name prefix
    stack_prefix = f"OpenSearchFaceRecognition-{environment.title()}"

    # Deploy only OpenSearch stack for testing (no Lambda layers that need Docker)
    opensearch_stack = OpenSearchFaceRecognitionStack(
        app,
        f"{stack_prefix}-OpenSearch",
        env=env,
        description="OpenSearch cluster for face recognition system",
    )

    # Add tags
    opensearch_stack.tags.set_tag("Project", "OpenSearchFaceRecognition")
    opensearch_stack.tags.set_tag("Environment", environment)
    opensearch_stack.tags.set_tag("ManagedBy", "CDK")

    app.synth()


if __name__ == "__main__":
    main()
