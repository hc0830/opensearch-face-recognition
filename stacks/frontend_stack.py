import os
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
    CfnOutput,
    CustomResource,
)
from constructs import Construct


class FrontendStack(Stack):
    """
    CDK Stack for Face Recognition Frontend

    This stack creates:
    - S3 bucket for hosting static frontend files
    - CloudFront distribution with Origin Access Control (OAC)
    - S3 deployment for frontend files
    - Proper security configurations
    """

    def __init__(
        self, scope: Construct, construct_id: str, api_gateway_url: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get account ID for unique bucket naming
        account_id = self.account

        # Create S3 bucket for frontend hosting
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"face-recognition-frontend-{account_id}",
            # Security: Block all public access
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # Lifecycle: Remove bucket when stack is deleted
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # Performance: Enable versioning for better caching
            versioned=True,
            # Security: Enable server-side encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Compliance: Enable access logging
            server_access_logs_prefix="access-logs/",
        )

        # Create Origin Access Control (OAC) for secure CloudFront -> S3 access
        oac = cloudfront.CfnOriginAccessControl(
            self,
            "FrontendOAC",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="FaceRecognitionFrontendOAC",
                description="OAC for Face Recognition Frontend S3 bucket",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
            ),
        )

        # Create CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            comment="Face Recognition Frontend Distribution - Secure with OAC",
            default_root_object="index.html",
            # Origin configuration
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(bucket=self.frontend_bucket),
                # Security: Force HTTPS
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                # Performance: Enable compression
                compress=True,
                # Caching: Optimize for static content
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                # Security: Modern TLS only
                origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                # Methods: Only GET and HEAD for static content
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            # Security: Modern protocols and TLS
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            # Performance: Global edge locations
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            # Features: Enable IPv6
            enable_ipv6=True,
            # Error handling: Custom error responses
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
                ),
            ],
        )

        # Grant CloudFront access to S3 bucket
        self.frontend_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipalReadOnly",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.frontend_bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"
                    }
                },
            )
        )

        # Create frontend assets directory if it doesn't exist
        frontend_assets_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

        # Deploy frontend files to S3
        self.deployment = s3deploy.BucketDeployment(
            self,
            "FrontendDeployment",
            sources=[
                # Deploy the frontend_test.html as index.html
                s3deploy.Source.asset(
                    os.path.dirname(__file__) + "/..",
                    exclude=["*", "!frontend_test.html"],
                )
            ],
            destination_bucket=self.frontend_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
            # Transform frontend_test.html to index.html during deployment
            website_redirect_location=None,
            # Cache invalidation
            prune=True,
            # Metadata
            metadata={"project": "face-recognition", "deployed-by": "cdk"},
        )

        # Create a custom resource to copy and rename the file
        from aws_cdk import custom_resources as cr

        # Custom resource to handle file renaming
        rename_file_provider = cr.Provider(
            self, "RenameFileProvider", on_event_handler=self._create_rename_lambda()
        )

        rename_file_resource = CustomResource(
            self,
            "RenameFileResource",
            service_token=rename_file_provider.service_token,
            properties={
                "BucketName": self.frontend_bucket.bucket_name,
                "SourceKey": "frontend_test.html",
                "DestinationKey": "index.html",
                "DistributionId": self.distribution.distribution_id,
                "ApiGatewayUrl": api_gateway_url,
            },
        )

        # Ensure deployment happens before renaming
        rename_file_resource.node.add_dependency(self.deployment)

        # Outputs
        CfnOutput(
            self,
            "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="S3 bucket name for frontend hosting",
        )

        CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront distribution ID",
        )

        CfnOutput(
            self,
            "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront distribution domain name",
        )

        CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="Frontend application URL",
        )

    def _create_rename_lambda(self):
        """Create Lambda function for renaming files and updating API URL"""
        from aws_cdk import aws_lambda as lambda_

        return lambda_.Function(
            self,
            "RenameFileLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import boto3
import json
import urllib3

s3 = boto3.client('s3')
cloudfront = boto3.client('cloudfront')

def handler(event, context):
    try:
        props = event['ResourceProperties']
        bucket_name = props['BucketName']
        source_key = props['SourceKey']
        dest_key = props['DestinationKey']
        distribution_id = props['DistributionId']
        api_gateway_url = props['ApiGatewayUrl']
        
        if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
            # Copy and rename file
            copy_source = {'Bucket': bucket_name, 'Key': source_key}
            
            # Get the original file
            response = s3.get_object(Bucket=bucket_name, Key=source_key)
            content = response['Body'].read().decode('utf-8')
            
            # Update API URL in the content
            # Replace the mock API URL with the real API Gateway URL
            updated_content = content.replace(
                'http://localhost:8000',
                api_gateway_url
            ).replace(
                'const API_BASE_URL = \\'http://localhost:8000\\';',
                f'const API_BASE_URL = \\'{api_gateway_url}\\';'
            )
            
            # Upload the updated content as index.html
            s3.put_object(
                Bucket=bucket_name,
                Key=dest_key,
                Body=updated_content.encode('utf-8'),
                ContentType='text/html',
                CacheControl='max-age=86400'
            )
            
            # Create CloudFront invalidation
            cloudfront.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': 1,
                        'Items': ['/*']
                    },
                    'CallerReference': f'cdk-deployment-{context.aws_request_id}'
                }
            )
            
            # Delete the original file
            s3.delete_object(Bucket=bucket_name, Key=source_key)
            
        send_response(event, context, 'SUCCESS', {'Message': 'File renamed and API URL updated successfully'})
        
    except Exception as e:
        print(f'Error: {str(e)}')
        send_response(event, context, 'FAILED', {'Message': str(e)})

def send_response(event, context, status, data):
    response_body = {
        'Status': status,
        'Reason': f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': data
    }
    
    http = urllib3.PoolManager()
    response = http.request('PUT', event['ResponseURL'], 
                          body=json.dumps(response_body).encode('utf-8'),
                          headers={'Content-Type': 'application/json'})
"""
            ),
            timeout=Duration.minutes(5),
        )
