# 整合部署指南

本文档介绍如何使用整合后的部署工具来管理 OpenSearch Face Recognition 系统。

## 🔧 整合的工具

### 1. 统一部署管理器 (`deployment_manager.py`)
整合了所有分步骤的部署脚本，提供统一的部署和管理接口。

### 2. Lambda 函数管理器 (`lambda_manager.py`)
整合了所有 Lambda 函数的创建、更新和管理功能。

### 3. 增强的 Makefile
提供了统一的命令行接口，支持分步骤部署和完整部署。

## 🚀 快速开始

### 方式一：一键部署（推荐）
```bash
# 完整的一键部署
make quickstart
```

### 方式二：分步骤部署
```bash
# 步骤1：准备OpenSearch环境
make step1

# 步骤2：迁移数据
make step2

# 步骤3：部署Lambda函数
make step3

# 步骤4：验证部署
make step4

# 或者一次性执行所有步骤
make deploy-steps
```

### 方式三：使用CDK部署
```bash
# 传统的CDK部署方式
make install
make build
make bootstrap
make deploy
```

## 📋 可用命令

### 快速部署命令
- `make quickstart` - 一键部署整个系统
- `make deploy-steps` - 分步骤部署
- `make deploy` - 使用CDK部署
- `make deploy-lambdas` - 仅部署Lambda函数

### 分步骤命令
- `make step1` - 步骤1: 准备OpenSearch环境
- `make step2` - 步骤2: 迁移数据
- `make step3` - 步骤3: 部署Lambda函数
- `make step4` - 步骤4: 验证部署

### 管理命令
- `make status` - 检查部署状态
- `make info` - 显示部署信息
- `make logs` - 查看Lambda函数日志
- `make monitor` - 监控系统状态

### 开发命令
- `make install` - 安装依赖
- `make build` - 构建项目
- `make test` - 运行测试
- `make lint` - 代码检查
- `make format` - 代码格式化
- `make clean` - 清理构建文件

### 清理命令
- `make destroy` - 销毁AWS资源

## 🔍 部署状态检查

### 检查整体状态
```bash
make status
```

### 检查特定组件
```bash
# 检查OpenSearch域状态
python deployment_manager.py --action status --region ap-southeast-1 --environment dev

# 检查Lambda函数
aws lambda list-functions --region ap-southeast-1 --query 'Functions[?contains(FunctionName, `face-recognition`)].FunctionName'

# 检查DynamoDB表
aws dynamodb list-tables --region ap-southeast-1 --query 'TableNames[?contains(@, `face-recognition`)]'
```

## 🛠️ 高级用法

### 自定义环境和区域
```bash
# 部署到不同环境
make deploy ENVIRONMENT=prod

# 部署到不同区域
make deploy REGION=us-east-1

# 组合使用
make deploy REGION=us-east-1 ENVIRONMENT=staging
```

### 使用部署管理器
```bash
# 直接使用部署管理器
python deployment_manager.py --region ap-southeast-1 --environment dev --action deploy

# 检查状态
python deployment_manager.py --region ap-southeast-1 --environment dev --action status

# 清理资源
python deployment_manager.py --region ap-southeast-1 --environment dev --action cleanup
```

### 使用Lambda管理器
```bash
# 部署所有Lambda函数
python lambda_manager.py --region ap-southeast-1 --environment dev --action deploy
```

## 📊 部署流程详解

### 步骤1：准备OpenSearch环境
- 检查OpenSearch域状态
- 验证域端点可用性
- 确认域处于就绪状态

### 步骤2：迁移数据
- 检查Rekognition Collection是否存在
- 获取现有面部数据
- 迁移数据到OpenSearch（如果需要）

### 步骤3：部署Lambda函数
- 创建或更新Lambda函数
- 配置环境变量
- 设置IAM权限

### 步骤4：验证部署
- 检查所有AWS资源状态
- 验证服务连通性
- 确认系统正常运行

## 🔧 故障排除

### 常见问题

#### 1. OpenSearch域不可用
```bash
# 检查域状态
aws opensearch describe-domain --domain-name face-recognition-search --region ap-southeast-1

# 等待域就绪
make step1
```

#### 2. Lambda函数部署失败
```bash
# 检查IAM角色
aws iam get-role --role-name FaceRecognitionLambdaRole

# 重新部署Lambda函数
make deploy-lambdas
```

#### 3. CDK部署失败
```bash
# 清理并重新部署
make clean
make build
make deploy
```

### 日志查看
```bash
# 查看Lambda函数日志
make logs

# 查看特定函数日志
aws logs tail /aws/lambda/face-recognition-index --region ap-southeast-1 --follow
```

## 📈 监控和维护

### 持续监控
```bash
# 启动监控（每30秒检查一次状态）
make monitor
```

### 定期检查
```bash
# 每日状态检查
make status

# 每周完整验证
make step4
```

## 🔄 更新和升级

### 更新Lambda函数
```bash
# 更新所有Lambda函数
make deploy-lambdas

# 或使用CDK更新
make deploy
```

### 更新基础设施
```bash
# 使用CDK更新
make deploy

# 或分步骤更新
make deploy-steps
```

## 📝 最佳实践

1. **使用版本控制**: 所有配置更改都应该通过Git管理
2. **环境隔离**: 使用不同的环境（dev/staging/prod）
3. **定期备份**: 定期备份DynamoDB数据和S3内容
4. **监控告警**: 设置CloudWatch告警监控系统健康状态
5. **安全审计**: 定期检查IAM权限和安全组配置

## 🆘 获取帮助

```bash
# 查看所有可用命令
make help

# 查看部署管理器帮助
python deployment_manager.py --help

# 查看Lambda管理器帮助
python lambda_manager.py --help
```

## 📚 相关文档

- [README.md](README.md) - 项目总体介绍
- [DEPLOYMENT.md](DEPLOYMENT.md) - 详细部署说明
- [DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md) - 部署就绪性评估
- [GITHUB_SETUP.md](GITHUB_SETUP.md) - GitHub Actions 设置
