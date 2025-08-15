# OpenSearch Face Recognition System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-CDK-orange.svg)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-14+-green.svg)](https://nodejs.org/)

An enterprise-grade face recognition system built on Amazon OpenSearch Service, designed to overcome AWS Rekognition Collection limitations while providing better scalability and cost efficiency.

## 🎯 Key Features

- **Massive Scale Storage**: Support for billions of facial vectors
- **High-Performance Search**: Millisecond-level similarity search
- **Hybrid Search**: Combined vector + keyword search capabilities
- **Auto Scaling**: Automatic resource adjustment based on load
- **Cost Optimized**: ~40% cost savings compared to Rekognition Collection
- **Complete Migration**: Migration tools from existing Rekognition Collections

## 🏗️ System Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Frontend  │───▶│ API Gateway  │───▶│ Lambda Functions│
└─────────────┘    └──────────────┘    └─────────────────┘
                                                │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
            ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
            │ OpenSearch  │              │  DynamoDB   │              │     S3      │
            │  (Vectors)  │              │ (Metadata)  │              │  (Images)   │
            └─────────────┘              └─────────────┘              └─────────────┘
                   ▲
                   │
            ┌─────────────┐
            │ Rekognition │
            │ (Features)  │
            └─────────────┘
```

### Core Components

- **OpenSearch Service**: Store and search facial vectors
- **AWS Rekognition**: Extract facial feature vectors
- **DynamoDB**: Store facial metadata and user information
- **S3**: Store original image files
- **Lambda Functions**: Process face indexing and search requests
- **API Gateway**: Provide RESTful API interface

## 🚀 Quick Start

### Prerequisites

- **Node.js** >= 14.x
- **Python** >= 3.8
- **AWS CLI** configured
- **CDK CLI** installed

```bash
npm install -g aws-cdk
```

### Installation and Deployment

1. **Clone the Repository**
```bash
git clone https://github.com/hc0830/opensearch-face-recognition.git
cd opensearch-face-recognition
```

2. **Quick Deployment**
```bash
make quickstart
```

Or deploy manually:

3. **Install Dependencies**
```bash
make install
```

4. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env file to set your AWS account ID and other configurations
```

5. **Build and Deploy**
```bash
make build
make bootstrap  # Required for first deployment
make deploy
```

### Verify Deployment

```bash
make info  # View deployment information
make test-api API_URL=https://your-api-gateway-url  # Test API
```

## 📖 API Documentation

### Index Face

```bash
POST /faces
Content-Type: application/json

{
  "image": "base64_encoded_image",
  "user_id": "user123",
  "collection_id": "default",
  "metadata": {
    "name": "John Doe",
    "department": "Engineering"
  }
}
```

### Search Faces

```bash
POST /search
Content-Type: application/json

{
  "search_type": "by_image",
  "image": "base64_encoded_image",
  "collection_id": "default",
  "max_faces": 10,
  "similarity_threshold": 0.8
}
```

### Delete Face

```bash
DELETE /faces/{face_id}
```

### Get Statistics

```bash
GET /stats
```

## 💰 Cost Analysis

Monthly cost estimation for 10 million facial vectors:

| Service | Cost | Description |
|---------|------|-------------|
| OpenSearch Service | ~$500 | t3.small.search instance |
| Lambda Functions | ~$50 | Request processing |
| DynamoDB | ~$100 | Metadata storage |
| API Gateway | ~$30 | API calls |
| S3 | ~$20 | Image storage |
| **Total** | **~$700** | **~40% savings vs Rekognition Collection** |

## 🛠️ Development Guide

### Project Structure

```
opensearch-face-recognition/
├── 📁 stacks/                    # CDK infrastructure definitions
│   ├── opensearch_face_recognition_stack.py
│   ├── lambda_stack.py
│   ├── api_gateway_stack.py
│   └── monitoring_stack.py
├── 📁 lambda_functions/          # Lambda function code
│   ├── index_face/
│   ├── search_faces/
│   ├── delete_face/
│   └── batch_process/
├── 📁 layers/                    # Lambda layer dependencies
├── 📁 scripts/                   # Deployment and migration scripts
├── 📄 frontend_test.html         # Frontend test interface
├── 📄 Makefile                   # Build and deployment commands
└── 📄 requirements.txt           # Python dependencies
```

### Available Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make build         # Build project
make deploy        # Deploy to AWS
make destroy       # Destroy AWS resources
make test          # Run tests
make clean         # Clean build files
make lint          # Code linting
make format        # Code formatting
make migrate       # Migrate from Rekognition
```

## 🔧 Configuration Options

### Environment Variables

Configure the following variables in your `.env` file:

```bash
# AWS Configuration
CDK_DEFAULT_ACCOUNT=your-aws-account-id
CDK_DEFAULT_REGION=ap-southeast-1
AWS_PROFILE=default

# Environment Settings
ENVIRONMENT=dev  # dev, staging, prod

# OpenSearch Configuration
OPENSEARCH_INSTANCE_TYPE=t3.small.search
OPENSEARCH_INSTANCE_COUNT=1
OPENSEARCH_VOLUME_SIZE=100

# Lambda Configuration
LAMBDA_MEMORY_SIZE=1024
LAMBDA_TIMEOUT=300
LAMBDA_RESERVED_CONCURRENCY=10
```

## 📊 Monitoring and Operations

### CloudWatch Dashboard
- System performance metrics
- API call statistics
- Error rate monitoring
- Cost tracking

### Alert Configuration
- High error rate alerts
- Performance anomaly alerts
- Cost threshold alerts

### Log Management
- Lambda function logs
- API Gateway access logs
- OpenSearch query logs

## 🔄 Migration Guide

### Migrating from Rekognition Collection

1. **List Existing Collections**
```bash
make migrate  # List all Collections
```

2. **Migrate Specific Collection**
```bash
python scripts/migrate_from_rekognition.py --collection-id your-collection-id
```

3. **Verify Migration Results**
```bash
python scripts/test_api.py --verify-migration
```

## 🧪 Testing

### Unit Tests
```bash
make test
```

### API Testing
```bash
make test-api API_URL=https://your-api-gateway-url
```

### Frontend Testing
Open the `frontend_test.html` file directly for visual testing.

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter issues or have questions:

1. Check [Issues](https://github.com/hc0830/opensearch-face-recognition/issues)
2. Create a new Issue
3. Review project documentation

## 🔗 Related Links

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [OpenSearch Documentation](https://docs.aws.amazon.com/opensearch-service/)
- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)

---

**Note**: Please ensure proper AWS credentials and permissions are configured before deployment.
