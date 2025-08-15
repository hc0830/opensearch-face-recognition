# 部署指南

## 🔐 安全配置

### 1. 环境变量配置

**重要**: 永远不要将包含真实AWS账户信息的`.env`文件提交到版本控制系统。

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的实际配置
nano .env
```

需要配置的关键变量：
- `CDK_DEFAULT_ACCOUNT`: 你的AWS账户ID
- `CDK_DEFAULT_REGION`: 部署区域
- `ALERT_EMAIL`: 接收告警的邮箱地址

### 2. AWS凭证配置

确保AWS CLI已正确配置：

```bash
# 配置AWS凭证
aws configure

# 或使用AWS SSO
aws sso login --profile your-profile
```

### 3. 权限要求

部署此项目需要以下AWS权限：
- CloudFormation: 完整权限
- OpenSearch: 完整权限
- Lambda: 完整权限
- API Gateway: 完整权限
- DynamoDB: 完整权限
- S3: 完整权限
- IAM: 创建角色和策略的权限
- Rekognition: 使用权限

## 🚀 部署步骤

### 快速部署

```bash
# 一键部署（推荐）
make quickstart
```

### 手动部署

```bash
# 1. 安装依赖
make install

# 2. 构建项目
make build

# 3. 首次部署需要bootstrap
make bootstrap

# 4. 部署所有堆栈
make deploy
```

### 验证部署

```bash
# 查看部署状态
make info

# 测试API（需要先获取API Gateway URL）
make test-api API_URL=https://your-api-gateway-url
```

## 🌍 多区域部署

### 支持的区域

- `us-east-1` (美国东部)
- `us-west-2` (美国西部)
- `eu-west-1` (欧洲)
- `ap-southeast-1` (新加坡)
- `ap-northeast-1` (东京)

### 区域配置

在`.env`文件中设置：

```bash
CDK_DEFAULT_REGION=ap-southeast-1  # 你选择的区域
AWS_REGION=ap-southeast-1
```

## 🔧 环境管理

### 开发环境

```bash
ENVIRONMENT=dev
OPENSEARCH_INSTANCE_TYPE=t3.small.search
OPENSEARCH_INSTANCE_COUNT=1
```

### 生产环境

```bash
ENVIRONMENT=prod
OPENSEARCH_INSTANCE_TYPE=m6g.large.search
OPENSEARCH_INSTANCE_COUNT=3
```

## 📊 成本优化

### 开发环境成本优化

- 使用`t3.small.search`实例
- 设置较小的存储卷
- 使用按需计费

### 生产环境成本优化

- 使用预留实例
- 启用数据生命周期管理
- 配置自动扩缩容

## 🔄 迁移现有数据

### 从Rekognition Collection迁移

```bash
# 列出现有Collections
python scripts/migrate_from_rekognition.py --list-only

# 迁移特定Collection
python scripts/migrate_from_rekognition.py --collection-id your-collection-id
```

## 🧪 测试和验证

### 功能测试

```bash
# 运行所有测试
make test

# API功能测试
python scripts/test_api.py --api-url https://your-api-gateway-url
```

### 前端测试

1. 打开`frontend_test.html`
2. 配置API端点
3. 上传测试图片
4. 验证搜索功能

## 🚨 故障排除

### 常见问题

1. **CDK Bootstrap失败**
   ```bash
   # 确保有足够权限
   aws sts get-caller-identity
   ```

2. **OpenSearch部署失败**
   ```bash
   # 检查VPC配置和可用区
   aws ec2 describe-availability-zones
   ```

3. **Lambda函数超时**
   ```bash
   # 增加超时时间和内存
   LAMBDA_TIMEOUT=300
   LAMBDA_MEMORY_SIZE=1024
   ```

### 日志查看

```bash
# CloudWatch日志
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/face-recognition"

# API Gateway日志
aws logs describe-log-groups --log-group-name-prefix "API-Gateway-Execution-Logs"
```

## 🗑️ 清理资源

### 删除所有资源

```bash
# 销毁所有CDK堆栈
make destroy

# 确认删除
aws cloudformation list-stacks --stack-status-filter DELETE_COMPLETE
```

### 手动清理

某些资源可能需要手动删除：
- S3存储桶中的对象
- OpenSearch域快照
- CloudWatch日志组

## 📞 支持

如遇到部署问题：

1. 检查AWS凭证和权限
2. 查看CloudFormation事件日志
3. 检查环境变量配置
4. 参考故障排除部分

---

**安全提醒**: 
- 定期轮换AWS访问密钥
- 使用最小权限原则
- 启用CloudTrail审计
- 定期检查成本和使用情况
