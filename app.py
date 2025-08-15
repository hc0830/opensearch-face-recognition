#!/usr/bin/env python3
"""
OpenSearch Face Recognition System CDK Application

This is the main entry point for the CDK application that deploys
the OpenSearch-based face recognition system.
"""

import os
from aws_cdk import App, Environment
from stacks.opensearch_face_recognition_stack import OpenSearchFaceRecognitionStack
from stacks.lambda_stack import LambdaStack
from stacks.api_gateway_stack import ApiGatewayStack
from stacks.monitoring_stack import MonitoringStack

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

    # Deploy OpenSearch stack (includes DynamoDB tables and S3 bucket)
    opensearch_stack = OpenSearchFaceRecognitionStack(
        app,
        f"{stack_prefix}-OpenSearch",
        env=env,
        description="OpenSearch cluster for face recognition system",
    )

    # Deploy Lambda functions stack
    lambda_stack = LambdaStack(
        app,
        f"{stack_prefix}-Lambda",
        opensearch_domain=opensearch_stack.opensearch_domain,
        face_metadata_table=opensearch_stack.face_metadata_table,
        user_vectors_table=opensearch_stack.user_vectors_table,
        images_bucket=opensearch_stack.images_bucket,
        env=env,
        description="Lambda functions for face recognition processing",
    )

    # Deploy API Gateway stack
    api_stack = ApiGatewayStack(
        app,
        f"{stack_prefix}-API",
        index_face_function=lambda_stack.index_face_function,
        search_faces_function=lambda_stack.search_faces_function,
        delete_face_function=lambda_stack.delete_face_function,
        env=env,
        description="API Gateway for face recognition REST API",
    )

    # Deploy monitoring stack
    monitoring_stack = MonitoringStack(
        app,
        f"{stack_prefix}-Monitoring",
        opensearch_domain=opensearch_stack.opensearch_domain,
        lambda_functions=lambda_stack.lambda_functions,
        api_gateway=api_stack.api,
        env=env,
        description="CloudWatch monitoring and alarms",
    )

    # Add dependencies
    lambda_stack.add_dependency(opensearch_stack)
    api_stack.add_dependency(lambda_stack)
    monitoring_stack.add_dependency(api_stack)

    # Add tags to all stacks
    for stack in [opensearch_stack, lambda_stack, api_stack, monitoring_stack]:
        stack.tags.set_tag("Project", "OpenSearchFaceRecognition")
        stack.tags.set_tag("Environment", environment)
        stack.tags.set_tag("ManagedBy", "CDK")

    app.synth()


if __name__ == "__main__":
    main()
