# OpenSearch Face Recognition System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-CDK-orange.svg)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-24+-green.svg)](https://nodejs.org/)

**Language**: [中文](README.md) | [English](README_EN.md)

基于Amazon OpenSearch Service的企业级面部识别系统，用于替代AWS Rekognition Collection的限制，提供更好的扩展性和成本效益。

## 🎯 项目特点

- **大规模存储**: 支持数十亿级面部向量存储
- **高性能搜索**: 毫秒级相似度搜索
- **混合搜索**: 向量+关键词组合搜索
- **自动扩缩容**: 根据负载自动调整资源
- **成本优化**: 相比Rekognition Collection节省约40%
- **完整迁移**: 提供从Rekognition Collection的迁移工具

## 🏗️ 系统架构

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

### 核心组件

- **OpenSearch Service**: 存储和搜索面部向量
- **AWS Rekognition**: 提取面部特征向量
- **DynamoDB**: 存储面部元数据和用户信息
- **S3**: 存储原始图像文件
- **Lambda Functions**: 处理面部索引和搜索请求
- **API Gateway**: 提供RESTful API接口

## 🚀 快速开始

### 前置要求

- **Node.js** >= 24.x
- **Python** >= 3.12
- **AWS CLI** 已配置
- **CDK CLI** 已安装

```bash
npm install -g aws-cdk
```

### 安装和部署

1. **克隆项目**
```bash
git clone https://github.com/your-username/opensearch-face-recognition.git
cd opensearch-face-recognition
```

2. **快速部署**
```bash
make quickstart
```

或者手动部署：

3. **安装依赖**
```bash
make install
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，设置你的AWS账户ID和其他配置
```

5. **构建和部署**
```bash
make build
make bootstrap  # 首次部署需要
make deploy
```

### 验证部署

```bash
make info  # 查看部署信息
make test-api API_URL=https://your-api-gateway-url  # 测试API
```

## 📖 API 文档

### 索引面部

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

### 搜索面部

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

### 删除面部

```bash
DELETE /faces/{face_id}
```

### 获取统计信息

```bash
GET /stats
```

## 💰 成本分析

基于1000万面部向量的月度成本估算：

| 服务 | 成本 | 说明 |
|------|------|------|
| OpenSearch Service | ~$500 | t3.small.search实例 |
| Lambda Functions | ~$50 | 处理请求 |
| DynamoDB | ~$100 | 元数据存储 |
| API Gateway | ~$30 | API调用 |
| S3 | ~$20 | 图像存储 |
| **总计** | **~$700** | **相比Rekognition Collection节省约40%** |

## 🛠️ 开发指南

### 项目结构

```
opensearch-face-recognition/
├── 📁 stacks/                    # CDK基础设施定义
│   ├── opensearch_face_recognition_stack.py
│   ├── lambda_stack.py
│   ├── api_gateway_stack.py
│   └── monitoring_stack.py
├── 📁 lambda_functions/          # Lambda函数代码
│   ├── index_face/
│   ├── search_faces/
│   ├── delete_face/
│   └── batch_process/
├── 📁 layers/                    # Lambda层依赖
├── 📁 scripts/                   # 部署和迁移脚本
├── 📄 frontend_test.html         # 前端测试界面
├── 📄 Makefile                   # 构建和部署命令
└── 📄 requirements.txt           # Python依赖
```

### 可用命令

```bash
make help          # 显示所有可用命令
make install       # 安装依赖
make build         # 构建项目
make deploy        # 部署到AWS
make destroy       # 销毁AWS资源
make test          # 运行测试
make clean         # 清理构建文件
make lint          # 代码检查
make format        # 代码格式化
make migrate       # 从Rekognition迁移
```

## 🔧 配置选项

### 环境变量

在`.env`文件中配置以下变量：

```bash
# AWS配置
CDK_DEFAULT_ACCOUNT=your-aws-account-id
CDK_DEFAULT_REGION=ap-southeast-1
AWS_PROFILE=default

# 环境设置
ENVIRONMENT=dev  # dev, staging, prod

# OpenSearch配置
OPENSEARCH_INSTANCE_TYPE=t3.small.search
OPENSEARCH_INSTANCE_COUNT=1
OPENSEARCH_VOLUME_SIZE=100

# Lambda配置
LAMBDA_MEMORY_SIZE=1024
LAMBDA_TIMEOUT=300
LAMBDA_RESERVED_CONCURRENCY=10
```

## 📊 监控和运维

### CloudWatch Dashboard
- 系统性能指标
- API调用统计
- 错误率监控
- 成本追踪

### 告警配置
- 高错误率告警
- 性能异常告警
- 成本超限告警

### 日志管理
- Lambda函数日志
- API Gateway访问日志
- OpenSearch查询日志

## 🔄 迁移指南

### 从Rekognition Collection迁移

1. **列出现有Collections**
```bash
make migrate  # 列出所有Collections
```

2. **迁移特定Collection**
```bash
python scripts/migrate_from_rekognition.py --collection-id your-collection-id
```

3. **验证迁移结果**
```bash
python scripts/test_api.py --verify-migration
```

## 🧪 测试

### 单元测试
```bash
make test
```

### API测试
```bash
make test-api API_URL=https://your-api-gateway-url
```

### 前端测试
直接打开`frontend_test.html`文件进行可视化测试。

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果你遇到问题或有疑问：

1. 查看 [Issues](https://github.com/your-username/opensearch-face-recognition/issues)
2. 创建新的 Issue
3. 查看项目文档

## 🔗 相关链接

- [AWS CDK 文档](https://docs.aws.amazon.com/cdk/)
- [OpenSearch 文档](https://docs.aws.amazon.com/opensearch-service/)
- [AWS Rekognition 文档](https://docs.aws.amazon.com/rekognition/)

---

**注意**: 请确保在部署前正确配置AWS凭证和权限。
