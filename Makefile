# OpenSearch Face Recognition System Makefile
# 提供统一的构建、部署和管理命令

.PHONY: help install build deploy destroy test clean lint format bootstrap info migrate quickstart
.PHONY: step1 step2 step3 step4 deploy-steps status deploy-lambdas

# 默认目标
.DEFAULT_GOAL := help

# 环境变量
PYTHON := python3
PIP := pip3
CDK := cdk
AWS := aws
REGION := ap-southeast-1
ENVIRONMENT := dev

# 颜色定义
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

help: ## 显示帮助信息
	@echo "$(BLUE)OpenSearch Face Recognition System$(RESET)"
	@echo "$(BLUE)====================================$(RESET)"
	@echo ""
	@echo "$(GREEN)快速部署:$(RESET)"
	@echo "  $(YELLOW)make quickstart$(RESET)     # 一键部署整个系统"
	@echo "  $(YELLOW)make deploy-steps$(RESET)   # 分步骤部署"
	@echo ""
	@echo "$(GREEN)分步骤部署:$(RESET)"
	@echo "  $(YELLOW)make step1$(RESET)          # 步骤1: 准备OpenSearch环境"
	@echo "  $(YELLOW)make step2$(RESET)          # 步骤2: 迁移数据"
	@echo "  $(YELLOW)make step3$(RESET)          # 步骤3: 部署Lambda函数"
	@echo "  $(YELLOW)make step4$(RESET)          # 步骤4: 验证部署"
	@echo ""
	@echo "$(GREEN)基础命令:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## 安装依赖
	@echo "$(BLUE)安装Python依赖...$(RESET)"
	$(PIP) install -r requirements.txt
	@echo "$(BLUE)安装Node.js依赖...$(RESET)"
	npm install
	@echo "$(GREEN)✅ 依赖安装完成$(RESET)"

build: ## 构建项目
	@echo "$(BLUE)构建Lambda层...$(RESET)"
	mkdir -p layers/dependencies/python
	$(PIP) install -r requirements.txt -t layers/dependencies/python/
	@echo "$(GREEN)✅ 构建完成$(RESET)"

bootstrap: ## 初始化CDK环境
	@echo "$(BLUE)初始化CDK环境...$(RESET)"
	$(CDK) bootstrap aws://$(shell aws sts get-caller-identity --query Account --output text)/$(REGION)
	@echo "$(GREEN)✅ CDK环境初始化完成$(RESET)"

deploy: build ## 部署到AWS (使用CDK)
	@echo "$(BLUE)使用CDK部署到AWS...$(RESET)"
	$(CDK) deploy --all --require-approval never --app "python app_deploy.py"
	@echo "$(GREEN)✅ CDK部署完成$(RESET)"

# 分步骤部署命令
step1: ## 步骤1: 准备OpenSearch环境
	@echo "$(BLUE)步骤1: 准备OpenSearch环境$(RESET)"
	$(PYTHON) deployment_manager.py --action deploy --region $(REGION) --environment $(ENVIRONMENT)

step2: ## 步骤2: 迁移数据
	@echo "$(BLUE)步骤2: 从Rekognition迁移数据$(RESET)"
	$(PYTHON) -c "from deployment_manager import DeploymentManager; DeploymentManager('$(REGION)', '$(ENVIRONMENT)').step2_migrate_data()"

step3: ## 步骤3: 部署Lambda函数
	@echo "$(BLUE)步骤3: 部署Lambda函数$(RESET)"
	$(PYTHON) lambda_manager.py --region $(REGION) --environment $(ENVIRONMENT) --action deploy

step4: ## 步骤4: 验证部署
	@echo "$(BLUE)步骤4: 验证部署$(RESET)"
	$(PYTHON) -c "from deployment_manager import DeploymentManager; DeploymentManager('$(REGION)', '$(ENVIRONMENT)').step4_verify_deployment()"

deploy-steps: step1 step2 step3 step4 ## 执行完整的分步骤部署
	@echo "$(GREEN)🎉 分步骤部署完成!$(RESET)"

deploy-lambdas: ## 仅部署Lambda函数
	@echo "$(BLUE)部署Lambda函数...$(RESET)"
	$(PYTHON) lambda_manager.py --region $(REGION) --environment $(ENVIRONMENT) --action deploy
	@echo "$(GREEN)✅ Lambda函数部署完成$(RESET)"

status: ## 检查部署状态
	@echo "$(BLUE)检查部署状态...$(RESET)"
	$(PYTHON) deployment_manager.py --action status --region $(REGION) --environment $(ENVIRONMENT)

destroy: ## 销毁AWS资源
	@echo "$(RED)销毁AWS资源...$(RESET)"
	@echo "$(YELLOW)警告: 这将删除所有AWS资源!$(RESET)"
	@read -p "确认继续? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(CDK) destroy --all --force --app "python app_deploy.py"
	@echo "$(GREEN)✅ 资源销毁完成$(RESET)"

test: ## 运行测试
	@echo "$(BLUE)运行测试...$(RESET)"
	$(PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)✅ 测试完成$(RESET)"

clean: ## 清理构建文件
	@echo "$(BLUE)清理构建文件...$(RESET)"
	rm -rf cdk.out/
	rm -rf layers/dependencies/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "$(GREEN)✅ 清理完成$(RESET)"

lint: ## 代码检查
	@echo "$(BLUE)运行代码检查...$(RESET)"
	flake8 . --exclude=venv,node_modules,cdk.out,layers
	@echo "$(GREEN)✅ 代码检查完成$(RESET)"

format: ## 代码格式化
	@echo "$(BLUE)格式化代码...$(RESET)"
	black . --exclude="/(venv|node_modules|cdk\.out|layers)/"
	@echo "$(GREEN)✅ 代码格式化完成$(RESET)"

info: ## 显示部署信息
	@echo "$(BLUE)获取部署信息...$(RESET)"
	$(CDK) list --app "python app_deploy.py"
	@echo "$(GREEN)✅ 信息获取完成$(RESET)"

migrate: ## 从Rekognition迁移数据
	@echo "$(BLUE)从Rekognition迁移数据...$(RESET)"
	$(PYTHON) scripts/migrate_from_rekognition.py
	@echo "$(GREEN)✅ 数据迁移完成$(RESET)"

quickstart: install build bootstrap deploy ## 一键部署整个系统
	@echo "$(GREEN)🎉 快速部署完成!$(RESET)"
	@echo "$(BLUE)系统已成功部署到AWS$(RESET)"
	@echo "$(YELLOW)运行 'make status' 检查部署状态$(RESET)"

# API测试命令
test-api: ## 测试API (需要API_URL参数)
	@if [ -z "$(API_URL)" ]; then \
		echo "$(RED)错误: 请提供API_URL参数$(RESET)"; \
		echo "$(YELLOW)使用方法: make test-api API_URL=https://your-api-url$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)测试API: $(API_URL)$(RESET)"
	$(PYTHON) scripts/test_api.py --api-url $(API_URL)
	@echo "$(GREEN)✅ API测试完成$(RESET)"

# 开发辅助命令
dev-setup: install ## 开发环境设置
	@echo "$(BLUE)设置开发环境...$(RESET)"
	pre-commit install
	@echo "$(GREEN)✅ 开发环境设置完成$(RESET)"

logs: ## 查看Lambda函数日志
	@echo "$(BLUE)查看Lambda函数日志...$(RESET)"
	$(AWS) logs describe-log-groups --log-group-name-prefix "/aws/lambda/face-recognition" --region $(REGION)

# 监控命令
monitor: ## 监控系统状态
	@echo "$(BLUE)监控系统状态...$(RESET)"
	watch -n 30 'make status'

# WAF 相关命令
deploy-waf: ## 单独部署WAF (在API Gateway创建后)
	@echo "$(BLUE)部署WAF...$(RESET)"
	$(PYTHON) scripts/deploy_waf.py
	@echo "$(GREEN)✅ WAF部署完成$(RESET)"

enable-waf: ## 启用WAF并重新部署
	@echo "$(BLUE)启用WAF并重新部署...$(RESET)"
	ENABLE_WAF=true $(CDK) deploy --all --require-approval never --app "python app_deploy.py"
	@echo "$(GREEN)✅ WAF已启用$(RESET)"

disable-waf: ## 禁用WAF并重新部署
	@echo "$(BLUE)禁用WAF并重新部署...$(RESET)"
	ENABLE_WAF=false $(CDK) deploy --all --require-approval never --app "python app_deploy.py"
	@echo "$(GREEN)✅ WAF已禁用$(RESET)"
