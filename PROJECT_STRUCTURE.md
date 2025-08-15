# 项目清理后结构

## 📁 主要目录结构

```
opensearch-face-recognition/
├── 📄 核心文件
│   ├── README.md                 # 项目说明
│   ├── requirements.txt          # Python依赖
│   ├── package.json             # Node.js依赖
│   ├── .env                     # 环境变量
│   └── .gitignore              # Git忽略文件
│
├── 📁 前端文件
│   └── frontend_test.html       # 前端测试页面
│
├── 📁 Lambda函数
│   └── lambda_functions/        # Lambda函数代码
│
├── 📁 CDK部署
│   ├── stacks/                  # CDK堆栈定义
│   ├── layers/                  # Lambda层
│   └── cdk.json                # CDK配置
│
├── 📁 脚本工具
│   └── scripts/                 # 实用脚本
│
├── 📁 Python环境
│   └── venv/                    # Python虚拟环境
│
└── 📁 归档文件
    └── archive/
        ├── test_scripts/        # 测试脚本
        ├── deployment_scripts/  # 部署脚本
        ├── fix_scripts/        # 修复脚本
        ├── documentation/      # 历史文档
        └── temp_files/         # 临时文件
```

## 🎯 清理完成的内容

### ✅ 保留的核心文件
- 项目配置文件 (package.json, requirements.txt, .env)
- 前端界面 (frontend_test.html)
- Lambda函数代码
- CDK部署配置
- Python虚拟环境

### 📦 归档的文件
- 所有测试脚本 → archive/test_scripts/
- 部署和配置脚本 → archive/deployment_scripts/
- 修复和诊断脚本 → archive/fix_scripts/
- 历史文档 → archive/documentation/
- 临时文件和日志 → archive/temp_files/

### 🗑️ 删除的内容
- 空的缓存目录
- 临时构建文件
- 重复的虚拟环境

## 🚀 当前系统状态

系统已成功迁移到OpenSearch架构：
- ✅ OpenSearch用于向量搜索
- ✅ Rekognition用于特征提取
- ✅ DynamoDB存储元数据
- ✅ S3存储图像文件
- ✅ 前端完全正常工作

## 📋 如何使用

1. **启动前端**: 直接打开 `frontend_test.html`
2. **查看归档**: 需要时可在 `archive/` 目录找到历史脚本
3. **部署更新**: 使用CDK进行基础设施更新
4. **开发调试**: 激活venv环境进行开发

项目现在结构清晰，易于维护！
