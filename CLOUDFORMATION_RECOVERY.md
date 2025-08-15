# CloudFormation 堆栈恢复指南

## 🎯 当前状态

### 问题描述
CDK部署失败，CloudFormation堆栈处于`UPDATE_ROLLBACK_COMPLETE`状态：

```
ToolkitError: The stack named OpenSearchFaceRecognition-Prod-API failed to deploy: 
UPDATE_ROLLBACK_FAILED: Resource handler returned message: 
"Invalid Resource identifier specified (Service: ApiGateway, Status Code: 404, Request ID: 29ca5b84-c3d2-4991-9828-48aa47a4fa40)"
```

### 根本原因
1. **资源状态不一致**: CloudFormation认为某些API Gateway资源存在，但实际已被手动删除
2. **堆栈漂移**: 手动操作导致CloudFormation模板与实际资源状态不匹配
3. **回滚失败**: 尝试恢复不存在的资源导致回滚失败

## ✅ 已执行的恢复操作

### 1. 继续回滚操作
```bash
aws cloudformation continue-update-rollback \
  --stack-name OpenSearchFaceRecognition-Prod-API \
  --resources-to-skip FaceRecognitionApihealthGET1BF30461
```

### 2. 当前堆栈状态
- **状态**: `UPDATE_ROLLBACK_COMPLETE` ✅
- **API Gateway ID**: `deheoet323` (仍然存在)
- **端点URL**: `https://deheoet323.execute-api.ap-southeast-1.amazonaws.com/prod/`

## 🚀 推荐的解决方案

### 选项1: 重新部署 (推荐)
由于堆栈现在处于稳定状态，GitHub Actions应该能够重新尝试部署：

1. **触发新的部署**
   - 推送新的提交到main分支
   - 或者手动重新运行GitHub Actions

2. **CDK将执行**
   - 检测堆栈状态
   - 创建缺失的资源
   - 更新现有资源

### 选项2: 手动修复堆栈漂移
如果重新部署仍然失败，可以手动修复：

```bash
# 1. 检测堆栈漂移
aws cloudformation detect-stack-drift \
  --stack-name OpenSearchFaceRecognition-Prod-API

# 2. 查看漂移详情
aws cloudformation describe-stack-resource-drifts \
  --stack-name OpenSearchFaceRecognition-Prod-API

# 3. 导入缺失的资源（如果需要）
aws cloudformation create-change-set \
  --stack-name OpenSearchFaceRecognition-Prod-API \
  --change-set-name import-missing-resources \
  --change-set-type IMPORT \
  --resources-to-import file://resources-to-import.json
```

### 选项3: 删除并重新创建堆栈
如果其他方法都失败，可以删除API堆栈并重新创建：

⚠️ **注意**: 这将导致API端点临时不可用

```bash
# 1. 删除API堆栈
aws cloudformation delete-stack \
  --stack-name OpenSearchFaceRecognition-Prod-API

# 2. 等待删除完成
aws cloudformation wait stack-delete-complete \
  --stack-name OpenSearchFaceRecognition-Prod-API

# 3. 重新部署
cdk deploy OpenSearchFaceRecognition-Prod-API
```

## 📋 验证步骤

### 部署成功后验证
```bash
# 1. 检查堆栈状态
aws cloudformation describe-stacks \
  --stack-name OpenSearchFaceRecognition-Prod-API \
  --query 'Stacks[0].StackStatus'

# 2. 测试API端点
curl "https://deheoet323.execute-api.ap-southeast-1.amazonaws.com/prod/health"
curl "https://deheoet323.execute-api.ap-southeast-1.amazonaws.com/prod/stats"
curl "https://deheoet323.execute-api.ap-southeast-1.amazonaws.com/prod/collections"

# 3. 验证CORS
curl -X OPTIONS "https://deheoet323.execute-api.ap-southeast-1.amazonaws.com/prod/health" \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: GET"
```

## 🔧 预防措施

### 避免未来的堆栈漂移
1. **统一资源管理**: 所有资源通过CDK管理，避免手动操作
2. **环境隔离**: 使用不同的AWS账户或区域隔离环境
3. **监控堆栈状态**: 定期检查CloudFormation堆栈健康状况
4. **备份策略**: 定期导出CloudFormation模板作为备份

### 最佳实践
1. **基础设施即代码**: 所有变更通过代码管理
2. **版本控制**: 使用Git管理所有基础设施变更
3. **自动化部署**: 使用CI/CD管道进行部署
4. **测试环境**: 在测试环境中验证变更后再应用到生产环境

## 📊 当前资源状态

### API Gateway (deheoet323)
- ✅ `/` - 根资源
- ✅ `/faces` - 面部管理
- ✅ `/faces/{face_id}` - 特定面部操作
- ✅ `/search` - 面部搜索
- ❌ `/health` - 需要重新创建
- ❌ `/stats` - 需要重新创建
- ❌ `/collections` - 需要重新创建

### Lambda函数
- ✅ CDK管理的核心函数 (Index, Search, Delete, Batch)
- ✅ CDK管理的新函数 (Stats, Collections, Health)
- ✅ 所有函数都已正确部署

## 🎯 下一步行动

### 立即行动
1. **重新触发GitHub Actions部署**
2. **监控部署进度**
3. **验证所有端点功能**

### 如果部署仍然失败
1. **检查具体错误信息**
2. **考虑使用选项2或选项3**
3. **联系AWS支持（如果需要）**

---

**恢复完成时间**: 2025-08-15 17:50 UTC  
**堆栈状态**: ✅ UPDATE_ROLLBACK_COMPLETE (稳定)  
**推荐行动**: 重新触发GitHub Actions部署
